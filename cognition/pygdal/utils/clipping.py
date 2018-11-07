from osgeo import gdal, ogr
import uuid

from cognition.pygdal.config import pygdal_config

def clip_wrapper(raster_data, vector_data, srs, **gdalwarp_opts):
    clip_list = []
    lyr = vector_data.GetLayer()
    for feat in lyr:
        clip = Clip(raster_data, feat, srs, **gdalwarp_opts)
        clip_list.append(clip)
    return clip_list

def create_clipper(geom, srs):
    fname = pygdal_config.tempfiles.gen_file('shp', 'clippers', str(uuid.uuid4().hex))
    out_ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(fname)
    out_lyr = out_ds.CreateLayer(fname, srs)
    out_feat = ogr.Feature(out_lyr.GetLayerDefn())
    out_feat.SetGeometry(geom)
    out_lyr.CreateFeature(out_feat)
    out_lyr = None
    out_ds = None
    return fname

@pygdal_config.log_operation
def Clip(raster_data, feat, srs, **gdalwarp_opts):
    fname = gdalwarp_opts.pop('fname')
    geom = feat.GetGeometryRef()
    clipper = create_clipper(geom, srs)
    gdal.Warp(fname, raster_data.ds, cutlineDSName=clipper, cropToCutline=True, format='VRT', **gdalwarp_opts)
    return fname