"""
    Forms for auto-reduction configuration

    @author: M. Doucet, Oak Ridge National Laboratory
    @copyright: 2014 Oak Ridge National Laboratory
"""
from django import forms
from django.core.exceptions import ValidationError
from models import ReductionProperty, Choice
from report.models import Instrument
import sys
import re
import logging
import view_util

def _get_choices(instrument):
    """
        Pull the grouping choices from the database
        @param instrument: short name of the instrument
    """
    form_choices = []
    try:
        instrument_id = Instrument.objects.get(name=instrument.lower())
        grp_property = ReductionProperty.objects.get(key='grouping', instrument=instrument_id)
        choices = Choice.objects.filter(instrument=instrument_id,
                                        property=grp_property)
        for item in choices:
            form_choices.append((item.value, item.description))
    except:
        logging.error("_get_choices: %s instrument or grouping does not exist\n %s" % (instrument.upper(), sys.exc_value))
    return sorted(form_choices, cmp=lambda x, y:cmp(x[0], y[0]))

def validate_integer_list(value):
    """
        Allow for "1,2,3" and "1-3"

        @param value: string value to parse
    """
    # Look for a list of ranges
    range_list = value.split(',')
    for value_range in range_list:
        for item in value_range.split('-'):
            try:
                int(item.strip())
            except:
                raise ValidationError(u'Error parsing %s for a range of integers' % value)

def validate_float_list(value):
    """
        @param value: string value to parse
    """
    # Look for a list of ranges
    range_list = value.split(',')
    for value_range in range_list:
        for item in value_range.split('-'):
            try:
                float(item.strip())
            except:
                raise ValidationError(u'Error parsing %s for a list of numbers' % value)


class BaseReductionConfigurationForm(forms.Form):
    """
        Base class for reduction form
    """
    def __init__(self, *args, **kwargs):
        super(BaseReductionConfigurationForm, self).__init__(*args, **kwargs)

    def set_instrument(self, instrument):
        """
            Populate instrument-specific options.
            @param instrument: instrument short name
        """
        pass

    def to_db(self, instrument_id, user=None):
        """
            Store the form data

            @param instrument_id: Instrument object
            @param user: user that made the change
        """
        for key in self._template_list:
            try:
                if key in self.cleaned_data:
                    # Make sure we treat booleans properly
                    if type(self.cleaned_data[key]) == bool and self.cleaned_data[key] is False:
                        value = ''
                    else:
                        value = str(self.cleaned_data[key])
                else:
                    value = ''
                view_util.store_property(instrument_id, key, value, user=user)
            except:
                logging.error("BaseReductionConfigurationForm.to_db: %s" % sys.exc_value)

    def to_template(self):
        template_dict = {}
        for key in self._template_list:
            if key in self.cleaned_data:
                template_dict[key] = str(self.cleaned_data[key])
            else:
                template_dict[key] = ''
        return template_dict

class ReductionConfigurationCNCSForm(BaseReductionConfigurationForm):
    """
        Generic form for DGS reduction instruments
    """
    mask = forms.CharField(required=False, initial='')
    sub_directory = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    raw_vanadium = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    processed_vanadium = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    vanadium_integration_min = forms.FloatField(required=True, initial=84000)
    vanadium_integration_max = forms.FloatField(required=True, initial=94000)
    grouping = forms.ChoiceField(choices=[])
    e_pars_in_mev = forms.BooleanField(required=False)
    e_min = forms.FloatField(required=True, initial=-0.2)
    e_step = forms.FloatField(required=True, initial=0.015)
    e_max = forms.FloatField(required=True, initial=0.95)
    tib_min = forms.CharField(required=False, initial="", validators=[validate_float_list])
    tib_max = forms.CharField(required=False, initial="", validators=[validate_float_list])
    t0 = forms.CharField(required=False, initial="", validators=[validate_float_list])
    motor_names = forms.CharField(required=False, initial='huber,SERotator2,OxDilRot,CCR13VRot,SEOCRot,CCR10G2Rot,Ox2WeldRot,ThreeSampleRot')
    temperature_names = forms.CharField(required=False, initial='SampleTemp,sampletemp,SensorC,SensorB,SensorA,temp5,temp8')
    create_elastic_nxspe = forms.BooleanField(required=False)
    create_md_nxs = forms.BooleanField(required=False)
    a = forms.FloatField(required=True, initial=7.76)
    b = forms.FloatField(required=True, initial=7.76)
    c = forms.FloatField(required=True, initial=7.02)
    alpha = forms.FloatField(required=True, initial=90)
    beta = forms.FloatField(required=True, initial=90)
    gamma = forms.FloatField(required=True, initial=90)
    u_vector = forms.CharField(required=False, initial="1,0,0", validators=[validate_float_list])
    v_vector = forms.CharField(required=False, initial="0,0,1", validators=[validate_float_list])

    # List of field that are used in the template
    _template_list = ['mask', 'sub_directory', 'raw_vanadium', 'processed_vanadium', 'grouping',
                      'vanadium_integration_min', 'vanadium_integration_max',
                      'tib_min', 'tib_max', 't0', 'motor_names', 'temperature_names',
                      'create_elastic_nxspe', 'create_md_nxs',
                      'alpha', 'beta', 'gamma',
                      'u_vector', 'v_vector', 'e_pars_in_mev',
                      'e_min', 'e_step', 'e_max', 'a', 'b', 'c']

    def __init__(self, *args, **kwargs):
        super(ReductionConfigurationCNCSForm, self).__init__(*args, **kwargs)

    def set_instrument(self, instrument):
        """
            Populate instrument-specific options.
            @param instrument: instrument short name
        """
        self.fields['grouping'].choices = _get_choices(instrument)


class ReductionConfigurationDGSForm(BaseReductionConfigurationForm):
    """
        Generic form for DGS reduction instruments
    """
    mask = forms.CharField(required=False, initial='')
    raw_vanadium = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    processed_vanadium = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    grouping = forms.ChoiceField(choices=[])
    e_min = forms.FloatField(required=True, initial=-0.2)
    e_step = forms.FloatField(required=True, initial=0.015)
    e_max = forms.FloatField(required=True, initial=0.95)

    # List of field that are used in the template
    _template_list = ['mask', 'raw_vanadium', 'processed_vanadium', 'grouping',
                      'e_min', 'e_step', 'e_max']

    def __init__(self, *args, **kwargs):
        super(ReductionConfigurationDGSForm, self).__init__(*args, **kwargs)

    def set_instrument(self, instrument):
        """
            Populate instrument-specific options.
            @param instrument: instrument short name
        """
        self.fields['grouping'].choices = _get_choices(instrument)


class ReductionConfigurationSEQForm(ReductionConfigurationDGSForm):
    """
        Reduction form for SEQ
    """
    create_elastic_nxspe = forms.BooleanField(required=False)
    _template_list = ReductionConfigurationDGSForm._template_list + ['create_elastic_nxspe']


class ReductionConfigurationCorelliForm(BaseReductionConfigurationForm):
    """
        Generic form for Corelli reduction instruments
    """
    mask = forms.CharField(required=False, initial='')
    plot_requests = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    ub_matrix_file = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    vanadium_flux_file = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    vanadium_SA_file = forms.CharField(required=False, initial='', widget=forms.TextInput(attrs={'class' : 'font_resize'}))
    useCC = forms.BooleanField(required=False)

    # List of field that are used in the template
    _template_list = ['mask', 'plot_requests', 'ub_matrix_file', 'vanadium_flux_file',
                      'vanadium_SA_file', 'useCC']

    def __init__(self, *args, **kwargs):
        super(ReductionConfigurationCorelliForm, self).__init__(*args, **kwargs)


class MaskForm(forms.Form):
    """
        Simple form for a mask entry.
        A combination of banks, tubes, pixels can be specified.
    """
    bank = forms.CharField(required=False, initial='', validators=[validate_integer_list])
    tube = forms.CharField(required=False, initial='', validators=[validate_integer_list])
    pixel = forms.CharField(required=False, initial='', validators=[validate_integer_list])
    remove = forms.BooleanField(required=False, initial=False)

    @classmethod
    def to_tokens(cls, value):
        """
            Takes a block of Mantid script and extract the
            dictionary argument. The template should be like

            MaskBTPParameters({'Bank':'', 'Tube':'', 'Pixel':''})

            @param value: string value for the code snippet
        """
        mask_list = []
        try:
            lines = value.split('\n')
            for line in lines:
                if 'MaskBTPParameters' in line:
                    mask_strings = re.findall("append\((.+)\)", line.strip())
                    for item in mask_strings:
                        mask_list.append(eval(item.lower()))
        except:
            logging.error("MaskForm count not parse a command line: %s" % sys.exc_value)
        return mask_list

    @classmethod
    def to_python(cls, mask_list, indent='    '):
        """
            Take a block of Mantid script from a list of mask forms

            @param mask_list: list of MaskForm objects
            @param indent: string indentation to add to each line
        """
        command_list = ''
        for mask in mask_list:
            if 'remove' in mask.cleaned_data and mask.cleaned_data['remove'] == True:
                continue
            command_str = str(mask)
            if len(command_str) > 0:
                command_list += "%s%s\n" % (indent, command_str)
        return command_list

    @classmethod
    def to_dict_list(cls, mask_list):
        """
            Create a list of mask dictionary from a set of mask forms
            @param mask_list: list of MaskForm objects
        """
        mask_info = []
        for mask in mask_list:
            entry_dict = {}
            if 'bank' in mask.cleaned_data and len(mask.cleaned_data['bank'].strip()) > 0:
                entry_dict["Bank"] = str(mask.cleaned_data['bank'])
            if 'tube' in mask.cleaned_data and len(mask.cleaned_data['tube'].strip()) > 0:
                entry_dict["Tube"] = str(mask.cleaned_data['tube'])
            if 'pixel' in mask.cleaned_data and len(mask.cleaned_data['pixel'].strip()) > 0:
                entry_dict["Pixel"] = str(mask.cleaned_data['pixel'])
            if len(entry_dict) > 0:
                mask_info.append(entry_dict)
        return mask_info

    @classmethod
    def from_dict_list(cls, param_value):
        """
            Return a list of dictionaries that is compatible with our form
            @param param_value: string representation of the dictionary
        """
        dict_list = eval(param_value)
        mask_info = []
        for mask in dict_list:
            entry_dict = {}
            for k in mask.keys():
                entry_dict[k.lower()] = mask[k]
            mask_info.append(entry_dict)
        return mask_info

    def __str__(self):
        """
            Return a string representing the Mantid command to run
            for this mask item.
        """
        entry_dict = {}
        if 'bank' in self.cleaned_data and len(self.cleaned_data['bank'].strip()) > 0:
            entry_dict["Bank"] = str(self.cleaned_data['bank'])
        if 'tube' in self.cleaned_data and len(self.cleaned_data['tube'].strip()) > 0:
            entry_dict["Tube"] = str(self.cleaned_data['tube'])
        if 'pixel' in self.cleaned_data and len(self.cleaned_data['pixel'].strip()) > 0:
            entry_dict["Pixel"] = str(self.cleaned_data['pixel'])
        if len(entry_dict) == 0:
            return ""
        return "MaskBTPParameters.append(%s)" % str(entry_dict)


class PlottingForm(forms.Form):
    """
        Simple form for a mask entry.
        A combination of banks, tubes, pixels can be specified.
    """
    perpendicular_to = forms.ChoiceField(required=False,
                                         choices=[('[H,0,0]', '[H,0,0]'), ('[0,K,0]', '[0,K,0]'),
                                                  ('[0,0,L]', '[0,0,L]'), ('Q_sample_x', 'Qx'),
                                                  ('Q_sample_y', 'Qy'), ('Q_sample_z', 'Qz')])
    minimum = forms.FloatField(required=False, initial=-0.05)
    maximum = forms.FloatField(required=False, initial=0.05)
    remove = forms.BooleanField(required=False, initial=False)

    @classmethod
    def to_dict_list(cls, opt_list):
        """
            Create a list of option dictionary from a set of plotting forms
            @param optlist: list of PlottingForm objects
        """
        plot_info = []
        for item in opt_list:
            entry_dict = {}
            if 'perpendicular_to' in item.cleaned_data and \
                len(item.cleaned_data['perpendicular_to'].strip()) > 0 and \
                'minimum' in item.cleaned_data and \
                'maximum' in item.cleaned_data:
                plot_info.append({'PerpendicularTo': str(item.cleaned_data['perpendicular_to']),
                                  'Minimum': str(item.cleaned_data['minimum']),
                                  'Maximum': str(item.cleaned_data['maximum'])})
        return plot_info

    @classmethod
    def from_dict_list(cls, param_value):
        """
            Return a list of dictionaries that is compatible with our form
            @param param_value: string representation of the dictionary
        """
        dict_list = eval(param_value)
        # Protect against bad DB entry
        if type(dict_list) == dict:
            dict_list = [dict_list]

        plot_info = []
        for plot in dict_list:
            entry_dict = {}
            if 'PerpendicularTo' in plot and \
                'Minimum' in plot and \
                'Maximum' in plot:
                entry_dict['perpendicular_to'] = plot['PerpendicularTo']
                try:
                    entry_dict['minimum'] = float(plot['Minimum'])
                except:
                    entry_dict['minimum'] = -0.05
                try:
                    entry_dict['maximum'] = float(plot['Maximum'])
                except:
                    entry_dict['maximum'] = 0.05
                plot_info.append(entry_dict)
        return plot_info

