import pytest

from ehb_datasources.drivers.nautilus.driver import ehbDriver
from ehb_datasources.drivers.exceptions import RecordCreationError, \
    IgnoreEhbExceptions


@pytest.fixture()
def driver():
    return ehbDriver(
        url='http://example.com/api/',
        user='foo',
        password='bar',
        secure=False
    )


def test_initialization(driver):
    assert driver.host == 'example.com'
    assert driver.path == '/api/'


def test_encode_nau_creds(driver):
    assert driver.encode_nau_creds() == 'Basic Zm9vOmJhcg=='


def test_update(driver, mocker):
    # Mocks
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=b'[\n    {\n        "name": "7316-118", \n        "status": "200", \n        "type": "SDG"\n    }\n]')
    kwargs = {'fldvals': {'EXTERNAL_REFERENCE': '2J25I1QYGRU1DCTA:7316-118:100', 'STATUS': 'V'}, 'name': '7316-118', 'nau_sub_path': 'sdg'}
    driver.PUT = mocker.MagicMock(return_value=MockNautilusResponse)
    # Test
    response = driver.update(kwargs)
    driver.PUT.assert_called_with(
        '/api/',
        {'Content-Type': 'application/json', 'NAUTILUS_CREDS': 'Basic Zm9vOmJhcg==', 'Accept': 'application/json'},
        '[{"null": null, "fldvals": {}}]'
    )
    assert response == b'[\n    {\n        "name": "7316-118", \n        "status": "200", \n        "type": "SDG"\n    }\n]'


def test_update_fix_path(driver, mocker):
    # Mocks
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=b'[\n    {\n        "name": "7316-118", \n        "status": "200", \n        "type": "SDG"\n    }\n]')
    kwargs = {'fldvals': {'EXTERNAL_REFERENCE': '2J25I1QYGRU1DCTA:7316-118:100', 'STATUS': 'V'}, 'name': '7316-118', 'nau_sub_path': 'sdg'}
    driver.path = '/api'
    driver.PUT = mocker.MagicMock(return_value=MockNautilusResponse)
    # Test
    response = driver.update(kwargs)
    driver.PUT.assert_called_with(
        '/api/',
        {'Content-Type': 'application/json', 'NAUTILUS_CREDS': 'Basic Zm9vOmJhcg==', 'Accept': 'application/json'},
        '[{"null": null, "fldvals": {}}]'
    )
    assert response == b'[\n    {\n        "name": "7316-118", \n        "status": "200", \n        "type": "SDG"\n    }\n]'


def test_get_sample_data(driver, mocker, nautilus_get_sample_payload):
    # Mocks
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=nautilus_get_sample_payload)
    driver.GET = mocker.MagicMock(return_value=MockNautilusResponse)
    # Test
    response = driver.get_sample_data(record_id='TESTID')
    assert 'SDG' in response.keys()
    assert isinstance(response, dict)


def test_get(driver):
    assert not driver.get()


def test_delete(driver):
    assert not driver.delete()


def test_create(driver):
    assert not driver.create('foo', 'bar')


def test_meta(driver):
    assert not driver.meta()


def test_configure(driver):
    assert not driver.configure()


def test_process_form(driver):
    assert not driver.processForm(None, 'foo')


def test_record_new_record_form_required(driver):
    assert driver.new_record_form_required()


def test_get_sample_data_error(driver, mocker, nautilus_get_sample_payload):
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=b'{"error": 6}')
    driver.GET = mocker.MagicMock(return_value=MockNautilusResponse)
    response = driver.get_sample_data(record_id='TESTID')
    assert 'error' in response.keys()
    assert isinstance(response, dict)


def test_extract_aliquots(driver, mocker, nautilus_get_sample_payload):
    # TODO: Needs more mock responses as Nautilus response _will_ vary project
    # to project
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=nautilus_get_sample_payload)
    driver.GET = mocker.MagicMock(return_value=MockNautilusResponse)
    response = driver.get_sample_data(record_id='TESTID')
    aliquots = driver.extract_aliquots(response)
    assert len(aliquots) == 4
    assert len(aliquots[0].keys()) == 89


def test_format_aliquots(driver, mocker, nautilus_get_sample_payload):
    # TODO: Needs more mock responses as Nautilus response _will_ vary project
    # to project
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=nautilus_get_sample_payload)
    driver.GET = mocker.MagicMock(return_value=MockNautilusResponse)
    response = driver.get_sample_data(record_id='TESTID')
    aliquots = driver.extract_aliquots(response)
    formatted_aliquots = driver.format_aliquots(aliquots)
    assert len(formatted_aliquots) == 4
    assert aliquots[0].keys() == formatted_aliquots[0].keys()
    assert aliquots[0]['label'] == 'Blood'
    assert aliquots[0]['STATUS'] == '<p class="text-warning"><em>Disposed</em></p>'
    assert aliquots[1]['STATUS'] == '<p class="text-success"><em>Available</em></p>'
    assert aliquots[1]['U_RECEIVED_DATE_TIME'] is None
    assert aliquots[1]['U_COLLECT_DATE_TIME'] == 'Unknown'
    assert aliquots[2]['STATUS'] == '<p class="text-warning"><em>Unreceived</em></p>'
    assert aliquots[3]['STATUS'] == '<p class="text-danger"><em>Cancelled</em></p>'
    assert len(formatted_aliquots[0].keys()) == 91


def test_srsf(driver, mocker, nautilus_get_sample_payload):
    # Mocks
    MockNautilusResponse = mocker.MagicMock(
        status=200
    )
    MockNautilusResponse.read = mocker.MagicMock(return_value=nautilus_get_sample_payload)
    driver.GET = mocker.MagicMock(return_value=MockNautilusResponse)
    form = driver.subRecordSelectionForm(form_url='/test/', record_id='foo')
    assert '<td>Blood<small class="text-muted"> <small style="font-size:1em"> -- Collected On: 1901-01-01 14:30:19 -- Received On: 2015-03-11 14:35:07</small><span class="label label-primary pull-right muted">7316-118-BLD [108880]</span></td><td align="center"><p class="text-warning"><em>Disposed</em></p></td>' in form
    assert '<td>Blood<small class="text-muted"> <small style="font-size:1em"> -- Collected On: Unknown -- Received On: None</small><span class="label label-primary pull-right muted">7316-118-BLD [108881]</span></td><td align="center"><p class="text-success"><em>Available</em></p></td>' in form
    assert '<td><span class="label label-primary pull-right muted">7316-118-BLD [108882]</span></td><td align="center"><p class="text-warning"><em>Unreceived</em></p></td>' in form
    assert '<td>Blood Flash Frozen<span class="label label-primary pull-right muted">7316-118-BLD [108881]</span></td><td align="center"><p class="text-danger"><em>Cancelled</em></p></td>' in form


def test_srf(driver):
    assert not driver.subRecordForm(None)


def test_create_new_record_form_get(driver, mocker):
    request = mocker.MagicMock(
        method='GET'
    )
    form = driver.create_new_record_form(request)
    assert form == '<table class="table table-bordered table-striped table-condensed"><tr><th>Description</th><th>Field</th></tr><tbody><tr><td>*Enter or Scan Subject ID</td><td><input type="text" onkeypress="return disableEnter(event);" name="SDG_NAME"/></td></tr></tbody></table>'


def test_create_new_record_form_post(driver, mocker):
    request = mocker.MagicMock(
        method='POST',
        _post={'SDG_NAME': '7316-118', 'csrfmiddlewaretoken': 'foo', 'label_id': '1'}
    )
    form = driver.create_new_record_form(request)
    assert form == '<table class="table table-bordered table-striped table-condensed"><tr><th>Description</th><th>Field</th></tr><tbody><tr><td>*Enter or Scan Subject ID</td><td><input type="text" onkeypress="return disableEnter(event);" name="SDG_NAME" value="7316-118"/></td></tr></tbody></table>'


def test_process_new_record_form(driver, mocker):
    request = mocker.MagicMock(
        method='POST',
        _post={'SDG_NAME': '7316-118', 'csrfmiddlewaretoken': 'foo', 'label_id': '1'}
    )
    driver.update = mocker.MagicMock(return_value=b'[{"status": "200"}]')
    validator_func = mocker.MagicMock(return_value=0)
    with pytest.raises(IgnoreEhbExceptions) as excinfo:
        driver.process_new_record_form(request, 'TESTPREFIX', validator_func)

    assert excinfo.typename == 'IgnoreEhbExceptions'


def test_process_new_record_form_record_exists_on_ds(driver, mocker):
    request = mocker.MagicMock(
        method='POST',
        _post={'SDG_NAME': '7316-118', 'csrfmiddlewaretoken': 'foo', 'label_id': '1'}
    )
    driver.update = mocker.MagicMock(return_value=b'[{"status": "400"}]')
    validator_func = mocker.MagicMock(return_value=1)
    with pytest.raises(RecordCreationError) as excinfo:
        driver.process_new_record_form(request, 'TESTPREFIX', validator_func)

    assert excinfo.typename == 'RecordCreationError'


def test_process_new_record_form_assigned_to_other(driver, mocker):
    request = mocker.MagicMock(
        method='POST',
        _post={'SDG_NAME': '7316-118', 'csrfmiddlewaretoken': 'foo', 'label_id': '1'}
    )
    driver.update = mocker.MagicMock(return_value=b'[{"status": "200"}]')
    validator_func = mocker.MagicMock(return_value=-1)
    with pytest.raises(RecordCreationError) as excinfo:
        driver.process_new_record_form(request, 'TESTPREFIX', validator_func)

    assert excinfo.typename == 'RecordCreationError'


def test_process_new_record_form_no_sdg(driver, mocker):
    request = mocker.MagicMock(
        method='POST',
        _post={'csrfmiddlewaretoken': 'foo', 'label_id': '1'}
    )
    driver.update = mocker.MagicMock(return_value=b'[{"status": "200"}]')
    validator_func = mocker.MagicMock(return_value=0)
    with pytest.raises(RecordCreationError) as excinfo:
        driver.process_new_record_form(request, 'TESTPREFIX', validator_func)

    assert excinfo.typename == 'RecordCreationError'
