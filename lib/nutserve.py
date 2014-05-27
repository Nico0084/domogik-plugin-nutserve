# !/usr/bin/python
#-*- coding: utf-8 -*-

#import PyNUT
import time
from domogik_packages.plugin_nutserve.lib.upsclient import UPSClient, getUPSId,  checkIfConfigured
from domogik_packages.plugin_nutserve.lib.nutsockclient import NUTSocketClient

class NUTMonitorException(Exception):
    """
    NUT Monitor exception
    """
    def __init__(self, value):
        Exception.__init__(self)
        self.value = "NutMonitor exception" + value

    def __str__(self):
        return repr(self.value)
        
class UpsManager :
    
    """" Manager UPS Clients.
    """
    def __init__ (self, xplPlugin,  host,  port,  login,  pwd, cb_send_xPL) :
        """Initialise le manager UPS Clients"""
        self._xplPlugin = xplPlugin
        self._host = host
        self._port = str(port)
        self._cb_send_xPL = cb_send_xPL
        self._stop = xplPlugin.get_stop()  # TODO : pas forcement util ?
        self.upsClients = {} # list of all UPS
        self._login = str(login) if login else None
        self._pwd = str(pwd) if pwd else None
        self.nut = None
        self.connectNUTServer()
        print "---- NUT UPS list ----\n",  self.nut.getUPSList()
        self._xplPlugin.log.info(u"Manager UPS Clients is ready.")
        
    def _del__(self):
        """Delete all UPS CLients"""
        print "try __del__ UPSClients"
        for id in self.upsClients : self.upsClients[id] = None
        
    def stop(self):
        """Close all UPS CLients and NUTSocketClient"""
        self._xplPlugin.log.info(u"Closing UPSManager.")
        for id in self.upsClients : self.upsClients[id].close()
        if self.nut: self.nut.handle_close()

    def connectNUTServer(self):
        """Connection en tant que client au server NUT"""
        try:
            self.nut = None
            self.nut = NUTSocketClient(self._host, self._port, self._login, self._pwd,  self._handle_UPS_Msg,  self._xplPlugin.log)
            self._xplPlugin.log.info(u"Manager UPS, NUT connection as client is ready.")
        except IOError as err:
            self.nut = None
            self._xplPlugin.log.info(u"Manager UPS, NUT connection as client fail. {0}".format(err))
            
    def checkNutConnection(self):
        """Vérifie la connection au server NUT et essais de la relancer si besoin."""
        print '----- check nut connection -----'
        if self.nut :
            print '   - NUT object exist try "GET LIST".'
            try :
                upsList = self.nut.getUPSList()
                print '       - "GET LIST"  OK.'
                return  True
            except IOError as err:
                self.nut = None
                print '       - "GET LIST"  ERR (timeout).'
                self._xplPlugin.log.info(u"Manager UPS, NUT connection as client fail. {0}".format(err))
        if not self.nut :
            print '   - NUT object NOT exist try connectNUTServer.'
            self.connectNUTServer()
            if self.nut :
                print '       - NUT object create.'
                return True
        return False
        
    def isKnownClient(self, upsName):
        """Verifie si le client UPS est connu par NUT, retourne l'objet True, ou False"""
        if self.checkNutConnection() :
            try :
                upsList = self.nut.getUPSList()
                if upslist.has_key(upsName) :
                   return  True
                else: return False
            except IOError as err:
                self.nut = None
                self._xplPlugin.log.info(u"Manager UPS, NUT connection as client fail. {0}".format(err))
        return False
     
    def sendNUTcmd(self,  upsName,  cmd):
        """Envoie une commmande au server NUT"""
    
    def addClient(self, device):
        """Add a UPS from domogik device"""
        name = getUPSId(device)
        if self.upsClients.has_key(name) :
            self._xplPlugin.log.debug(u"Manager UPS : UPS Client {0} already exist, not added.".format(name))
            return False
        else:
            if checkIfConfigured(device["device_type_id"],  device ) :
                if device["device_type_id"] == "ups.device" :
                    self.upsClients[name] = UPSClient(self,  device,  self._xplPlugin.log)
                else :
                    self._xplPlugin.log.error(u"Manager UPS : UPS Client type {0} not exist, not added.".format(name))
                    return False                
                self._xplPlugin.log.info(u"Manager UPS : created new client {0}.".format(name))
            else : 
                self._xplPlugin.log.info(u"Manager UPS : device not configured can't add new client {0}.".format(name))
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
        self._xplPlugin.log.debug (u"getIdsClient check for device : {0}".format(idToCheck))
        if isinstance(idToCheck,  IRTransClient) :
            for id in self.upsClients.keys() :
                if self.upsClients[id] == idToCheck :
                    retval = [id]
                    break
        else :
            self._xplPlugin.log.debug (u"getIdsClient, no UPSClient instance...")
            if isinstance(idToCheck,  str) :  
                findId = idToCheck
                self._xplPlugin.log.debug (u"str instance...")
            else :
                if isinstance(idToCheck,  dict) :
                    if idToCheck.has_key('device') : findId = idToCheck['device']
                    else :
                        if idToCheck.has_key('name') and idToCheck.has_key('id'): 
                            findId = getUPSId(idToCheck)
            if self.upsClients.has_key(findId) : 
                retval = [findId]
                self._xplPlugin.log.debug (u"key id type find")
            else :
                self._xplPlugin.log.debug (u"No key id type, search {0} in devices {1}".format(findId, self.upsClients.keys()))
                for id in self.upsClients.keys() :
                    self._xplPlugin.log.debug(u"Search in list by device key : {0}".format(self.upsClients[id].domogikDevice))
                    if self.upsClients[id].domogikDevice == findId : 
                        self._xplPlugin.log.debug('find UPS Client :)')
                        retval.append(id)
        self._xplPlugin.log.debug(u"getIdsClient result : {0}".format(retval))
        return retval
        
    def refreshClientDevice(self,  client):
        """Request a refresh domogik device data for a UPS Client."""
        cli = MQSyncReq(zmq.Context())
        msg = MQMessage()
        msg.set_action('device.get')
        msg.add_data('type', 'plugin')
        msg.add_data('name', self._xplPlugin.get_plugin_name())
        msg.add_data('host', get_sanitized_hostname())
        devices = cli.request('dbmgr', msg.get(), timeout=10).get()
        for a_device in devices:
            if a_device['device_type_id'] == client._device['device_type_id']  and a_device['id'] == client._device['id'] :
                if a_device['name'] != client.device['name'] : # rename and change key client id
                    old_id = getUPSId(client._device)
                    self.upsClients[getUPSId(a_device)] = self.upsClients.pop(old_id)
                    self._xplPlugin.log.info(u"UPS Client {0} is rename {1}".format(old_id,  getUPSId(a_device)))
                client.updateDevice(a_device)
                break
        
    def _handle_UPS_Msg(self,  msg):
        """dispatch to client UPS msg received by broadcast."""
        if msg.has_key('ups') :
            for id in self.upsClients :
                if self.upsClients[id].upsName == msg['ups']:
                    self.upsClients[id].handle_UPS_Msg(msg)
                    break
    
    def sendXplAck(self,  data):
        """Send an ack xpl message"""
        self._cb_send_xPL("sensor.basic", data)

    def sendXplTrig(self,  schema,  data):
        """Send an xpl message"""
        self._cb_send_xPL(schema,  data)
