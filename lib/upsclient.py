# !/usr/bin/python
#-*- coding: utf-8 -*-


""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Monitor UPS (Uninterruptible Power Supplies) through NUT lib

Implements
==========

- class UPSclients to handle UPS

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2007-2014 Domogik project
@license: GPL(v3)
@organization: Domogik
"""


import json
import threading
import time
import sys
from domogik_packages.plugin_nutserve.lib.nutdevices import createDevice


UPSEvent =  {'onmains': 'The UPS has begun operating on mains power', 
                    'onbattery':'The UPS has begun operating on battery power', 
                    'battlow': 'The UPS battery is low',
                    'battfull': 'The UPS battery is fully charged',
                    'bti': 'Battery test initiated',
                    'btp': 'Battery Test Passed',
                    'btf': 'Battery Test Failed',
                    'comms_lost': 'The host has lost communication with the UPS',
                    'comms_ok': 'Communication with the UPS has been restored',
                    'input_freq_error': 'The input frequency is out of range',
                    'input_freq_ok': 'The input frequency has returned from an error condition.',
                    'input_voltage_high': 'The input voltage is too high',
                    'input_voltage_low': 'The input voltage is too low',
                    'input_voltage_ok': 'The input voltage is OK following a previously "too low" or "too high" state',
                    'output_voltage_high': 'The UPS output voltage is too high',
                    'output_voltage_low': 'THe UPS output voltage is too low',
                    'output_voltage_ok': 'The UPS output voltage has returned to normal following a "too high" or "too low" condition.',
                    'output_overload': 'The UPS output is in overload',
                    'output_ok': 'The UPS output has returned from overload',
                    'temp_high': 'The UPS temperature is too high',
                    'temp_ok': 'The UPS temperature has returned from an over-temperature condition'
                    }
    
class UPSClientException(Exception):
    """
    IRClient exception
    """
    def __init__(self, value):
        Exception.__init__(self)
        self.value = "UPSClient exception, " + value

    def __str__(self):
        return repr(self.value)

def getUPSId(device):
    """Return key UPS id."""
    if device.has_key('name') and device.has_key('id'):
        return "{0}_{1}".format(device['name'], + device['id'])
    else : return None
    
def checkIfConfigured(deviceType,  device):
#    print device
    if deviceType == 'ups.device' :
        if device["name"] : return True # and \
#           device["parameters"]["device"]["value"] : return True
        else : return False
    return False

class TimerClient:
    def __init__(self, tempo, callback, args= [], kwargs={}):
        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        self._tempo = tempo

    def _run(self):
        self._timer = threading.Timer(self._tempo, self._run)
        self._timer.start()
        self._callback(*self._args, **self._kwargs)
        
    def start(self):
        self._timer = threading.Timer(self._tempo, self._run)
        self._timer.start()

    def stop(self):
        self._timer.cancel()

class UPSClient :
    "Objet client de base pour la liaison server NUT."

    def __init__ (self,  manager,  device, log) :
        "Initialise le client"
        self._manager = manager
        self._device = device
        self._cptDmgUpDev = 100
        self.upsName = str(self.domogikDevice)
        self._log = log
        self.status = ""
        self._connected = False
        self._nutDevice = None
        self._typeVars = {}
        self._failedStatus = 0
        self._lock = threading.Lock()
        self._nutDevice = createDevice(self.getUPSVars())
        self.__initSensorsValue()
        self._rwVars = self.getRWVars()
        self._upsCmds = self.getUPSCommands()
        self._getTypeVar()
        self.updateUPSVars()
        timer = self._manager._xplPlugin.get_parameter(self._device, 'timer_poll')
        print 'Get parameter timer poll status: ',  timer
        if timer == None : 
            timer = self._nutDevice.getPollInterval()
        if timer !=0 :
            self._timerPollSt = TimerClient(timer,  self.getUPSStatus)
            self._timerPollSt.start()
            self._log.info("Timer polling UPS status fo UPS Client {0} call every {1} sec.".format(self.upsName,  timer))
        else :
            self._timerPollSt = None
            self._log.info("Timer polling UPS status desactivat fo UPS Client {0}".format(self.upsName))
        self._timerPollValue = TimerClient(30,  self.updateUPSVars)
        self._timerPollValue.start()
        self._log.info("Timer polling UPS Value fo UPS Client {0} call every {1} sec.".format(self.upsName,  30))

    # On accède aux attributs uniquement depuis les property
    upsId = property(lambda self: getUPSId(self._device)) 
    domogikDevice = property(lambda self: self._getDomogikDevice())

    def __del__(self):
        '''Send Xpl message and Close updater timers.'''
        print "Try __del__ client"
        self.close()
        
    def close(self):
        """Send Xpl message and Close updater timers."""
        self._log.info("Close UPS client {0}".format(self.upsName))
        if self._timerPollSt: self._timerPollSt.stop()
        self._timerPollValue.stop()
        data = {'device' : self.domogikDevice, 'status': 'unknown', 'event': 'comms_lost'}
        self._manager.sendXplTrig('ups.basic',  data)
        
    def updateDevice(self,  device):
        """Update device data."""
        self._device = device
        self.upsName = str(self.domogikDevice)

    def _getDomogikDevice(self):
        """Return device Id for xPL domogik device"""
        if self._cptDmgUpDev > 10 :
            self._cptDmgUpDev = 0
            if self._device :
                return self._manager._xplPlugin.get_parameter_for_feature(self._device, 'xpl_stats',  'xPL_UPS-Status',  'device')
            else : return None
        else :
            self._cptDmgUpDev += 1
            return self.upsName

    def __initSensorsValue(self):
        self._sensorsValue = {'input.voltage' : 0, 'output.voltage' :0, 'battery.voltage' :0, 'battery.charge': 0}
        
    def _updateSensorValue(self, var, value):
        if var in ["input.voltage",  "output.voltage"]: round = 0.2
        elif var == "battery.voltage": round = 0.1
        elif var == "battery.charge": round = 2
        else: return False
        if (value <= self._sensorsValue[var] - round) or (value >= self._sensorsValue[var] + round) :
            self._sensorsValue[var] = value
            return True
        return False
    
    def getUPSVar(self, var):
        retval = self._manager.nut.getUPSVar(self.upsName,  var)
#        print '   getUPSVar : ',  retval
        if retval['error'] == '':
#            self.updateXplNutConnection(True)
            if retval.has_key('var') and retval['var'] == var :
                return self.parseUPSVar(var,  retval['value'])
            else : return ''
        else :
            self.status = 'unknown'
            self._log.info(u"In getUPSVar Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updateXplNutConnection(False)
            return ''

    def getUPSVars(self):
        retval = self._manager.nut.getUPSVars(self.upsName)
#        print '   getUPSVarssss : ',   retval
        if retval['error'] == '':
            if retval['cmd'] == 'LIST VAR':
                self.status = retval['data']['ups.status']
                if self._nutDevice :
                    self.updateXplNutConnection(True)
                for var in retval['data']: retval['data'][var] = self.parseUPSVar(var,  retval['data'][var])
                return retval['data']
            else :
                print '     - getUPSVars No good result Abort by return {}'
                return {} 
        else :
            self.status = 'unknown'
            self._log.info(u"Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updateXplNutConnection(False)
            return retval

    def getRWVars(self):
        retval = self._manager.nut.getUPSRWVars(str(self.upsName))
        print '   getRWVars : ',   retval
        if retval['error'] == '':
            self.updateXplNutConnection(True)
            return retval['data']
        else :
            self._log.info(u"In getUPSVars Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updateXplNutConnection(False)
        return retval
        
    def getUPSCommands(self):
        retval = self._manager.nut.getUPSCommands(self.upsName)
        print '   getUPSCommands : ',   retval
        if retval['error'] == '':
            self.updateXplNutConnection(True)
            return retval['data']
        else:
            self._log.info(u"Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updateXplNutConnection(False)
        return retval
        
    def _getTypeVar(self,  var = None):
        if var :
#            print "*** Retrieve Single type var"
            type = ''
            retval = self._manager.nut.getUPSVarType(self.upsName,  var)
            if retval['error'] == '':
                type = retval['type']
            else:
                self._log.info(u"Client UPS, {0} error in type var : {1}".format(var,  retval['error']))
                self.updateXplNutConnection(False)
#            print var,  type
            return type
        elif self._nutDevice :
            if not self._typeVars : self._typeVars ={}
            print "*** Retrieve all type vars"
            for var in self._nutDevice._vars :
                if not self._typeVars.has_key(var) or self._typeVars[var] == '': 
                    retval = self._manager.nut.getUPSVarType(self.upsName,  var)
                    if retval['error'] == '':
                        self._typeVars[var] = retval['type']
                        print "--- new type {0} : {1}".format(var, self._typeVars[var] )
                    else:
                        self._log.info(u"Client UPS, {0} error in type var : {1}".format(var,  retval['error']))
                        self.updateXplNutConnection(False)
#            print self._typeVars
            return self._typeVars
    
    def parseUPSVar(self, var,  value):
        if not self._typeVars.has_key(var) :
            type = self._getTypeVar(var) 
            if type !='': self._typeVars[var] = type
        else: type = self._typeVars[var]
        if type in ['', 'UNKNOWN'] :
            try :
                v = int(value)
                type = 'INTEGER'
            except :
                try : 
                    v = float(value)
                    type = 'FLOAT'
                except :
                    type = 'STRING'
            if self._typeVars.has_key(var) : self._typeVars[var] = type
#            print "++++ parse new type {0} = {1}".format(var, self._typeVars[var] )
        if type == 'STRING' : return str(value)
        elif type == 'RANGE' : return int(value)
        elif type == 'ENUM' : return str(value)
        elif type == 'INTEGER' : return int(value)
        elif type == 'FLOAT' : return float(value)
        else : return value
    
    def getUPSStatus(self):
        self._lock.acquire()
        status = self.getUPSVar('ups.status')
        self._lock.release()
        if status =='' : 
            self._failedStatus += 1
            print '++++ Get UPS Status fail : {0} time ({1})'.format(self._failedStatus,  status)
        else :
            self._failedStatus = 0
            print '++++ Get UPS Status : ', status 
            if status != self.status :
                self.updateUPSVars()

        
    def updateUPSVars(self):
        """Update les valeurs de l'UPS et envois les xpl-trig au besoin.""" 
        self._lock.acquire()
        upsVars = self.getUPSVars()
        if upsVars != {}:
            print "***** Update All UPS Variables"
            self._nutDevice.update(upsVars)
            data = self._nutDevice.checkAll()
            for var in data :
                if var and var['modify'] :
                    self.sendXplUpdate('ups.basic',  var['xPLData'])
            for var in upsVars :
                if self._updateSensorValue(var, upsVars[var]) :
                    self.sendXplUpdate('sensor.basic', {var.replace('.',  '-', 4): float(upsVars[var])})
#                else : print 'No Xpl Update for {0}, value : {1}'.format(var,  upsVars[var])
            if 'battery.charge' not in upsVars.keys():
                btCh = self._nutDevice.getBatteryCharge()
                if btCh :
                    if self._updateSensorValue('battery.charge',  btCh):
                        self.sendXplUpdate('sensor.basic', {'battery-charge' : btCh})
        self._lock.release()

    def sendXplUpdate(self,  schema,  data):
        """Envoi un message xpl-trig sur le réseaux xPL.""" 
        data['device'] = self.domogikDevice
        self._manager.sendXplTrig(schema,  data)
    
    def handle_UPS_Msg(self, message):
        """verifie si la valeur est à updater."""
        print '*** In Client _handle_UPS_Msg : ',  message
        
    
    def updateXplNutConnection(self,  state):
        if self._connected != state :
            d = self._nutDevice.checkConnection(state)
            if d['modify'] :
                self._connected = state
                data = {'device' : self.domogikDevice}
                data.update(d['xPLData'])
                self._manager.sendXplTrig('ups.basic',  data)
        if not state :
            self._manager.checkNutConnection()

    def sendCmd (self,  dataType, cmd) :
        """Envoi la commande au server NUT"""
        return ""

    def handle_xpl_cmd(self,  xPLmessage):
        '''Handle a xpl-cmnd message from hub.
        '''
        if xPLmessage['command'] == 'send' :
            self.sendCmd(xPLmessage['code'])
        else : self._log.debug(u"UPS Client {0}, recieved unknows command {1}".format(getIRTransId(self._device), xPLmessage['command']))
