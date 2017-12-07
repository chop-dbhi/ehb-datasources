import pytest

from ehb_datasources.drivers.phenotype.driver import PhenotypeDriver

@pytest.fixture()
def driver():
    return PhenotypeDriver(
        url='http://example.com/api/',
        user='foo',
        password='bar',
        secure=False
    )


def test_initialization(driver):
    assert driver.host == 'example.com'
    assert driver.path == '/api/'


def test_new_record_form_required(driver):
    assert not driver.new_record_form_required()


def test_srsf(driver):
    assert driver.subRecordSelectionForm(form_url='/test/') == '<h3>Record created. Return to <a href="../../../list/">Subject Summary List</a> to view.</h3>'


def test_srf(driver):
    assert driver.subRecordForm(None, form_url='/test/') == '<h3 style="color:red"><em>The sample record is saved. Currently no other actions are supported.</em></h3><br/><br/>'


# The following functions tested are essentially no-ops


def test_get(driver):
    assert not driver.get()


def test_delete(driver):
    assert not driver.delete()


def test_create(driver):
    assert driver.create('prefix', None) == 'prefix'


def test_update(driver):
    assert not driver.update()


def test_configure(driver):
    assert not driver.configure()


def test_meta(driver):
    assert not driver.meta()


def test_create_new_record_form(driver):
    assert not driver.create_new_record_form(None, None, None)


def test_process_new_record_form(driver):
    assert not driver.process_new_record_form(None, None, None)


def test_process_form(driver):
    assert not driver.processForm(None, None, None)
