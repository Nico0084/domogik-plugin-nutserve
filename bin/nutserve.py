#!/usr/bin/python
# -*- coding: utf-8 -*-

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
=====================================

- Nut Monitor service manager

@author: Nico <nico84dev@gmail.com>
@copyright: (C) 2013-2016 Domogik project
@license: GPL(v3)
@organization: Domogik
"""
# A debugging code checking import error
try:
    from domogik.common.plugin import Plugin
    from domogikmq.message import MQMessage
    import traceback
    import threading

    from domogik_packages.plugin_nutserve.lib.nutserve import UpsManager
    from domogik_packages.plugin_nutserve.lib.upsclient import getUPSId

    import traceback
except ImportError as exc :
    import logging
    logging.basicConfig(filename='/var/log/domogik/nutserve_start_error.log',level=logging.DEBUG)
    log = logging.getLogger('nutmonitor_start_error')
    err = "Error: Plugin Starting failed to import module ({})".format(exc)
    print err
    logging.error(err)
    print log

class NUTManager(Plugin):
    """ Main class running at plugin start
        Send and receive UPS codes
    """

    def __init__(self):
        """ Init plugin
        """
        Plugin.__init__(self, name='nutserve')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return
        host = self.get_config("host")
        port = self.get_config("port")
        login =  self.get_config("login")
        pwd =  self.get_config("pwd")
        # get the devices list
        self.managerClients = None
        self.refreshDevices()
        # get the config values
        self.managerClients = UpsManager(self, host, port, login if login else None, pwd if login else None, self.send_sensor)
        for a_device in self.devices :
            try :
                if a_device['device_type_id'] != 'ups.device' :
                    self.log.error(u"No a device type reconized : {0}".format(a_device['device_type_id']))
                    break
                else :
                    if self.managerClients.addClient(a_device) :
                        self.log.info("Ready to work with device {0}".format(getUPSId(a_device)))
                    else : self.log.info("Device parameters not configured, can't create UPS Client : {0}".format(getUPSId(a_device)))
            except:
                self.log.error(traceback.format_exc())
        self.add_stop_cb(self.managerClients.stop)
        self.log.info("Plugin ready :)")
        self.ready()

    def __del__(self):
        """Close managerClients"""
        print "Try __del__ self.managerClients."
        self.managerClients = None

    def threadingRefreshDevices(self, max_attempt = 2):
        """Call get_device_list from MQ
            could take long time, run in thread to get free process"""
        threading.Thread(None, self.refreshDevices, "th_refreshDevices", (), {"max_attempt": max_attempt}).start()

    def refreshDevices(self, max_attempt = 2):
        self.get_device_list(quit_if_no_device = False, max_attempt = 2)
        if self.devices != []:
            self.log.debug(u"Device list refreshed: {0}".format(self.devices))
            if self.managerClients is not None : self.managerClients.checkClientsRegistered(self.devices)
        elif self.devices == [] :
            self.log.warning(u"No existing device, create one with admin.")
        else :
            self.log.error(u"Can't retrieve the device list, MQ no response, try again or restart plugin.")

    def on_message(self, msgid, content):
        """Handle pub message from MQ"""
        if msgid == "device.update":
            self.log.debug(u"New pub message {0}, {1}".format(msgid, content))
            self.threadingRefreshDevices()

    def on_mdp_request(self, msg):
        """ Called when a MQ req/rep message is received
        """
        Plugin.on_mdp_request(self, msg)
        self.log.info(u"Received 0MQ messages: {0}".format(msg))
        action = msg.get_action().split(".")
        if action[0] == "client" and action[1] == "cmd" :
            # action on dmg device
            data = msg.get_data()
            reply_msg = MQMessage()
            reply_msg.set_action('client.cmd.result')
            idsClient = self.managerClients.getIdsClient(data)
            find = False
            if idsClient != [] :
                for id in idsClient :
                    client = self.managerClients.getClient(id)
                    if client :
                        self.log.debug(u"Handle requested action for NUT client {0} : {1}".format(id, data))
                        commands = client.getDmgCommands()
                        for cmd in commands :
                            if commands[cmd]['id'] == data['command_id'] :
                                find = True
                                client.handle_cmd(data)
                                reply_msg.add_data('status', True)
                                reply_msg.add_data('reason', None)
                                break

            if not find :
                self.log.warning(u"Requested action received for unknown NUT client : {0}".format(data))
                reply_msg.add_data('status', False)
                reply_msg.add_data('reason', u"Requested action received for unknown NUT client : {0}".format(data))
            self.log.debug(u"Reply to MQ: {0}".format(reply_msg.get()))
            self.reply(reply_msg.get())

    def send_sensor(self, sensor_id, dt_type, value):
        """Send pub message over MQ"""
        self.log.info(u"Sending MQ sensor id:{0}, dt type: {1}, value:{2}" .format(sensor_id, dt_type, value))
        self._pub.send_event('client.sensor', {sensor_id : value})

if __name__ == "__main__":
    NUTManager()
