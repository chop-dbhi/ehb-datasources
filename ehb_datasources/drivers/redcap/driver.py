import json
import os
import re
import urllib.request
import urllib.parse
import urllib.error
import xml.dom.minidom as xml
from xml.parsers.expat import ExpatError
from collections import OrderedDict
from jinja2 import Template
import http.client
import time

from ehb_datasources.drivers.exceptions import PageNotFound,\
    ImproperArguments, ServerError
from ehb_datasources.drivers.Base import Driver, RequestHandler
from ehb_datasources.drivers.exceptions import RecordDoesNotExist,\
    RecordCreationError
from ehb_datasources.drivers.redcap.formBuilderJson import FormBuilderJson
from functools import reduce


class GenericDriver(RequestHandler):
    '''
    Designed to allow making multiple request to a REDCap API for a specific
    user token.

    Note that REDCap tokens are unique to the user and REDCap project. Thus if
    a single user is to access multiple projects, it will be necessary to
    create multiple instances of this class OR change the token.

    Supports imports, exports, and exporting metadata. Currently files are
    not handled.
    '''

    def __init__(self, host, path, token, secure=False):
        super(GenericDriver, self).__init__(host, secure)
        self.token = token
        self.path = path

    FORMAT_JSON = 'json'
    FORMAT_XML = 'xml'
    FORMAT_CSV = 'csv'
    TYPE_FLAT = 'flat'
    TYPE_EAV = 'eav'

    # blank/empty values ignored
    OVERWRITE_NORMAL = 'normal'
    # blank empty values are valid and will overwrite data
    OVERWRITE_OVERWRITE = 'overwrite'
    # export raw coded values for multiple choice fields
    MULTIPLE_CHOICE_RAW = 'raw'
    # export labels for multiple choice fields
    MULTIPLE_CHOICE_LABEL = 'label'
    # export raw coded values and labels for multiple choice fields
    MULTIPLE_CHOICE_BOTH = 'both'
    # export the event label (this is NOT the unique event name)
    EVENT_NAME_LABEL = 'label'
    # export the unique event name
    EVENT_NAME_UNIQUE = 'unique'

    CONTENT_RECORD = 'record'
    CONTENT_METADATA = 'metadata'
    STANDARD_HEADER = {'Content-Type': 'application/x-www-form-urlencoded'}

    def build_parameter(self, _list):
        p = ''
        for item in _list:
            p += str(item) + ','
        return p[0: p.__len__() - 1]

    def write_records(self, data, _type=TYPE_FLAT,
                      overwrite=OVERWRITE_NORMAL, headers=STANDARD_HEADER,
                      useRawData=False):
        '''
        Attempts to write records contained in data to REDCap project
        associated with the current token. The REDCap API currently works
        reliably on while using XML formatting.

        Inputs:
        -------

        * _format : the format of the data to be written (json, xml, csv).
        * type = : record structure used in data
        * headers : header dictionary sent in request
        * useRawData : boolean.

            If True, this method assumes data is a String that is in the
            correct format for the request.

            If False (default), this method tries to convert data to a String
            for the request as follows:
                if format==FORMAT_JSON assumes data is a list OR dict and
                    converts as json.dumps(data)
                if format==FORMAT_XML assumes data=xml.dom.minidom instance and
                    converts as data.toxml('UTF-8')
                if format==FORMAT_CSVdata = string, no conversion

        * data : string, list, dict, or xml.dom.minidom

        Outputs:
        --------

        * Integer -- number of records created

        '''
        if useRawData:
            req_data = data
        else:
            req_data = data.toxml('UTF-8')

        headers['Accept'] = 'text/xml'
        params = {
            'token': self.token,
            'content': self.CONTENT_RECORD,
            'format': self.FORMAT_XML,
            'type': _type,
            'overwriteBehavior': overwrite,
            'data': req_data
        }
        params = OrderedDict(sorted(params.items(), key=lambda t: t[0]))
        response = self.POST(self.path, headers, urllib.parse.urlencode(params))
        if response.status == 201 or response.status == 200:
            # Record was processed properly
            processed_response = self.processResponse(response, self.path)
            num_recs_updated = -1
            # This is necessary because the REDCap API changed it's response
            # format for record import at REDCap version 4.8
            try:
                response_xml = xml.parseString(processed_response)
                num_recs_updated = int(
                    response_xml.getElementsByTagName(
                        'count'
                    )[0].firstChild.nodeValue
                )
            except TypeError:
                num_recs_updated = int(processed_response)
            except ExpatError:
                num_recs_updated = int(processed_response)

            return num_recs_updated
        else:
            # Don't know what happened, let processResponse raise appropriate
            # exception
            return self.processResponse(response, self.path)

    def read_records(self, _format=FORMAT_JSON, _type=TYPE_FLAT,
                     headers=STANDARD_HEADER, rawResponse=False, **kwargs):
        '''
        Attempts to read records from the REDCap project associated with the
        current token.

        Inputs:
        -------

        * _format : the format of the string response returned by the REDCap
            api, default JSON
        * _type : record structure in response, default is flat
        * headers : headers dictionary sent in request
        * rawResponse : boolean.

            If True, this method will return the String response received from
            the REDCap server,
            If False, the String response will be converted to:
                if _format==FORMAT_JSON : Python json object
                if _format==FORMAT_XML : Python xml.dom.minidom
                if _format==FORMAT_CSV : Unprocessed String

        Allowed Kwargs:
        ---------------

        * records: an iterable collection of record ids to read, default is
            all records
        * fields: an iterable collection of field names to read, default is
            all fields
        * forms: an iterable collection of form names to read, default is all
            form names with spaces will automatically be converted to
            underscored version.
        * events: an iterable collection of unique event names to read records
            for (longitudinal only) default is all.
        * event: a String value indicating whether the Event Label or
            Unique Event Name should be exported default is label

        '''
        params = {
            'token': self.token,
            'content': self.CONTENT_RECORD,
            'format': _format,
            'type': _type
        }
        params = OrderedDict(sorted(params.items(), key=lambda t: t[0]))

        for item in ['records', 'fields', 'forms', 'events']:
            if kwargs.get(item):
                params[item] = self.build_parameter(kwargs.get(item))

        if kwargs.get('event'):
            params['event'] = kwargs.get('event')

        response = self.POST(self.path, headers, urllib.parse.urlencode(params))
        if rawResponse:
            return response
        else:
            return self.transformResponse(
                _format,
                self.processResponse(response, self.path)
            )

    def read_metadata(self, _format=FORMAT_JSON, headers=STANDARD_HEADER,
                      rawResponse=False, **kwargs):
        '''
        Attempts to read metadata from the REDCap project associated with the
        current token.

        Inputs:
        -------

        * _format : the format of the string response returned by the REDCap
            api, default JSON
        * type : record structure in response, default is flat
        * headers : headers dictionary sent in request
        * rawResponse : boolean.

            If True, this method will return the String response received from
            the REDCap server,
            If False, the String response will be converted to:
                if _format==FORMAT_JSON : Python json object
                if _format==FORMAT_XML : Python xml.dom.minidom
                if _format==FORMAT_CSV : Unprocessed String

        Allowed Kwargs:
        ---------------

        * fields: An iterable collection of field names to read, default is
            all fields
        * forms: An iterable collection of form names to read, default is
            all form names with spaces will automatically be converted to
            underscored version

        '''
        params = {
            'token': self.token,
            'content': self.CONTENT_METADATA,
            'format':
            _format
        }
        params = OrderedDict(sorted(params.items(), key=lambda t: t[0]))

        for item in ['fields', 'forms']:
            if kwargs.get(item):
                params[item] = self.build_parameter(kwargs.get(item))

        params = urllib.parse.urlencode(params).replace('forms', 'forms[]')
        response = self.processResponse(
            self.POST(self.path, headers, params),
            self.path
        )
        if rawResponse:
            return response
        else:
            return self.transformResponse(_format, response)

    # overriding method from Base.py in order to
    # clean and parse redcap error message
    def processResponse (self, response, path =''):
        status = response.status
        if status == 200:
            return self.readAndClose(response)
        elif status == 201:
            return self.readAndClose(response)
        elif status == 400:
            #this means the data being imported isn't formatted correctly
            #redcap api will return a message
            msg = response.read()
            #xml to string
            msg = msg.decode ("utf-8")
            #for more than one error, errors are separated by \n
            if "\n" in msg:
                msg=msg.split('\n')
                msgShow =''
                for error in msg:
                    error=error.split(',')
                    #there are 3 parts to error message returned by redcap
                    #[0] -> user's name
                    #[1] -> field name
                    #[2] -> user input
                    #[3] -> error message
                    msgShow += "You entered " + error[2] + " for the field " + error[1]+ ". " + error [3] + "<br><br>"
                self.closeConnection()
                raise Exception (msgShow)
            else:
                #there is only one error message
                msg = msg.split(',')
                #there are 3 parts to error message returned by redcap
                #[0] -> user's name
                #[1] -> field name
                #[2] -> user input
                #[3] -> error message
                self.closeConnection()
                raise Exception("You entered " + msg[2] + " for the field " + msg[1]+ ". " + msg [3])
        elif status == 406:
            msg = "The data being imported was formatted incorrectly"
            self.closeConnection()
            raise Exception(msg)
        elif status == 404:
            self.closeConnection()
            raise PageNotFound(path=path)
        elif status == 500:
            self.closeConnection()
            raise ServerError
        else:
            self.closeConnection()
            msg = 'Unknown response code from server: {}'.format(status)
            raise Exception(msg)


class ehbDriver(Driver, GenericDriver):

    def __init__(self, url, password, username=None, secure=False):
        def getHost(url):
            return url.split('/')[2]

        def getPath(url):
            sp = url.split('/')
            path = '/'
            if sp.__len__() > 2:
                for i in range(3, sp.__len__()):
                    path += sp[i] + '/'
            return path[0: path.__len__() - 1]
        Driver.__init__(
            self,
            url=url,
            username=None,
            password=password,
            secure=secure
        )
        host = getHost(url)
        path = getPath(url)
        GenericDriver.__init__(
            self,
            host=host,
            path=path,
            token=password,
            secure=secure
        )
        self.unique_event_names = None
        self.event_labels = None
        self.form_data = None
        self.form_data_ordered = None
        self.form_names = None
        self.record_id_field_name = None

    def meta(self, *args, **kwargs):
        '''returns meta data'''
        return self.read_metadata(**kwargs)

    def get(self, record_id=None, *args, **kwargs):
        '''
        Retrieves records from REDCap

        Required Inputs
        ---------------

        * None: will return all records in json format

        Optional Inputs
        ---------------

        * record_id : id of the desired record
        * format
        * type
        * headers
        * rawResponse
        * fields
        * records
        * forms
        * events
        * event

        Also see GenericDriver.read_records doc

        If record_id and records are both specified, the union of the
        corresponding records will be returned.
        If ONLY record_id is specified (indicating a single record is desired)
        and NO record is found, a RecordDoesNotExist exception will be raised.

        '''

        # record_id = kwargs.pop('record_id',None)
        records = kwargs.pop('records', [])
        rawResponse = kwargs.pop('rawResponse', False)
        _format = kwargs.pop('_format', self.FORMAT_JSON)
        if record_id and record_id not in records:
            records.append(record_id)
        if len(records) == 1:
            try:
                rv = self.read_records(
                    records=records,
                    _format=_format,
                    rawResponse=rawResponse,
                    **kwargs
                )
                if rv:
                    if (
                        not rawResponse and
                        _format == self.FORMAT_XML and
                        len(rv.getElementsByTagName('item')) == 0
                    ):
                        raise RecordDoesNotExist(
                            self.url,
                            self.path,
                            record_id)
                    elif (
                        not rawResponse and
                        _format == self.FORMAT_JSON and
                        len(rv) == 0
                    ):
                        raise RecordDoesNotExist(
                            self.url,
                            self.path,
                            record_id)
                    else:
                        return rv
                else:
                    raise RecordDoesNotExist(self.url, self.path, record_id)
            except PageNotFound:
                raise RecordDoesNotExist(self.url, self.path, record_id)
        elif len(records) > 0:
            return self.read_records(records=records, **kwargs)
        else:
            return self.read_records(**kwargs)

    def delete(self, *args, **kwargs):
        return 0

    def create(self, record_id_prefix, record_id_validator, *args, **kwargs):
        '''
        Creates a REDCap record.

        Optional
        --------
        * record_id = id for the new record, if not supplied a random id will
            be generated
        * record_id_prefix = a prefix to prepend to the record_id
            (particularly intended for identifying a record as belonging to a
            group)

            If both a rec_id_prefix AND a record_id are supplied, the prefix
            will be added to the record_id

        * redcap_event_name = the event name used for initial record creation,
            if not provided the first event name provide in the configuration
            setup will be used for longitudinal studies. Ignored for Survey
            and Data Entry Classic
        * record_values = dictionary of record fields and values to add to
            initial record
        * overwrite = overwrite behavior, choices are *overwrite* and *normal*

        '''

        def validate_id(pid):
            try:
                x = None
                x = self.get(record_id=record_id_prefix + ':' + pid)
                if x:
                    return False
                else:
                    return True
            except RecordDoesNotExist:
                return True
            except PageNotFound:
                return True

        temp = self.create_random_record_id(validator_func=validate_id)
        study_id = kwargs.get('record_id', temp)
        if record_id_prefix:
            study_id = record_id_prefix + ':' + study_id

        event = None
        if self.unique_event_names:
            event = kwargs.pop('redcap_event_name', self.unique_event_names[0])

        overwrite = kwargs.pop('overwrite', self.OVERWRITE_NORMAL)
        record_values = kwargs.pop('record_values', None)

        if not study_id and not (event or self.form_names):
            raise ImproperArguments(
                'redcap.ehbDriver.create',
                ['study_id', 'redcap_event_name', 'form_names']
            )

        meta_data = self.meta(_format=self.FORMAT_XML)
        records = meta_data.getElementsByTagName('records')

        if records and len(records) == 1:
            # it is assumed that the first item in the meta data is the
            # record id in REDCap
            first_item = records[0].getElementsByTagName(
                'item'
                )[0].getElementsByTagName('field_name')[0].firstChild
            if first_item:
                id_label = first_item.wholeText
            else:
                raise Exception('Unable to get record id label')
        else:
            raise Exception('Unable to obtain meta_data')

        if event:
            record = '<records><item><' + id_label + '><![CDATA[' + study_id +\
                ']]></' + id_label + '><redcap_event_name><![CDATA[' + event +\
                ']]></redcap_event_name>'
        else:
            record = '<records><item><' + id_label + '><![CDATA[' + study_id +\
                ']]></' + id_label + '>'

        if record_values:
            for k, v in record_values:
                record += '<' + k + '><![CDATA[' + v + ']]></' + k + '>'

        record += '</item></records>'

        if 1 != self.write_records(
            data=xml.parseString(record),
            overwrite=overwrite
        ):
            errors = self.write_records(
                data=xml.parseString(record),
                overwrite=overwrite)
            raise RecordCreationError(self.url, self.path, study_id, errors)
        else:
            return study_id

    def update(self, *args, **kwargs):
        return 0

    def configure(self, driver_configuration='', *args, **kwargs):
        '''
        Configures the driver for the specific REDCap project.

        Required Inputs (kwargs only):
        ------------------------------

        * driver_configuration : a string representation of json configuration
            data of the form:

            Single Survey or Data Entry Forms Classic (i.e. non longitudinal)
            -----------------------------------------------------------------
            {
                "form_names":["value", ...]
            }

            OR

            Data Entry Longitudinal
            -----------------------
            {
                "unique_event_names":["value", ...],
                "event_labels":["value", ...],
                "form_data":{"form_name":[0,1,...], ...}
            }

        ***

        Single Survey or Data Entry Forms

        * form_names: List[String]

        Data Entry Longitudinal

        * unique_event_names: List[String] , the event names for this REDCap
          project
        * event_labels : List[String]
        * form_event_data : dictionary of the form {"form_label":[Booleans]
          where the number of Booleans
          should be the same as the number of events and the value indicates if
          this form should be available for that event'''

        config = driver_configuration

        if config:
            json_config = json.loads(config)
            self.record_id_field_name = json_config.get('record_id_field_name',
                                                        None)
            self.form_names = json_config.get('form_names', None)
            if self.form_names:
                self.form_data_ordered = self.form_names
            else:
                # longitudinal study
                self.form_data_ordered = []
                self.unique_event_names = json_config['unique_event_names']
                self.event_labels = json_config['event_labels']
                self.form_data = {}
                for k in list(json_config['form_data'].keys()):
                    bools = []
                    values = json_config['form_data'][k]
                    for v in values:
                        bools.append(v == 1)
                    self.form_data[k] = bools
                temp = config[config.index('form_data') + 12: len(config)]
                temp = temp[0: temp.index('}')]
                for item in re.findall(r'"[^"\r\n]*"', temp):
                    self.form_data_ordered.append(item[1: len(item) - 1])
        else:
            self.unique_event_names = kwargs.pop('unique_event_names', None)
            self.event_labels = kwargs.pop('event_labels', None)
            self.form_event_data = kwargs.pop('form_event_data', None)
            self.form_names = kwargs.pop('form_names', None)

    # new function to find and display redcap form status
    def find_completed_forms(self, record_id, form_url='', *args, **kwargs):

        # construct field name for completion field in every form
        def create_completion_field_name(list_of_forms):
            form_completion_fields=[]
            for form in list_of_forms:
                form_completion_fields.append(form + "_complete")
            return form_completion_fields

        def get_form_statuses(self, record, form_completion_fields, event_index=-1):
            form_statuses = {}
            for f in form_completion_fields:
                form_complete_value = record[f]
                form_name = f[:-9]
                # key is the form spec according to driver config
                if event_index == -1: # nonlong study
                    key = str(self.form_names.index(form_name))
                else:
                    key = str(list(self.form_data.keys()).index(form_name)) + "_" + str(event_index)
                if (form_complete_value == '1'):
                    form_statuses[key] = 1
                elif (form_complete_value == '2'):
                    form_statuses[key] = 2
            return form_statuses

        def merge_two_dicts(d_1, d_2): # deprecated, python 3.5 library has this function
            d_3 = d_1.copy()   # start with d_1's keys and values
            d_3.update(d_2)    # modifies d_3 with d_2's keys and values & returns None
            return d_3

        def find_completed_forms_nonlongitudinal(self):
            # construct field name for completion field in every form
            form_completion_fields = create_completion_field_name(self.form_names)
            record_set = self.get(_format=self.FORMAT_JSON,
                                  records=[record_id],
                                  rawResponse=True,
                                  fields=form_completion_fields).read().strip()
            record_set = self.raw_to_json(record_set)
            # iterate through the record set to find the completion field
            for r in record_set:
                form_statuses = get_form_statuses(self,r, form_completion_fields)
            return form_statuses

        def find_completed_forms_longitudinal(self):
            # must specify field study_id for redcap api to return study_id and event name
            field_names = ['study_id']
            form_completion_fields = create_completion_field_name(list(self.form_data.keys()))
            field_names += form_completion_fields
            temp = self.get(_format=self.FORMAT_JSON, rawResponse=True,
                        records=[record_id], fields=field_names).read().strip()
            record_set = self.raw_to_json(temp)
            record_set = json.dumps(record_set) # have to reload json in order for the field
            record_set = json.loads(record_set) # redcap_event_name to be read

            first_event = True
            for r in record_set: # iterate through the record set to find the completion field
                redcap_eventname = r['redcap_event_name']
                if redcap_eventname in self.unique_event_names:
                    event_index = self.unique_event_names.index(redcap_eventname)
                    if first_event:
                        form_statuses = get_form_statuses(self,r, form_completion_fields, event_index)
                        first_event = False
                    else:
                        form_statuses = merge_two_dicts(form_statuses, get_form_statuses(self,r, form_completion_fields, event_index))
            return form_statuses

        if self.form_names:
            return find_completed_forms_nonlongitudinal(self)
        else:
            return find_completed_forms_longitudinal(self)

    def subRecordSelectionForm(self, form_url='', redcap_form_complete_codes={}, *args, **kwargs):

        '''
        Generates the REDCap data entry table.

        Requires that the configure method has been called previously.

        Required Input (kwargs):
        ------------------------

        form_url = the prefix for the url for further form rendering
        '''
        # make sure the configure method has been called
        if not self.form_names and not (
            self.event_labels and
            self.unique_event_names and
            self.form_data and
            form_url
        ):
            return None

        def counter(start):
            while True:
                yield start
                start += 1

        # method to identify button color and icon
        # based on form completion status
        def get_button_icon(key):
            all_form_status = redcap_form_complete_codes
            button_icon=[]
            try:
                if all_form_status[key] == 1: # form is unverified
                    button_icon.append('btn-warning')
                    button_icon.append('fa-adjust')
                    return button_icon
                elif all_form_status[key] == 2: # form is complete
                    button_icon.append('btn-success')
                    button_icon.append('fa-circle')
                    return button_icon
            except: # form is incomplete
                button_icon.append('btn-primary')
                button_icon.append('fa-circle-o')
                return button_icon

        if self.form_names:
            # The project is not longitudinal
            def makeRow(form_name, form_index):
                key = str(form_index)
                row = '<tr><td>' + reduce(
                    lambda x,
                    y: x + ' ' + y.capitalize(),
                    form_name.split('_'), '') + '</td>'

                return row + ('<td><button data-toggle="modal"' +
                      ' data-backdrop="static" data-keyboard="false"' +
                      ' href="#pleaseWaitModal" class="btn btn-small ' + '{button_icon[0]}'
                      ' " onclick="location.href=\'' + form_url + key +
                      '/\'">Edit <i class="fa ' +'{button_icon[1]}' +
                      '"></i></button></td>').format(button_icon=get_button_icon(key))

            form = ('<table class="table table-bordered table-striped ' +
                    'table-condensed"><tr><th>Data Form</th><th></th></tr>')
            count = counter(0)
            rows = [makeRow(form_name, next(count)) for form_name in self.form_names]
            form += ''.join(rows) + '</table>'
            return form
        else:
            # The project is longitudinal
            def make_td(form_index, event_index, form_exists):
                key = str(form_index) + "_" + str(event_index)
                if form_exists:
                    return ('<td><button data-toggle="modal"' +
                            'data-backdrop="static" data-keyboard="false" ' +
                            'href="#pleaseWaitModal" class="btn btn-small ' +
                            '{button_icon[0]}' + '" onclick="location.href=\'' +
                            form_url + key + '/\'">Edit <i class="fa ' +
                            '{button_icon[1]}' + '"></i></button></td>').format(button_icon=get_button_icon(key))
                else:
                    return '<td></td>'

            def make_trs(form_index, form_list):
                count = counter(0)
                if len(form_list) > 1:
                    return '<tr><td>' + reduce(
                        lambda x,
                        y: x + ' ' + y.capitalize(),
                        form_list[0].split('_'), '') + '</td>' + reduce(
                        lambda x,
                        y: x + make_td(form_index, next(count), y),
                        self.form_data[form_list[0]],
                        '') + '</tr>' + make_trs(form_index + 1, form_list[1: len(form_list)]) # reduces number of forms in list after its been processed
                else:
                    return '<tr><td>' + reduce(
                        lambda x,
                        y: x + ' ' + y.capitalize(),
                        form_list[0].split('_'), '') + '</td>' + reduce(
                        lambda x,
                        y: x + make_td(form_index, next(count), y),
                        self.form_data[form_list[0]],
                        '')
            number_of_events = str(len(self.event_labels))
            form = ('<table class="table table-bordered table-striped' +
                    'table-condensed"><tr><th rowspan="2">' +
                    'Data Collection Instrument</th><th colspan="' +
                    number_of_events + '">Events</th></tr>')
            form += '<tr>' + reduce(
                lambda x,
                y: x + '<td>' + y + '</td>',
                self.event_labels,
                '') + '</tr>'
            form += make_trs(0, self.form_data_ordered) + '</table>'
            return form

    def subRecordForm(self, external_record, form_spec='', *args, **kwargs):
        '''
        Generates a REDCap data entry form for a specific ExternalRecord and
        REDCap Form and event. It is necessary to call configure before calling
        this method.

        Required Inputs (kwargs):
        -------------------------

        * external_record = ExternalRecord object from ehb_client
        * form_spec = String in the form N_M
            N is the form number (0 indexed)
            M is the event number (0 indexed).

        The form and event numbers are mapped to form names and event names in
        the order they were provided in the call to configure
        If the REDCap project is not longitudinal (i.e. Survey or Data Forms
        Classic) the event number is not required and will be ignored if
        included

        Optional Inputs:
        ----------------

        session = the session var.

        If provided the driver will use the session var to cache form field
        names which improves save time performance
        '''

        er = external_record

        # make sure the proper information has been provided and that configure
        #  has been called
        if not er or not form_spec:
            return None
        if not (
            self.event_labels and self.unique_event_names and self.form_data
        ) and not self.form_names:
            return None
        # make sure form_spec is of the correct format, N_M, negatives NOT
        # allowed for non longitudinal studies event number is not required,
        # is ok if supplied it will be ignored
        if self.form_names and not (
            re.match(r'^\d+$', form_spec) or re.match(r'^\d+_\d+$', form_spec)
        ):
            return None

        split = form_spec.split('_')
        form_num = int(split[0])

        if not self.form_names:
            event_num = int(split[1])

        # Make sure the form and event indices are inbounds
        if self.form_names and form_num > (len(self.form_names) - 1):
            return None
        elif not self.form_names and (
            form_num > (len(self.form_data_ordered) - 1) or
            event_num > (len(self.unique_event_names) - 1)
        ):
            return None

        form_name = self.form_data_ordered[form_num]
        # need to get the meta data from REDCAp to construct the form and the
        # record to populate previously entered values
        form_builder = FormBuilderJson()
        meta_data = self.raw_to_json(self.meta(
            _format=self.FORMAT_JSON,
            rawResponse=True)
        )
        session = kwargs.get('session', None)

        if self.form_names:
            record_set = self.get(_format=self.FORMAT_JSON,
                                  records=[er.record_id],
                                  rawResponse=True,
                                  forms=[form_name]).read().strip()
            record_set = self.raw_to_json(record_set)
            return form_builder.construct_form(meta_data,
                                               record_set,
                                               form_name,
                                               er.record_id,
                                               None,
                                               None,
                                               None,
                                               session,
                                               self.record_id_field_name)
        else:
            temp = self.get(_format=self.FORMAT_JSON,
                            rawResponse=True,
                            records=[er.record_id])
            record_set = temp.read().strip()
            record_set = self.raw_to_json(record_set)
            return form_builder.construct_form(meta_data,
                                               record_set,
                                               form_name,
                                               er.record_id,
                                               event_num,
                                               self.unique_event_names,
                                               self.event_labels,
                                               session,
                                               self.record_id_field_name)

    def __getCDATA(self, item, tag_name, default=None):
            CDATA = item.getElementsByTagName(tag_name)
            if CDATA:
                fc = CDATA[0].firstChild
                if fc:
                    return fc.wholeText
                else:
                    return default
            else:
                return default

    def processForm(self, request, external_record, form_spec='', *args,
                    **kwargs):
        '''
        Saves data to REDCap record from the raw data in the HTTP request
        object assuming that data was generated as from the form created by
        the subRecordForm method in this class. It is necessary to call
        configure before calling this method.

        Required Kwargs:
        ----------------

        * request - The HTTP Request object
        * external_record = ExternalRecord object from ehb_client
        * form_spec = String in the form N_M where N is the form number
        (0 indexed) and M is the event number (0 indexed). The form and event
        numbers are mapped to form names and event names in the order they were
        provided the call to configure

        Optional Inputs
        * session = the session var. If provided the driver will use the
        session var to cache form field names which improves performance'''

        def fieldDataXmlFrom(field_name, field_value):
            if field_value and field_value != '':
                return '<{field_name}><![CDATA[{field_value}]]></{field_name}>'.format(
                    field_name=field_name,
                    field_value=str(field_value))
            else:
                return '<{field_name}/>'.format(field_name=field_name)

        def make_data_entry_for(item):
            ft = self.__getCDATA(item, 'field_type')
            ft = ft.lower()
            fn = self.__getCDATA(item, 'field_name')
            if not ft or not fn:
                return ''
            if ft == 'checkbox':
                # Checkboxes must have a 0 or 1 in request sent to redcap api,
                # but the submitted form has no entry if unchecked
                choices = self.__getCDATA(
                    item, 'select_choices_or_calculations').split('\\n')
                kvals = [choice.split(',')[0].strip() for choice in choices]

                def getValue(k):
                    v = data.get(fn + '___' + k)
                    if v and v != '':
                        return str(v)
                    else:
                        return '0'
                xml_data = [
                    fieldDataXmlFrom(
                        fn + '___' + k,
                        getValue(k)
                    ) for k in kvals]
                return ''.join(xml_data)
            elif ft == 'slider':
                # value = data.get(fn,None)
                # print 'slider value=',value
                # print fieldDataXmlFrom(fn,value)
                # value = data.get(fn, None) #the value submitted in the form
                # return fieldDataXmlFrom(fn, value)
                return ''
            else:
                # The value submitted in the form
                value = data.get(fn, None)
                return fieldDataXmlFrom(fn, value)

        def make_data_entry_from_session(field_name, field_dict):
            ft = field_dict['type']
            fv = data.get(field_name, '')
            if ft == 'checkbox' and (not fv or fv == ''):
                return fieldDataXmlFrom(field_name, '0')
            elif ft == 'slider':
                return ''
            else:
                return fieldDataXmlFrom(field_name, str(fv))

        # This will hold the data submitted in the form
        data = {}

        post_data = request.POST
        if post_data:
            for k, v in list(post_data.items()):
                data[k] = v
        else:
            return ['No data in request']

        er = external_record

        # Make sure the proper information has been provided and that configure
        # has been called
        if not er or not form_spec:
            return ['external record and form_spec must be supplied']
        if not (
            self.event_labels and
            self.unique_event_names and
            self.form_data
        ) and not self.form_names:
            return ['REDCap driver not configured.']

        # Make sure form_spec is of the correct format, N_M, negatives NOT
        # allowed

        # For non longitudinal studies event number is not required, is ok if
        #  supplied it will be ignored
        if self.form_names and not (
            re.match(r'^\d+$', form_spec) or
            re.match(r'^\d+_\d+$', form_spec)
        ):
            # Longitudinal study must have event number and form number
            return ['REDCap Driver form_spec argument is invalid']
        elif not self.form_names and not re.match(r'^\d+_\d+$', form_spec):
            return ['REDCap Driver form_spec argument is invalid']

        split = form_spec.split('_')
        form_num = int(split[0])
        if not self.form_names:
            event_num = int(split[1])
        if self.form_names and form_num > (len(self.form_names) - 1):
            # Make sure the form and event indices are inbounds
            return ['Invalid event or form numbers in REDCap driver']
        elif (
            not self.form_names and
            (
                form_num > (len(self.form_data_ordered) - 1) or
                event_num > (len(self.unique_event_names) - 1)
            )
        ):
            return ['Invalid event or form numbers in REDCap driver']

        form_name = self.form_data_ordered[form_num]
        # Need to get the meta data for this form from REDCAp to construct the
        #  import request to the REDCap API
        session = kwargs.get('session', None)
        id_label = self.record_id_field_name
        if session:
            form_fields = session.get('{0}_fields'.format(form_name), None)
        if id_label and session and form_fields:
            data_entries = ''.join(
                [make_data_entry_from_session(field_name, field_dict) for field_name, field_dict in list(form_fields.items())]  # noqa
            )
        else:
            # Use meta data from REDCap
            meta_data = self.meta(_format=self.FORMAT_XML, forms=[form_name])
            # Try to figure out the id field from the metadata
            # It is assumed that the first item is the record id field
            records = meta_data.getElementsByTagName('records')
            if records and len(records) == 1:
                items = records[0].getElementsByTagName('item')
                first_item = items[0].getElementsByTagName(
                    'field_name')[0].firstChild
                if first_item:
                    id_label = first_item.wholeText
                else:
                    return ['REDCap Driver could not obtain the REDCap record id field from the metadata']  # noqa
            else:
                return ['The meta data was not found for the specified REDCap record']  # noqa
            # loop over items in meta_data to construct data entries from data
            data_entries = ''.join([make_data_entry_for(item) for item in items[1: len(items)] if self.__getCDATA(item, 'form_name') == form_name])  # noqa

        if id_label in list(data.keys()):
            record = '<records><item>'
        else:
            record = '<records><item><' + id_label + '><![CDATA[' + \
                er.record_id + ']]></' + id_label + '>'
        if self.form_names:
            # This is not a longitudinal study
            record += data_entries + '</item></records>'
        else:
            # This is a longitudinal study
            unique_event_label = self.unique_event_names[event_num]
            record += '<redcap_event_name><![CDATA[' + \
                unique_event_label + ']]></redcap_event_name>' + \
                data_entries + '</item></records>'

        # Now write the record to REDCap, if successful don't return anything
        try:
            if 1 != self.write_records(
                data=record,
                overwrite=GenericDriver.OVERWRITE_OVERWRITE,
                useRawData=True
            ):
                return ['Unknown error. REDCap reports multiple records were' +
                        'updated, should have only been 1.']
        except Exception as error:
            return  repr(error)
