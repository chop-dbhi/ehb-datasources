class RecordDoesNotExist(Exception):
    def __init__(self, url, path, record_id):
        self.url = url
        self.record_id = record_id
        self.errmsg = 'No record(s) found for record_id(s)' + \
            str(record_id) + ' at ' + str(url) + ':' + str(path)


class RecordCreationError(Exception):
    def __init__(self, url, path, record_id, cause):
        self.url = str(url)
        self.record_id = str(record_id)
        self.cause = str(cause)
        self.raw_cause = cause
        self.path = str(path)
        self.errmsg = 'Record ' + str(record_id) + \
            ' could not be created at ' + str(url) + \
            ':' + str(path) + ' due to: ' + str(cause)


class PageNotFound(Exception):
    def __init__(self, path):
        self.path = path
        self.errmsg = 'Page not found: '+str(path)


class ServerError(Exception):
    def __init__(self):
        self.errmsg = 'Error at server'


class ImproperArguments(Exception):
    def __init__(self, method_name, required_args):
        msg = 'The method ' + method_name + 'requires the following kwargs: '
        for arg in required_args:
            msg += arg + ', '
        self.errmsg = msg[0:msg.__len__()-1]


class IgnoreEhbExceptions(Exception):
    '''
    This is a hack used to accommodate Nautilus Phase I where the same record
    appears to be created multiple times
    '''
    def __init__(self, record_id):
        self.record_id = record_id
