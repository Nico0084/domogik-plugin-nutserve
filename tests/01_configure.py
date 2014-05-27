#!/usr/bin/python
#-*- coding: utf-8 -*-

from domogik.tests.common.helpers import configure

configure("plugin", "nutserve", "vmdomogik0", "host", "192.168.0.192")
configure("plugin", "nutserve", "vmdomogik0", "port", 3493)
configure("plugin", "nutserve", "vmdomogik0", "login", "admin")
configure("plugin", "nutserve", "vmdomogik0", "pwd", "onduleur")
configure("plugin", "nutserve", "vmdomogik0", "configured", True)
