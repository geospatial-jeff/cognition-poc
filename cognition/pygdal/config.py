import os
import uuid
import shutil
import json

from osgeo import ogr, osr


class ConfigHandler(object):

    @classmethod
    def log_operation(cls, func):
        def wrapper(*args, **kwargs):
            child_id = str(uuid.uuid4().hex)
            operation = func.__name__
            #If operation logging is on
            if pygdal_config.state == 1:
                parent_id = args[0].id
                args_serial = deserialize(list(args[1:]))
                arguments = {**dict(zip(func.__code__.co_varnames[1:1+len(args_serial)], args_serial)), **kwargs}
                package = [parent_id, child_id, operation, arguments]

                if parent_id not in pygdal_config.files:
                    pygdal_config.operation.log_input(*package, args[0].filename)
                elif operation == "Save" or operation == "Upload":
                    pygdal_config.operation.log_output(*package)
                else:
                    pygdal_config.operation.log_intermediate(*package)
                pygdal_config.files.append(child_id)
                pygdal_config.files.append(parent_id)
                pygdal_config.incr_op_count(operation)
            fname = pygdal_config.tempfiles.gen_file('vrt', operation, child_id)
            return func(*args, **kwargs, fname=fname)
        return wrapper

    def __init__(self):
        self.args = {'TEMP_SAVE': 'MEMORY',
                     'LOGGING': 'FALSE'}
        self.operations = {"inputs": [],
                           "intermediates": [],
                           "outputs": []}

        self.files = []
        self.opcount = {}
        self.tempfiles = TempfileHandler()
        self.operation = OperationHandler()

        self.__tempdir = None
        self.__state = 0


    @property
    def tempdir(self):
        return self.__tempdir

    @tempdir.setter
    def tempdir(self, value):
        self.__tempdir = value

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, value):
        self.__state = value

    def incr_op_count(self, op_name):
        if op_name not in self.opcount.keys():
            self.opcount.update({op_name: 1})
        else:
            self.opcount[op_name]+=1

    def SetConfigOption(self, key, value):
        self.args.update({key:value})

    def ReadConfig(self):
        if self.args['TEMP_SAVE'] == 'MEMORY':
            self.tempdir = '/vsimem/'
        else:
            self.tempdir = self.args['TEMP_SAVE']
            if not os.path.exists(self.tempdir):
                os.makedirs(self.tempdir)
        if self.args['LOGGING'] == 'TRUE':
            self.state = 1

    def logs(self):
        print(json.dumps(self.operations, indent=2))

class TempfileHandler(object):

    def __init__(self):
        self.fcount = 0

    def gen_file(self, ext, func, id):
        self.fcount+=1
        fname = id + '.' + ext
        if pygdal_config.tempdir == '/vsimem/':
            return os.path.join(pygdal_config.tempdir, func, fname)
        else:
            fpath = os.path.join(pygdal_config.tempdir, func)
            if not os.path.exists(fpath):
                os.makedirs(fpath)
            return os.path.join(fpath, fname)

    def cleanup(self, folder=None):
        flush_dir = pygdal_config.tempdir
        if folder:
            flush_dir = os.path.join(flush_dir, folder)
        if pygdal_config.args['TEMP_SAVE'] == 'MEMORY':
            pass #Flush the vsimem cache
        else:
            shutil.rmtree(flush_dir)

class OperationHandler(object):

    def __init__(self):
        pass

    def log_input(self, parent_id, child_id, operation, arguments, fname):
        pygdal_config.operations["inputs"].append({"id": parent_id,
                                          "fname": fname})
        pygdal_config.operations["intermediates"].append({"parent": parent_id,
                                                 "id": child_id,
                                                 "operation": operation,
                                                 "args": arguments
                                                 })
    def log_intermediate(self, parent_id, child_id, operation, arguments):
        pygdal_config.operations["intermediates"].append({"parent": parent_id,
                                                 "id": child_id,
                                                 "operation": operation,
                                                 "args": arguments
                                                 })

    def log_output(self, parent_id, child_id, operation, arguments):
        pygdal_config.operations["outputs"].append({"parent": parent_id,
                                           "id": child_id,
                                           "operation": operation,
                                           "args": arguments})


def deserialize(arg_list):
    for idx, arg in enumerate(arg_list):
        if type(arg) == ogr.Feature:
            arg_list[idx] = arg.ExportToJson()
        elif type(arg) == osr.SpatialReference:
            arg_list[idx] = arg.ExportToWkt()
    return arg_list


pygdal_config = ConfigHandler()
pygdal_config.ReadConfig()