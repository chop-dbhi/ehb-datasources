import base64
import datetime
import json
import logging
import os
import codecs
from collections import OrderedDict
import urllib.request, urllib.parse, urllib.error

from jinja2 import Template

from ehb_datasources.drivers.Base import Driver, RequestHandler
from ehb_datasources.drivers.exceptions import RecordCreationError, \
    IgnoreEhbExceptions

log = logging.getLogger(__file__)


class ehbDriver(Driver, RequestHandler):

    FORM_SDG_ID = 'SDG_ID'
    FORM_SDG_NAME = 'SDG_NAME'
    NAU_REC_ID = 'id'
    NAU_REC_NAME = 'name'
    NAU_REC_EXT_REF = 'ext-ref'
    VALID_NAU_ELEM_IDENTIFIERS = [NAU_REC_ID, NAU_REC_NAME, NAU_REC_EXT_REF]
    NAU_ERROR_MAP = {
        '': 'UNKNOWN ERROR.',
        '0': 'UNKNOWN ERROR.',
        '1': 'Unable to communicate with Laboratory System because of expired or incorrect credentials.',
        '2': 'Username not provided.',
        '3': 'Password not provided.',
        '4': 'Request type not provided.',
        '5': 'Request body not provided.',
        '6': 'Malformed Request.',
        '7': 'Unsupported request type.',
        '8': 'Form data is not valid.',
        '100': 'NAU socket service not found.',
        '101': 'NAU invalid authorization header.',
        '500': 'server error.'
    }

    def __init__(self, url, user, password, secure):
        def getHost(url):
            return url.split('/')[2]

        def getPath(url):
            sp = url.split('/')
            path = '/'
            if sp.__len__() > 2:
                for i in range(3, sp.__len__()):
                    path += sp[i] + '/'
            return path[0:path.__len__() - 1]

        Driver.__init__(self, url=url, username=user, password=password,
                        secure=secure)

        host = getHost(url)
        self.path = getPath(url)

        RequestHandler.__init__(self, host=host, secure=secure)

    def find_nau_elem_identifier(self, dict_):
        for vid in self.VALID_NAU_ELEM_IDENTIFIERS:
            ident = dict_.get(vid)
            if ident:
                return (vid, ident)
        return (None, None)

    def encode_nau_creds(self):
        creds = base64.b64encode(bytes('{0}:{1}'.format(self.username, self.password), 'utf-8'))
        return 'Basic {0}'.format(creds.decode('utf-8'))

    def get(self, record_id=None, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def create(self, record_id_prefix, record_id_validator, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        '''
        This will submit an update request to the Nautilus-REST service

        Inputs: The following inputs must be supplied in the kwargs
            * fldvals : dict containing the record values to be updated
            * nau_sub_path : String constant indicating the sub-path on the
                NauREST web api to. The value is used to determine the NauREST
                path when submitting the request. For example, if the NauREST
                web API is at http://naurest.com then a sample update is
                submitted to http://naurest.com/api/sample and the proper
                value for this input is 'sample'
        '''
        fldvals = kwargs.get('fldvals', {})
        nau_sub_path = kwargs.get('nau_sub_path', '')
        rec_key, rec_id = self.find_nau_elem_identifier(kwargs)
        # Using OrderedDict for test reproducibility.
        params = OrderedDict([
            (rec_key, rec_id),
            ("fldvals", fldvals)
        ])
        body = [
            params
        ]
        body = json.dumps(body)
        nau_creds = self.encode_nau_creds()
        headers = {
            'Accept': 'application/json',
            'NAUTILUS-CREDS': nau_creds,
            'Content-Type': 'application/json'
        }
        full_path = self.path + nau_sub_path
        if not full_path.endswith('/'):
            full_path += '/'
        response = self.PUT(full_path, headers, body)
        processed_response = self.processResponse(response, self.path)
        return processed_response

    def get_sample_data(self, *args, **kwargs):
        '''
        This will submit a request to the Nautilus-REST service to retrieve
        sample information.
        '''
        body = ''
        nau_creds = self.encode_nau_creds()
        headers = {
            'Accept': 'application/json',
            'NAUTILUS-CREDS': nau_creds,
            'Content-Type': 'application/json'
        }
        full_path = self.path + 'sdg'
        if not full_path.endswith('/'):
            full_path += '/'
        full_path += '?name={sdg}'.format(sdg=kwargs.get('record_id'))
        response = self.GET(full_path, headers, body)
        if (response.status != 200):
            if (response.status == 401):
                log.error('Error: Nautilus Authentication error')
                return {"error": "Nautilus Authentication error. Please e-mail BioRC@email.chop.edu, EiGSupport@email.chop.edu and your research coordinator to resolve"}
            elif(response.status == 404):
                log.error('Error: SDG name {sdg} does not exist in Nautilus'.format(sdg=kwargs.get('record_id')))
                return{"error": "SDG name {sdg} does not exist in Nautilus. Please e-mail BioRC@email.chop.edu if this SDG should exist.".format(sdg=kwargs.get('record_id'))}
            elif(response.status == 400):
                log.error('Error: SDG name {sdg} could not be processed by Nautilus.'.format(sdg=kwargs.get('record_id')))
                return{"error": "SDG name {sdg} could not be processed by Nautilus. Please e-mail EiGSupport@email.chop.edu and your research coordinator to resolve.".format(sdg=kwargs.get('record_id'))}
            else:
                log.error('Error with Nautilus Webservice when trying to retrieve SDG name {sdg}'.format(sdg=kwargs.get('record_id')))
                return {"error": "Error with Nautilus Webservice when trying to retrieve SDG name {sdg}. Please e-mail BioRC@email.chop.edu, EiGSupport@email.chop.edu and your research coordinator to resolve".format(sdg=kwargs.get('record_id'))}
        try:
            return json.loads(response.read().decode('utf-8'))[0]
        except KeyError:
            try:  # grab error number and process error
                responseDict = json.loads(response.read().decode('utf-8'))
                status = responseDict['error']
                errorMsg = self.NAU_ERROR_MAP.get(status, 'UNKNOWN ERROR')
                log.error(errorMsg)
                return {"error": errorMsg}
            except (KeyError, TypeError):
                log.error('Error retrieving sample data')
                return {"error": "Unable to retrieve sample data."}
        except IndexError:
            if (response == '[]'):
                log.error('Zero samples returned, This SDG does exist in Nautilus but it does not have any aliquots alligned to it.')
                return {"warning": "Zero samples returned, This SDG does exist in Nautilus but it does not have any aliquots aligned to it. reach out to the BioRC if this is unexpected. <a href=\"mailto:BioRC@email.chop.edu\"> BioRC@email.chop.edu"}
            else:
                log.error('Error retrieving sample data.')
                return {"error": "Unable to retrieve sample data. Please contact the data coordinating center or <a href=\"mailto:eigsupport@email.chop.edu\"> eigsupport@email.chop.edu"}
        except:
            log.error('Error retrieving sample data')
            return {"error": "Unable to retrieve sample data. Please contact the data coordinating center or <a href=\"mailto:eigsupport@email.chop.edu\"> eigsupport@email.chop.edu"}

    def extract_aliquots(self, sample_data):
        aliquots = []
        try:
            assert type(sample_data['SDG']['SAMPLE']) is list
            for sample in sample_data['SDG']['SAMPLE']:
                for i in sample['ALIQUOT']:
                    aliquots.append(i)
            return aliquots
        except:
            pass
        try:
            assert type(sample_data['SDG']['SAMPLE']['ALIQUOT']) is dict
            if type(sample_data['SDG']['SAMPLE']['ALIQUOT']) is dict:
                aliquots = [sample_data['SDG']['SAMPLE']['ALIQUOT']]
            return aliquots
        except:
            pass
        try:
            aliquots = sample_data['SDG']['SAMPLE']['ALIQUOT']
        except:
            pass
        return aliquots

    def format_aliquots(self, sample_data):
        type_map = {
            'TISS': 'Tissue',
            'BLD': 'Blood',
            'CBLD': 'Cord Blood',
            'BLDFP': 'Blood Ficoll Pellet',
            'BMA': 'Bone Marrow Aspirate',
            'BMC': 'Bone Marrow Cells',
            'DNA': 'DNA',
            'TUM': 'Tumor Tissue',
            'PBMC': 'PBMC',
            'PHER': 'Pheresate',
            'RNA': 'RNA',
            'CSF': 'Cerebral Spinal Fluid',
            'BMLC': 'Bone Marrow Cells - Left',
            'BMCL': 'Bone Marrow Cells',
            'BMRC': 'Bone Marrow Cells - Right',
            'BSWB': 'Buccal Swab',
            'PLAS': 'Plasma',
            'PLF': 'Pleural Fluid',
            'PHC': 'Apheresis Cells',
            'CELN': 'Cell Line',
            'CELLFRZ': 'Cell Freeze',
            'SAL': 'Saliva',
            'SER': 'Serum',
            'SLD': 'Slide',
            'LYS': 'Lysate',
            'XEN': 'Xenograft',
            'PROT': 'Protein',
            'QC-GEL': 'QC Gel',
            'QC-Xpose': 'QC Xpose',
            'QC-AGIL': 'QC Agilent',
            'STL': 'Stool',
            'URN': 'Urine',
            'URNCP': 'Urine Cell Pellet',
        }
        secondary_type_map = {
            'CELC': 'Cell Culture',
            'CYSF': 'Cyst Fluid',
            'FFRZ': 'Flash Frozen',
            'FRZM': 'Freezing Media',
            'DNA': 'DNA',
            'LEFT': 'Left',
            'RIGHT': 'Right',
            'MAT': 'Maternal',
            'PAT': 'Paternal',
            'SUP': 'Supernant',
            'CELP': 'Cell Pellet',
            'FFPE': 'FFPE',
        }
        for each in sample_data:
            try:
                sample_type = type_map[each['U_SAMPLE_TYPE']]
            except:
                log.debug('Unable to find sample mapping for {0}'.format(
                    each['U_SAMPLE_TYPE']
                ))
                sample_type = ''
            try:
                typ = secondary_type_map[each['U_SECONDARY_SAMPLE_TYPE']]
                secondary_type = typ
            except:
                if each['U_SECONDARY_SAMPLE_TYPE'] != '':
                    log.debug('Unable to find secondary sample mapping for {0}'.format(
                        each['U_SECONDARY_SAMPLE_TYPE']
                    ))
                secondary_type = ''

            each['label'] = '%s %s' % (sample_type, secondary_type)
            each['label'] = each['label'].rstrip(' ')
            if each['STATUS'] == 'U':
                each['STATUS'] = '<p class="text-warning"><em>Unreceived</em></p>'  # noqa
                each['is_received'] = False
            elif each['STATUS'] == 'X':
                each['STATUS'] = '<p class="text-danger"><em>Cancelled</em></p>'  # noqa
            elif each['STATUS'] == 'V' or each['STATUS'] == 'C' or each['STATUS'] == 'P':  # noqa
                if each['U_DISPOSED'] == 'T':
                    each['STATUS'] = '<p class="text-warning"><em>Disposed</em></p>'  # noqa
                elif each['U_ALQ_STATUS'] == 'Virtual':
                    each['STATUS'] = '<p class="text-success"><em>Virtual</em></p>'
                elif each['U_ALQ_STATUS'] == 'Shipped':
                    each['STATUS'] = '<p class="text-success"><em>Shipped</em></p>'
                else:
                    each['STATUS'] = '<p class="text-success"><em>Available</em></p>'  # noqa
                each['is_received'] = True
                try:
                    each['U_RECEIVED_DATE_TIME'] = datetime.datetime.strptime(
                        each['U_RECEIVED_DATE_TIME'], '%d %m %Y %H:%M:%S'
                    )
                except:
                    each['U_RECEIVED_DATE_TIME'] = None
                try:
                    each['U_COLLECT_DATE_TIME'] = datetime.datetime.strptime(
                        each['U_COLLECT_DATE_TIME'], '%d %m %Y %H:%M:%S'
                    )
                except:
                    each['U_COLLECT_DATE_TIME'] = "Unknown"
        return sample_data

    def configure(self, driver_configuration='', *args, **kwargs):
        pass

    def meta(self, *args, **kwargs):
        pass

    def subRecordSelectionForm(self, form_url='', record_id='', *args,
                               **kwargs):
        tpl = open(
            os.path.join(
                os.path.dirname(__file__),
                'templates/sample_display.html'), 'r').read()

        t = Template(tpl)

        # Grab Info about related aliquots here
        sdg = self.get_sample_data(record_id=record_id)
        aliquots = self.extract_aliquots(sdg)
        try:
            aliquots = self.format_aliquots(aliquots)
        except:
            raise
            aliquots = []
        c = {
            'aliquots': aliquots,
        }
        try: # grab error message
            errorMsg = (sdg['error'])
            c = {'error': errorMsg}
            log.error(errorMsg)
        except:
            pass
        html = t.render(c)
        return html

    def subRecordForm(self, external_record, form_spec='', *args, **kwargs):
        pass

    def processForm(self, request, external_record, form_spec='', *args,
                    **kwargs):
        pass

    def new_record_form_required(self):
        '''
        Returns boolean indicating if the user is required to complete a form
        in order to create a new record.

        Since we don't know how to create a record in Nautilus yet, we need to
        show a form where the user can scan in the bar code.
        '''
        return True

    def create_new_record_form(self, request, *args, **kwargs):
        '''
        Should generate a string representation of an html form for creating a
        new record or None if no information is needed from the user to
        generate a new record.
        '''
        fld_sdg_name = '<input type="text" ' + \
            'onkeypress="return disableEnter(event);" name="' + \
            self.FORM_SDG_NAME + '"'

        if request.method == 'POST':
            data = self.extract_data_from_post_request(request)
            sdg_name = data.get(self.FORM_SDG_NAME, '')
            fld_sdg_name += ' value="' + sdg_name + '"'

        fld_sdg_name += '/>'

        form = '<table class="table table-bordered table-striped ' + \
            'table-condensed"><tr><th>Description</th><th>Field</th></tr>' + \
            '<tbody><tr><td>*Enter or Scan Subject ID</td><td>' + \
            fld_sdg_name + '</td></tr></tbody></table>'
        return form

    def process_new_record_form(self, request, record_id_prefix,
                                record_id_validator, *args, **kwargs):
        '''
        Should process new data in new record form and return the record id.
        '''

        # Need to pull sdg_name from the form and check it in with the NauRest
        data = self.extract_data_from_post_request(request)
        sdg_name = data.get(self.FORM_SDG_NAME)

        valid = -1
        if sdg_name:
            sdg_name = str(sdg_name).strip()
            valid = record_id_validator(sdg_name, False)

        valid = (valid == 0) or (valid == 1)
        if sdg_name and valid:
            ex_ref = '{0}:{1}:100'.format(record_id_prefix, sdg_name)
            response = self.update(
                name=sdg_name,
                fldvals={
                    'STATUS': 'V',
                    'EXTERNAL_REFERENCE': ex_ref},
                nau_sub_path='sdg'
            )
            status = json.loads(response.decode('utf-8'))[0].get('status')
            if not str(status) == '200':
                msg = self.NAU_ERROR_MAP.get(status, 'UNKNOWN ERROR')
                raise RecordCreationError(url=self.url,
                                          path='/api/sdg/',
                                          record_id='',
                                          cause=msg)
            # This is a hack until the BRP can create records in Nautilus
            raise IgnoreEhbExceptions(record_id=sdg_name)
        else:
            if sdg_name:
                log.error('subject id {0} has been already assigned to another subject.'.format(sdg_name))  # noqa
                err = 'This Subject ID has been already assigned to another subject.'  # noqa
                raise RecordCreationError(url=self.url,
                                          path=None,
                                          record_id=None,
                                          cause=err)
            else:
                log.error('subject id not provided')
                raise RecordCreationError(url=self.url,
                                          path=None,
                                          record_id=None,
                                          cause='Subject ID is required')
