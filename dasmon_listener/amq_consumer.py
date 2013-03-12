"""
    DASMON ActiveMQ consumer class
"""
import time
import stomp
import logging
import json
import os
import sys
import datetime
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
from settings import INSTALLATION_DIR
from settings import PURGE_TIMEOUT
sys.path.append(INSTALLATION_DIR)

from dasmon.models import StatusVariable, Parameter
from report.models import Instrument

class Listener(stomp.ConnectionListener):
    """
        Base listener class for an ActiveMQ client

        A fully implemented class should overload
        the on_message() method to process incoming
        messages.
    """
    def __init__(self, instrument):
        self._instrument = instrument
        
    def on_message(self, headers, message):
        """
            Process a message.
            @param headers: message headers
            @param message: JSON-encoded message content
        """
        destination = headers["destination"]
        try:
            data_dict = json.loads(message)
        except:
            logging.error("Could not decode message from %s" % headers["destination"])
            return
           
        try:
            instrument_id = Instrument.objects.get(name=self._instrument)
        except Instrument.DoesNotExist:
            instrument_id = Instrument(name=self._instrument)
            instrument_id.save()
            
        for key in data_dict:
            try:
                key_id = Parameter.objects.get(name=key)
            except:
                key_id = Parameter(name=key)
                key_id.save()
            status_entry = StatusVariable(instrument_id=instrument_id,
                                          key_id=key_id,
                                          value=data_dict[key])
            status_entry.save()
        

class Client(object):
    """
        ActiveMQ client
        Holds the connection to a broker
    """
    
    def __init__(self, brokers, user, passcode, 
                 queues=None, consumer_name="amq_consumer"):
        """ 
            @param brokers: list of brokers we can connect to
            @param user: activemq user
            @param passcode: passcode for activemq user
            @param queues: list of queues to listen to
            @param consumer_name: name of the AMQ listener
        """
        self._brokers = brokers
        self._user = user
        self._passcode = passcode
        self._connection = None
        self._connected = False        
        self._queues = queues
        self._consumer_name = consumer_name
        self._listener = None
        
    def set_listener(self, listener):
        """
            Set the listener object that will process each
            incoming message.
            @param listener: listener object
        """
        self._listener = listener
        
    def get_connection(self, listener=None):
        """
            Establish and return a connection to ActiveMQ
            @param listener: listener object
        """
        if listener is None:
            if self._listener is None:
                listener = Listener()
            else:
                listener = self._listener

        logging.info("[%s] Attempting to connect to ActiveMQ broker" % self._consumer_name)
        conn = stomp.Connection(host_and_ports=self._brokers, 
                                user=self._user,
                                passcode=self._passcode, 
                                wait_on_receipt=True)
        conn.set_listener(self._consumer_name, listener)
        conn.start()
        conn.connect()        
        return conn
            
    def connect(self):
        """
            Connect to a broker
        """
        if self._connection is None or not self._connection.is_connected():
            self._disconnect()
            self._connection = self.get_connection()
        
        logging.info("[%s] Subscribing to %s" % (self._consumer_name,
                                                 str(self._queues)))
        for q in self._queues:
            self._connection.subscribe(destination=q, ack='auto', persistent='true')
        self._connected = True
    
    def _disconnect(self):
        """
            Clean disconnect
        """
        if self._connection is not None and self._connection.is_connected():
            self._connection.disconnect()
        self._connection = None
        
    def stop(self):
        """
            Disconnect and stop the client
        """
        self._disconnect()
        if self._connection is not None:
            self._connection.stop()
        self._connection = None
        self._connected = False
        
    def listen_and_wait(self, waiting_period=1.0):
        """
            Listen for the next message from the brokers.
            This method will simply return once the connection is
            terminated.
            @param waiting_period: sleep time between connection to a broker
        """
        self.connect()
        while(self._connected):
            # Remove old entries
            delta_time = datetime.timedelta(days=PURGE_TIMEOUT)
            cutoff = timezone.now()-delta_time
            StatusVariable.objects.filter(timestamp__lte=cutoff).delete()
            
            time.sleep(waiting_period)
            
    def send(self, destination, message, persistent='true'):
        """
            Send a message to a queue
            @param destination: name of the queue
            @param message: message content
        """
        if self._connection is None or not self._connection.is_connected():
            self._disconnect()
            self._connection = self.get_connection()
        self._connection.send(destination=destination, message=message, persistent=persistent)
