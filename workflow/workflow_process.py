"""
    Actual process that each data run must go through.
"""
from database.report.models import WorkflowSummary
from states import StateAction
import logging

class WorkflowProcess(object):
    
    def __init__(self, connection=None, recovery=False):
        """
            @param recovery: if True, the system will try to recover from workflow problems
        """
        self._connection = connection
        self._recovery = recovery
        
    def has_status(self, status):
        """
            Checks that a particular status message type
            exists for this run
        """
        pass
        
    def verify_workflow(self):
        """
            Walk through the data runs and make sure they have
            gone through the whole workflow.
            
            TODO: check whether a message is already in the queue
            The worker nodes might be busy with a previous task.
        """    
        # Get a list of run with an incomplete workflow
        run_list = WorkflowSummary.objects.incomplete()
        for r in run_list:
            r.update()
            if r.complete is False:
                # The workflow for this run is still incomplete
                # Generate a JSON description of the run, to be used
                # when sending a message
                message = r.run_id.json_encode()
                
                #TODO: add information to the message as needed
                
                
                # Run is not cataloged
                if r.cataloged is False and r.catalog_started is False:
                    logging.warn("Cataloging incomplete for %s" % str(r))
                    StateAction().send(destination='/queue/POSTPROCESS.INFO',
                                       message=message, persistent='true')
                    if self._recovery:
                        StateAction().send(destination='/queue/CATALOG.DATA_READY',
                                           message=message, persistent='true')
            
                # Run hasn't been reduced
                if r.reduction_needed is True and r.reduced is False and \
                    r.reduction_started is False:
                    logging.warn("Reduction incomplete for %s" % str(r))
                    StateAction().send(destination='/queue/POSTPROCESS.INFO',
                                       message=message, persistent='true')
                    if self._recovery:
                        StateAction().send(destination='/queue/REDUCTION.DATA_READY',
                                           message=message, persistent='true')                    
                
                # Reduced data hasn't been cataloged
                if r.reduction_needed is True and r.reduced is True and \
                    r.reduction_cataloged is False and \
                    r.reduction_catalog_started is False:
                    logging.warn("Reduction cataloging incomplete for %s" % str(r))
                    StateAction().send(destination='/queue/POSTPROCESS.INFO',
                                       message=message, persistent='true')
                    if self._recovery:
                        StateAction().send(destination='/queue/REDUCTION_CATALOG.DATA_READY',
                                           message=message, persistent='true')                    
                    
