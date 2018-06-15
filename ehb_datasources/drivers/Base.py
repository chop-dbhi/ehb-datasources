from abc import ABCMeta, abstractmethod
from .exceptions import PageNotFound, ServerError
import datetime
import http.client
import json
import random
import string
import logging
import re
import urllib.request, urllib.parse, urllib.error
import xml.dom.minidom as xml

log = logging.getLogger('ehb_datasources')

class Driver(object, metaclass=ABCMeta):
    '''
    Abstract electronic honest broker (ehb) datasource driver class
    '''

    def __init__(self, url, username, password, secure):
        self.url = url
        self.username = username
        self.password = password
        self.secure = secure

    @abstractmethod
    def get(self, record_id=None, *args, **kwargs):
        '''
        Should enable getting one or more records. Should return None if no
        records are found.

        If record_id is supplied (other driver dependent options may allow
        calls without this parameter) and no record exists, this method should
        raise RecordDoesNotExist
        '''
        pass

    @abstractmethod
    def delete(self, *args, **kwargs):
        '''
        Should enable deleting one or more records
        '''
        pass

    @abstractmethod
    def create(self, record_id_prefix, record_id_validator, *args, **kwargs):
        '''
        Should enable creating a new record
        Inputs:
            * record_id_prefix = a prefix to prepend to the record_id
                (particularly intended for identifying a record as belonging to
                a group)
            * record_id_validator is function that accepts two positional
                arguments, the first is the new record id and the second is a
                boolean indicating if the external system path should be
                included in the compared record set.

            Checks if the newly produced record id is valid WRT to the eHB.
            It will return 0 for valid and an integer > 0 corresponding to an
            error code if not valid

        Output:
            Primary id of the newly created record or RecordCreationError
        '''
        pass

    @abstractmethod
    def update(self, *args, **kwargs):
        '''
        Should enable updating one or more records
        '''
        pass

    @abstractmethod
    def configure(self, driver_configuration='', *args, **kwargs):
        '''
        Perform any necessary driver configuration actions.

        `driver_configuration` is a string representation of
        driver_configuration values. The expected format is driver dependent
        '''
        pass

    @abstractmethod
    def meta(self, *args, **kwargs):
        '''
        Should enable obtaining meta data for the underlying data store if
        appropriate
        '''
        pass

    @abstractmethod
    def subRecordSelectionForm(self, form_url='', *args, **kwargs):
        '''
        Should return a string representation of an html form to be used to
        select additional input data forms for a specific record. If there is
        only a top level form this method can just return the single form.
        `form_url` is the base url for this form and should be used for setting
        links to sub-forms.
        '''
        pass

    @abstractmethod
    def subRecordForm(self, external_record, form_spec='', *args, **kwargs):
        '''
        Should return a string representation of an html form to be used as
        data entry for a specific record (or portion of the record).
        `external_record` is an appropriate representation of the ehb-service
        externalRecord class, e.g
        ehb-client.external_record_request_handler.ExternalRecord
        `form_spec` is a string representing any required additional form
        specification information, this is driver dependent.
        '''
        pass

    @abstractmethod
    def processForm(self, request, external_record, form_spec='', *args,
                    **kwargs):
        '''
        Given the HTTP request, which has the raw data, process the data.

        Inputs:
        * request: the HTTP request object
        * external_record: an appropriate representation of the ehb-service
            externalRecord class, e.g
            ehb-client.external_record_request_handler.ExternalRecord
            `form_spec` is a string representing any required additional form
            specification information, this is driver dependent.

        OUTPUT:
        * List of error messages, None if successful
        '''
        pass

    def create_random_record_id(self, size=9,
                                chars=string.ascii_uppercase + string.digits,
                                validator_func=None, max_attempts=10):
        '''
        Attempts to create a new random record id. If supplied it will use the
        validator_func to verify that the random id does not already exist.
        If it does, it will try a new random id up to max_attempts number of
        times.

        INPUTS:
            * size: number of characters to include in id
            * chars: valid character choices
            * validator_func: function that accepts a string id and returns
                True if the id is acceptable as a new record id
                False otherwise
            * max_attempts: the number of new id attempts to make
        '''
        if validator_func:
            attempt_count = 0
            while attempt_count < max_attempts:
                pid = ''.join(random.choice(chars) for idx in range(size))
                if validator_func(pid):
                    return pid
                else:
                    attempt_count += 1
        else:
            return ''.join(random.choice(chars) for idx in range(size))

    def new_record_form_required(self):
        '''
        Returns boolean indicating if the user is required to complete a form
        in order to create a new record.
        '''
        return False

    def create_new_record_form(self, request, *args, **kwargs):
        '''
        Should generate a string representation of an html form for creating a
        new record or None if no information is needed from the user to
        generate a new record. The request is supplied so that if the form had
        been submitted previously with errors it can be recreated with the
        appropriate data.
        '''
        None

    def process_new_record_form(self, request, record_id_prefix,
                                record_id_validator, *args, **kwargs):
        '''
        Should process data in new record form and return the new record id
        from the external system.
        Inputs:
            * request: Django HTTP request object
            * record_id_prefix: a prefix to prepend to the record_id.
                (particularly intended for identifying a record as belonging to
                a group)
            * record_id_validator: function that accepts two positional
                arguments, the first is the new record id and the second is a
                boolean indicating if the external system path should be
                included in the compared record set.

                Checks if the newly produced record id is valid WRT to the eHB.

                It will return 0 for valid and an integer > 0 corresponding to
                an error code if not valid
        '''
        None


class RequestHandler(object):
    '''
    The Request Handler object is designed to allow making multiple requests
    from a fixed host
    '''

    def __init__(self, host, secure=False):
        self.host = host
        self.secure = secure
        self.lastrequestbody = ''
        self.currentConnection = None

    FORMAT_JSON = 'json'
    FORMAT_XML = 'xml'
    FORMAT_CSV = 'csv'

    def sendRequest(self, verb, path='', headers='', body=''):

        self.closeConnection()
        self.lastrequestbody = body

        if(self.secure):
            c = http.client.HTTPSConnection(self.host)
        else:
            c = http.client.HTTPConnection(self.host)

        ts = datetime.datetime.now()

        c.request(verb, path, body, headers)

        log.debug(
            "datasource request ({0}) {1}ms".format(
                path,
                (datetime.datetime.now() - ts).microseconds/1000)
        )

        print ("THIS IS THE REQUEST")
        print (path)
        # print (body)

        r = c.getresponse()

        return r

    def POST(self, path='', headers='', body=''):
        self.lastrequestbody = body
        return self.sendRequest('POST', path, headers, body)

    def GET(self, path='', headers='', body=''):
        self.lastrequestbody = body
        return self.sendRequest('GET', path, headers, body)

    def PUT(self, path='', headers='', body=''):
        self.lastrequestbody = body
        return self.sendRequest('PUT', path, headers, body)

    def closeConnection(self):
        if self.currentConnection:
            self.currentConnection.close()

    def processResponse(self, response, path=''):
        status = response.status
        if status == 200:
            return self.readAndClose(response)
        elif status == 201:
            return self.readAndClose(response)
        elif status == 400:
            msg = 'Bad Request: {}'.format(response.read())
            self.closeConnection()
            raise Exception(msg)
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

    def readAndClose(self, response):
        rd = response.read()
        self.closeConnection()
        return rd

    def raw_to_json(self, raw_string):
        def controls_repl(matchobj):
            if matchobj.group(1) == '\r':
                return '\n'
            else:
                return matchobj.group(1)

        def non_controls_repl(matchobj):
            return matchobj.group(1)




        try:
            # return json.loads(raw_string)
            return json.loads(raw_string.decode('utf-8', 'backslashreplace'))
        except:
            raise
            return json.loads(raw_string.decode('unicode-escape'))
        else:
            raise

    def transformResponse(self, _format, responseString):
        try:
            if _format == self.FORMAT_JSON:
                return self.raw_to_json(responseString)
            if _format == self.FORMAT_XML:
                return xml.parseString(responseString)
            return responseString
        except Exception:
            # TODO: Pass up some informative error
            raise
            pass

    def extract_data_from_post_request(self, request):
        data = {}  # this will hold the data submitted in the form
        post_data = request._post
        if post_data:
            for k, v in list(post_data.items()):
                data[k] = v
            return data
