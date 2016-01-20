"""
    Forms for auto-reduction configuration
    
    @author: M. Doucet, Oak Ridge National Laboratory
    @copyright: 2016 Oak Ridge National Laboratory
"""
from django import forms
from django.core.exceptions import ValidationError
from report.models import Instrument, IPTS, DataRun, StatusQueue
from dasmon.models import ActiveInstrument
import logging
import sys

def validate_integer_list(value):
    """
        Allow for "1,2,3" and "1-3"

        @param value: string value to parse
    """
    value_list = []
    # Look for a list of ranges
    for item in value.split(','):
        if '-' in item:
            range_toks = item.split('-')
            if len(range_toks) == 2:
                try:
                    value_list.extend(range(int(range_toks[0]), int(range_toks[1])+1))
                except:
                    logging.error(sys.exc_value)
                    raise ValidationError(u'Error parsing %s for a range of integers' % value)
            else:
                logging.error("Found more than two tokens around -")
                raise ValidationError(u'Error parsing %s for a range of integers' % value)
                
        else:
            try:
                value_list.append(int(item))
            except:
                logging.error(sys.exc_value)
                raise ValidationError(u'Error parsing %s for a range of integers' % value)

    return value_list
    
class ProcessingForm(forms.Form):
    """
        Form to send a post-processing request
    """
    instrument = forms.ChoiceField(choices=[])
    experiment = forms.CharField(required=False, initial='')
    run_list = forms.CharField(required=False, initial='', validators=[validate_integer_list])
    task = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super(ProcessingForm, self).__init__(*args, **kwargs)
        
        # Get the list of available instruments
        instruments = [ (str(i), str(i)) for i in Instrument.objects.all().order_by('name') if ActiveInstrument.objects.is_alive(i) ]
        self.fields['instrument'].choices = instruments
        
        # Get the list of available inputs
        queue_ids = StatusQueue.objects.filter(is_workflow_input=True)
        tasks = [ (str(q), str(q)) for q in queue_ids ]
        self.fields['task'].choices = tasks

    def process(self):
        """
            Process the completed form
        """
        output_report = ""
        # Retrieve the instrument
        try:
            instrument = Instrument.objects.get(name=self.cleaned_data['instrument'])
            output_report += "Found instrument %s<br>" % str(instrument)
        except Instrument.DoesNotExist:
            output_report += "Could not find instrument [%s]" % self.cleaned_data['instrument']
            output_report += "Fix your inputs and re-submit<br>"
            return {'report': output_report, 'task': None}
        
        # Verify that the experiment exists
        try:
            ipts = IPTS.objects.get(instruments=instrument,
                                    expt_name=self.cleaned_data['experiment'].upper())
            output_report += "Found experiment %s<br>" % str(ipts)
        except IPTS.DoesNotExist:
            output_report += 'Could not find experiment [%s]' % self.cleaned_data['experiment']
            output_report += "Fix your inputs and re-submit<br>"
            return {'report': output_report, 'task': None}
        
        # Parse the runs and make sure they all exist
        run_list = validate_integer_list(self.cleaned_data['run_list'])
        invalid_runs = []
        valid_run_objects = []
        for run in run_list:
            try:
                run_obj = DataRun.objects.get(instrument_id=instrument,
                                              ipts_id = ipts,
                                              run_number=run)
                valid_run_objects.append(run_obj)
            except DataRun.DoesNotExist:
                invalid_runs.append(run)
        if len(invalid_runs) == 0:
            output_report += "All the runs were valid<br>"
        else:
            output_report += "The following were invalid runs: %s<br>" % str(invalid_runs)
            output_report += "Fix your inputs and re-submit<br>"
            return {'report': output_report, 'task': None}
        
        # Retrieve the command
        try:
            queue = StatusQueue.objects.get(name=self.cleaned_data['task'])
        except StatusQueue.DoesNotExist:
            logging.error(sys.exc_value)
        
        # Returns a report and task to be sent
        return {'report': output_report, 'task': str(queue),
                'instrument': instrument, 'runs': valid_run_objects}