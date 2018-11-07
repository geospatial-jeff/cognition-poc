import numpy as np
def add_bands(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize,raster_ysize, buf_radius, gt, **kwargs):
    np.seterr(divide='ignore', invalid='ignore')
    red = in_ar[0].astype('float')
    nir = in_ar[1].astype('float')

    num = (nir - red)
    den = (nir + red)
    ndvi = np.nan_to_num(num/den).astype('Float32')
    np.clip(ndvi, np.min(ndvi), np.max(ndvi), out = out_ar)
