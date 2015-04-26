# -*- coding: utf-8 -*-

"""The listener.

"""

__license__ = """

This file is part of **python-openzwave** project https://github.com/bibi21000/python-openzwave.

License : GPL(v3)

**python-openzwave** is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

**python-openzwave** is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with python-openzwave. If not, see http://www.gnu.org/licenses.
"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'

import os
import sys
import time

from openzwave.network import ZWaveNetwork
from openzwave.controller import ZWaveController
from openzwave.option import ZWaveOption
import threading
#from multiprocessing import Process
from threading import Thread
from louie import dispatcher, All
#from socketIO_client import SocketIO, LoggingNamespace

from pyozwweb.app.rooms import data_room_network
from flask import Flask, render_template, session, request, current_app

import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """NullHandler logger for python 2.6"""
        def emit(self, record):
            pass
logging.getLogger('pyozwweb').addHandler(NullHandler())

listener = None

class ListenerThread(Thread):
    def __init__(self, _socketio, _app):
        """The constructor"""
        #server
        #socketIO.emit('aaa')
        #socketIO.wait(seconds=1)
        Thread.__init__(self)
        self._stopevent = threading.Event( )
        self.socketio = _socketio
        self.app = _app
        self.connected = False

    def connect(self):
        if self.connected == False:
            logging.debug("Listener connects to socketio")
            self.join_room_network()
            self.join_room_controller()
            self.join_room_nodes()
            self.join_room_values()
            self.connected = True

    def run(self):
        """The running method"""
        logging.info("Start listener")
        self._stopevent.wait(10.0)
        self.connect()
        while not self._stopevent.isSet():
            self._stopevent.wait(1.0)

    def join_room_network(self):
        """Join room network"""
        #join_room("network")
        dispatcher.connect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
        dispatcher.connect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
        dispatcher.connect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_AWAKED)
        dispatcher.connect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_READY)
        dispatcher.connect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_STOPPED)
        return True

    def leave_room_network(self):
        """Leave room network"""
        #join_room("network")
        dispatcher.disconnect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
        dispatcher.disconnect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
        dispatcher.disconnect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_AWAKED)
        dispatcher.disconnect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_READY)
        dispatcher.disconnect(self._louie_network, ZWaveNetwork.SIGNAL_NETWORK_STOPPED)
        return True

    def _louie_network(self, network):
        if network is None:
            logging.debug('OpenZWave network notification : Network is None.')
            self.socketio.emit('my network response',
                {'data': data_room_network(current_app.extensions['zwnetwork']), 'count': session['receive_count']},
                namespace='/socket',
                broadcast=True)
        else:
            logging.debug('OpenZWave network notification : homeid %0.8x (state:%s) - %d nodes were found.' % (network.home_id, network.state, network.nodes_count))
            self.socketio.emit('my network response',
                {'data': data_room_network(current_app.extensions['zwnetwork']), 'count': session['receive_count']},
                namespace='/socket',
                broadcast=True)

    def join_room_nodes(self):
        """Join room nodes"""
        #join_room("nodes")
        dispatcher.connect(self._louie_nodes, ZWaveNetwork.SIGNAL_NODE)
        return True

    def leave_room_nodes(self):
        """Leave room nodes"""
        #join_room("nodes")
        dispatcher.disconnect(self._louie_nodes, ZWaveNetwork.SIGNAL_NODE)
        return True

    def _louie_nodes(self, network, node):
        if network is None:
            logging.debug('OpenZWave nodes notification : Network is None.')
            self.socketio.emit('my nodes response',
                          {'node_id':None, 'homeid':None,
                          'room':'nodes', 'namespace':'/socket', 'broadcast':True})
        elif node is None:
            logging.debug('OpenZWave nodes notification : Node is None.')
            self.socketio.emit('my nodes response',
                          {'node_id':None, 'homeid':network.home_id_str,
                          'room':'nodes', 'namespace':'/socket', 'broadcast':True})
        else:
            logging.debug('OpenZWave nodes notification : homeid %0.8x - node %d.' % (network.home_id, node.node_id))
            self.socketio.emit('my nodes response',
                          {'node_id':node.node_id, 'homeid':network.home_id_str,
                          'room':'nodes', 'namespace':'/socket', 'broadcast':True})

    def join_room_values(self):
        """Join room values"""
        #join_room("values")
        dispatcher.connect(self._louie_values, ZWaveNetwork.SIGNAL_VALUE)
        return True

    def leave_room_values(self):
        """Leave room values"""
        #join_room("values")
        dispatcher.disconnect(self._louie_values, ZWaveNetwork.SIGNAL_VALUE)
        return True

    def _louie_values(self, network, node, value):
            with self.app.test_request_context():
                from flask import request
#               request = req
                if network is None:
                    logging.debug('OpenZWave values notification : Network is None.')
                    self.socketio.emit('my values response',
                                       {'data': {'node_id':None, 'homeid':None, 'value_id':None},},
                                       namespace='/ozwave')
                elif node is None:
                    logging.debug('OpenZWave values notification : Node is None.')
                    self.socketio.emit('my values response',
                                       {'data': {'node_id':None, 'homeid':network.home_id_str, 'value_id':None},},
                                       namespace='/ozwave')
                elif value is None:
                    logging.debug('OpenZWave values notification : Value is None.')
                    self.socketio.emit('my values response',
                                       {'data': {'node_id':node.node_id, 'homeid':network.home_id_str, 'value_id':None},},
                                       namespace='/ozwave')
                else:
                    logging.debug('OpenZWave values notification : homeid %0.8x - node %d - value %d.', network.home_id, node.node_id, value.value_id)
                    self.socketio.emit('my values response',
                                       {'data': network.nodes[node.node_id].values[value.value_id].to_dict(),},
                                       namespace='/ozwave')
    def join_room_controller(self):
        """Join room controller"""
        #join_room("values")
        dispatcher.connect(self._louie_controller, ZWaveController.SIGNAL_CTRL_WAITING)
        dispatcher.connect(self._louie_controller, ZWaveController.SIGNAL_CONTROLLER)
        return True

    def leave_room_controller(self):
        """Leave room controller"""
        #join_room("values")
        dispatcher.disconnect(self._louie_controller, ZWaveController.SIGNAL_CTRL_WAITING)
        dispatcher.disconnect(self._louie_controller, ZWaveController.SIGNAL_CONTROLLER)
        return True

    def _louie_controller(self, state, message, network, controller):
            with self.app.test_request_context():
                from flask import request
#               request = req
                if network is None or controller is None:
                    logging.debug('OpenZWave controller message : Nework or Controller is None.')
                    self.socketio.emit('my message response',
                                       {'data': {'state':None, 'message':None},},
                                       namespace='/ozwave')
                else:
                    logging.debug('OpenZWave controller message : state %s - message %s.', state, message)
                    self.socketio.emit('my message response',
                                       {'data': {'state':state, 'message':message},},
                                       namespace='/ozwave')

    def stop(self):
        """Stop the tread"""
        self.leave_room_nodes()
        self.leave_room_values()
        self.leave_room_controller()
        self.leave_room_network()
        logging.info("Stop listener")
        #if self.is_alive() == True:
        #self.terminate()
        #self._stopevent.set( )

def start_listener(app_, socketio_):
    global listener
    if listener is None:
        listener = ListenerThread(socketio_, app_)
        listener.start()
    return listener

def stop_listener():
    global listener
    print "Stop listener"
    listener.stop()
    listener = None