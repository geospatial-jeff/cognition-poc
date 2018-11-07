import math
from osgeo import gdal
import functools
from multiprocessing import Pool

from cognition.pygdal.geometry import Polygon, wktBoundBox
from cognition.pygdal.raster import RasterDataset
from cognition.pygdal.config import pygdal_config



class COG(RasterDataset):

    """Represents a Cloud Optimized Geotiff"""

    @staticmethod
    @pygdal_config.log_operation
    def read_block(ds, offset, fname):
        gdal.Translate(fname, ds.ds, srcWin=offset)
        return fname


    def __init__(self, ds, id=None):
        RasterDataset.__init__(self, ds, id)

    def offsets(self, filter=None):
        """
        Generator to calculate offsets for each block
        Pass an extent of form (xmin, xmax, ymin, ymax) to `filter` to only return offsets within extent
        """
        def wrapper():
            xsize, ysize = self.blocksize
            shape = self.shape
            nxblocks = int(math.floor(shape[0] + xsize - 1) / xsize)
            nyblocks = int(math.floor(shape[1] + ysize - 1) / ysize)
            for yblock in range(nyblocks):
                yoff = yblock * ysize
                if yblock < nyblocks - 1:
                    block_ny = ysize
                else:
                    block_ny = shape[1] - (yblock * ysize)
                for xblock in range(nxblocks):
                    xoff = xblock * xsize
                    if xblock < (nxblocks - 1):
                        block_nx = xsize
                    else:
                        block_nx = shape[0] - (xblock * xsize)
                    yield (xoff, yoff, block_nx, block_ny)
        if not filter:
            return wrapper()
        else:
            extent_poly = Polygon(wktBoundBox(filter))
            cog_poly = Polygon(wktBoundBox(self.extent))
            if cog_poly.Intersects(extent_poly.geom):
                intersection = cog_poly.Intersection(extent_poly.geom)
                env = intersection.Envelope()
                # tl = [env[0], env[3]]
                tl_pix = [(self.tlx - env[0])/self.xres, (self.tly - env[3])/self.yres]
                br_pix = [(env[1] - self.tlx)/self.xres, (self.tly - env[2])/self.yres]
                for item in wrapper():
                    if tl_pix[0] <= item[0] <= br_pix[0] and tl_pix[1] <= item[1] <= br_pix[1]:
                        yield item

    def blocks(self, offsets=None):
        """Uses gdal.Translate to generate a VRT of each offset"""
        if not offsets:
            offsets = self.offsets()
        for item in offsets:
            block = self.read_block(self, item)
            yield block

    def embed(self, pixel_func, bands, offsets=None, multi=False, **kwargs):
        """Embeds a pixel function in all blocks"""
        blocks = list(self.blocks(offsets=offsets))
        if multi:
            m = Pool()
            embed_list = m.map(functools.partial(_embed, pixel_func=pixel_func, bands=bands, **kwargs), blocks)
            return embed_list
        embed_list = []
        for item in self.blocks(offsets=offsets):
            embedded = item.EmbedFunction(pixel_func, bands, **kwargs)
            embed_list.append(embedded)
        return embed_list

def _embed(ds, pixel_func, bands, **kwargs):
    return RasterDataset(gdal.Open(ds)).EmbedFunction(pixel_func, bands, **kwargs)

