from osgeo import osr, ogr
import json
import cognition.pygdal as pg

class GeometryBase(object):

    def __init__(self, data, type):
        self.gtype = type
        self.geom = createGeom(data, type)

    def Reproject(self, in_epsg, out_epsg):
        """
        Method to reproject a geometry from one EPSG to another
        :param in_epsg: Initial EPSG of geometry.
        :param out_epsg: Desired output EPSG.
        :return: Geometry class containing the reprojected geometry.
        """
        transform = createTransformer(in_epsg, out_epsg)
        proj_geom = self.geom.Clone()
        proj_geom.Transform(transform)
        return pg.OpenGeometry(proj_geom, self.gtype)

    def ReprojectFast(self, transformer):
        """
        Optimized method for the bulk reprojection and on-the-fly reprojection of geometries.  Allows the user to pass
        in an osr.CoordinateTransformation() object which avoids recreating the object in each call (see Reproject).  This method
        is exponentially faster than Reproject() when used in a for loop and should be used when speed is a concern.

        :param transformer: osr.CoordinateTransformation() object determining the projection.  The function createTransformer()
                            provides an easy way of generating an osr.CoordinateTransformation() object.
        :return: Geometry class containing the reprojected geometry
        """
        proj_geom = self.geom.Clone()
        proj_geom.Transform(transformer)
        return pg.OpenGeometry(proj_geom, self.gtype)

    def Valid(self):
        """
        Method to check if geometry is valid.  A geometry is invalid if it breaks basic topology rules.
        :return: Boolean (True/False)
        """
        return self.geom.IsValid()

    def Envelope(self):
        """
        Method to return the extent of a geometry in the standard GDAL representation (xmin,xmax,ymin,ymax)
        :return: Tuple of format (xmin,xmax,ymin,ymax) indicating the extent of the geometry.
        """
        return self.geom.GetEnvelope()

    def SpatialReference(self):
        """
        Method to retrieve the projection of the geometry.  Projection information is typically not stored
        at the geometry level, so this method may not be used very much.
        :return: osr.SpatialReference() object containing the projection of the geometry.
        """
        return self.geom.GetSpatialReference()

    def AssignSpatialReference(self, epsg):
        """
        Method to assign a projection to the geometry.  This does not reproject the geometry, just assigns a reference system
        to the geometry (like updating metadata).
        :param epsg: EPSG of projection to embed into geometry.
        :return: Geometry with embedded projection.
        """
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        self.geom.AssignSpatialReference(srs)

    def Distance(self, geom1):
        """
        Method to calculate the distance between the Geometry class and an external geometry (either ogr.Geometry or Geometry class).
        Need to add scale factor support.
        :param geom1: Second geometry to calculate distance to.  May be either ogr.Geometry() or Geometry class
        :return: Distance between two geometries expressed in native units of the input projection
        """
        #Handle for ogr.Geometry as input
        if type(geom1) == ogr.Geometry:
            return self.geom.Distance(geom1)
        else:
            #Handle for a geometry class as input
            return self.geom.Distance(geom1.geom)

    def Centroid(self):
        """
        Method to calculate the centroid of a geometry.
        :return: Point  class with the centroid.
        """
        return Point(self.geom.Centroid())

    def BoundingBox(self):
        """
        Method to calculate the bounding box of a geometry.  Note this is different than Envelope(), which returns a tuple.
        :return: Geometry class containing geometry's bounding box.
        """
        return Polygon(wktBoundBox(self.Envelope()))

    def Touches(self, geom):
        """
        Geometric operator that checks if two geometries touch each other.
        :param geom: Second geometry to check against.
        :return: Boolean (True/False)
        """
        return self.geom.Touches(geom)

    def Buffer(self, dist):
        """
        Method to calculate the buffer of a geometry.
        :param dist: Buffer distance to apply.  Determines the width of the buffer.
        :return: Either Polygon or MultiPolygon class depending if output buffer intersects itself.
        """
        return pg.OpenGeometry(self.geom.Buffer(dist), self.gtype)

    def Union(self, geom):
        """
        Method to calculate the geometric union of two geometries.
        :param geom: Geometry to calculate union against
        :return: Either Polygon or MultiPolygon class depending if output geometry intersects itself.
        """
        return pg.OpenGeometry(self.geom.Union(geom), self.gtype)

    def Contains(self, geom):
        """
        Geometric operator that checks if the Geometry class contains a second geometry.
        :param geom: Geometry to check.
        :return: Boolean (True/False)
        """
        return self.geom.Contains(geom)

    def Difference(self, geom):
        return self.geom.Difference(geom)

    def SymmetricDifference(self, geom):
        return pg.OpenGeometry(self.geom.SymmetricDifference(geom), self.gtype)

    def Dimension(self):
        return self.geom.CoordinateDimension()

    def Intersects(self, geom):
        return self.geom.Intersects(geom)

    def Intersection(self, geom):
        return pg.OpenGeometry(self.geom.Intersection(geom), self.gtype)

    def Within(self, geom):
        return self.geom.Within(geom)

    def ExportToWkt(self):
        return self.geom.ExportToWkt()

    def ExportToJson(self):
        return self.geom.ExportToJson()

    def ExportToList(self):
        return geomToList(self.geom)

    def ExportToWkb(self):
        return self.geom.ExportToWkb()

    # def ExportToGdal(self, epsg):
    #     out_ds = rb.CreateVector(epsg, geom_type=self.gtype)
    #     lyr = out_ds.ds.GetLayer()
    #     feat = ogr.Feature(lyr.GetLayerDefn())
    #     feat.SetGeometry(self.geom)
    #     lyr.CreateFeature(feat)
    #     feat = None
    #     lyr = None
    #     return out_ds

    def ExportToGeom(self):
        return self.geom

    def ExportToISOWkb(self):
        return self.geom.ExportToIsoWkb()

    def ExportToISOWkt(self):
        return self.geom.ExportToIsoWkt()

    def ExportToKml(self):
        return self.geom.ExportToKML()

class _Dot(GeometryBase):

    def __init__(self, data, type):
        GeometryBase.__init__(self, data, type)

class _Segment(_Dot):

    def __init__(self, data, type):
        _Dot.__init__(self, data, type)

    def GeometryCount(self):
        return self.geom.GetGeometryCount()

    def ConvexHull(self):
        return self.geom.ConvexHull()

    def Simplify(self, tolerance):
        return pg.OpenGeometry(self.geom.Simplify(tolerance), self.gtype)

    def SimplifyPreserveTopology(self, tolerance):
        return pg.OpenGeometry(self.geom.SimplifyPreserveTopology(tolerance), self.gtype)

    def Perimeter(self):
        return self.geom.Boundary().Length()

class _Ring(_Segment):

    def __init__(self, data, type):
        _Segment.__init__(self, data, type)

    def HoleCount(self):
        if self.gtype == 'Polygon':
            return self.GeometryCount() - 1
        elif self.gtype == 'MultiPolygon':
            return sum([poly.GetGeometryCount() - 1 for poly in self.geom])

    def Area(self, scale=None, epsg=None):
        area = self.geom.Area()
        if scale:
            centroid = self.Centroid().Reproject(epsg, 4326).ExportToList()
            return scale(centroid, area)
        else:
            return area

class Point(_Dot):
    """
    All of the point geometry operations are covered in _Dot.  This class is here for consistency.
    """

    def __init__(self, data):
        GeometryBase.__init__(self, data, 'Point')


class Line(_Segment):

    def __init__(self, data):
        _Segment.__init__(self, data, 'LineString')


class Polygon(_Ring):

    def __init__(self, data):
        _Ring.__init__(self, data, 'Polygon')


class MultiPoint(_Dot):

    def __init__(self, data):
        GeometryBase.__init__(self, data, 'MultiPoint')

    def Explode(self):
        return [MultiPoint(point) for point in self.geom]


class MultiLine(_Segment):

    def __init__(self, data):
        _Segment.__init__(self, data, 'MultiLineString')

    def Explode(self):
        return [MultiPoint(point) for point in self.geom]


class MultiPolygon(_Ring):

    def __init__(self, data):
        _Ring.__init__(self, data, 'MultiPolygon')

    def Explode(self):
        return [Polygon(poly) for poly in self.geom]

    def CascadedUnion(self):
        cunion = self.geom.UnionCascaded()
        if cunion.GetGeometryName() == "POLYGON":
            return Polygon(cunion)
        else:
            return MultiPolygon(cunion)

def createGeom(data, type):
    base_list = [
        'POINT', 'MULTIPOINT', 'LINESTRING', 'MULTILINESTRING', 'POLYGON',
        'MULTIPOLYGON'
    ]
    if isinstance(data, str):
        if len([x for x in base_list if data.startswith(x)]) > 0:
            return ogr.CreateGeometryFromWkt(data)
        return ogr.CreateGeometryFromJson('''{}'''.format(data))
    elif isinstance(data, list):
        return listToGeom(type, data)
    elif isinstance(data, ogr.Geometry):
        return data
    return

def listToGeom(geom_type, coords):
    geoj = {"type": geom_type, "coordinates": coords}
    geom = ogr.CreateGeometryFromJson(json.dumps(geoj))
    return geom

def geomToList(geom):
    return json.loads(geom.ExportToJson())['coordinates']

def createTransformer(in_epsg, out_epsg):
    """
    Method to generate an ogr transformer to reproject geometry from one epsg to another
    :param in_epsg: Input epsg
    :param out_epsg: Output epsg to transform to
    :return: Transformer class (osr.CoordinateTransformation())
    """
    in_srs = osr.SpatialReference()
    in_srs.ImportFromEPSG(in_epsg)
    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(out_epsg)
    return osr.CoordinateTransformation(in_srs, out_srs)

def wktBoundBox(bounds):
    '''
    :param bounds: an extent tuple in the format (xmin,xmax,ymin,ymax)
    :return: A wkt string
    '''
    list = minMaxToFivePoints(bounds)
    return ogr.CreateGeometryFromWkt(createWKTPolygon(list))


def minMaxToFivePoints(points):
    '''
    :param points: a boinding box in one of the following formats:
    [xmin,xmax,ymin,ymax], [xmax,xmin,ymax,ymin]
    :return: a bounding box in the 5 point format
    '''
    return ([points[0], points[2]], [points[0], points[3]],
            [points[1], points[3]], [points[1],
                                     points[2]], [points[0], points[2]])

def createWKTPolygon(points):
    '''
    :param points: a list of points in a Polygon
    :return: a WKT Polygon string
    '''
    wkt = 'POLYGON (('
    for point in points:
        wkt = wkt + str(point[0]) + ' ' + str(point[1]) + ','
    return wkt[:-1] + '))'