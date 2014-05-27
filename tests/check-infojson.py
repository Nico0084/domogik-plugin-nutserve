#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
json_file = "/home/admdomo/Partage-VM/domogik-plugin-nutserve/info.json"
########################################################

import json
import sys
from domogik.common.packagejson import PackageJson

data = json.load(open(json_file))
print data
print 'Domogik validation ...'
p = PackageJson(path=json_file)
p.validate()
print 'Fin validation fichier {0}'.format(json_file)
