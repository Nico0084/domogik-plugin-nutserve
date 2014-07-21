#!/usr/bin/python
#-*- coding: utf-8 -*-

from domogik.tests.common.helpers import configure, delete_configuration
from domogik.common.utils import get_sanitized_hostname

plugin =  "nutserve"

host_id = get_sanitized_hostname()
delete_configuration("plugin", plugin, host_id)

configure("plugin", plugin,  host_id, "host", "192.168.0.192")
configure("plugin", plugin,  host_id, "port", 3493)
configure("plugin", plugin,  host_id, "login", "admin")
configure("plugin", plugin,  host_id, "pwd", "onduleur")
configure("plugin", plugin,  host_id, "configured", True)
