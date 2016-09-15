 # !/usr/bin/python
#-*- coding: utf-8 -*-

import asyncore, socket
import threading
import time
from distutils import version

class NUTSocketClient(asyncore.dispatcher):

    def __init__(self, host, port, login=None, pwd=None, callback=None, log=None):
        asyncore.dispatcher.__init__(self)
        self.host = host
        self.port = int(float(port))
        self._cb = callback
        self._sync = False
        self.buffer = ""
        self.upscVer ="1.0.0"
        self._lastCmd =''
        self._data = ''
        self._bufData = ''
        self._waitList = False
        self.connected = False
        self._log = log
        print u" +++ Internal NUTSocketClient created +++"
        self.Connect_to_NUT()

    def __del__(self):
        print u" --- Internal NUTSocketClient deleted ---"

    def Connect_to_NUT(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (self.host, self.port))
        self.th = threading.Thread(None, self.runAsyncoreLoop, "th_run_asyncore.loop")
        self.th.start()
        self.connected = True
        if self._log: self._log.info(u'Socket Client connected to NUT Server {0}:{1}'.format(self.host, self.port))
        self.getNUTVersion()
        time.sleep(1)

    def runAsyncoreLoop(self):
        asyncore.loop(timeout = 1)
        self._connected = False
        if self._log: self._log.info(u'Asynchronous loop NUTsockectClient terminated.')

    def handle_connect(self):
        if self._log: self._log.info(u'Socket Client opened on NUT Server {0}:{1}'.format(self.host, self.port))

    def handle_close(self):
        if self._log: self._log.info(u'Socket Client disconnected from NUT Server {0}:{1}'.format(self.host, self.port))
        self.close()

    def handle_read(self):
        data = self.recv(8192)
#        print data
        if data :
            if not self._sync :
                print u"*********** Broadcast Message received , data : ",  data
                if self._cb : self._cb(self.received_message(data))
                else : print " No callback registered."
            else :
                lines = data.split('\n')
    #            print 'Handle_read : \n', lines
                if lines[0][:3] == 'ERR':
                    self._waitList = False
                    self._data = data
                elif lines[0][:10] == 'BEGIN LIST':
    #                print 'start wait list'
                    if lines[len(lines)-2][:8] == 'END LIST':
    #                    print 'End Wait List 0'
                        self._waitList = False
                        self._data = data
                    else:
    #                    print 'Wait List, 0 ...',  lines[len(lines)-2]
                        self._waitList = True
                        self._bufData = data
                elif lines[len(lines)-2][:8] == 'END LIST':
    #                print 'End Wait List X ',  lines[len(lines)-2]
                    self._data = self._bufData + data
                    self._bufData = ''
                    self._waitList = False
                elif self._waitList :
    #                print 'Wait List, next  ...'
                    self._bufData += data
                else:
                    self._data = data
#                    print 'Not List' , self._data
#            print '++++ END READ +++',  self._data
        else : print 20*"-" + " No data to read"

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]

    def received_message(self, message):
#        print "*********** Message received *************"
        lines = message.split("\n")
        data = {}
        if lines[0] =="BEGIN LIST UPS" : data = self._decodeUPSList(lines)
        elif lines[0][:14] =="BEGIN LIST VAR" : data = self._decodeListVars(lines)
        elif lines[0][:13] =="BEGIN LIST RW" : data = self._decodeListRWVars(lines)
        elif lines[0][:14] =="BEGIN LIST CMD" : data = self._decodeListCmds(lines)
        elif lines[0][:15] =="BEGIN LIST ENUM" : data = self._decodeListEnum(lines)
        elif lines[0][:16] =="BEGIN LIST RANGE" : data = self._decodeListRange(lines)
        elif lines[0][:4] =="TYPE" : data = self._decodeVarType(lines)
        elif lines[0][:3] =="VAR" : data = self._decodeVar(lines)
        elif lines[0][:9] =="NUMLOGINS" :
            data = {'cmd':'NUMLOGINS', 'error': '',  'data': lines[0].split()[2]}
        elif lines[0][:3] =="ERR" : data = self._decodeErrorNUT(lines)
        elif lines[0][:2] == "OK" : data = {'cmd': 'OK', 'error': '', 'data': {}}
        elif lines[0][:17] =="Network UPS Tools":
            data = {'cmd':'VER', 'error': '',  'data': lines[0].split()[4]}
            self.upscVer = data['data']
        else: print message
        self._lastCmd =''
        return data

    def _decodeErrorNUT(self, lines) :
        l = lines[0].split()
        err = l.pop(0)
        err = l.pop(0)
        retval = {'cmd': self._lastCmd, 'error': err,  'data' : []}
        for extra in l :
            retval['data'].append(extra)
        return retval

    def _decodeUPSList(self, lines):
        retval = {'cmd': 'LIST UPS', 'error': "No completed list.",  'data' : {}}
        for line in lines:
            if line[:3] == "UPS" :
                ups, desc = line[4:-1].split( '"' )
                retval['data'][ ups.replace( " ", "" ) ] = desc
            elif line == "END LIST UPS":
                retval['error'] = ''
        return retval

    def _decodeListVars(self,  lines):
        retval = {'cmd': 'LIST VAR',  'ups' : lines.pop(0).split()[3], 'error': "No completed list.",  'data': {}}
        for line in lines:
            if line[:3] == "VAR" :
                item = line.split()
                retval['data'].update({item[2] : item[3].replace('"', '')})
            elif line == "END LIST VAR %s" %retval['ups'] :
                retval['error'] = ''
        return retval

    def _decodeListRWVars(self,  lines):
        retval = {'cmd': 'LIST RW', 'ups': lines.pop(0).split()[3], 'error': "No completed list.", 'data': {}}
        for line in lines:
            if line[:2] == "RW" :
                item = line.split()
                retval['data'].update({item[2]: item[3].replace('"', '')})
            elif line == "END LIST RW %s" %retval['ups'] :
                retval['error'] = ''
        return retval

    def _decodeListCmds(self,  lines):
        retval = {'cmd': 'LIST CMD', 'ups': lines.pop(0).split()[3], 'error': "No completed list.", 'data': []}
        for line in lines:
            if line[:3] == "CMD" :
                item = line.split()
                retval['data'].append(item[2])
            elif line == "END LIST CMD %s" %retval['ups'] :
                retval['error'] = ''
        return retval

    def _decodeListEnum(self,  lines):
        h = lines.pop(0).split()
        retval = {'cmd': 'LIST ENUM', 'ups': h[3], 'var': h[4], 'error': "No completed list.", 'data': []}
        for line in lines:
            if line[:4] == "ENUM" :
                item = line.split()
                retval['data'].append(item[3].replace('"', ''))
            elif line == "END LIST ENUM %s %s" %(retval['ups'], retval['var']):
                retval['error'] = ''
        return retval

    def _decodeListRange(self,  lines):
        h = lines.pop(0).split()
        retval = {'cmd': 'LIST RANGE', 'ups': h[3], 'var': h[4], 'error': "No completed list.", 'data': []}
        for line in lines:
            if line[:4] == "RANGE" :
                item = line.split()
                retval['data'].append({'min': item[3].replace('"', ''), 'max': item[4].replace('"', '')})
            elif line == "END LIST RANGE %s %s" %(retval['ups'], retval['var']):
                retval['error'] = ''
        return retval

    def _decodeVarType(self, lines):
        h = lines.pop(0).split()
        return {'cmd': 'GET TYPE', 'ups': h[1], 'var': h[2], 'type': h[3].replace('"', ''), 'error': ""}

    def _decodeVar(self, lines):
        h = lines.pop(0).split()
        return {'cmd': 'GET VAR', 'ups': h[1], 'var': h[2], 'value': h[3].replace('"', ''), 'error': ""}

    def _sendNUTCmd(self, cmd):
#        print "+++++ Request NUT cmd :{0}".format(cmd)
        if not self.connected : self.Connect_to_NUT()
        self._lastCmd = cmd
        self._sync = True
        data = ''
        self.send(cmd + "\n")
        timeout = 10
        begin = time.time()
        while 1:
            if time.time()-begin > timeout:
                data = {'cmd': cmd, 'error': 'No response, timeout {0}s, check NUT server'.format(timeout), 'data': ''}
                break
            if self._data :
#                print 'Handle data :\n',  self._data
                data = self._data
                self._data =''
                break
            else: time.sleep(0.05)
        self._sync = False
        if type(data) is dict :
            return data
        return self.received_message(data)

    def getUPSList(self):
        return self._sendNUTCmd("LIST UPS")

    def getUPSNumLogin(self, ups):
        return self._sendNUTCmd("GET NUMLOGINS %s" %ups)

    def getUPSVars(self, ups):
        return self._sendNUTCmd('LIST VAR %s' %ups)

    def getUPSRWVars(self, ups):
        return self._sendNUTCmd('LIST RW %s' %ups)

    def getUPSCommands(self, ups):
        return self._sendNUTCmd('LIST CMD %s' %ups)

    def getUPSVarType(self, ups, var):
        return self._sendNUTCmd('GET TYPE %s %s' %(ups, var))

    def getUPSVar(self, ups, var):
        return self._sendNUTCmd('GET VAR %s %s' %(ups, var))

    def getListEnum(self, ups, var):
        return self._sendNUTCmd('LIST ENUM %s %s' %(ups, var))

    def getListRange(self, ups, var):
        return self._sendNUTCmd('LIST RANGE %s %s' %(ups, var))

    def getNUTVersion(self):
        return self._sendNUTCmd('VER')

    def getNUTHelp(self):
        cmd = 'HELP'
        if version.StrictVersion(self.upscVer) >= version.StrictVersion('2.6.3') :
            return self._sendNUTCmd(cmd)
        else : return {'cmd': cmd,
                       'error': "NUT version to old ({0}), {1} function not handle, Update NUT lib >= 2.6.3".format(self.upscVer, cmd)}

    def getNUTNetworkVersion(self):
        cmd = 'NETVER'
        if version.StrictVersion(self.upscVer) >= version.StrictVersion('2.6.4') :
            return self._sendNUTCmd(cmd)
        else : return {'cmd': cmd,
                       'error': "NUT version to old ({0}), {1} function not handle, Update NUT lib >= 2.6.4".format(self.upscVer, cmd)}

    def getUPSListClients(self, ups):
        cmd = 'LIST CLIENT'
        if version.StrictVersion(self.upscVer) >=version. StrictVersion('2.6.4') :
            return self._sendNUTCmd(cmd)#' %s' %ups)
        else : return {'cmd': cmd,
                       'error': "NUT version to old ({0}), {1} function not handle, Update NUT lib >= 2.6.4".format(self.upscVer, cmd)}

    def sendInstCmd(self, ups, cmd, extra=None):
        cmd = 'INSTCMD %s %s' %(ups,  cmd)
        if extra: cmd = cmd + " {0}".format(extra)
        print "***** Send : {0}".format(cmd)
        return self._sendNUTCmd(cmd)

    def login(self, user, pwd):
        cmd = 'USERNAME %s' %(user)
        retVal = self._sendNUTCmd(cmd)
        if retVal['error'] == '' and retVal['cmd'] =='OK':
            cmd = 'PASSWORD %s' %(pwd)
            retVal = self._sendNUTCmd(cmd)
            if retVal['error'] == '' and retVal['cmd'] =='OK':
                return {'cmd': 'login',  'error': '',  'data': 'login success'}
        return retVal

    def logout(self):
        retVal = self._sendNUTCmd('LOGOUT')
        if retVal['error'] == '' and retVal['cmd'] =='OK':
            return {'cmd': 'logout',  'error': '',  'data': 'Goodbye'}
        return retVal

if __name__ == "__main__":
    # Set  upsaddr,  upsport and upsname depending on your config
    upsaddr = '192.168.0.192'
    upsport = 3493
    upsname = 'Z3_SERVER'
    url = upsaddr + ":" + str(upsport)
    client = NUTSocketClient(upsaddr, upsport)
    print "Client connected to {0}".format(upsname)
    try:
            print "\n*** getNUTVersion"
            print client.getNUTVersion()
            print "\n*** getNUTNetworkVersion "
            print client.getNUTNetworkVersion()
            print "\n*** getNUTHelp"
            print client.getNUTHelp()
            print "\n*** getUPSList"
            print client.getUPSList()
            print "\n*** getUPSVars"
            print client.getUPSVars(upsname)
            print "\n*** getUPSRWVars"
            print client.getUPSRWVars(upsname)
            print "\n*** getUPSCommands"
            print client.getUPSCommands(upsname)
            print "\n*** getUPSListClients"
            print client.getUPSListClients(upsname)
            print "\n*** getUPSVar"
            print client.getUPSVar(upsname, 'ups.status')
            print "\n*** getUPSNumLogin"
            print client.getUPSNumLogin(upsname)

    finally:  # when you CTRL+C exit, we clean up
        client.close()
        print "Terminated"
