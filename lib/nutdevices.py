 # !/usr/bin/python
#-*- coding: utf-8 -*-

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
                    
def createDevice(data):
    """Create a device depending of 'driver.name' given by data dict.
        - Developer : add your python class derived from DeviceBase class."""
    if data.has_key('driver.name') :
        if data['driver.name'] == 'blazer_usb' : return Blazer_USB(data)
        else : return DeviceBase(data)
    else : return DeviceBase(data)
                    
class DeviceBase():
    """ Basic Class for driver functionnalities.
        - Developper : Use on inherite class to impllement new driver class
                Overwrite methodes to handle xpl event."""
    def __init__(self,  data):
        self._connected = False
        self._vars = data
        self._xPLEvents = {}
        for k in UPSEvent.keys() : self._xPLEvents[k] = False
        print self._vars
        self.checkAll()
        
    def update(self,  data):
        if self._vars : self._vars.update(data)
        else : self._vars = data
        
    def _handleXplEvent(self, xPLEvent,  status):
        if self._xPLEvents.has_key(xPLEvent):
            if self._xPLEvents[xPLEvent] != status :
                self._xPLEvents[xPLEvent] = status
                if xPLEvent == 'comms_ok' : self._xPLEvents['comms_lost'] = not status
                elif xPLEvent == 'comms_lost' : self._xPLEvents['comms_ok'] = not status
                return xPLEvent if status else ''
            else: return ''
        else :
            print "xPL key event '{0}' not exist.".format(xPLEvent)
            return 'error : {0} not exist.'.format(xPLEvent)

    def getPollInterval(self):
        timer =0
        if self._vars :
            if self._vars.has_key('driver.parameter.pollinterval') : timer = self._vars['driver.parameter.pollinterval']
            else : timer = 5
        return timer
        
    def checkAll(self):
        data = []
        data.append(self.checkStatus())
        data.append(self.checkInputVoltage())
        data.append(self.checkInputFreq())
        data.append(self.checkOutputVoltage())
        data.append( self.checkOutput())
        data.append(self.checkTemperature())
        return data
     
    def checkConnection(self, state):
        "Return UPS status with xPL specifications in key 'xPLData'."
        if self._connected != state :
            self._connected = state
            retVal = self.checkStatus(self._vars)
            retVal['modify'] = True
            if state : retVal['xPLData']['event'] = self._handleXplEvent('comms_ok',  True)
            else : retVal['xPLData'] = {'status': 'unknown', 'event': self._handleXplEvent('comms_lost',  True)}
            return retVal
        return {'modify' : False}
    
    def checkStatus(self,  data = None):
        "Return UPS status with xPL specifications in key 'xPLData'."
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
                retVal['xPLData'] = {'status': 'mains', 'event': self._handleXplEvent('onmains',  True)}
                self._handleXplEvent('onbattery',  False)
            elif  status == 'OB' :
                retVal['xPLData'] = {'status': 'battery', 'event': self._handleXplEvent('onbattery',  True)}
                self._handleXplEvent('onmains',  False)
            elif status == 'LB' : 
                retVal['xPLData'] = {'status': 'unknown', 'event': self._handleXplEvent('battlow',  True)}
                self._handleXplEvent('onmains',  False)
                self._handleXplEvent('onbattery',  False)
            else :
                retVal['xPLData'] = {'status': 'unknown', 'event': 'unknown' if retVal['modify'] else ''}
                self._handleXplEvent('onmains',  False)
                self._handleXplEvent('onbattery',  False)
            return retVal
        retVal['xPLData'] = {'status': 'unknown', 'event': 'unknown'}
        self._handleXplEvent('onmains',  False)
        self._handleXplEvent('onbattery',  False)
        return retVal
    
    def checkBattery(self):
        retVal = {'modify' : False}
        if self._vars.has_key('ups.status'):
            if self._vars['ups.status'] == 'LB' :
                retVal['modify'] = True if self._handleXplEvent('battlow', True) != '' else False
                retVal['xPLData'] = {'status': 'unknown', 'event': 'battlow'}
                self._handleXplEvent('battfull', False)
                return retVal
        charge = self.getBatteryCharge()
        if charge :
            retVal = self.checkStatus(self._vars)
            if charge >= 100 :
                retVal['xPLData']['event'] = self._handleXplEvent('battfull', True)
                retVal['modify'] = True if retVal['xPLData']['event'] != '' else False 
            elif charge <= 20 :
                retVal['modify'] = True if self._handleXplEvent('battlow', True) != '' else False 
                retVal['xPLData'] = {'status': 'unknown', 'event': 'battlow'}
                self._handleXplEvent('battfull', False)
            else :
                if self._xPLEvents['battfull'] : 
                    retVal['modify'] = True
                    self._handleXplEvent('battfull', False)
                if self._xPLEvents['battlow'] : 
                    retVal['modify'] = True
                    self._handleXplEvent('battlow', False)
                retVal['xPLData']['event'] = ''
            return retVal
        return None
        
    def getBatteryCharge(self):
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
                retVal['modify'] = True if self._handleXplEvent('input_voltage_high',  True) != '' else False
                self._handleXplEvent('input_voltage_low',  False)
                self._handleXplEvent('input_voltage_ok',  False)
                retVal['xPLData']['event'] = 'input_voltage_high'
            elif self._vars['input.voltage'] <= low :
                retVal['modify'] = True if self._handleXplEvent('input_voltage_low',  True) != '' else False
                self._handleXplEvent('input_voltage_high',  False)
                self._handleXplEvent('input_voltage_ok',  False)
                retVal['xPLData']['event'] = 'input_voltage_low'
            else :
                retVal['xPLData']['event'] = self._handleXplEvent('input_voltage_ok',  True)
                retVal['modify'] = True if retVal['xPLData']['event']  != '' else False
                self._handleXplEvent('input_voltage_high',  False)
                self._handleXplEvent('input_voltage_low',  False)
            return retVal                
        return None
        
    def checkInputFreq(self):
        if self._vars.has_key('input.frequency.nominal') and self._vars.has_key('input.frequency'):
            high = self._vars['input.frequency.nominal'] * 1.02
            low = self._vars['input.frequency.nominal'] * 0.98
            retVal = self.checkStatus()
            if (self._vars['input.frequency'] >= high) or (self._vars['input.frequency'] <= low):
                retVal['modify'] = True if self._handleXplEvent('input_freq_error',  True) != '' else False
                self._handleXplEvent('input_freq_ok',  False)
                retVal['xPLData']['event'] = 'input_freq_error'
            else: 
                retVal['xPLData']['event'] = self._handleXplEvent('input_freq_ok',  True)
                retVal['modify'] = True if retVal['xPLData']['event']  != '' else False
                self._handleXplEvent('input_freq_error',  False)
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
                retVal['modify'] = True if self._handleXplEvent('output_voltage_high',  True) != '' else False
                self._handleXplEvent('output_voltage_low',  False)
                self._handleXplEvent('output_voltage_ok',  False)
                retVal['xPLData']['event'] = 'output_voltage_high'
            elif self._vars['output.voltage'] <= low :
                retVal['modify'] = True if self._handleXplEvent('output_voltage_low',  True) != '' else False
                self._handleXplEvent('output_voltage_high',  False)
                self._handleXplEvent('output_voltage_ok',  False)
                retVal['xPLData']['event'] = 'output_voltage_low'
            else :
                retVal['xPLData']['event'] = self._handleXplEvent('output_voltage_ok',  True)
                retVal['modify'] = True if retVal['xPLData']['event']  != '' else False
                self._handleXplEvent('output_voltage_high',  False)
                self._handleXplEvent('output_voltage_low',  False)
            return retVal                
        return None
    
    def checkOutput(self):
        if self._vars.has_key('input.current.nominal') and self._vars.has_key('input.current'):
            high = self._vars['input.current.nominal'] * 1.05
            low = self._vars['input.current.nominal'] * 0.95
            retVal = self.checkStatus()
            if (self._vars['input.current'] >= high) or (self._vars['input.current'] <= low):
                retVal['modify'] = True if self._handleXplEvent('output_overload',  True) != '' else False
                self._handleXplEvent('output_ok',  False)
                retVal['xPLData']['event'] = 'output_overload'
            else: 
                retVal['xPLData']['event'] = self._handleXplEvent('output_ok',  True)
                retVal['modify'] = True if retVal['xPLData']['event']  != '' else False
                self._handleXplEvent('output_overload',  False)
            return retVal      
        return None

    def checkTemperature(self):
        if self._vars.has_key('ups.temperature'):
            high = 40  # TODO : Check what is this ups temperature
            retVal = self.checkStatus()
            if (self._vars['ups.temperature'] >= high) :
                retVal['modify'] = True if self._handleXplEvent('temp_high',  True) != '' else False
                self._handleXplEvent('temp_ok',  False)
                retVal['xPLData']['event'] = 'temp_high'
            else: 
                retVal['xPLData']['event'] = self._handleXplEvent('temp_ok',  True)
                retVal['modify'] = True if retVal['xPLData']['event']  != '' else False
                self._handleXplEvent('temp_high',  False)
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
