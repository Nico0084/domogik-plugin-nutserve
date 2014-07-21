#!/usr/bin/python
# -*- coding: utf-8 -*-

from domogik.xpl.common.plugin import XplPlugin
from domogik.xpl.common.xplmessage import XplMessage
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor
from domogik.tests.common.testcommand import TestCommand


from domogik.common.utils import get_sanitized_hostname
from datetime import datetime
import unittest
import sys
import os
import traceback
import threading
import time

### global variables
DEVICE_NAME="Z3_SERVER"
TIMER_POLL = 3

class NUTServeTestCase(PluginTestCase):

    def test_0100_dummy(self):
        self.assertTrue(True)

    def test_0110_send_test_battery(self):
        """ check if the xpl messages about get_switch_state are OK
            Sample message : 
            xpl-trig
            {
            hop=1
            source=domogik-daikcode.domogik-vm1
            target=*
            }
            irtrans.basic
            {
            device=/home
            device=Daikin remote 1
            current=19465224
            }
        dmg_send xpl-cmnd irtrans.basic "device=IRTrans_1,command=send,datatype=IRTrans standard,code=a22222,timing=a45454"   
            
        """
        
        
        global device_id
        global xpl_plugin
        
        # do the test
        print(u"********** start testing xpl command send test_battery_start.")
        command = TestCommand(self,  device_id,  'test_battery_start')
        print (u'try to send xpl_cmnd fake....')  
        self.assertTrue(command.test_XplCmd({"test": 'a battery test',  "command": 'test-battery-start'}, {"result" :"ok"}))
        msg1_time = datetime.now()
        time.sleep(8)

    def send_xplTrig(self, data):
        """ Send xPL fake message on network
        """
        global xpl_plugin
        
        msg = XplMessage()
        msg.set_type("xpl-trig")
        msg.set_header(source ="domogik-{0}.{1}".format(self.name, get_sanitized_hostname()))
        msg.set_schema("sensor.basic")
        msg.add_data(data)
        print (u"send fake xpl switch on : {0}".format(msg))
        xpl_plugin.myxpl.send(msg)

    def send_xpCmd(self, data):
        """ Send xPL fake message on network
        """
        global xpl_plugin
        
        msg = XplMessage()
        msg.set_type("xpl-cmnd")
     #   msg.set_header(source ="domogik-{0}.{1}".format(self.name, get_sanitized_hostname()))
        msg.set_schema("ups.basic")
        msg.add_data(data)
        print (u"send fake xpl cmd on : {0}".format(msg))
        xpl_plugin.myxpl.send(msg)

if __name__ == "__main__":

    ### configuration

    # set up the xpl features
    xpl_plugin = XplPlugin(name = 'testnut', 
                           daemonize = False, 
                           parser = None, 
                           nohub = True,
                           test  = True)
    # set test plugin ready for manager
    th = threading.Thread(None, xpl_plugin.ready, "plugin_test_ready") 
    th.start()

    # set up the plugin name
    name = "nutserve"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = {'configured': True, 'host': '192.168.0.192', 'port': 3493, 'login': '', 'pwd': ''}

    ### start tests

    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except:
        print(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        sys.exit(1)

    # create a test device
    try:
        device_id = td.create_device(client_id, "test_UPS_Monitor", "ups.device")
        params = {"device" : DEVICE_NAME, "timer_poll" : TIMER_POLL}
        print (u"configure_global_parameters : {0}".format(params))
        td.configure_global_parameters(params)
    except:
        print(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        sys.exit(1)

    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(NUTServeTestCase("test_0001_domogik_is_running", xpl_plugin, name, cfg))
    suite.addTest(NUTServeTestCase("test_0010_configure_the_plugin", xpl_plugin, name, cfg))

    # start the plugin
    suite.addTest(NUTServeTestCase("test_0050_start_the_plugin", xpl_plugin, name, cfg))

    # do the specific plugin tests
    suite.addTest(NUTServeTestCase("test_0110_send_test_battery", xpl_plugin, name, cfg))

   # do some tests comon to all the plugins
    suite.addTest(NUTServeTestCase("test_9900_hbeat", xpl_plugin, name, cfg))
    suite.addTest(NUTServeTestCase("test_9990_stop_the_plugin", xpl_plugin, name, cfg))
    unittest.TextTestRunner().run(suite)

    # quit
    xpl_plugin.force_leave()
