import base64
import datetime
import json
import logging
import os
import urllib

from jinja2 import Template

from ehb_datasources.drivers.Base import Driver, RequestHandler
from ehb_datasources.drivers.exceptions import RecordCreationError, \
    IgnoreEhbExceptions

log = logging.getLogger('ehb')

LBL_EDIT_MODAL_TEMPLATE = Template(
    open(os.path.join(
        os.path.dirname(__file__),
        'templates/label_edit_modal.html'), 'rb').read())


class ehbDriver(Driver, RequestHandler):

    FORM_SDG_ID = 'SDG_ID'
    FORM_SDG_NAME = 'SDG_NAME'
    NAU_REC_ID = 'id'
    NAU_REC_NAME = 'name'
    NAU_REC_EXT_REF = 'ext-ref'
    VALID_NAU_ELEM_IDENTIFIERS = [NAU_REC_ID, NAU_REC_NAME, NAU_REC_EXT_REF]
    NAU_ERROR_MAP = {
        '0': 'UNKNOWN ERROR',
        '1': 'Unable to login into LIMS',
        '8': 'Form data is not valid'
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
            return path[0:path.__len__()-1]

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
        return 'Basic ' + base64.b64encode(self.username+':'+self.password)

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
        body = [
            {
                rec_key: rec_id,
                "fldvals": fldvals
            }
        ]
        body = json.dumps(body)
        nau_creds = self.encode_nau_creds()
        headers = {
            'Accept': 'application/json',
            'NAUTILUS_CREDS': nau_creds,
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
            'NAUTILUS_CREDS': nau_creds,
            'Content-Type': 'application/json'
        }
        full_path = self.path + 'sdg'
        if not full_path.endswith('/'):
            full_path += '/'
        full_path += '?name={sdg}'.format(sdg=kwargs.get('record_id'))
        response = self.GET(full_path, headers, body).read()
        return json.loads(response)[0]

    def extract_aliquots(self, sample_json):
        aliquots = []
        try:
            assert type(sample_json['SDG']['SAMPLE']) is list
            for sample in sample_json['SDG']['SAMPLE']:
                for i in sample['ALIQUOT']:
                    aliquots.append(i)
            return aliquots
        except:
            pass
        try:
            assert type(sample_json['SDG']['SAMPLE']['ALIQUOT']) is dict
            if type(sample_json['SDG']['SAMPLE']['ALIQUOT']) is dict:
                aliquots = [sample_json['SDG']['SAMPLE']['ALIQUOT']]
            return aliquots
        except:
            pass
        try:
            aliquots = sample_json['SDG']['SAMPLE']['ALIQUOT']
        except:
            pass
        return aliquots

    def format_aliquots(self, sample_json):
        type_map = {
            'TISS': 'Tissue',
            'BLD': 'Blood',
            'BMA': 'Bone Marrow Aspirate',
            'BMC': 'Bone Marrow Cells',
            'DNA': 'DNA',
            'TUM': 'Tumor Tissue',
            'PBMC': 'PBMC',
            'PHER': 'Pheresate',
            'RNA': 'RNS',
            'CSF': 'Cerebral Spinal Fluid',
            'BMLC': 'Bone Marrow Cells - Left',
            'BMCL': 'Bone Marrow Cells',
            'BMRC': 'Bone Marrow Cells - Right',
            'BSWB': 'Buccal Swab',
            'PLAS': 'Plasma',
            'PLF': 'Pleural Fluid',
            'PHC': 'Apheresis Cells'
         }
        secondary_type_map = {
            'CELC': 'Cell Culture',
            'FFRZ': 'Flash Frozen',
            'FRZM': 'Freezing Media',
            'DNA': 'DNA',
            'LEFT': 'Left',
            'RIGHT': 'Right',
            'MAT': 'Maternal',
            'PAT': 'Paternal'
        }
        for each in sample_json:
            try:
                sample_type = type_map[each['U_SAMPLE_TYPE']]
            except:
                sample_type = ''
            try:
                typ = secondary_type_map[each['U_SECONDARY_SAMPLE_TYPE']]
                secondary_type = typ
            except:
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
        return sample_json

    def configure(self, driver_configuration='', *args, **kwargs):
        pass

    def meta(self, *args, **kwargs):
        pass

    def subRecordSelectionForm(self, form_url='', record_id='', *args,
                               **kwargs):
        tpl = open(
            os.path.join(
                os.path.dirname(__file__),
                'templates/sample_display.html'), 'rb').read()

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
        html = t.render(c)
        return html

    def printLabels(self, aliquot_id, dest_printer, fmt, pds):
        nau_creds = self.encode_nau_creds()
        headers = {
            'Accept': 'application/json',
            'NAUTILUS_CREDS': nau_creds,
            'Content-Type': 'application/json'
        }
        full_path = self.path + 'label/'
        body = pds.driver_configuration
        f = {
            'aliq_id': aliquot_id,
            'dest_printer': dest_printer,
            'fmt': fmt
        }
        query = urllib.urlencode(f)

        full_path += '?{query}'.format(query=query)

        response = self.POST(full_path, headers, body).read()

        return response

    def subRecordForm(self, external_record, form_spec='', *args, **kwargs):
        html = '<h3><em>Print Labels</em></h3><br/><br/><button class="btn' + \
            'btn-primary">Print labels for this sample group</button><br><br>'
        return html

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
        sdg_name = str(data.get(self.FORM_SDG_NAME)).strip()

        valid = -1
        if sdg_name:
            valid = record_id_validator(sdg_name, False)

        valid = (valid == 0) or (valid == 1)
        if sdg_name and valid:
            ex_ref = record_id_prefix+':'+sdg_name+':'+'100'
            response = self.update(
                name=sdg_name,
                fldvals={
                    'STATUS': 'V',
                    'EXTERNAL_REFERENCE': ex_ref},
                nau_sub_path='sdg'
            )
            status = json.loads(response)[0].get('status')
            if not status == '200':
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

    def recordListForm(self, record_urls, records, labels, *args,
                       **kwargs):
        rows = ''
        for url, record in zip(record_urls, records):
            r_lbl = 'Sample'
            for label in labels:
                if (
                    record['label'] == label['id'] and
                    record['label'] != 1
                ):
                    r_lbl = label['label']
            rows += ('<tr><td><a href="{url}"><span id="{id}_label">{label}' +
                     '</span></a>\t<a href="#" data-target="#labelUpdate" ' +
                     'data-toggle="modal" data-id={id}><span class="" ' +
                     'style="font-size:.7em">[edit label]</span></a></td>' +
                     '<td>{created}</td><td>{modified}</td></tr>').format(
                url=url,
                label=r_lbl,
                id=record['id'],
                created=record['created'],
                modified=record['modified']
            )

        return ('<table class="table table-bordered table-striped"><thead>' +
                '<tr><th>Sample</th><th>Created</th><th>Modified</th></tr>' +
                '</thead><tbody>' + rows + '</tbody></table>' +
                LBL_EDIT_MODAL_TEMPLATE.render({'labels': labels}))
