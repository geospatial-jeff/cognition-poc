import uuid

from cognition.pygdal.projection import SpatialRef

class Vector(object):

    def __init__(self, ds, id=None):
        self.ds = ds
        self.lyr = self.ds.GetLayer()
        self.srs = SpatialRef(self.ds, "vector")

        if not id:
            self.id = str(uuid.uuid4().hex)
        else:
            self.id = id

    @property
    def features(self):
        for feat in self.lyr:
            yield feat

    @property
    def geometries(self):
        for feat in self.features:
            yield feat.GetGeometryRef()

    @property
    def dtype(self):
        return self.lyr.GetGeomType()

    @property
    def fcount(self):
        return self.lyr.GetFeatureCount()