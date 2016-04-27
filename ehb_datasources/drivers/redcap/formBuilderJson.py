import re
import json
from string import Template


class redcapTemplate(Template):
    '''
    Subclass string.Template to ease in the templating of javascript.

    Template by default uses a delimiter of "$" which conflicts with jQuery
    string.format() uses brackets: {} which conflict with javascript code
    generally
    '''
    delimiter = '^'


class FormBuilderJson(object):

    def construct_form(self, meta, record_set, form_name, record_id,
                       event_num=None, unique_event_names=None,
                       event_labels=None, session=None, record_id_field=None):
        '''
        Constructs a string representation of an html form for the specified
        REDCap record, meta_data, form_name, event_num

        meta : json object representing the meta data for this form as reported
            by REDCap
        record_set : json object representing the record_set for this form as
            reported by REDCap.

            If this is a longitudinal study it is expected that there are
            multiple records in the set, one for each event. All event records
            are needed in order to handle the branching logic and calculated
            field values. Otherwise there should be only one record in the set.

        unique_event_names : list of the unique event names used by REDCap

        event_labels : list of the display names for the events
        '''
        self.form_field_info = {}
        self.record_id_field = None
        if session:
            session['{0}_fields'.format(form_name)] = self.form_field_info
        # Check if a non-default record_id_field is set via driver config
        if record_id_field:
            self.record_id_field = record_id_field
        else:
            self.record_id_field = 'record_id'
        record = None
        if event_num:
            uen = unique_event_names[event_num]
            for rec in record_set:
                if rec.get('redcap_event_name') == uen:
                    record = rec
        else:
            record = record_set[0]
        form_fields = [
            item for item in meta if item.get("form_name") == form_name
        ]
        self.form_fields = form_fields
        # Remove identifiers from form
        for field in self.form_fields:
            if field['field_name'] == self.record_id_field:
                self.form_fields.remove(field)
        master_dep_map, branch_logic_functions, apriori_branch_evals = self.build_branch_logic(
            meta, record_set, form_name, event_num, unique_event_names, event_labels)
        html = redcapTemplate("""
<script type="text/javascript">
  $(function() {
    $( ".field_input_date" ).datepicker({
            format: 'yyyy-mm-dd'
        });
  });

  $(function() {
    $( ".field_input_date" ).datepicker()
        .on('changeDate', function(ev){
            $(this).datepicker('hide');
            // and clear out any existing warnings:
            var textid = $(this).attr('id');
            var datespanid = textid.replace('dateinput_', 'datespan_');
            var datespanEl = $('#' + datespanid)[0];
            datespanEl.innerHTML = "";
        });
  });

  $(function () {
    $(".todaybutton").on('click', function () {
        var btnid = $(this).attr('id');
        var textid = btnid.replace('datebtn_', 'dateinput_');
        var textField = $('#' + textid)[0];

        var today = new Date();
        var monthstr = today.getMonth() + 1;
        if (monthstr < 10) {
            monthstr = '0' + monthstr;
        }
        var datestr = today.getDate();
        if (datestr < 10) {
            datestr = '0' + datestr;
        }
        var todaystr = today.getFullYear() + "-" + monthstr + "-" + datestr;
        textField.value = todaystr;

        // and clear out any existing warnings:
        var datespanid = btnid.replace('datebtn_', 'datespan_');
        var datespanEl = $('#' + datespanid)[0];
        datespanEl.innerHTML = "";
    });
  });

  function valiDate(dateFieldId, datespanFieldId) {
      var parts, day, month, year;
      var dateField = document.getElementById(dateFieldId);
      var dateStr = dateField.value;

      // clear out any existing warnings:
      var datespanEl = document.getElementById(datespanFieldId);
      datespanEl.innerHTML = "";

      if (dateStr == "") {
          return true;
      }

      // Part 1: check for the expected format without validating the #s:
      if(!/^^\d{4}\-\d{1,2}\-\d{1,2}$/.test(dateStr)) {
         // format is not as expected, but is it a variation we can auto-fix?
         if(/^^\d{4}\/\d{1,2}\/\d{1,2}$/.test(dateStr)) {
             // date-delimiter '/' used instead of '-', auto-fix:
             dateStr = dateStr.replace(/\//g, '-');
             dateField.value = dateStr;
         }
         else if (/^^\d{1,2}[-\/]\d{1,2}[-\/]\d{4}$/.test(dateStr)){
             // MM[-/]DD[-/]YYYY possibly used instead, auto-fix:
             parts   = dateStr.split(/[-\/]/);
             dateStr = parts[2] + "-" + parts[0] + "-" + parts[1];
             dateField.value = dateStr;
         }
         else {
             datespanEl.innerHTML = "ERROR: Expecting YYYY-MM-DD date format";
             return false;
         }
      }

      // Part 2: now that all seems to be YYYY-MM-DD format, validate MM&DD #s:
      parts   = dateStr.split(/-/);
      year    = parseInt(parts[0], 10);
      month   = parseInt(parts[1], 10);
      day     = parseInt(parts[2], 10);

      if(month <= 0 || month > 12)
      {
          datespanEl.innerHTML = "ERROR: month does not validate for YYYY-MM-DD";
          return false;
      }

      var monthLength = [ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 ];

      // Adjust for leap years
      if(year % 400 == 0 || (year % 100 != 0 && year % 4 == 0))
      {
          monthLength[1] = 29;
      }

      if (day <= 0 || day > monthLength[month - 1]) {
          datespanEl.innerHTML = "ERROR: day of month does not validate for YYYY-MM-DD";
          return false;
      }

      return true;
  }

  var cascaded_branch_functions = [];

  //Function to reconstruct form submit post
  function ajaxFormSubmit(next_form_url,start_url){
    var form_fields = []
    dataString = '';
    $(".field_input, .field_input_date").each(function(){
        var elem = $(this)
        var elem_type = elem.prop('type')
        if($.inArray(elem.attr("name"),form_fields)<0){
            if(elem_type == "checkbox" && elem.prop("checked") == true){
              dataString = dataString + elem.attr("name") + '=' + '1' +'&'
            }
            else if(elem_type == "radio" && elem.prop("checked") == true){
              dataString = dataString + elem.attr("name") + '=' + encodeURIComponent(elem.val()) +'&'
            }
            else if(elem_type == "textarea" ||
              elem_type == "text" ||
              elem_type == "hidden"){
              dataString = dataString + elem.attr("name") + '=' + encodeURIComponent(elem.val()) +"&";
            }
            else if(elem_type == "select-one"){
              $(this).children().each(function(){
                if($(this).is(':selected')){
                  dataString = dataString + elem.attr("name") + "=" + encodeURIComponent(elem.val()) + "&";
                }
              })
            }
        }
    })
    $.ajax({
      type: "POST",
      url:$(location).attr('pathname'),
      data: dataString,
      success: function(data){
        if(data == 'Parse error. REDCap response is an unknown format. Please contact system administrator.'){
          $("#pleaseWaitModal").modal('hide');
          $("#errorModal").modal('show');
        }
        else{
          if(next_form_url != ""){
            window.location=next_form_url
          }
          else{
            window.location=start_url;
          }
          $("#pleaseWaitMsg").html("<p>Form Saved. Generating next form...</p>");
        }
      }
    }
    )
  }
  function clear_hidden_fld_values(eid){
      var node = document.getElementById(eid);
      var options = node.getElementsByTagName('option');
      if(options!=null){
        for (var i=0; i<options.length; i++){
          options[i].selected = false;
        }
      }

      var selects = node.getElementsByTagName('select');
      if(selects != null){
         for(var i = 0; i<selects.length; i++){
            cascaded_branch_functions.push(selects[i].getAttribute('name'));
         }
      }

      var tas = node.getElementsByTagName('textarea');
      if(tas != null){
        for(var i=0; i<tas.length; i++){
          tas[i].value='';
          cascaded_branch_functions.push(tas[i].getAttribute('name'));
        }
      }

      var inputs = node.getElementsByTagName('input');
      if(inputs != null){
        for (var i=0; i<inputs.length; i++){
            this_in = inputs[i];
            var t = this_in.getAttribute('type');
            var vt = true;
            if(t=='checkbox')this_in.checked=false;
            else if(t=='text')this_in.value='';
            else if(t=='radio')this_in.checked=false;
            else vt=false;
            if(vt){
              var n = this_in.getAttribute('name');
              cascaded_branch_functions.push(n);
            }
        }
      }
  }

  function unique_elements(input){
    var set = {};
    for (var i = 0; i<input.length; i++){
       set[input[i]]=0;
    }
    ans = [];
    for (var item in set) ans.push(item);
    return ans;
  }

  function execute_onchange(name){
     var flds = document.getElementsByName(name);
     if(flds.length>0){
        $(flds[0]).trigger('onchange');
     }
  }

  function execute_cascaded_branchs(){
      cascaded_branch_functions = unique_elements(cascaded_branch_functions);
      var work = true
      while(work){
          if(cascaded_branch_functions.length>0){
             var n = cascaded_branch_functions.shift();
             execute_onchange(n);
          }else work = false;
      }
  }

   function getFieldValue(fid){
      var flds = document.getElementsByName(fid);
      if(flds == null) return undefined;
      //IE hack to remove elements with id=fid as oppossed to name=fid which is what getEelementsByNAME is suppossed to return
      flds = $.grep(flds, function(a){if(typeof a.name!='undefined') return true; else return false;});
      var val = '';
      if (flds.length==1){
          var f = flds[0];
          var nt = f.nodeName.toLowerCase();
          if(nt == 'input'){
              var t = f.getAttribute('type')
              if(t=='checkbox' && f.checked) val = f.getAttribute('value');
              else if(t=='text') val = f.value;
              else if(t=='radio' && f.checked)val = f.getAttribute('value');
          }
          else if(nt=='option' && f.selected) val = f.getAttribute('value');
          else if(nt='textarea') val = f.value
      }
      else {  //this will handle radio types
          for(var i=0; i<flds.length; i++){
             if(flds[i].checked)val = flds[i].getAttribute('value');
          }
      }
      return val;
    }

  ^blank

  ^branch_logic

</script>

^form_header

<table class="table table-bordered table-striped table-condensed">^table_rows</table>""")

        return html.substitute(
            form_header=self.form_header(form_name, event_num, event_labels),
            table_rows=self.table_rows(meta, record, form_name, master_dep_map, apriori_branch_evals),
            blank='',
            branch_logic=''.join(['\n\n{0}'.format(item) for item in branch_logic_functions.values()]),
        )

    def table_rows(self, meta, record, form_name, master_dep_map, apriori_branch_evals):
        #we need to find the fields that belong to this form since REDCap does not correctly return these values
        #form_fields = [item for item in meta[1:len(meta)] if item.get("form_name")==form_name]
        return ''.join([self.make_tr_for(item, record, master_dep_map, apriori_branch_evals) for item in self.form_fields])

    def make_tr_for(self, field, record, master_dep_map, apriori_branch_evals):
        def isRequired():
                if field.get('required_field') and field.get('required_field')=='Y': return '* must provide value'
                else: return ''

        def fieldNote():
                if field.get('field_note'): return field.get('field_note')
                else: return ''

        section_header = field.get('section_header')
        header = ''
        radio_reset = ''
        if section_header: header = """<tr><th colspan="2">{0}</th></tr>""".format(section_header)
        dis = 'style="display:notnone"'
        el = apriori_branch_evals.get(field.get("field_name"))
        if el and not eval(el): dis='style="display:none"'
        if field.get('field_type') == 'radio':
            radio_reset = """<a class="pull-right radio_reset" href="javascript:void(0)">reset</a>"""

        return """{0}
                  <tr id="{5}" {6}>
                  <td><div>{1}</div><div style="color:red; font-size:12px;">{2}</div></td>
                  <td><div>{3}</div><div style="color:blue; font-size:12px;">{4}</div>{7}</td>
                  </tr>
               """.format(header,
                          field.get('field_label'),
                          isRequired(),
                          self.build_field(field, record, master_dep_map),
                          fieldNote(),
                          field.get('field_name'),
                          dis,
                          radio_reset
                   )

    def build_fld_on_change_function(self, fld_name, master_dep_map):
        branch_impact = master_dep_map.get(fld_name)
        if branch_impact:
            lines = ''.join('{0}_branch_logic(); '.format(item) for item in branch_impact)
            return '{0}{1}{2}'.format('{',lines, '}')

    def build_field(self, field, record, master_dependency_map):
        ffi = self.form_field_info
        ft = field.get('field_type')
        if not ft: return ''
        ft = ft.lower()
        name = field.get('field_name')
        value = ''
        if record: value = record.get(name)
        if value: value = value.strip()
        onchange = self.build_fld_on_change_function(name, master_dependency_map)
        if onchange:
            onchange = ' onchange="{0}"'.format(onchange)
        else:
            onchange = ''
        if ft == 'text':
            ffi[name]={'type':ft}
            field_class="field_input"
            text_field_id="input_"+field.get('field_name')
            today_button=""
            if field.get('text_validation_type_or_show_slider_number') == 'date_ymd':
                field_class="field_input_date"
                text_field_id="date"+text_field_id
                today_button="""<input type="button" value="Today" class="todaybutton" id="datebtn_{0}" /> <br/>
                             <span style="color:red" class="datespan" id="datespan_{0}"></span>""".format(field.get('field_name'))
                onchange += """ onblur="valiDate('{0}','datespan_{1}');" """.format(text_field_id, field.get('field_name'))
            return """<input type="text" value="{0}" name="{1}" class="{2}" id="{3}" {4} />{5}
                  """.format(value, name, field_class, text_field_id, onchange, today_button)
        elif ft == 'notes':
            ffi[name]={'type':ft}
            return """<textarea rows="5" cols="20" name="{0}" class="field_input" {1}>{2}</textarea>
                   """.format(name, onchange, value)
        elif ft == 'dropdown':
            def constructChoice(k,v):
                selected=''
                option_name = '{0}___{1}'.format(name, k)
                if value==k: selected='selected="selected"'
                return """<option value="{0}" {1} name="{2}" class="field_input">{3}</option>
                       """.format(k, selected, option_name, v)

            ffi[name]={'type':ft}
            options = ''.join(self.choiceBldr(constructChoice, field))
            return """<select {0} name="{1}" class="field_input"><option value></option>{2}</select>
                   """.format(onchange,name, options)
        elif ft=='checkbox':
            def constructChoice(k,v):
                check_name = '{0}___{1}'.format(name,k)
                check_value = 0
                if record: check_value = int(record.get(check_name).strip())
                checked = ''
                if check_value == 1: checked = 'checked="checked"'
                onchange = self.build_fld_on_change_function(check_name, master_dependency_map)
                if onchange:
                    onchange = ' onchange="{0}"'.format(onchange)
                else:
                    onchange = ''
                ffi[check_name]={'type':ft}
                return """<div><input class="field_input" type="checkbox" {0} name="{1}" value="1" style="margin-top:-1px" {2}/> {3}</div>
                       """.format(onchange, check_name, checked, v)

            return ''.join(self.choiceBldr(constructChoice, field))
        elif ft=='radio':
            def constructChoice(k,v):
                checked = ''
                if value==k: checked='checked="checked"'
                return """<input type="radio" class="field_input" {0} name="{1}" style="margin-top:-1px" value="{2}" {3} /> {4}<br/>
                       """.format(onchange, name, k, checked, v)

            ffi[name]={'type':ft}
            return ''.join(self.choiceBldr(constructChoice, field))
        elif ft=='yesno':
            yes_checked = ''
            no_checked = ''
            if not value=='':
                if value == '1':yes_checked = 'checked="checked"'
                else: no_checked = 'checked="checked"'
            yes = """<div><input type="radio" class="field_input" {0} {1} name="{2}" value="1"/> Yes</div>
                  """.format(onchange, yes_checked, name)
            no = """<div><input type="radio" class="field_input" {0} {1} name="{2}" value="0"/> No</div>
                 """.format(onchange, no_checked, name)

            ffi[name]={'type':ft}
            return '{0}{1}'.format(yes,no)
        elif ft=='truefalse':
            t_checked = ''
            f_checked = ''
            if not value=='':
                if value=='1': t_checked='checked="checked"'
                else: f_checked = 'checked="checked"'
            t = """<div><input type="radio" class="field_input" {0} {1} name="{2}" value="1"/> True</div>
                """.format(onchange, t_checked, name)
            f = """<div><input type="radio" class="field_input" {0} {1} name="{2}" value="0"/> False</div>
                """.format(onchange, f_checked, name)

            ffi[name]={'type':ft}
            return '{0}{1}'.format(t,f)
        else: return ''

    def extractChoiceKeyValue(self, kv, pat = '(\s*)(?P<key>[\d\w]+)(\s*),(\s*)(?P<value>.+)'):
            m = re.match(pat, kv)
            if m: return (m.group('key'),m.group('value'))
            else: raise Exception('Invalid Choices Found in REDCap Form: '+kv)

    def choiceBldr(self, f, item):
            def g(choice):
                #k,v = choice.split(',')
                k,v = self.extractChoiceKeyValue(choice)
                return f(k.strip(),v.strip())
            choices = item.get('select_choices_or_calculations')
            if choices: return [g(choice) for choice in choices.split('|')]
            else: return ''

    def form_header(self, form_name, event_num, event_labels):
        if event_num:
            event_label = event_labels[event_num]
            return """<table class="table table-bordered table-striped table-condensed"><tr><td>{0}</td><td>Event Name:{1}</td></tr></table>
            """.format(self.clean_form_name(form_name),
                       reduce(lambda x,y: x+' '+y.capitalize(), event_label.split(' '),'')
                       )
        else:
            return """<table class="table table-bordered table-striped table-condensed"><tr><td>{0}</td></tr></table>
            """.format(self.clean_form_name(form_name))

    def clean_form_name(self, dirty_form_name): return reduce(lambda x,y: x+' '+y.capitalize(), dirty_form_name.split('_'),'')

    def clean_eq(self, branch_logic):
        #Replace = with ==
        for m in re.findall("""\]\s*=\s*[\'"\w\d]""", branch_logic):
            branch_logic = re.sub(m.replace('[','\[').replace(']','\]'), m.replace('=', '=='), branch_logic)
        return branch_logic

    def clean_branch_logic(self, branch_logic):
        #Replace = with ==
        branch_logic = self.clean_eq(branch_logic)

        #replace and operators with &&
        for m in re.findall("""(?<=[\d"'\)])\s*and\s*(?=[\[\(])""", branch_logic):
            branch_logic = re.sub(m.replace('[','\[').replace(']','\]').replace(')','\)').replace('(','\)'),m.replace('and', '&&'), branch_logic)

        #replace or operators with ||
        for m in re.findall("""(?<=[\d"'\)])\s*or\s*(?=[\[\(])""", branch_logic):
            branch_logic = re.sub(m.replace('[','\[').replace(']','\]').replace(')','\)').replace('(','\)'),m.replace('or', '||'), branch_logic)

        #branch_logic = branch_logic.replace('[', '').replace(']','')

        return branch_logic

    def isFldOnThisForm(self, fld, form_name, fld_unique_event_name, form_unique_event_name):
        return (fld_unique_event_name == form_unique_event_name) and (fld.get("form_name") == form_name)

    def build_fld_getters(self, meta, record_set, form_name, event_num=None, unique_event_names=None):
        '''output tuple (d,e)
        d{key,value} is a dict whose keys are the form field names and whose values are the strings that should be
        used to represent the value of a given fld in a javascript function. If the field is on the form, the value
        will be a getFieldValue() function call. If the field is not on the form, it will be a value
        e{key,value} is a dict whose keys are the form field names and whose values are strings that can be evaluated
        in python using eval(value) to determine if the field should be visible when the form is first rendered'''
        event_names = unique_event_names
        if not event_names:
            event_names = [None]

        thisFormUen = None
        if not event_num == None: thisFormUen = unique_event_names[event_num]
        d = {}
        e = {}
        for uen in event_names:
            record = None
            if event_num:
                for rec in record_set:
                    if rec.get("redcap_event_name")==uen: record = rec
            else: record = record_set[0]
            for fld in meta:
                field_name = fld.get('field_name')
                choices = None
                if fld.get('field_type') == 'checkbox': choices = fld.get('select_choices_or_calculations')
                if self.isFldOnThisForm(fld, form_name, uen, thisFormUen):
                    #field is on this form so need to check its value dynamically
                    if choices: #this is a checkbox
                        for choice in choices.split('|'):
                            k= self.extractChoiceKeyValue(choice)[0]
                            check_name = '{0}___{1}'.format(field_name, k)
                            key = '{0}:{1}'.format(str(uen), check_name)
                            d[key] = "getFieldValue('{0}')".format(check_name)
                            v = None
                            if record: v = record.get(check_name)
                            if v and len(v.strip())>0: e[key] = v
                            else: e[key] = 'None'
                    else:
                        key = '{0}:{1}'.format(str(uen), field_name)
                        d[key] = "getFieldValue('{0}')".format(field_name)
                        v = None
                        if record: v = record.get(field_name)
                        if v and len(v.strip())>0: e[key] = v
                        else: e[key] = 'None'
                else: #field is not on this form so use a static value
                    if choices: #this is a checkbox
                        for choice in choices.split('|'):
                            k = self.extractChoiceKeyValue(choice)[0]
                            check_name = '{0}___{1}'.format(field_name, k)
                            fld_value = None
                            if record: fld_value = record.get(check_name)
                            key = '{0}:{1}'.format(str(uen), check_name)
                            if fld_value and len(fld_value.strip())>0:
                                d[key] = fld_value
                                e[key] =  fld_value
                            else:
                                e[key] = 'None'
                                d[key] = 'undefined'
                    else:
                        key = '{0}:{1}'.format(str(uen), field_name)
                        fld_value = None
                        if record: fld_value = record.get(field_name)
                        if fld_value and len(fld_value.strip())>0:
                            d[key] = fld_value
                            e[key] = fld_value
                        else:
                            e[key] = 'None'
                            d[key] = 'undefined'
        return (d,e)

    def build_branch_logic(self, meta, record_set, form_name, event_num, unique_event_names, event_labels):
        '''Outputs a 2 tuple contianing:
               a dict with entries of the form "master_field_name":["dep_field_name_1", "dep_field_name_2", ...]
               where the list value contains the names of the fields whose visibility is dependent on the value of the
               key, master_field_name AND
               a dict whose keys are the names of the branch functiosn by field and whose values are the strings
               representing the branch functions in javascript format
               e.g. key = some_field_branch
                    valye = function some_field_branch(){ ...} '''

        def add_master_dep(master, dep, d):
            if not master in d: d[master] = [dep]
            elif not dep in d.get(master): d.get(master).append(dep)
        standard_key_prefix = 'None'
        if not event_num == None: standard_key_prefix = unique_event_names[event_num]
        master_dep_map = {}
        branch_logic_functions = {}
        apriori_branch_evals = {}
        js_getters, es_getters = self.build_fld_getters(meta, record_set, form_name, event_num, unique_event_names)
        p1 = r'\[(?P<event>\w+)\]\[(?P<fld>\w+)\]' #will ONLY match entries of type [event][field] op value
        p2 = r'\[(?P<event>\w+)\]\[(?P<fld>\w+)\((?P<idx>\d+)\)\]' #will ONLY match entries of type [event][field(idx)] op value
        p3 = r'(?<!\])\[(?P<fld>\w+)\](?!\[)' #will ONLY match entries of type [field] op value
        p4 = r'(?<!\])\[(?P<fld>\w+)\((?P<idx>\d+)\)\](?!\[)' #will ONLY match entries of the type [field(idx)] op value
        for fld in self.form_fields:
            bl = fld.get('branching_logic').strip()
            el = self.clean_eq(bl).strip()
            bl = self.clean_branch_logic(bl)
            if len(bl)>0:
                dep = fld.get('field_name')
                for m in re.findall(p1, bl):
                    add_master_dep(m[1], dep, master_dep_map)
                    bl = bl.replace('[{0}][{1}]'.format(m[1], m[2]), js_getters['{0}:{1}'.format(m[1],m[2])])
                    el = el.replace('[{0}][{1}]'.format(m[1], m[2]), "'{0}'".format(es_getters['{0}:{1}'.format(m[1],m[2])]))
                for m in re.findall(p2, bl):
                    add_master_dep('{0}___{1}'.format(m[1], m[2]), dep, master_dep_map)
                    bl = bl.replace('[{0}][{1}({2})]'.format(m[1],m[2],m[3]), js_getters['{0}:{1}___{2}'.format(m[1],m[2],m[3])])
                    el = el.replace('[{0}][{1}({2})]'.format(m[1],m[2],m[3]), "'{0}'".format(es_getters['{0}:{1}___{2}'.format(m[1],m[2],m[3])]))
                for m in re.findall(p3, bl):
                    add_master_dep(m, dep, master_dep_map)
                    bl = bl.replace('[{0}]'.format(m), js_getters['{0}:{1}'.format(standard_key_prefix, m)])
                    el = el.replace('[{0}]'.format(m), "'{0}'".format(es_getters['{0}:{1}'.format(standard_key_prefix, m)]))
                for m in re.findall(p4, bl):
                    check_name = '{0}___{1}'.format(m[0], m[1])
                    add_master_dep(check_name, dep, master_dep_map)
                    bl = bl.replace('[{0}({1})]'.format(m[0],m[1]), js_getters['{0}:{1}'.format(standard_key_prefix, check_name)])
                    el = el.replace('[{0}({1})]'.format(m[0],m[1]), "'{0}'".format(es_getters['{0}:{1}'.format(standard_key_prefix, check_name)]))

                bl = bl.replace('[', '').replace(']','').replace("<>","!=")
                el = el.strip().replace('[', '').replace(']','')
                for m in re.findall("""'\d+'""", el):
                    el = el.replace(m, m.replace("'", ""))
                el = el.replace('"','').replace("<>","!=''").replace("'None'","''")
                for m in re.findall("""''\s*[><]=\s*\d+""",el):
                    el = el.replace(m, 'False')
                bl_func_name = """{0}_branch_logic""".format(dep)
                bl_func = """function {0}(){1}
                                var e = document.getElementById('{4}');
                                var d = e.style.display;
                                var currentViz = !(d=='none')
                                var setViz = {3};
                                if(setViz && !currentViz){1}$('#{4}').show();{2}
                                else if(!setViz && currentViz){1}
                                    $('#{4}').hide();
                                    clear_hidden_fld_values('{4}');
                                    execute_cascaded_branchs();
                                {2}
                             {2}""".format(bl_func_name,'{','}', bl,dep)
                branch_logic_functions[bl_func_name]=bl_func
                apriori_branch_evals[dep]=el
        return (master_dep_map, branch_logic_functions, apriori_branch_evals);
