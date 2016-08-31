import pytest

from ehb_datasources.drivers.external_identifiers.driver import ehbDriver


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


def test_get(driver):
    assert not driver.get()


def test_delete(driver):
    assert not driver.delete()


def test_create(driver):
    assert driver.create('foo', False) is 'foo'


def test_update(driver):
    assert not driver.update()


def test_configure(driver):
    assert not driver.configure()


def test_meta(driver):
    assert not driver.meta()


def test_srsf(driver):
    form = driver.subRecordSelectionForm(form_url='/test/')
    assert form == '<h3>Record created. Return to <a href="../../../list/">Subject Summary List</a> to view.</h3>'


def test_srf(driver):
    form = driver.subRecordForm('foo', 'spec')
    assert form == '<h3 style="color:red"><em>The External ID is saved. Currently no other actions are supported.</em></h3><br/><br/>'


def test_process_form(driver):
    assert not driver.processForm(None, None, None)


def test_record_new_record_form_required(driver):
    assert driver.new_record_form_required()


def test_create_new_record_form_get(driver, mocker):
    request = mocker.MagicMock(
        status=200,
        method='GET'
    )
    form = driver.create_new_record_form(request)
    assert form == '<table class="table table-bordered table-striped table-condensed"><tr><th>Description</th><th>Field</th></tr><tbody><tr><td>*Enter External ID</td><td><input type="text" onkeypress="return disableEnter(event);" name="ex_id_form"/></td></tr></tbody></table>'


def test_create_new_record_form_post(driver, mocker):
    request = mocker.MagicMock(
        status=200,
        method='POST',
        _post={'ex_id_form': 'TEST123'}
    )
    form = driver.create_new_record_form(request)
    assert form == '<table class="table table-bordered table-striped table-condensed"><tr><th>Description</th><th>Field</th></tr><tbody><tr><td>*Enter External ID</td><td><input type="text" onkeypress="return disableEnter(event);" name="ex_id_form" value="TEST123"/></td></tr></tbody></table>'


def test_process_new_record_form(driver, mocker):
    request = mocker.MagicMock(
        status=200,
        method='POST',
        _post={'ex_id_form': 'TEST123'}
    )
    validator_func = mocker.MagicMock(return_value=0)
    response = driver.process_new_record_form(request, 'TESTPREFIX', validator_func)
    assert response == 'TEST123'
