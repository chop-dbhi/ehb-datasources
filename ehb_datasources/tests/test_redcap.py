import unittest
import os
from datetime import datetime

from ehb_datasources.drivers.redcap.driver import GenericDriver, ehbDriver
from ehb_datasources.drivers.redcap.formBuilderJson import FormBuilderJson
import json
import xml.dom.minidom as xml

from mock import Mock


class RequestResources(object):
    host = 'redcap.vanderbilt.edu'
    path = '/api/'
    isSecure = True
    regular_token = '8E66DB6844D58E990075AFB51658A002'
    token = "1387872621BBF1C17CC47FD8AE25FF54"


class TestDriver(unittest.TestCase, RequestResources):
    def setUp(self):
        self.client = GenericDriver(host=self.host, path=self.path,
                                    token=self.token, secure=self.isSecure)
        self.driver = ehbDriver('https://'+self.host+self.path,
                                password=self.token, secure=self.isSecure)
        self.regular_config = '''{
            "form_names":["demographics", "testing", "imaging"]
        }'''
        self.long_config = '''{
            "unique_event_names": [
                "initial_arm_1",
                "update_one_arm_1",
                "update_two_arm_2"
                ],
            "event_labels": [
                "Initial",
                "Update 1",
                "Update 2"
                ],
            "form_data": {
                "demographics_form": [
                    1,
                    0,
                    0
                ],
                "treatment": [
                    1,
                    1,
                    1
                ]
            },
            "record_id_field_name": "study_id"
        }'''

    def test_configure_regular(self):
        self.assertEqual(self.driver.form_names, None)
        self.driver.configure(self.regular_config)
        self.assertEqual(self.driver.form_names,
                         [u'demographics', u'testing', u'imaging'])

    def test_configure_longitudinal(self):
        pass
        self.assertEqual(self.driver.unique_event_names, None)
        self.assertEqual(self.driver.event_labels, None)
        self.assertEqual(self.driver.form_data, None)
        self.assertEqual(self.driver.form_data_ordered, None)
        self.driver.configure(self.long_config)
        self.assertEqual(self.driver.unique_event_names,
                         [u'initial_arm_1', u'update_one_arm_1',
                          u'update_two_arm_2'])
        unique_event_names = None
        event_labels = None
        form_data = None
        form_data_ordered = None
        form_names = None
        record_id_field_name = None

    def test_longitudinal_srsf(self):
        self.driver.configure(self.long_config)
        srf = '''<table class="table table-bordered table-stripedtable-condensed"><tr><th rowspan="2">Data Collection Instrument</th><th colspan="3">Events</th></tr><tr><td>Initial</td><td>Update 1</td><td>Update 2</td></tr><tr><td> Demographics Form</td><td><button data-toggle="modal"data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href=\'testurl0_0\'">Edit</button></td><td></td><td></td></tr><tr><td> Treatment</td><td><button data-toggle="modal"data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href=\'testurl1_0\'">Edit</button></td><td><button data-toggle="modal"data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href=\'testurl1_1\'">Edit</button></td><td><button data-toggle="modal"data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href=\'testurl1_2\'">Edit</button></td></table>'''  # noqa
        self.assertEqual(srf, self.driver.subRecordSelectionForm('testurl'))

    def test_regular_srsf(self):
        test_config = '''{
            "form_names":["demographics", "testing", "imaging"]
        }'''
        self.driver.configure(self.regular_config)
        srf = '''<table class="table table-bordered table-striped table-condensed"><tr><th>Data Form</th><th></th></tr><tr><td> Demographics</td><td><button data-toggle="modal" data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href='testurl0'">Edit</button></td><tr><td> Testing</td><td><button data-toggle="modal" data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href='testurl1'">Edit</button></td><tr><td> Imaging</td><td><button data-toggle="modal" data-backdrop="static" data-keyboard="false" href="#pleaseWaitModal" class="btn btn-small btn-primary" onclick="location.href='testurl2'">Edit</button></td></table>'''  # noqa
        self.assertEqual(srf, self.driver.subRecordSelectionForm('testurl'))

    def test_regular_srf(self):
        form_builder = FormBuilderJson()
        # Redcap metadata fixture
        metadata = open(
            os.path.join(
                os.path.dirname(__file__),
                'fixtures/regular_project_metadata.json'), 'rb').read()
        # Redcap record fixture
        record_set = open(
            os.path.join(
                os.path.dirname(__file__),
                'fixtures/regular_record_set.json'), 'rb').read()
        # Construct form from fixtures
        html = form_builder.construct_form(json.loads(metadata),
                                           json.loads(record_set),
                                           'demographics',
                                           '1')
        # Load test fixture
        fixture = open(os.path.join(
            os.path.dirname(__file__),
            'fixtures/test_regular_srf.html'), 'rb').read()

        self.assertEqual(html, fixture)

    def test_record_select_form(self):

        record_urls = ['some_url']
        labels = [{'id': '1', 'label': 'Some label'}]
        er = Mock()
        er.id = '1'
        er.record_label = '1'
        er.created = datetime(2000, 1, 1)
        er.modified = datetime(2000, 1, 2)
        records = [er]
        fixture = open(os.path.join(
            os.path.dirname(__file__),
            'fixtures/record_list.html'), 'r').read()

        html = self.driver.recordListForm(None, record_urls, records, labels)
        self.assertEqual(fixture, html)

if __name__ == '__main__':
    unittest.main()
