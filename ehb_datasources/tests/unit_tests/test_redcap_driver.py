import pytest
import xml

from urllib.parse import parse_qs
from http.client import HTTPResponse
from ehb_datasources.drivers.Base import random
from ehb_datasources.drivers.redcap.driver import ehbDriver
from ehb_datasources.drivers.exceptions import ServerError, RecordDoesNotExist, \
    PageNotFound, RecordCreationError

@pytest.fixture()
def driver():
    return ehbDriver(
        url='http://example.com/api/',
        password='foo',
    )


def test_initialization(driver):
    assert driver.host == 'example.com'
    assert driver.path == '/api/'


def test_read_metadata(mocker, driver, redcap_metadata_json):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value=redcap_metadata_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    meta = driver.meta()
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=metadata&format=json&token=foo')
    assert isinstance(meta, list)
    assert len(meta) == 26


def test_read_metadata_raw(mocker, driver, redcap_metadata_json):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value=redcap_metadata_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    meta = driver.meta(rawResponse=True)
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=metadata&format=json&token=foo')
    assert isinstance(meta, bytes)


def test_get_raw_json(mocker, driver, redcap_record_json):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    rv = driver.get(
        record_id='0GUQDBCDE0EAWN9Q:8LAG76CHO',
        _format='json',
        rawResponse=True
    )
    data = rv.read()
    assert isinstance(data, bytes)
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=record&format=json&token=foo&type=flat&records=0GUQDBCDE0EAWN9Q%3A8LAG76CHO')


def test_get_transformed_json(mocker, driver, redcap_record_json):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    rv = driver.get(
        record_id='0GUQDBCDE0EAWN9Q:8LAG76CHO',
        _format='json',
        rawResponse=False
    )
    assert isinstance(rv, list)
    assert isinstance(rv[0], dict)
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=record&format=json&token=foo&type=flat&records=0GUQDBCDE0EAWN9Q%3A8LAG76CHO')


def test_get_raw_xml(mocker, driver, redcap_record_xml):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_xml)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    rv = driver.get(
        record_id='0GUQDBCDE0EAWN9Q:8LAG76CHO',
        _format='xml',
        rawResponse=True
    )
    data = rv.read()
    assert isinstance(data, bytes)
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=record&format=xml&token=foo&type=flat&records=0GUQDBCDE0EAWN9Q%3A8LAG76CHO')


def test_get_processed_xml(mocker, driver, redcap_record_xml):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_xml)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    rv = driver.get(
        record_id='0GUQDBCDE0EAWN9Q:8LAG76CHO',
        _format='xml',
        rawResponse=False
    )

    assert isinstance(rv, xml.dom.minidom.Document)
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=record&format=xml&token=foo&type=flat&records=0GUQDBCDE0EAWN9Q%3A8LAG76CHO')


def test_get_with_fields_and_forms(mocker, driver, redcap_record_fields_specified):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value=redcap_record_fields_specified)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    rv = driver.get(
        record_id='0GUQDBCDE0EAWN9Q:8LAG76CHO',
        _format='json',
        rawResponse=False,
        fields=['height', 'weight']
    )
    assert isinstance(rv, list)
    assert isinstance(rv[0], dict)
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded'},
        'content=record&format=json&token=foo&type=flat&records=0GUQDBCDE0EAWN9Q%3A8LAG76CHO&fields=height%2Cweight')


def test_create(mocker, driver, redcap_metadata_xml):
    driver.POST = mocker.MagicMock()
    # patch metadata call
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    # patch create records call
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    # patch create random id
    driver.create_random_record_id = mocker.MagicMock(return_value='deadbeef')
    driver.create(
        record_id_prefix='0GUQDBCDE0EAWN9Q',
        record_id_validator=True)
    driver.meta.assert_called_with(_format='xml')
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22UTF-8%22%3F%3E%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3Adeadbeef%5D%5D%3E%3C%2Fstudy_id%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=normal&returnFormat=json&token=foo&type=flat')



def test_create_rce(mocker, driver, redcap_metadata_xml):
    driver.POST = mocker.MagicMock()
    # patch metadata call
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    # patch create records call
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    # patch create random id
    driver.create_random_record_id = mocker.MagicMock(return_value='deadbeef')
    # mock write_records response
    driver.write_records = mocker.MagicMock(return_value=2)
    with pytest.raises(RecordCreationError):
        driver.create(
            record_id_prefix='0GUQDBCDE0EAWN9Q',
            record_id_validator=True)
    driver.meta.assert_called_with(_format='xml')
    driver.POST.assert_not_called


def test_create_w_mocked_validate(mocker, driver, redcap_metadata_xml):
    driver.POST = mocker.MagicMock()
    # patch metadata call
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    # patch create records call
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    driver.get = mocker.MagicMock(
        return_value='',
        side_effect=RecordDoesNotExist('/api/', 'test', 1)
    )
    # mock random to make tests repeatable
    random.choice = mocker.MagicMock(return_value='X')
    driver.create(
        record_id_prefix='0GUQDBCDE0EAWN9Q',
        record_id_validator=True)
    driver.meta.assert_called_with(_format='xml')
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22UTF-8%22%3F%3E%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3AXXXXXXXXX%5D%5D%3E%3C%2Fstudy_id%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=normal&returnFormat=json&token=foo&type=flat')


def test_create_w_mocked_validate_record_exists(mocker, driver, redcap_metadata_xml):
    driver.POST = mocker.MagicMock()
    # patch metadata call
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    # patch create records call
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    driver.get = mocker.MagicMock(
        return_value='Some Record',
    )
    # mock random to make tests repeatable
    random.choice = mocker.MagicMock(return_value='X')
    driver.create(
        record_id_prefix='0GUQDBCDE0EAWN9Q',
        record_id='XXXX',
        record_id_validator=True)
    driver.meta.assert_called_with(_format='xml')
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22UTF-8%22%3F%3E%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3AXXXX%5D%5D%3E%3C%2Fstudy_id%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=normal&returnFormat=json&token=foo&type=flat')


def test_create_w_mocked_validate_record_isnone(mocker, driver, redcap_metadata_xml):
    driver.POST = mocker.MagicMock()
    # patch metadata call
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    # patch create records call
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    driver.get = mocker.MagicMock(
        return_value=None,
    )
    # Should create a record with the provided record_id
    driver.create(
        record_id_prefix='0GUQDBCDE0EAWN9Q',
        record_id='XXXX',
        record_id_validator=True)
    driver.meta.assert_called_with(_format='xml')
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22UTF-8%22%3F%3E%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3AXXXX%5D%5D%3E%3C%2Fstudy_id%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=normal&returnFormat=json&token=foo&type=flat')


def test_create_w_mocked_validate_404(mocker, driver, redcap_metadata_xml):
    driver.POST = mocker.MagicMock()
    # patch metadata call
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    # patch create records call
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(
        return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    driver.get = mocker.MagicMock(
        return_value=None,
        side_effect=PageNotFound('/test_path/')
    )
    # Should create a record with the provided record_id
    driver.create(
        record_id_prefix='0GUQDBCDE0EAWN9Q',
        record_id_validator=True)
    driver.meta.assert_called_with(_format='xml')
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22UTF-8%22%3F%3E%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3AXXXXXXXXX%5D%5D%3E%3C%2Fstudy_id%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=normal&returnFormat=json&token=foo&type=flat')


def test_configure_longitudinal(driver, driver_configuration_long):
    driver.configure(driver_configuration_long)
    assert driver.form_data_ordered == ['baseline_visit_data', 'meal_description_form']
    assert driver.unique_event_names == [
        'visit_arm_1',
        'breakfast_at_visit_arm_1',
        'lunch_at_visit_arm_1',
        'dinner_at_visit_arm_1']
    assert driver.event_labels == ['Visit Baseline', 'Breakfast', 'Lunch', 'Dinner']
    assert driver.form_data == {
        'baseline_visit_data': [True, False, False, False],
        'meal_description_form': [False, True, True, True]}


def test_configure_nonlongitudinal(driver, driver_configuration_nonlong):
    driver.configure(driver_configuration_nonlong)
    assert driver.form_data_ordered == ['demographics', 'baseline_data']
    assert driver.unique_event_names is None
    assert driver.event_labels is None
    assert driver.form_data is None


def test_configure_viakwargs(driver):
    driver.configure(
        unique_event_names=['event_1_arm_1', 'event_1_arm_2'],
        event_labels=['Event 1', 'Event 2'],
        form_event_data=[''],
        form_names=['']
    )
    # TODO
    # assert driver.form_data_ordered == ['demographics', 'baseline_data']
    # assert driver.unique_event_names == ['event_1_arm_1']
    # assert driver.event_labels == ['Baseline Data']
    # assert driver.form_data == {'baseline_data': [True], 'demographics': [True]}


def test_srf_longitudinal_noformspec(mocker, driver, driver_configuration_long):
    external_record = mocker.MagicMock(
        id=1
    )
    driver.configure(driver_configuration_long)
    assert driver.subRecordForm(external_record) is None


def test_srf_bad_config(mocker, driver, driver_configuration_long):
    external_record = mocker.MagicMock(
        id=1
    )
    # Bad key combination
    driver.configure(
        event_labels=['Label 1'],
        unique_event_names=['event_1'],
        form_data=['data'])
    # Should return None due to lack of form_names
    assert driver.subRecordForm(external_record, form_spec='0_0') is None
    # Bad form_spec
    driver.configure(
        form_names=['test_form']
    )
    assert driver.subRecordForm(external_record, form_spec='0_Z') is None
    # Bad form_spec index no form_names
    driver.configure(
        form_data_ordered=['health_log', 'misc_log']
    )
    assert driver.subRecordForm(external_record, form_spec='1_0') is None
    # Bad form_spec index
    driver.configure(driver_configuration_long)
    assert driver.subRecordForm(external_record, form_spec='4_0') is None
    driver.configure(
        form_names=['test_form']
    )
    assert driver.subRecordForm(external_record, form_spec='4_0') is None


def test_srf_long(mocker, driver, driver_configuration_long, redcap_metadata_json, redcap_record_json):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata request
    driver.meta = mocker.MagicMock(return_value=redcap_metadata_json)
    driver.configure(driver_configuration_long)
    # Record Request
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    form = driver.subRecordForm(external_record, form_spec='1_3')
    assert '<td><div>Meal Description</div><div style="color:red; font-size:12px;"></div></td>' in form


def test_srf_nonlong(mocker, driver, driver_configuration_nonlong, redcap_metadata_json, redcap_record_json):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata request
    driver.meta = mocker.MagicMock(return_value=redcap_metadata_json)
    driver.configure(driver_configuration_nonlong)
    # Record Request
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    form = driver.subRecordForm(external_record, form_spec='0_0')
    assert '<table class="table table-bordered table-striped table-condensed"><tr><th colspan="2">Consent Information</th></tr>' in form


def test_srsf_long(mocker, driver, driver_configuration_long, redcap_metadata_json, redcap_record_json):
    # Mocks
    # Metadata request
    driver.meta = mocker.MagicMock(return_value=redcap_metadata_json)
    driver.configure(driver_configuration_long)
    # Record Request
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    form = driver.subRecordSelectionForm(form_url='/test/')
    assert '/test/1_3' in form
    assert '/test/0_0' in form


def test_srsf_nonlong(mocker, driver, driver_configuration_nonlong, redcap_metadata_json, redcap_record_json):
    # Mocks
    # Metadata request
    driver.meta = mocker.MagicMock(return_value=redcap_metadata_json)
    driver.configure(driver_configuration_nonlong)
    # Record Request
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=redcap_record_json)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    form = driver.subRecordSelectionForm(form_url='/test/')
    assert '/test/1' in form
    assert '/test/0' in form


def test_process_form_norec_or_spec(mocker, driver, driver_configuration_long, redcap_metadata_json):
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    driver.meta = mocker.MagicMock(return_value=redcap_metadata_json)
    driver.configure(driver_configuration_long)
    request = mocker.MagicMock()
    request.POST = mocker.MagicMock(return_value='garbage')

    errors = driver.processForm(request, external_record)
    assert 'external record and form_spec must be supplied' in errors


def test_process_form_bad_formspec(mocker, driver, driver_configuration_long, redcap_metadata_json):
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    driver.meta = mocker.MagicMock(return_value=redcap_metadata_json)
    driver.configure(driver_configuration_long)
    request = mocker.MagicMock()
    request.POST = mocker.MagicMock(return_value='garbage')

    errors = driver.processForm(request, external_record, form_spec='9_0')
    assert 'Invalid event or form numbers in REDCap driver' in errors


def test_process_form(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert errors is None


def test_process_form_nonlong(mocker, driver, driver_configuration_nonlong, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_nonlong)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert errors is None


def test_process_form_multirecreturned(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(return_value=2)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert 'Unknown error. REDCap reports multiple records wereupdated, should have only been 1.' in errors


def test_process_form_badrcresponse(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(side_effect=ServerError)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert 'Parse error. REDCap response is an unknown format. Please contact system administrator.' in errors


def test_process_form_bad_metadata_norecordid(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=xml.dom.minidom.parseString('<records><item><field_name></field_name></item></records>'))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert 'REDCap Driver could not obtain the REDCap record id field from the metadata' in errors


def test_process_form_bad_metadata_norecords(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=xml.dom.minidom.parseString('<error></error>'))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert 'The meta data was not found for the specified REDCap record' in errors


def test_process_form_w_session(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    session = mocker.MagicMock()
    session.get = mocker.MagicMock(return_value={
        'chrons': {'type': 'text'},
        'meds___3': {'type': 'checkbox'},
        'chol_b': {'type': 'text'},
        'creat_b': {'type': 'text'},
        'meds___1': {'type': 'checkbox'},
        'prealb_b': {'type': 'text'},
        'comments': {'type': 'notes'},
        'meal_date': {'type': 'text'},
        'colonoscopy_date': {'type': 'text'},
        'height': {'type': 'text'},
        'transferrin_b': {'type': 'text'},
        'general_ibd': {'type': 'text'},
        'meds___2': {'type': 'checkbox'},
        'meds___5': {'type': 'checkbox'},
        'colonoscopy': {'type': 'yesno'},
        'ulcerative_colitis': {'type': 'text'},
        'weight': {'type': 'text'},
        'meds___4': {'type': 'checkbox'},
        'foo': {'type': 'slider'},
        'ibd_flag': {'type': 'yesno'}
    })
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))

    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0', session=session)
    session.get.assert_called_with('baseline_visit_data_fields', None)
    assert errors is None


def test_process_form_nodata(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=None)
    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert 'No data in request' in errors


def test_process_form_baddriver(mocker, driver, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure()
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))
    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='0_0')
    assert 'REDCap driver not configured.' in errors


def test_process_form_badspec_nonlong(mocker, driver, driver_configuration_nonlong, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_nonlong)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))
    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='Z_0')
    assert 'REDCap Driver form_spec argument is invalid' in errors


def test_process_form_badspec_long(mocker, driver, driver_configuration_long, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_long)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))
    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='Z_0')
    assert 'REDCap Driver form_spec argument is invalid' in errors


def test_process_form_badspec_nonlong_out_of_range(mocker, driver, driver_configuration_nonlong, redcap_metadata_xml, redcap_form_datastring):
    # Mocks
    # External Record
    external_record = mocker.MagicMock(
        id=1
    )
    # Metadata Mock
    driver.meta = mocker.MagicMock(
        return_value=driver.transformResponse('xml', redcap_metadata_xml))
    driver.configure(driver_configuration_nonlong)
    # Request Mock
    request = mocker.MagicMock(POST=parse_qs(redcap_form_datastring))
    driver.write_records = mocker.MagicMock(return_value=1)
    errors = driver.processForm(request, external_record, form_spec='8_0')
    assert 'Invalid event or form numbers in REDCap driver' in errors


def test_write_records(mocker, driver, redcap_payload):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value='<count>1</count>')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    record_count = driver.write_records(
        data=redcap_payload,
        overwrite=driver.OVERWRITE_OVERWRITE,
        useRawData=True
    )
    assert record_count == 1
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3A8LAG76CHO%5D%5D%3E%3C%2Fstudy_id%3E%3Credcap_event_name%3E%3C%21%5BCDATA%5Bvisit_arm_1%5D%5D%3E%3C%2Fredcap_event_name%3E%3Ccolonoscopy_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fcolonoscopy_date%3E%3Cgeneral_ibd%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fgeneral_ibd%3E%3Ctransferrin_b%3E%3C%21%5BCDATA%5B102%5D%5D%3E%3C%2Ftransferrin_b%3E%3Cmeds___2%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___2%3E%3Cmeal_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fmeal_date%3E%3Culcerative_colitis%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fulcerative_colitis%3E%3Cmeds___1%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fmeds___1%3E%3Ccomments%3E%3C%21%5BCDATA%5BTest+Data%5D%5D%3E%3C%2Fcomments%3E%3Cweight%3E%3C%21%5BCDATA%5B20%5D%5D%3E%3C%2Fweight%3E%3Cchrons%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fchrons%3E%3Cchol_b%3E%3C%21%5BCDATA%5B101%5D%5D%3E%3C%2Fchol_b%3E%3Ccolonoscopy%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fcolonoscopy%3E%3Cprealb_b%3E%3C%21%5BCDATA%5B19%5D%5D%3E%3C%2Fprealb_b%3E%3Cheight%3E%3C%21%5BCDATA%5B100%5D%5D%3E%3C%2Fheight%3E%3Ccreat_b%3E%3C%21%5BCDATA%5B0.6%5D%5D%3E%3C%2Fcreat_b%3E%3Cibd_flag%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fibd_flag%3E%3Cmeds___5%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___5%3E%3Cmeds___4%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___4%3E%3Cmeds___3%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___3%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=overwrite&returnFormat=json&token=foo&type=flat'
    )


def test_write_records_intstringresp(mocker, driver, redcap_payload):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value='1')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    record_count = driver.write_records(
        data=redcap_payload,
        overwrite=driver.OVERWRITE_OVERWRITE,
        useRawData=True
    )
    assert record_count == 1
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3A8LAG76CHO%5D%5D%3E%3C%2Fstudy_id%3E%3Credcap_event_name%3E%3C%21%5BCDATA%5Bvisit_arm_1%5D%5D%3E%3C%2Fredcap_event_name%3E%3Ccolonoscopy_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fcolonoscopy_date%3E%3Cgeneral_ibd%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fgeneral_ibd%3E%3Ctransferrin_b%3E%3C%21%5BCDATA%5B102%5D%5D%3E%3C%2Ftransferrin_b%3E%3Cmeds___2%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___2%3E%3Cmeal_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fmeal_date%3E%3Culcerative_colitis%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fulcerative_colitis%3E%3Cmeds___1%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fmeds___1%3E%3Ccomments%3E%3C%21%5BCDATA%5BTest+Data%5D%5D%3E%3C%2Fcomments%3E%3Cweight%3E%3C%21%5BCDATA%5B20%5D%5D%3E%3C%2Fweight%3E%3Cchrons%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fchrons%3E%3Cchol_b%3E%3C%21%5BCDATA%5B101%5D%5D%3E%3C%2Fchol_b%3E%3Ccolonoscopy%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fcolonoscopy%3E%3Cprealb_b%3E%3C%21%5BCDATA%5B19%5D%5D%3E%3C%2Fprealb_b%3E%3Cheight%3E%3C%21%5BCDATA%5B100%5D%5D%3E%3C%2Fheight%3E%3Ccreat_b%3E%3C%21%5BCDATA%5B0.6%5D%5D%3E%3C%2Fcreat_b%3E%3Cibd_flag%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fibd_flag%3E%3Cmeds___5%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___5%3E%3Cmeds___4%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___4%3E%3Cmeds___3%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___3%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=overwrite&returnFormat=json&token=foo&type=flat'
    )


def test_write_records_intresp(mocker, driver, redcap_payload):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=200)
    MockREDCapResponse.read = mocker.MagicMock(return_value=1)
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    record_count = driver.write_records(
        data=redcap_payload,
        overwrite=driver.OVERWRITE_OVERWRITE,
        useRawData=True
    )
    assert record_count == 1
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3A8LAG76CHO%5D%5D%3E%3C%2Fstudy_id%3E%3Credcap_event_name%3E%3C%21%5BCDATA%5Bvisit_arm_1%5D%5D%3E%3C%2Fredcap_event_name%3E%3Ccolonoscopy_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fcolonoscopy_date%3E%3Cgeneral_ibd%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fgeneral_ibd%3E%3Ctransferrin_b%3E%3C%21%5BCDATA%5B102%5D%5D%3E%3C%2Ftransferrin_b%3E%3Cmeds___2%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___2%3E%3Cmeal_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fmeal_date%3E%3Culcerative_colitis%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fulcerative_colitis%3E%3Cmeds___1%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fmeds___1%3E%3Ccomments%3E%3C%21%5BCDATA%5BTest+Data%5D%5D%3E%3C%2Fcomments%3E%3Cweight%3E%3C%21%5BCDATA%5B20%5D%5D%3E%3C%2Fweight%3E%3Cchrons%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fchrons%3E%3Cchol_b%3E%3C%21%5BCDATA%5B101%5D%5D%3E%3C%2Fchol_b%3E%3Ccolonoscopy%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fcolonoscopy%3E%3Cprealb_b%3E%3C%21%5BCDATA%5B19%5D%5D%3E%3C%2Fprealb_b%3E%3Cheight%3E%3C%21%5BCDATA%5B100%5D%5D%3E%3C%2Fheight%3E%3Ccreat_b%3E%3C%21%5BCDATA%5B0.6%5D%5D%3E%3C%2Fcreat_b%3E%3Cibd_flag%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fibd_flag%3E%3Cmeds___5%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___5%3E%3Cmeds___4%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___4%3E%3Cmeds___3%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___3%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=overwrite&returnFormat=json&token=foo&type=flat'
    )


def test_write_records_badresp(mocker, driver, redcap_payload):
    MockREDCapResponse = mocker.MagicMock(
        spec=HTTPResponse,
        status=500)
    MockREDCapResponse.read = mocker.MagicMock(return_value='<error>Unknown Error</error>')
    driver.POST = mocker.MagicMock(return_value=MockREDCapResponse)
    with pytest.raises(ServerError):
        driver.write_records(
            data=redcap_payload,
            overwrite=driver.OVERWRITE_OVERWRITE,
            useRawData=True
        )
    driver.POST.assert_called_with(
        '/api/',
        {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'text/xml'},
        'content=record&data=%3Crecords%3E%3Citem%3E%3Cstudy_id%3E%3C%21%5BCDATA%5B0GUQDBCDE0EAWN9Q%3A8LAG76CHO%5D%5D%3E%3C%2Fstudy_id%3E%3Credcap_event_name%3E%3C%21%5BCDATA%5Bvisit_arm_1%5D%5D%3E%3C%2Fredcap_event_name%3E%3Ccolonoscopy_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fcolonoscopy_date%3E%3Cgeneral_ibd%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fgeneral_ibd%3E%3Ctransferrin_b%3E%3C%21%5BCDATA%5B102%5D%5D%3E%3C%2Ftransferrin_b%3E%3Cmeds___2%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___2%3E%3Cmeal_date%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fmeal_date%3E%3Culcerative_colitis%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fulcerative_colitis%3E%3Cmeds___1%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fmeds___1%3E%3Ccomments%3E%3C%21%5BCDATA%5BTest+Data%5D%5D%3E%3C%2Fcomments%3E%3Cweight%3E%3C%21%5BCDATA%5B20%5D%5D%3E%3C%2Fweight%3E%3Cchrons%3E%3C%21%5BCDATA%5B2016-08-31%5D%5D%3E%3C%2Fchrons%3E%3Cchol_b%3E%3C%21%5BCDATA%5B101%5D%5D%3E%3C%2Fchol_b%3E%3Ccolonoscopy%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fcolonoscopy%3E%3Cprealb_b%3E%3C%21%5BCDATA%5B19%5D%5D%3E%3C%2Fprealb_b%3E%3Cheight%3E%3C%21%5BCDATA%5B100%5D%5D%3E%3C%2Fheight%3E%3Ccreat_b%3E%3C%21%5BCDATA%5B0.6%5D%5D%3E%3C%2Fcreat_b%3E%3Cibd_flag%3E%3C%21%5BCDATA%5B1%5D%5D%3E%3C%2Fibd_flag%3E%3Cmeds___5%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___5%3E%3Cmeds___4%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___4%3E%3Cmeds___3%3E%3C%21%5BCDATA%5B0%5D%5D%3E%3C%2Fmeds___3%3E%3C%2Fitem%3E%3C%2Frecords%3E&format=xml&overwriteBehavior=overwrite&returnFormat=json&token=foo&type=flat'
    )
