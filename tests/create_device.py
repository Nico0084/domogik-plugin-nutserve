#!/usr/bin/python
#-*- coding: utf-8 -*-create_device.py

### configuration ######################################
DEVICE_NAME="Z3_SERVER"
TIMER_POLL= 3
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

def create_device():
    ### create the device, and if ok, get its id in device_id
    print("Creating the UPS device...")
    td = TestDevice()
    print 'host :',  get_sanitized_hostname()
    device_id = td.create_device("plugin-nutserve.{0}".format(get_sanitized_hostname()), "test_UPS_Monitor", "ups.device")
    print "Device UPS created"
    td.configure_global_parameters({"device" : DEVICE_NAME,  "timer_poll" : TIMER_POLL})
    print "Device UPS {0} configured".format(DEVICE_NAME) 
    
if __name__ == "__main__":
    create_device()



