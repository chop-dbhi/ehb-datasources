import os

from ehb_datasources.drivers.Base import Driver, RequestHandler
from ehb_datasources.drivers.exceptions import RecordCreationError, \
    IgnoreEhbExceptions

from jinja2 import Template

LBL_EDIT_MODAL_TEMPLATE = Template(
    open(os.path.join(
        os.path.dirname(__file__),
        'templates/label_edit_modal.html'), 'rb').read())


class ehbDriver(Driver, RequestHandler):

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
        html = ('<h3 style="color:red"><em>The External ID is saved. ' +
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
        return True

    def create_new_record_form(self, request, *args, **kwargs):
        '''
        Should generate a string representation of an html form for creating a
        new record or None if no information is needed from the user to
        generate a new record.
        '''
        fld_sdg_name = '<input type="text" ' + \
            'onkeypress="return disableEnter(event);" name="ex_id_form"'

        if request.method == 'POST':
            data = self.extract_data_from_post_request(request)
            ex_id = data.get("ex_id_form", '')
            fld_sdg_name += ' value="' + sdg_name + '"'

        fld_sdg_name += '/>'

        form = '<table class="table table-bordered table-striped ' + \
            'table-condensed"><tr><th>Description</th><th>Field</th></tr>' + \
            '<tbody><tr><td>*Enter External ID</td><td>' + \
            fld_sdg_name + '</td></tr></tbody></table>'
        return form

    def process_new_record_form(self, request, record_id_prefix,
                                record_id_validator, *args, **kwargs):
        data = self.extract_data_from_post_request(request)
        ex_id = str(data.get("ex_id_form")).strip()

        valid = -1
        if ex_id:
            valid = record_id_validator(ex_id, False)

        valid = (valid == 0) or (valid == 1)
        if valid:
            return ex_id

    def recordListForm(self, record_urls, records, labels, *args,
                       **kwargs):
        rows = ''
        for url, record in zip(record_urls, records):
            r_lbl = 'Record'
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
                '<tr><th>Record</th><th>Created</th><th>Modified</th></tr>' +
                '</thead><tbody>' + rows + '</tbody></table>' +
                LBL_EDIT_MODAL_TEMPLATE.render({'labels': labels}))
