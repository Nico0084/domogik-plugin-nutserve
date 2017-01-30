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

import threading

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
        self.value = u"UPSClient exception, " + value

    def __str__(self):
        return repr(self.value)

def getUPSId(device):
    """Return key UPS id."""
    if device.has_key('name') and device.has_key('id'):
        return "{0}_{1}".format(device['name'], device['id'])
    else : return None

def checkIfConfigured(deviceType,  device):
    if deviceType == 'ups.device' :
        if device["name"] : return True # and \
#           device["parameters"]["device"]["value"] : return True
        else : return False
    return False

class TimerClient(object):
    def __init__(self, tempo, callback, args= [], kwargs={}):
        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        self._tempo = float(tempo)

    def _run(self):
        self._timer = threading.Timer(self._tempo, self._run)
        self._timer.start()
        self._callback(*self._args, **self._kwargs)

    def start(self):
        self._timer = threading.Timer(self._tempo, self._run)
        self._timer.start()

    def stop(self):
        self._timer.cancel()

class UPSClient(object) :
    """Basic class for NUT server link."""

    def __init__ (self, manager, dmgDevice, log) :
        """Client init."""
        self._manager = manager
        self._dmgDevice = dmgDevice
        self.upsName = str(self.domogikDevice)
        self._log = log
        self._log.info(u"Creating UPSClient {0} ...".format(self.upsName))
        try :
            self.status = self._dmgDevice['sensors']['ups_status']['last_value']
        except :
            self.status = ""
        self._connected = False
        self._nutDevice = None
        self._typeVars = {}
        self._failedStatus = 0
        self._lock = threading.Lock()
        self._nutDevice = createDevice(self.getUPSVars(), log)
        self.__initSensorsValue()
        self._rwVars = self.getRWVars()
        self._upsCmds = self.getUPSCommands()
        self._getTypeVar()
        self.updateUPSVars()
        if 'timer_status' in self._dmgDevice['parameters'] :
            timer = self._dmgDevice['parameters']['timer_status']['value']
        else :
            timer = self._nutDevice.getPollInterval()
        self._log.debug(u'Parameter timer poll status: {0}'.format(timer))
        if timer !=0 :
            self._timerPollSt = TimerClient(timer, self.getUPSStatus)
            self._timerPollSt.start()
            self._log.info(u"Timer polling UPS status fo UPS Client {0} call every {1} sec.".format(self.upsName, timer))
        else :
            self._timerPollSt = None
            self._log.info(u"Timer polling UPS status desactivat fo UPS Client {0}".format(self.upsName))
        if 'timer_poll' in self._dmgDevice['parameters'] :
            timer = self._dmgDevice['parameters']['timer_poll']['value']
            self._timerPollValue = TimerClient(timer, self.updateUPSVars)
            self._timerPollValue.start()
            self._log.info(u"Timer polling UPS Value fo UPS Client {0} call every {1} sec.".format(self.upsName, timer))
        else : self._log.info(u"Timer polling UPS Value fo UPS Client {0} desactivat.".format(self.upsName))

    # On accède aux attributs uniquement depuis les property
    upsId = property(lambda self: getUPSId(self._dmgDevice))
    domogikDevice = property(lambda self: self._getDomogikDevice())

    def __del__(self):
        """Close updater timers."""
        self._log.debug(u"Try __del__ client")
        self.close()

    def close(self):
        """Send sensor message and Close updater timers."""
        self._log.info("Close UPS client {0}".format(self.upsName))
        if self._timerPollSt: self._timerPollSt.stop()
        self._timerPollValue.stop()
        sensors = self.getDmgSensors()
        # sensor event before status
        for sensor in sensors:
            if sensors[sensor]['data_type'] == 'DT_UPSEvent':
                self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], 'comms_lost')
        for sensor in sensors:
            if sensors[sensor]['data_type'] == 'DT_UPSState':
                self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], 'LB')

    def updateDevice(self, dmgDevice):
        """Update device data."""
        self._dmgDevice = dmgDevice
        self.upsName = str(self.domogikDevice)

    def _getDomogikDevice(self):
        """Return device Id for domogik device"""
        if self._dmgDevice :
            return self._dmgDevice['parameters']['device']['value']
        else : return None

    def getDmgDeviceId(self):
        """Return domogik device ID."""
        if self._dmgDevice :
            return self._dmgDevice['id']
        return None

    def getDmgCommands(self):
        """Return domogik commands for send message."""
        commands = {}
        if self._dmgDevice :
            for cmd in self._dmgDevice['commands']:
                commands[cmd] = {'parameters': self._dmgDevice['commands'][cmd]['parameters'],
                                 'id': self._dmgDevice['commands'][cmd]['id']}
        else :
            self._log.warning(u"Can't get domogik commands. Client {0} have not domogik device registered.".format(self.name))
        return commands

    def getDmgSensors(self):
        """Return domogik sensors status and error send."""
        sensors = {}
        if self._dmgDevice :
            for sensor in self._dmgDevice['sensors']:
                sensors[sensor] = {'data_type': self._dmgDevice['sensors'][sensor]['data_type'],
                                            'id': self._dmgDevice['sensors'][sensor]['id']}
        else :
            self._log.warning(u"Can't get domogik sensors. Client {0} have not domogik device registered.".format(self.name))
        return sensors

    def __initSensorsValue(self):
        self._sensorsValue = {'input.voltage' : 0, 'output.voltage' :0, 'battery.voltage' :0, 'battery.charge': 0}

    def _updateSensorValue(self, var, value):
        if var in ["input.voltage",  "output.voltage"]: threshold = 0.8
        elif var == "battery.voltage": threshold = 0.5
        elif var == "battery.charge": threshold = 2
        else: return False
        if (value <= self._sensorsValue[var] - threshold) or (value >= self._sensorsValue[var] + threshold) :
            self._sensorsValue[var] = value
            return True
        return False

    def getUPSVar(self, var):
        retval = self._manager.nut.getUPSVar(self.upsName,  var)
        if retval['error'] == '':
            if retval.has_key('var') and retval['var'] == var :
                return self.parseUPSVar(var,  retval['value'])
            else : return ''
        else :
            self.status = 'unknown'
            self._log.info(u"In getUPSVar Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updatelNutConnection(False)
            return ''

    def getUPSVars(self):
        retval = self._manager.nut.getUPSVars(self.upsName)
        if retval['error'] == '':
            if retval['cmd'] == 'LIST VAR':
                self.status = retval['data']['ups.status']
                if self._nutDevice :
                    self.updatelNutConnection(True)
                for var in retval['data']: retval['data'][var] = self.parseUPSVar(var,  retval['data'][var])
                return retval['data']
            else :
                self._log.warning(u"getUPSVars bad result : {0}".format(retval))
                return {}
        else :
            self.status = 'unknown'
            self._log.info(u"Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updatelNutConnection(False)
            return retval

    def getRWVars(self):
        retval = self._manager.nut.getUPSRWVars(str(self.upsName))
        self._log.debug(u'getRWVars : {0}'.format(retval))
        if retval['error'] == '':
            self.updatelNutConnection(True)
            return retval['data']
        else :
            self._log.info(u"In getRWVars Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updatelNutConnection(False)
        return retval

    def getUPSCommands(self):
        retval = self._manager.nut.getUPSCommands(self.upsName)
        self._log.debug(u'getUPSCommands : {0}'.format(retval))
        if retval['error'] == '':
            self.updatelNutConnection(True)
            return retval['data']
        else:
            self._log.info(u"Client UPS, NUT connection as client fail. {0}".format(retval['error']))
            self.updatelNutConnection(False)
        return retval

    def _getTypeVar(self,  var = None):
        if var :
            type = ''
            retval = self._manager.nut.getUPSVarType(self.upsName,  var)
            if retval['error'] == '':
                type = retval['type']
            else:
                self._log.info(u"Client UPS, {0} error in type var : {1}".format(var,  retval['error']))
                self.updatelNutConnection(False)
            return type
        elif self._nutDevice :
            if not self._typeVars : self._typeVars ={}
            for var in self._nutDevice._vars :
                if not self._typeVars.has_key(var) or self._typeVars[var] == '':
                    retval = self._manager.nut.getUPSVarType(self.upsName,  var)
                    if retval['error'] == '':
                        self._typeVars[var] = retval['type']
                        self._log.debug(u"--- new type {0} : {1}".format(var, self._typeVars[var]))
                    else:
                        self._log.warning(u"Client UPS, {0} error in type var : {1}".format(var,  retval['error']))
                        self.updatelNutConnection(False)
            return self._typeVars

    def parseUPSVar(self, var, value):
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
            self._log.warning(u'Get UPS Status fail : {0} time ({1})'.format(self._failedStatus,  status))
        else :
            self._failedStatus = 0
            if status != self.status :
                self.updateUPSVars(status)

    def updateUPSVars(self, newStatus=''):
        """Update UPS values and send sensor to MQ."""
        sensors = self.getDmgSensors()
        # set send status after ups event if needed.
        sendStatus = {}
        if newStatus != '':
            data = self._nutDevice.checkStatus({'ups.status': newStatus})
            sId = 'ups.status'.replace('.',  '_', 4) # get sensors domogik id format
            if data['modify'] :
                for sensor in sensors:
                    if sensor == sId:
                        sendStatus = {'id': sensors[sensor]['id'], 'data_type': sensors[sensor]['data_type'], 'status': newStatus}
        self._lock.acquire()
        upsVars = self.getUPSVars()
        if upsVars != {}:
#            self._log.debug(u"***** Update All UPS Variables {0}".format(upsVars))
            self._nutDevice.update(upsVars)
            data = self._nutDevice.checkAll()
#            self._log.debug(u"Sensors : {0}".format(sensors))
            for var in data :
                if var and var['modify'] :
                    for sensor in sensors:
                        if sensors[sensor]['data_type'] == "DT_UPSEvent":
                            self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], var['sensorsData']['event'])
            for var in upsVars :
                if self._updateSensorValue(var, upsVars[var]) :
                    sId = var.replace('.',  '_', 4) # get sensors domogik id format
                    for sensor in sensors:
                        if sensor == sId:
                            self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], float(upsVars[var]))
            if 'battery.charge' not in upsVars.keys():
                btCh = self._nutDevice.getBatteryCharge()
                if btCh :
                    if self._updateSensorValue('battery.charge', btCh):
                        for sensor in sensors:
                            if sensor == 'battery-charge':
                                self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], btCh)
        self._lock.release()
        # send status just after ups event and var update, in order to get good ups value at this momment
        if sendStatus != {} :
            self._manager.sendSensorValue(sendStatus['id'], sendStatus['data_type'], sendStatus['status'])

    def handle_UPS_Msg(self, message):
        """verifie si la valeur est a updater."""
        self._log.debug(u'In Client _handle_UPS_Msg : {0}'.format(message))

    def updatelNutConnection(self, state):
        if self._connected != state :
            d = self._nutDevice.checkConnection(state)
            if d['modify'] :
                self._connected = state
                data = {'device' : self.domogikDevice}
                data.update(d['sensorsData'])
                sensors = self.getDmgSensors()
                # send event before status
                for sensor in sensors:
                    if sensors[sensor]['data_type'] == 'DT_UPSEvent':
                        self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], d['sensorsData']['event'])
                for sensor in sensors:
                    if sensors[sensor]['data_type'] == 'DT_UPSState':
                        self._manager.sendSensorValue(sensors[sensor]['id'], sensors[sensor]['data_type'], d['sensorsData']['status'])
        if not state :
            self._manager.checkNutConnection()

    def sendCmd (self, dataType, cmd) :
        """Envoi la commande au server NUT"""
        return ""

    def handle_cmd(self, data):
        """Handle a UPS command from external."""
        if data['command'] == 'send' :
            self.sendCmd(data['code'])
        else : self._log.debug(u"UPS Client {0}, recieved unknows command {1}".format(getUPSId(self._dmgDevice), data['command']))
