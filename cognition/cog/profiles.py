from osgeo import gdal
import math
from haversine import haversine


class COGBase(object):

    """Base class for creating COG profiles"""

    accepted = ["blocksize", "predictor", "compression", "predictor", "zlevel"]

    def __init__(self, ds):
        self.ds = ds

        #Must be set by user
        self.__blocksize = None
        self.__compression = None
        self.__predictor = None
        self.__zlevel = None

        #Best practice but may be changed with setters
        self.__bigtiff = "IF_SAFER"
        self.__num_threads = "ALL_CPUS"
        self.__resample = "LANCZOS"

        #Immutable (no setter) -- requirements of COG spec
        self.__tiled = "YES"
        self.__zoom = self.get_zoom()


    @property
    def predictor(self):
        return self.__predictor

    @predictor.setter
    def predictor(self, value):
        self.__predictor = value

    @property
    def compression(self):
        return self.__compression

    @compression.setter
    def compression(self, value):
        self.__compression = value

    @property
    def zlevel(self):
        return self.__zlevel

    @zlevel.setter
    def zlevel(self, value):
        self.__zlevel = value

    @property
    def blocksize(self):
        return self.__blocksize

    @blocksize.setter
    def blocksize(self, value):
        self.__blocksize = value

    @property
    def bigtiff(self):
        return self.__bigtiff

    @bigtiff.setter
    def bigtiff(self, value):
        self.__bigtiff = value

    @property
    def num_threads(self):
        return self.__num_threads

    @num_threads.setter
    def num_threads(self, value):
        self.__num_threads = value

    @property
    def resample(self):
        return self.__resample

    @resample.setter
    def resample(self, value):
        self.__resample = value

    @property
    def tiled(self):
        return self.__tiled

    @property
    def zoom(self):
        return self.__zoom

    def get_resolution(self):
        if self.ds.srs.is_geographic:
            extent = self.ds.extent
            left = (extent[0], (extent[2]+extent[3])/2)
            right = (extent[1], (extent[2]+extent[3])/2)
            top = ((extent[0]+extent[1])/2, extent[3])
            bottom = ((extent[0]+extent[1])/2, extent[2])
            return max(
                haversine(left, right) * 1000 / self.ds.shape[0],
                haversine(top, bottom) * 1000 / self.ds.shape[1]
            )
        else:
            return max(self.ds.xres, self.ds.yres)

    def get_zoom(self):
        return math.ceil(
            math.log((2 * math.pi * 6378137) /
                     (self.get_resolution() * 256), 2))

    def dumps(self):
        out_d = {}
        for item in self.accepted:
            out_d[item] = getattr(self, item)
        return out_d

    def overviews(self):
        shape = self.ds.shape
        overviews = []
        for i in range(1, self.zoom):
            overviews.append(2**i)
            if (shape[1] / 2**i) < int(self.blocksize) and (shape[0] / 2**i) < int(self.blocksize):
                break
        return overviews

    def creation_options(self):
        accepted = ["tiled", "blocksize", "num_threads", "bigtiff", "predictor", "zlevel"]
        creation_list = []
        for item in accepted:
            if item == "blocksize":
                creation_list.append(f"BLOCKXSIZE={getattr(self, item)}")
                creation_list.append(f"BLOCKYSIZE={getattr(self, item)}")
            else:
                creation_list.append(f"{item.upper()}={getattr(self, item)}")
        return creation_list

    def overview_opts(self):
        gdal.SetConfigOption('TILED_OVERVIEW', 'YES')
        gdal.SetConfigOption('GDAL_TIFF_OVR_BLOCKSIZE', self.blocksize)
        gdal.SetConfigOption('BLOCKXSIZE_OVERVIEW', self.blocksize)
        gdal.SetConfigOption('BLOCKYSIZE_OVERVIEW', self.blocksize)
        gdal.SetConfigOption('NUM_THREADS_OVERVIEW', 'ALL_CPUS')
        if self.compression:
            gdal.SetConfigOption('COMPRESS_OVERVIEW', self.compression)
        if self.predictor:
            gdal.SetConfigOption('PREDICTOR_OVERVIEW', self.predictor)
        if self.zlevel:
            gdal.SetConfigOption('ZLEVEL_OVERVIEW', self.zlevel)


class DefaultCOG(COGBase):

    def __init__(self, ds):
        COGBase.__init__(self, ds)

        self.blocksize = '512'
        self.set_predictor()
        self.set_compression()

    def set_predictor(self):
        if 'Int' in self.ds.bitdepth:
            self.predictor = '2'
        elif 'Float' in self.ds.bitdepth:
            self.predictor = '3'

    def set_compression(self):
        if self.ds.bitdepth is 'Byte':
            self.compression = 'JPEG'
        else:
            self.compression = 'DEFLATE'
            self.zlevel = '9'


