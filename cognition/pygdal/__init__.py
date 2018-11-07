from . import geometry, config

def OpenGeometry(in_data, type):
    if type == 'Point':
        return geometry.Point(in_data)
    elif type == 'LineString':
        return geometry.Line(in_data)
    elif type == 'Polygon':
        return geometry.Polygon(in_data)
    elif type == 'MultiPoint':
        return geometry.MultiPoint(in_data)
    elif type == 'MultiLine':
        return geometry.MultiLine(in_data)
    elif type == 'MultiPolygon':
        return geometry.MultiPolygon(in_data)


def SetConfigOption(key, value):
    """Set a configuration option and update configuration"""
    config.pygdal_config.SetConfigOption(key, value)
    config.pygdal_config.ReadConfig()

def logs():
    config.pygdal_config.logs()

def cleanup():
    config.pygdal_config.tempfiles.cleanup()