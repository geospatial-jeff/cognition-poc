from cognition.pygdal.raster import RasterDataset
import os
from osgeo import gdal

in_dir = '/home/slingshot/Documents/Cognition/cognition-poc/testdata/proj'
out_dir = '/home/slingshot/Documents/Cognition/cognition-poc/testdata/compressed'

for item in os.listdir(in_dir):
    ds = gdal.Open(os.path.join(in_dir, item))
    out_ds = gdal.Translate(os.path.join(out_dir, item), ds, creationOptions=["COMPRESS=DEFLATE", "ZLEVEL=9", "PREDICTOR=2", "NUM_THREADS=ALL_CPUS"])
    out_ds = None