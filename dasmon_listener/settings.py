# Django settings for reporting_app project.
import os
import django

# The DB settings are defined in the workflow manager
from workflow.database.settings import DATABASES

TIME_ZONE = 'America/New_York'

USE_TZ = True

INSTALLED_APPS = (
    'report',
    'dasmon',
    )

"""
    ActiveMQ settings
"""
# List of brokers
from workflow.database.settings import brokers
from workflow.database.settings import icat_user as amq_user
from workflow.database.settings import icat_passcode as amq_pwd

queues = ["/topic/ADARA.APP.DASMON.0",
          "/topic/ADARA.STATUS.DASMON.0",
          "/topic/ADARA.SIGNAL.DASMON.0"]
instrument_shortname = 'hysa'

INSTALLATION_DIR = "/var/www/workflow/app"

PURGE_TIMEOUT = 7

# Import local settings if available
try:
    from local_settings import *
except ImportError, e:
    LOCAL_SETTINGS = False
    pass
   
