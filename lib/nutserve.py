# !/usr/bin/python
#-*- coding: utf-8 -*-

#import PyNUT
import traceback

from domogik_packages.plugin_nutserve.lib.upsclient import UPSClient, getUPSId, checkIfConfigured
from domogik_packages.plugin_nutserve.lib.nutsockclient import NUTSocketClient

class NUTMonitorException(Exception):
    """
    NUT Monitor exception
    """
    def __init__(self, value):
        Exception.__init__(self)
        self.value = u"NutMonitor exception" + value

    def __str__(self):
        return repr(self.value)

class UpsManager :

    """" Manager UPS Clients.
    """
    def __init__ (self, plugin, host, port, login, pwd, cb_send_sensor) :
        """Initialise le manager UPS Clients"""
        self._plugin = plugin
        self._host = host
        self._port = str(port)
        self._send_sensor = cb_send_sensor
        self._stop = plugin.get_stop()  # TODO : pas forcement util ?
        self.upsClients = {} # list of all UPS
        self._login = str(login) if login else None
        self._pwd = str(pwd) if pwd else None
        self.nut = None
        try :
            self.connectNUTServer()
            self._plugin.log.debug(u"---- NUT UPS list ----\n".format(self.nut.getUPSList()))
        except :
            pass
        self._plugin.log.info(u"Manager UPS Clients is ready.")

    def _del__(self):
        """Delete all UPS CLients"""
        for id in self.upsClients : self.upsClients[id] = None

    def stop(self):
        """Close all UPS CLients and NUTSocketClient"""
        self._plugin.log.info(u"Closing UPSManager.")
        for id in self.upsClients : self.upsClients[id].close()
        if self.nut: self.nut.handle_close()

    def connectNUTServer(self):
        """Connecting as client to NUT server"""
        try:
            self.nut = None
            self.nut = NUTSocketClient(self._host, self._port, self._login, self._pwd,  self._handle_UPS_Msg,  self._plugin.log)
            self._plugin.log.info(u"Manager UPS, NUT connection as client is ready.".format(self._host))
        except IOError as err:
            self.nut = None
            self._plugin.log.info(u"Manager UPS, NUT connection as client fail. {0}".format(err))

    def checkNutConnection(self):
        """Vérifie la connection au server NUT et essais de la relancer si besoin."""
        if self.nut :
            try :
                self.nut.getUPSList()
                return  True
            except IOError as err:
                self.nut = None
                self._plugin.log.warning(u"Manager UPS, NUT connection as client fail. {0}".format(err))
        if not self.nut :
            self.connectNUTServer()
            if self.nut :
                return True
        return False

    def isKnownClient(self, upsName):
        """Verifie si le client UPS est connu par NUT, retourne l'objet True, ou False"""
        if self.checkNutConnection() :
            try :
                upsList = self.nut.getUPSList()
                if upsList.has_key(upsName) :
                   return  True
                else: return False
            except IOError as err:
                self.nut = None
                self._plugin.log.info(u"Manager UPS, NUT connection as client fail. {0}".format(err))
        return False

    def sendNUTcmd(self,  upsName,  cmd):
        """Envoie une commmande au server NUT"""

    def addClient(self, dmgDevice):
        """Add a UPS from domogik device"""
        name = getUPSId(dmgDevice)
        if self.upsClients.has_key(name) :
            self._plugin.log.debug(u"Manager UPS : UPS Client {0} already exist, not added.".format(name))
            return False
        else:
            if checkIfConfigured(dmgDevice["device_type_id"], dmgDevice ) :
                if dmgDevice["device_type_id"] == "ups.device" :
                    self.upsClients[name] = UPSClient(self, dmgDevice, self._plugin.log)
                else :
                    self._plugin.log.error(u"Manager UPS : UPS Client type {0} not exist, not added.".format(name))
                    return False
                self._plugin.log.info(u"Manager UPS : created new client {0}.".format(name))
            else :
                self._plugin.log.info(u"Manager UPS : device not configured can't add new client {0}.".format(name))
                return False
            return True

    def removeClient(self, name):
        """Remove a UPS client and close it"""
        client = self.getClient(name)
        if client :
            client.close()
            self.upsClients.pop(name)

    def getClient(self, id):
        """Get UPS client object by id."""
        if self.upsClients.has_key(id) :
            return self.upsClients[id]
        else :
            return None

    def getIdsClient(self, idToCheck):
        """Get UPS client key ids."""
        retval =[]
        findId = ""
        self._plugin.log.debug (u"getIdsClient check for device : {0}".format(idToCheck))
        if isinstance(idToCheck,  UPSClient) :
            for id in self.upsClients.keys() :
                if self.upsClients[id] == idToCheck :
                    retval = [id]
                    break
        else :
            self._plugin.log.debug (u"getIdsClient, no UPSClient instance...")
            if isinstance(idToCheck,  str) :
                findId = idToCheck
                self._plugin.log.debug (u"str instance...")
            else :
                if isinstance(idToCheck,  dict) :
                    if idToCheck.has_key('device') : findId = idToCheck['device']
                    else :
                        if idToCheck.has_key('name') and idToCheck.has_key('id'):
                            findId = getUPSId(idToCheck)
            if self.upsClients.has_key(findId) :
                retval = [findId]
                self._plugin.log.debug (u"key id type find")
            else :
                self._plugin.log.debug (u"No key id type, search {0} in devices {1}".format(findId, self.upsClients.keys()))
                for id in self.upsClients.keys() :
                    self._plugin.log.debug(u"Search in list by device key : {0}".format(self.upsClients[id].domogikDevice))
                    if self.upsClients[id].domogikDevice == findId :
                        self._plugin.log.debug('find UPS Client :)')
                        retval.append(id)
        self._plugin.log.debug(u"getIdsClient result : {0}".format(retval))
        return retval

    def checkClientsRegistered(self, dmgDevices):
        """Check if UPS clients existing or not in domogiks devices and do creation, update or remove action."""
        for device in dmgDevices:
            cId = getUPSId(device)
            if self.clients.has_key(cId) :  # Client exist with same ref, just do an update of parameters
                 self.clients[cId].updateDevice(device)
            else :
                exist_Id = self.getIdsClient(device)
                if exist_Id != [] :
                    if len(exist_Id) == 1 : # Client exist but without same ref, just do an update of parameters
                        self.clients[cId] = self.clients.pop(exist_Id[0]) # rename and change key client id
                        self.Plugin.log.info(u"Notify Client {0} renamed {1}".format(exist_Id[0], cId))
                        self.clients[cId].updateDevice(device)  # update client
                    else :
                        self.log.warning(u"Inconsistency clients for same domogik device. Clients: {0}, domogik device :{1}".format(exist_Id, device))
                else :  # client doesn't exist, create it:
                    try :
                        if self.managerClients.addClient(device) :
                            self.clients[cId].NotifyConnection()
                            self.log.info(u"Ready to work with device {0}".format(cId))
                        else : self.log.info(u"Device parameters not configured, can't create Notify Client : {0}".format(cId))
                    except:
                        self.log.error(traceback.format_exc())
        # check clients to remove
        delC = []
        for cId in self.clients:
            for device in dmgDevices:
                if getUPSId(device) == cId :
                    find = True
                    break;
            if not find : delC.append(cId)
        for cId in delC : self.removeClient(cId)

    def _handle_UPS_Msg(self,  msg):
        """dispatch to client UPS msg received by broadcast."""
        if msg.has_key('ups') :
            for id in self.upsClients :
                if self.upsClients[id].upsName == msg['ups']:
                    self.upsClients[id].handle_UPS_Msg(msg)
                    break

    def sendSensorValue(self, sensor_id, dt_type, value):
        """Send value to domogik sensor """
        self._send_sensor(sensor_id, dt_type, value)
