import json
import pytest
from ehb_datasources.drivers.redcap.formBuilderJson import FormBuilderJson


@pytest.fixture()
def form_builder():
    return FormBuilderJson()


def test_construct_form(form_builder, redcap_metadata_json, redcap_record_json):
    form = form_builder.construct_form(
        json.loads(redcap_metadata_json.decode('utf-8')),
        json.loads(redcap_record_json.decode('utf-8')),
        'baseline_visit_data',
        1,
    )

    print("form: " + form)
    print("form end")
    assert '0GUQDBCDE0EAWN9Q:8LAG76CHO' not in form
    assert '<div><input class="field_input" type="checkbox"  name="meds___1" value="1" style="margin-top:-1px" checked="checked"/> Antibiotic</div>' in form
    assert '<input style="min-width: 100px;" type="text" value="100" name="height" class="field_input" id="input_height"  />' in form
    assert 'input style="min-width: 100px;" type="text" value="20" name="weight" class="field_input" id="input_weight"  />' in form
    assert '<textarea rows="5" cols="20" name="comments" class="field_input" >Test Data2</textarea>' in form


def test_construct_form2_branch_logic_functions(form_builder, redcap_metadata_json2, redcap_record_json2):
    form = form_builder.construct_form(
        json.loads(redcap_metadata_json2.decode('utf-8')),
        json.loads(redcap_record_json2.decode('utf-8')),
        'diagnosis_form',
        1
    )
    assert 'function diag_other2_cf0_branch_logic()' in form
    assert 'function des_tests_branch_logic()' in form
    assert 'function site_prog_branch_logic()' in form
    assert 'function describe_branch_logic()' in form
    assert 'function relapse_number2_7d6_branch_logic()' in form
    assert 'function other_med_condition_branch_logic()' in form
    assert 'function diag_other_branch_logic()' in form
    assert 'function time_surg_prog2_a49_branch_logic()' in form
    assert 'function metas_at_submit_site_branch_logic()' in form
    assert 'function time_to_prog_branch_logic()' in form
    assert 'function autop_cause_death_branch_logic()' in form
    assert 'function vps_etv_branch_logic()' in form
    assert 'function autopsy_branch_logic()' in form
    assert 'function if_other_describe_metatases_sites_branch_logic()' in form
    assert 'function path_test_avail_branch_logic()' in form


def test_construct_form2_w_custom_record_id(form_builder, redcap_metadata_json2, redcap_record_json2):
    form = form_builder.construct_form(
        json.loads(redcap_metadata_json2.decode('utf-8')),
        json.loads(redcap_record_json2.decode('utf-8')),
        'diagnosis_form',
        1,
        record_id_field='study_id'
    )
    assert '0GUQDBCDE0EAWN9Q:8LAG76CHO' not in form


def test_construct_form2_w_imported_record(form_builder, redcap_metadata_json2, redcap_imported_record_json):
    form = form_builder.construct_form(
        json.loads(redcap_metadata_json2.decode('utf-8')),
        json.loads(redcap_imported_record_json.decode('utf-8')),
        'demographics_form',
        1,
        0,
        ['diagnosis_arm_1', '6_month_update_arm_1', '12_month_update_arm_1', '18_month_update_arm_1', '24_month_update_arm_1', '36_month_update_arm_1', '48_month_update_arm_1', '60_month_update_arm_1', '5_year_plus_update_arm_1', '10_year_plus_updat_arm_1', '15_year_plus_updat_arm_1'],
        ['Diagnosis', '6 Month Update', '12 Month Update', '18 Month Update', '24 Month Update', '36 Month Update', '48 Month Update', '60 Month Update', '5 Year Plus Update', '10 Year Plus Update', '15 Year Plus Update'],
        None,
        'study_id'
    )
    assert '0GUQDBCDE0EAWN9Q:8LAG76CHO' not in form


def test_construct_form_bad_redcap_record(form_builder, redcap_metadata_json2):
    form = form_builder.construct_form(
        json.loads(redcap_metadata_json2.decode('utf-8')),
        json.loads(b'[]'.decode('utf-8')),
        'demographics_form',
        1,
        0,
        ['diagnosis_arm_1', '6_month_update_arm_1', '12_month_update_arm_1', '18_month_update_arm_1', '24_month_update_arm_1', '36_month_update_arm_1', '48_month_update_arm_1', '60_month_update_arm_1', '5_year_plus_update_arm_1', '10_year_plus_updat_arm_1', '15_year_plus_updat_arm_1'],
        ['Diagnosis', '6 Month Update', '12 Month Update', '18 Month Update', '24 Month Update', '36 Month Update', '48 Month Update', '60 Month Update', '5 Year Plus Update', '10 Year Plus Update', '15 Year Plus Update'],
        None,
        'study_id'
    )
    assert 'There was an error retrieving this record from REDCap' in form
