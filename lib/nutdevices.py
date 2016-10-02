 # !/usr/bin/python
#-*- coding: utf-8 -*-

UPS_Events =  [{'onmains': {'keep' : False, 'description': 'The UPS has begun operating on mains power'},
                    'onbattery':{'keep' : False, 'description': 'The UPS has begun operating on battery power'}},
                    {'battlow': {'keep' : True, 'description': 'The UPS battery is low'},
                    'battfull': {'keep' : False, 'description':  'The UPS battery is fully charged'}},
                    {'bti': {'keep' : False, 'description': 'Battery test initiated'},
                    'btp': {'keep' : False, 'description': 'Battery Test Passed'},
                    'btf': {'keep' : False, 'description': 'Battery Test Failed'}},
                    {'comms_lost': {'keep' : True, 'description': 'The host has lost communication with the UPS'},
                    'comms_ok': {'keep' : False, 'description': 'Communication with the UPS has been restored'}},
                    {'input_freq_error': {'keep' : True, 'description': 'The input frequency is out of range'},
                    'input_freq_ok': {'keep' : False, 'description': 'The input frequency has returned from an error condition.'}},
                    {'input_voltage_high': {'keep' : True, 'description': 'The input voltage is too high'},
                    'input_voltage_low': {'keep' : True, 'description': 'The input voltage is too low'},
                    'input_voltage_ok': {'keep' : False, 'description': 'The input voltage is OK following a previously "too low" or "too high" state'}},
                    {'output_voltage_high': {'keep' : True, 'description': 'The UPS output voltage is too high'},
                    'output_voltage_low': {'keep' : True, 'description': 'THe UPS output voltage is too low'},
                    'output_voltage_ok': {'keep' : False, 'description': 'The UPS output voltage has returned to normal following a "too high" or "too low" condition.'}},
                    {'output_overload': {'keep' : True, 'description': 'The UPS output is in overload'},
                    'output_ok': {'keep' : False, 'description': 'The UPS output has returned from overload'}},
                    {'temp_high': {'keep' : True, 'description': 'The UPS temperature is too high'},
                    'temp_ok': {'keep' : False, 'description': 'The UPS temperature has returned from an over-temperature condition'}}]

def createDevice(data):
    """ Create a device depending of 'driver.name' given by data dict.
        - Developer : add your python class derived from DeviceBase class."""
    if data.has_key('driver.name') :
        if data['driver.name'] == 'blazer_usb' : return Blazer_USB(data)
        else : return DeviceBase(data)
    else : return DeviceBase(data)

class DeviceBase():
    """ Basic Class for driver functionnalities.
        - Developper : Use on inherite class to impllement new driver class
                Overwrite  methods to handle UPS event."""
    def __init__(self,  data):
        """ Not necessary overwrited.
            @param data : dict with all NUT vars formated by type.
                type : dict
        """
        self._connected = False
        self._vars = data
        self._UPS_Events = {}
        for events in UPS_Events :
            for event in events.keys() : self._UPS_Events[event] = False
        print self._vars
        self.checkAll()

    def update(self,  data):
        """ Create or update internal data.
            @param data : dict with all NUT vars formated by type.
                type : dict
        """
        if self._vars : self._vars.update(data)
        else : self._vars = data

    def handleUPS_Events(self, ups_Event, status):
        """Handle UPS event value, return value to set in 'event' key DT_UPSEvent sensor message.
            @param ups_Event : id of the UPS_Events
                type : str
            @param status : Event status to set, True/False
                type : bool
            @return Value to set in 'event' key, A modify flag to give change status
                type : tuple of str, bool
        """
        if self._UPS_Events.has_key(ups_Event):
            if self._UPS_Events[ups_Event] != status :
                self._UPS_Events[ups_Event] = status
                if status :
                    for events in UPS_Events :
                        if ups_Event in events.keys() :
                            for event in events.keys() :
                                if event != ups_Event :
                                    self._UPS_Events[event] = False
                            break
                    return True,  ups_Event
                else: return True, '',
            else:
                event = ''
                if status :
                    for events in UPS_Events :
                        if ups_Event in events.keys() :
                            if events[ups_Event]['keep'] : event = ups_Event
                            break
                return False,  event
        else :
            print(u"UPS key event '{0}' not exist.".format(ups_Event))
            return  False, 'error : {0} not exist.'.format(ups_Event),

    def getPollInterval(self):
        timer = 0
        if self._vars :
            if self._vars.has_key('driver.parameter.pollinterval') : timer = self._vars['driver.parameter.pollinterval']
            else : timer = 5
        return timer

    def checkAll(self):
        """ Check All UPS stuff and return they values.
            @return : list of all values
                type : list of dict {'modify': True/false, 'status': Formated status, 'event': UPS event type}.
            Developer :
                You can overwrite this method but it is essential to call original method at first.
                Overwrite could be necessary only for new check, otherwise overwrite existing methods.
                Overwriting structure :
                    data = DeviceBase.checkAll(self)
                    data = data.append(self.Your_New_Check())
                    .....
                    return data

        """
        data = []
        data.append(self.checkStatus())
        data.append(self.checkInputVoltage())
        data.append(self.checkInputFreq())
        data.append(self.checkOutputVoltage())
        data.append(self.checkOutput())
        data.append(self.checkTemperature())
        return data

    def checkConnection(self, state):
        """Return UPS status in key 'sensorsData'."""
        if self._connected != state :
            self._connected = state
            retVal = self.checkStatus(self._vars)
            retVal['modify'] = True
            if state : retVal['sensorsData']['event'] = self.handleUPS_Events('comms_ok',  True)[1]
            else : retVal['sensorsData'] = {'status': 'LB', 'event': self.handleUPS_Events('comms_lost',  True)[1]}
            return retVal
        return {'modify' : False}

    def checkStatus(self,  data = None):
        """Return UPS status in key 'sensorsData'."""
        if not data : data = self._vars
        retVal = {'modify' : False}
        if data.has_key('ups.status'):
            status = data['ups.status']
            if self._vars and self._vars.has_key('ups.status'):
                retVal['modify'] = False if status == self._vars['ups.status'] else True
            else :
                self.update(data)
                retVal['modify'] = True
            if status == 'OL' :
                retVal['sensorsData'] = {'status': status, 'event': self.handleUPS_Events('onmains',  True)[1]}
#                self.handleUPS_Events('onbattery',  False)
            elif  status == 'OB' :
                retVal['sensorsData'] = {'status': status, 'event': self.handleUPS_Events('onbattery',  True)[1]}
#                self.handleUPS_Events('onmains',  False)
            elif status == 'LB' :
                retVal['sensorsData'] = {'status': status, 'event' : ''}
                retVal['modify'], retVal['sensorsData']['event'] =  self.handleUPS_Events('battlow',  True)
                self.handleUPS_Events('onmains',  False)
                self.handleUPS_Events('onbattery',  False)
            else :
                retVal['sensorsData'] = {'status': 'LB', 'event': 'unknown' if retVal['modify'] else ''}
                self.handleUPS_Events('onmains',  False)
                self.handleUPS_Events('onbattery',  False)
            return retVal
        retVal['sensorsData'] = {'status': 'LB', 'event': 'unknown'}
        return retVal

    def checkBattery(self):
        """Check battery status."""
        retVal = self.checkStatus()
        if self._vars.has_key('ups.status'):
            if self._vars['ups.status'] == 'LB' : return retVal
        charge = self.getBatteryCharge()
        if charge :
            retVal = self.checkStatus(self._vars)
            if charge >= 100 :
                retVal['modify'],  retVal['sensorsData']['event'] = self.handleUPS_Events('battfull', True)
            elif charge <= 20 :
                retVal['modify'],  retVal['sensorsData']['event']  = self.handleUPS_Events('battlow', True)
            else :
                if self._UPS_Events['battfull'] :
                    retVal['modify'],  retVal['sensorsData']['event'] = self.handleUPS_Events('battfull', False)
                if self._UPS_Events['battlow'] :
                    retVal['modify'],  retVal['sensorsData']['event'] = self.handleUPS_Events('battlow', False)
            return retVal
        return None

    def getBatteryCharge(self):
        """ Return battery level charge (0 to 100%).
            @return : value charge (0 to 100%)
                type: float
            Developer :
                You can overwrite this method but it is essential to call original method at first, Because if NUt serve has is own level it's probably the better.
                Overwriting structure, begin your method with :
                    charge = DeviceBase.getBatteryCharge(self)
                    if charge: return charge
                    ............
        """
        if self._vars.has_key('battery.charge') :
            return self._vars['battery.charge']
        return None

    def checkInputVoltage(self):
        return None

    def checkInputFreq(self):
        return None

    def checkOutputVoltage(self):
        return None

    def checkOutput(self):
        return None

    def checkTemperature(self):
        return None

class Blazer_USB(DeviceBase):

    def getBatteryCharge(self):
        charge = DeviceBase.getBatteryCharge(self)
        if charge: return charge
        if self._vars.has_key('battery.voltage.high') : high = self._vars['battery.voltage.high']
        elif self._vars.has_key('battery.voltage.nominal') : high = self._vars['battery.voltage.nominal']
        else:
            return None
        if self._vars.has_key('battery.voltage.low') : low = self._vars['battery.voltage.low']
        else: low = 0.75 * high
        if self._vars.has_key('battery.voltage'):
            if self._vars['battery.voltage'] > high : high = self._vars['battery.voltage']
            charge = ((self._vars['battery.voltage'] - low) / (high - low)) * 100
        return charge

    def checkInputVoltage(self):
        if self._vars.has_key('input.voltage.nominal') :
            high = self._vars['input.voltage.nominal'] * 1.06
            low = self._vars['input.voltage.nominal'] * 0.94
        else : return None
        if self._vars.has_key('input.voltage') :
            retVal = self.checkStatus()
            if self._vars['input.voltage'] >= high :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('input_voltage_high',  True)
            elif self._vars['input.voltage'] <= low :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('input_voltage_low',  True)
            else :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('input_voltage_ok',  True)
            return retVal
        return None

    def checkInputFreq(self):
        if self._vars.has_key('input.frequency.nominal') and self._vars.has_key('input.frequency'):
            high = self._vars['input.frequency.nominal'] * 1.02
            low = self._vars['input.frequency.nominal'] * 0.98
            retVal = self.checkStatus()
            if (self._vars['input.frequency'] >= high) or (self._vars['input.frequency'] <= low):
               retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('input_freq_error',  True)
            else:
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('input_freq_ok',  True)
            return retVal
        return None

    def checkOutputVoltage(self):
        if self._vars.has_key('input.voltage.nominal') :
            high = self._vars['input.voltage.nominal'] * 1.06
            low = self._vars['input.voltage.nominal'] * 0.94
        else : return None
        if  self._vars.has_key('output.voltage') :
            retVal = self.checkStatus()
            if self._vars['output.voltage'] >= high :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('output_voltage_high',  True)
            elif self._vars['output.voltage'] <= low :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('output_voltage_low',  True)
            else :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('output_voltage_ok',  True)
            return retVal
        return None

    def checkOutput(self):
        if self._vars.has_key('input.current.nominal') and self._vars.has_key('input.current'):
            high = self._vars['input.current.nominal'] * 1.05
            low = self._vars['input.current.nominal'] * 0.95
            retVal = self.checkStatus()
            if (self._vars['input.current'] >= high) or (self._vars['input.current'] <= low):
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('output_overload',  True)
            else:
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('output_ok',  True)
            return retVal
        return None

    def checkTemperature(self):
        if self._vars.has_key('ups.temperature'):
            high = 40  # TODO : Check what is this ups temperature
            retVal = self.checkStatus()
            if (self._vars['ups.temperature'] >= high) :
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('temp_high',  True)
            else:
                retVal['modify'], retVal['sensorsData']['event'] = self.handleUPS_Events('temp_ok',  True)
            return retVal
        return None

if __name__ == "__main__" :

    DATASAMPLE = { 'battery.voltage.nominal': 12.0,
                        'battery.voltage': 13.60,
                        'beeper.status': 'enabled',
                        'device.type': 'ups',
                        'driver.version.internal': 0.04,
                        'driver.name': 'blazer_usb',
                        'driver.version': '2.6.3',
                        'driver.parameter.pollinterval': 2,
                        'driver.parameter.port': '/dev/upsZ3',
                        'driver.parameter.productid': 5161,
                        'driver.parameter.vendorid': 0665,
                        'input.voltage.nominal': 230,
                        'input.voltage.fault': 240.2,
                        'input.voltage': 240.2,
                        'input.current.nominal': 2.0,
                        'input.frequency.nominal': 50,
                        'input.frequency': 49.9,
                        'output.voltage': 240.2,
                        'ups.type': 'offline',
                        'ups.vendorid': 0665,
                        'ups.delay.shutdown': 30,
                        'ups.productid': 5161,
                        'ups.delay.start': 180,
                        'ups.status': 'OL'
                    }

    sample2 =dict(DATASAMPLE)
    sample2['input.voltage'] = 210
    sample2['ups.status'] ='OB'
    dev = createDevice(DATASAMPLE)
    print dev.checkConnection(True)
    print dev.checkStatus(sample2)
    print dev.checkBattery()
    print dev.getBatteryCharge()
    print dev.checkInputVoltage()
    dev.update(sample2)
    print dev.checkInputVoltage()
    print dev.checkInputVoltage()
    sample2['input.voltage'] = 240
    sample2['ups.status'] ='OL'
    dev.update(sample2)
    print dev.checkInputVoltage()
    print dev.checkInputVoltage()
    print dev.checkOutputVoltage()
    sample2['output.voltage'] = 260
    dev.update(sample2)
    print dev.checkOutputVoltage()
    print dev.checkInputFreq()
    print dev.checkOutput()
    print dev.checkTemperature()
    sample2['ups.status'] ='LB'
    dev.update(sample2)
    print dev.checkBattery()
    print dev.checkBattery()
    sample2['ups.status'] ='OB'
    dev.update(sample2)
    print dev.checkBattery()
    print dev.checkBattery()
    sample2['battery.voltage'] = 8
    dev.update(sample2)
    print dev.checkBattery()
    print dev.checkAll()
