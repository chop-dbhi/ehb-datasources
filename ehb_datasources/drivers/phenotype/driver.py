from ehb_datasources.drivers.Base import Driver, RequestHandler
from ehb_datasources.drivers.exceptions import RecordCreationError, \
    IgnoreEhbExceptions


class PhenotypeDriver(Driver, RequestHandler):

    def __init__(self, url, user, password, secure):
        def getHost(url):
            return url.split('/')[2]

        def getPath(url):
            sp = url.split('/')
            path = '/'
            if sp.__len__() > 2:
                for i in range(3, sp.__len__()):
                    path += sp[i] + '/'
            return path[0:path.__len__()-1]

        Driver.__init__(self, url=url, username=user, password=password,
                        secure=secure)

        host = getHost(url)
        self.path = getPath(url)
        RequestHandler.__init__(self, host=host, secure=secure)

    def get(self, record_id=None, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def create(self, record_id_prefix, record_id_validator, *args, **kwargs):
        return record_id_prefix

    def update(self, *args, **kwargs):
        pass

    def configure(self, driver_configuration='', *args, **kwargs):
        pass

    def meta(self, *args, **kwargs):
        pass

    def subRecordSelectionForm(self, form_url='', *args, **kwargs):
        return ('<h3>Record created. Return to <a href="../../../list/">' +
                'Subject Summary List</a> to view.</h3>')

    def subRecordForm(self, external_record, form_spec='', *args, **kwargs):
        html = ('<h3 style="color:red"><em>The sample record is saved. ' +
                'Currently no other actions are supported.</em></h3>' +
                '<br/><br/>')
        return html

    def processForm(self, request, external_record, form_spec='', *args,
                    **kwargs):
        pass

    def new_record_form_required(self):
        '''
        Returns boolean indicating if the user is required to complete a form
        in order to create a new record
        '''
        return False

    def create_new_record_form(self, request, *args, **kwargs):
        '''
        Should generate a string representation of an html form for creating
        a new record or None if no information is needed from the user to
        generate a new record
        '''
        return None

    def process_new_record_form(self, request, record_id_prefix,
                                record_id_validator, *args, **kwargs):
        '''
        Should process new data in new record form and return the record id
        '''
        pass
