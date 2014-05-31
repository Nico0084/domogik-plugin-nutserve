domogik-plugin-nutserve
=========================

A Domogik (www.domogik.org) plugin monitor UPS (Uninterruptible Power Supplies) through communicat with`NUT project server <http://code.google.com/>`_.
Create a socket connection with NUT to get UPS informations and format them to xPL format according to `xPL_project <http://xplproject.org.uk/wiki/index.php?title=Schema_-_UPS.BASIC>`_ specifications.

You must configure as your needs the  NUT library and give parameters connection at plugin..
UPS Status, on mains (line), on battery, connected, lost connection,.... are send to domogik device.

Sensors values for input, output, battery voltage and battery charge are also send to domogik device.
