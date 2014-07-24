#!/usr/bin/python
#-*- coding: utf-8 -*-create_device.py

### configuration ######################################
DEVICE_NAME="Z3_SERVER"
TIMER_POLL= 3
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

plugin =  "nutserve"

def create_device():
    ### create the device, and if ok, get its id in device_id
    client_id  = "plugin-{0}.{1}".format(plugin, get_sanitized_hostname())
    print("Creating the UPS device...")
    td = TestDevice()
    params = td.get_params(client_id, "ups.device")
        # fill in the params
    params["device_type"] = "ups.device"
    params["name"] = "test_UPS_Monitor"
    params["reference"] = "NUT Sockect client"
    params["description"] = "Monitor UPS"
    for idx, val in enumerate(params['global']):
        if params['global'][idx]['key'] == 'timer_poll' :  params['global'][idx]['value'] = TIMER_POLL

    for idx, val in enumerate(params['xpl']):
        params['xpl'][idx]['value'] = DEVICE_NAME

    # go and create
    td.create_device(params)
    print "Device UPS {0} configured".format(DEVICE_NAME) 
    
if __name__ == "__main__":
    create_device()



