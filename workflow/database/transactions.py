"""
    Perform DB transactions
"""
import os
import sys
import json
import logging
import traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "database.settings")

# The report database module must be on the python path for Django to find it 
sys.path.append(os.path.dirname(__file__))

# Import your models for use in your script
from database.report.models import DataRun, RunStatus, StatusQueue, WorkflowSummary, IPTS, Instrument

def add_status_entry(headers, data):
    """
        Populate the reporting database with the contents
        of a status message of the following format:
        
        @param headers: ActiveMQ message header dictionary
        @param data: JSON encoded message content
        
        headers: {'expires': '0', 'timestamp': '1344613053723', 
                  'destination': '/queue/POSTPROCESS.DATA_READY', 
                  'persistent': 'true',
                  'priority': '5', 
                  'message-id': 'ID:mac83086.ornl.gov-59780-1344536680877-8:2:1:1:1'}
                  
        The data is a dictionary in a JSON format.
        
        data: {"instrument": tokens[2],
               "ipts": tokens[3],
               "run_number": run_number,
               "data_file": message}
    """
    # Find the DB entry for this queue
    destination = headers["destination"].replace('/queue/','')
    status_id = StatusQueue.objects.filter(name__startswith=destination)
    if len(status_id)==0:
        status_id = StatusQueue(name=destination)
        status_id.save()
    else:
        status_id = status_id[0]
    
    # Process the data
    data_dict = json.loads(data)
    
    # Check whether we already have an entry for this run
    run_number = data_dict["run_number"]
    run_ids = DataRun.objects.filter(run_number=run_number)
    
    if len(run_ids)>0:
        run_id = run_ids[0]
    else:
        logging.info("Creating entry for run %d" % run_number)
        
        # Look for instrument
        instrument = data_dict["instrument"].lower()
        instrument_ids = Instrument.objects.filter(name=instrument)
        if len(instrument_ids)>0:
            instrument_id = instrument_ids[0]
        else:
            instrument_id = Instrument(name=instrument)
            instrument_id.save()

        # Look for IPTS ID
        ipts = data_dict["ipts"]
        ipts_ids = IPTS.objects.filter(expt_name=ipts)
        if len(ipts_ids)>0:
            ipts_id = ipts_ids[0]
        else:
            ipts_id = IPTS(expt_name=ipts)
            ipts_id.save()
            
        # Add instrument to IPTS if not already in there
        try:
            if IPTS.objects.filter(id=ipts_id.id, instruments__in=[instrument_id]).count()==0:
                ipts_id.instruments.add(instrument_id)
                ipts_id.save()
        except:
            traceback.print_exc()
            logging(sys.exc_value)
        
        run_id = DataRun(run_number=run_number,
                         instrument_id=instrument_id,
                         ipts_id=ipts_id,
                         file=data_dict["data_file"])
        run_id.save()
        
        # Add a workflow summary for this new run
        summary_id = WorkflowSummary(run_id=run_id)
        summary_id.save()
    
    # Create a run status object in the DB
    run_status = RunStatus(run_id=run_id,
                           queue_id=status_id,
                           message_id=headers["message-id"])
    run_status.save()
    
    # Update the workflow summary
    summary_id = WorkflowSummary.objects.get_summary(run_id)
    summary_id.update()
    
def add_workflow_status_entry(destination, message):
    """
        Add a database entry for an event generated by the workflow manager.
        This represents additional information regarding interventions by
        the workflow manager.
        @param destination: string representing the StatusQueue
        @param message: JSON encoded data dictionary
    """
    pass