import uuid
from osgeo import gdal, osr, ogr
import multiprocessing
import os
import functools
import xml.etree.ElementTree as ET
import boto3

from cognition.pygdal.projection import SpatialRef
from cognition.pygdal.vector import Vector
from cognition.pygdal.geometry import Polygon
from cognition.pygdal.utils import clip_wrapper as clip
from cognition.pygdal.config import pygdal_config
from cognition.cog.profiles import DefaultCOG
from cognition.cog.validate import validate

gdal.SetConfigOption('GDAL_VRT_ENABLE_PYTHON', 'YES')

dtype = {
    1: 'Byte',
    2: 'UInt16',
    3: 'Int16',
    4: 'UInt32',
    5: 'Int32',
    6: 'Float32',
    7: 'Float64'
}

s3 = boto3.resource('s3')


class Raster(object):

    def __init__(self, ds, id=None):
        self.ds = ds
        self.srs = SpatialRef(self.ds, 'raster')
        if not id:
            self.id = str(uuid.uuid4().hex)
        else:
            self.id = os.path.splitext(os.path.split(id)[-1])[0]

    @property
    def bitdepth(self):
        return dtype[self.ds.GetRasterBand(1).DataType]

    @property
    def epsg(self):
        return self.srs.epsg

    @property
    def name(self):
        return 'tlx_{}__tly_{}__xres_{}__yres_{}__cols_{}__rows_{}__bands_{}__epsg_{}.tif'.format(self.tlx,
                                                                                                 self.tly,
                                                                                                 self.xres,
                                                                                                 self.yres,
                                                                                                 self.shape[0],
                                                                                                 self.shape[1],
                                                                                                 self.shape[2],
                                                                                                 self.epsg
                                                                                                 )

    @property
    def extent(self):
        gt = self.gt
        shape = self.shape
        return [gt[0], gt[0] + (gt[1] * shape[0]),
                gt[3] + (gt[5] * shape[1]), gt[3]]

    @property
    def xres(self):
        return self.gt[1]

    @property
    def yres(self):
        return abs(self.gt[5])

    @property
    def tlx(self):
        return self.gt[0]

    @property
    def tly(self):
        return self.gt[3]

    @property
    def shape(self):
        return (self.ds.RasterXSize, self.ds.RasterYSize, self.ds.RasterCount)

    @property
    def gt(self):
        return self.ds.GetGeoTransform()

    @property
    def filename(self):
        return self.ds.GetDescription()

    @property
    def nodatavalue(self):
        return self.ds.GetRasterBand(1).GetNoDataValue()

    @property
    def blocksize(self):
        return self.ds.GetRasterBand(1).GetBlockSize()

class RasterDataset(Raster):

    def __init__(self, ds, id=None):
        Raster.__init__(self, ds, id)

    @pygdal_config.log_operation
    def Reproject(self, out_srs, **kwargs):
        fname = kwargs.pop('fname')
        args = {'in': self.srs.srs}
        if type(out_srs) == int:
            args['out'] = 'EPSG: {}'.format(out_srs)
        elif type(out_srs) == osr.SpatialReference:
            args['out'] = out_srs
        elif type(out_srs) == SpatialRef:
            args['out'] = out_srs.srs
        warped = gdal.Warp(fname,
                           self.ds,
                           srcSRS=args['in'],
                           dstSRS=args['out'],
                           format='VRT',
                           **kwargs)
        return RasterDataset(warped, id=fname)

    @pygdal_config.log_operation
    def TileGrid(self, pixel_x, pixel_y, x_overlap=0, y_overlap=0, **kwargs):
        fname = kwargs.pop('fname')
        extent = self.extent
        width = extent[1] - extent[0]
        height = extent[3] - extent[2]
        step_x = float(pixel_x * self.xres)
        step_y = float(pixel_y * self.yres)
        rows = int(round(width / step_y))
        cols = int(round(height / step_x))

        out_ds = gdal.GetDriverByName('ESRI Shapefile').Create(fname, 0, 0, 0)
        out_lyr = out_ds.CreateLayer(fname, self.srs.srs, ogr.wkbPolygon)

        for col in range(cols):
            for row in range(rows):
                x = extent[0] + (col * step_x - cols * (x_overlap * self.xres))
                y = extent[3] - (row * step_y - row * (y_overlap * self.yres))
                xmax = x + step_x
                ymin = y - step_y
                poly = Polygon([[[x, y], [xmax, y], [xmax, ymin], [x, ymin], [x, y]]]).ExportToGeom()
                out_feat = ogr.Feature(out_lyr.GetLayerDefn())
                out_feat.SetGeometry(poly)
                out_lyr.CreateFeature(out_feat)
        out_lyr = None
        return Vector(out_ds)

    def Clip(self, vector_data, **gdalwarp_opts):
        clips = clip(self, vector_data.ds, self.srs.srs, **gdalwarp_opts)
        return ClipHandler(clips)

    @pygdal_config.log_operation
    def BboxClip(self, bbox, **gdaltranslate_opts): #xmin, xmax, ymin, ymax
        fname = gdaltranslate_opts.pop('fname')
        return RasterDataset(gdal.Translate(fname, self.ds, projWin=[bbox[0], bbox[3], bbox[1], bbox[2]], **gdaltranslate_opts))

    @pygdal_config.log_operation
    def Save(self, out_path, **gdaltranslate_opts):
        fname = gdaltranslate_opts.pop('fname')
        ext = 'GTiff'
        if out_path.endswith('.vrt'):
            ext = 'VRT'
        gdal.Translate(out_path, self.ds, format=ext, **gdaltranslate_opts)

    @pygdal_config.log_operation
    def Upload(self, prefix, name=None, **kwargs):
        upload_name = self.filename
        fname = kwargs.pop('fname')
        if '/vsimem/' not in upload_name:
            raise AttributeError("Can only call RasterDataset.Upload on files saved to the /vsimem/ filesystem")
        #Convert to .tif if its stored as a VRT (upload is usually the final step done locally)
        if self.filename.endswith('.vrt'):
            upload_name = os.path.splitext(fname)[0] + '.tif'
            self.Save(upload_name)
        #Finally upload the file
        vsimem_file = SimpleVSIMEMFile(upload_name)
        parts = prefix.split('/')
        bucket = parts[0]
        key = '/'.join(parts[1:])
        if not name:
            obj = s3.Object(bucket, os.path.join(key, self.name))
        else:
            obj = s3.Object(bucket, os.path.join(key, name))
        obj.put(Body=vsimem_file)


    @pygdal_config.log_operation
    def EmbedFunction(self, pixel_func, bands, out_depth=None, **kwargs):


        def get_function(func_string):
            if func_string.endswith('.py'):
                with open(func_string, 'r') as f:
                    return f.read()
            return func_string

        fname = kwargs.pop('fname')
        pixel_func = get_function(pixel_func)
        func_name = pixel_func.split('def')[-1].split('(')[0][1:]
        if not out_depth:
            out_bitdepth = self.bitdepth
        else:
            out_bitdepth = out_depth
        base_xml = f"""
        <VRTDataset rasterXSize="{self.shape[0]}" rasterYSize="{self.shape[1]}">
          <SRS>{self.srs.ExportToWkt()}</SRS>
          <GeoTransform>{str(self.gt)[1:-1]}</GeoTransform>
          <VRTRasterBand dataType="{out_bitdepth}" bands="1" subClass="VRTDerivedRasterBand">
            <PixelFunctionType>{func_name}</PixelFunctionType>
            <PixelFunctionLanguage>Python</PixelFunctionLanguage>
            <PixelFunctionCode><![CDATA[{pixel_func}]]>
            </PixelFunctionCode>
          </VRTRasterBand>
        </VRTDataset>
        """
        root = ET.fromstring(base_xml)
        rasterband = root.findall("./VRTRasterBand")[0]
        if len(kwargs) > 0:
            pixel_func_args = ET.SubElement(rasterband, "PixelFunctionArguments", kwargs)
        for band in bands:
            simple_source = ET.SubElement(rasterband, "SimpleSource")
            source_filename = ET.SubElement(simple_source, "SourceFilename", {"relativeToVRT": "1"})
            source_filename.text = self.filename
            source_band = ET.SubElement(simple_source, "SourceBand")
            source_band.text = str(band)
            source_properties = ET.SubElement(simple_source, "SourceProperties", {"RasterXSize": str(self.shape[0]),
                                                                                  "RasterYSize": str(self.shape[1]),
                                                                                  "DataType": self.bitdepth,
                                                                                  "BlockXSize": str(self.blocksize[0]),
                                                                                  "BlockYSize": str(self.blocksize[1])
                                                                                  })
            src_rect = ET.SubElement(simple_source, "SrcRect", {"xOff": "0",
                                                                "yOff": "0",
                                                                "xSize": str(self.shape[0]),
                                                                "ySize": str(self.shape[1])})
            dst_rect = ET.SubElement(simple_source, "DstRect", {"xOff": "0",
                                                                "yOff": "0",
                                                                "xSize": str(self.shape[0]),
                                                                "ySize": str(self.shape[1])})
        out_ds = RasterDataset(gdal.Open(ET.tostring(root)))
        # print(out_ds.filename)
        return out_ds

    @pygdal_config.log_operation
    def SplitBands(self, **kwargs):
        fname = kwargs.pop('fname')
        band_list = []
        for i in range(self.shape[2]):
            fname_band = os.path.splitext(fname)[0]+'_B{}.vrt'.format(i+1)
            band_list.append(RasterDataset(gdal.Translate(fname_band, self.ds, bandList=[i+1])))
        return band_list

    @pygdal_config.log_operation
    def Cogify(self, profile=DefaultCOG, **kwargs):

        class InvalidCOGException(Exception):
            pass

        fname = os.path.splitext(kwargs.pop('fname'))[0] + '.tif'
        profile = profile(self)

        #Transcoding
        temp_fname = '/vsimem/transcode/{}.tif'.format(str(uuid.uuid4().hex))
        gdal.Translate(temp_fname, self.ds, creationOptions=profile.creation_options())

        #Build overviews
        transcoded = gdal.Open(temp_fname)
        profile.overview_opts()
        transcoded.BuildOverviews(profile.resample, profile.overviews())

        #Create COG
        gdal.Translate(fname, transcoded, creationOptions=profile.creation_options()+['COPY_SRC_OVERVIEWS=YES'])
        out_cog = gdal.Open(fname)
        errors, details = validate(out_cog)
        if len(errors) == 0:
            return RasterDataset(out_cog)
        raise InvalidCOGException("The COG has the following errors: {}".format(errors))

class ClipHandler(object):

    def __init__(self, vrt_filepath_list):
        self.items = vrt_filepath_list

    def Save(self, out_dir, multi=False):

        if multi:
            m = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
            m.map(functools.partial(_save, out_dir=out_dir), self.items)
            return

        for item in self.items:
            _save(item, out_dir)

    def EmbedFunction(self, pixel_func, bands, multi=False, **kwargs):
        if multi:
            m = multiprocessing.Pool(multiprocessing.cpu_count()-1)
            flist = m.map(functools.partial(_embed, pixel_func=pixel_func, bands=bands, *kwargs), self.items)
            return flist
        flist = [_embed(item, pixel_func, bands, **kwargs) for item in self.items]
        return flist

    def Upload(self, prefix, name=None, multi=False):
        if multi:
            m = multiprocessing.Pool(multiprocessing.cpu_count()-1)
            m.map(functools.partial(_upload, out_dir=prefix, name=name), self.items)
        for file in self.items:
            RasterDataset(gdal.Open(file)).Upload(prefix, name=name)

def _upload(package, out_dir, name):
    ds = RasterDataset(gdal.Open(package), package)
    ds.Upload(out_dir, name=name)

def _save(package, out_dir):
    ds = RasterDataset(gdal.Open(package), package)
    ds.Save(os.path.join(out_dir, ds.name))


def _embed(vrt_path, pixel_func, bands, **kwargs):
    ds = RasterDataset(gdal.Open(vrt_path))
    fname = ds.EmbedFunction(pixel_func, bands, **kwargs)
    return fname

class BandStack(RasterDataset):


    def __init__(self, vrt_stack):
        ds = gdal.BuildVRT('/vsimem/bandstack/{}.vrt'.format(str(uuid.uuid4().hex)), [gdal.Open(x) for x in vrt_stack], separate=True)
        RasterDataset.__init__(self, ds)
        ds = None


class SimpleVSIMemFileError(Exception):
    """Unknown SimpleVSIMemFile error with VSI subsystem."""

class SimpleVSIMEMFile(object):
    def __init__(self, path):
        """Simple file-like object for reading out of a VSIMEM dataset.
        Params:
            path: /vsimem path to use
        """
        self._path = path
        self._size = gdal.VSIStatL(self._path).size
        self._check_error()
        self._pos = 0

    def __len__(self):
        """Length of the file."""
        return self._size

    def read(self, size=-1):
        """Read size bytes from the file.
        Params:
            size: Number of bytes to read.
        """
        length = len(self)
        if self._pos >= length:
            # No more data to read
            return b""

        if size == -1:
            # Set size to remainder of file
            size = length - self._pos
        else:
            # Limit size to remainder of file
            size = min(size, length - self._pos)

        # Open file
        vsif = gdal.VSIFOpenL(self._path, "r")
        self._check_error()
        try:
            # Seek to current position, read data, and update position
            gdal.VSIFSeekL(vsif, self._pos, 0)
            self._check_error()
            buf = gdal.VSIFReadL(1, size, vsif)
            self._check_error()
            self._pos += len(buf)

        finally:
            # Close file
            gdal.VSIFCloseL(vsif)
            self._check_error()

        return buf

    def seek(self, offset, whence=0):
        """Seek to position in file."""
        if whence == 0:
            # Seek from start of file
            self._pos = min(offset, len(self))
        elif whence == 1:
            # Seek from current position
            self._pos = min(max(0, self._pos + offset), len(self))
        elif whence == 2:
            # Seek from end of file
            self._pos = max(0, len(self) - offset)
        return self._pos

    def tell(self):
        """Tell current position in file."""
        return self._pos

    def _check_error(self):
        if gdal.VSIGetLastErrorNo() != 0:
            raise SimpleVSIMemFileError(gdal.VSIGetLastErrorMsg())