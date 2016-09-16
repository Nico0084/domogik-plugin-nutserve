domogik-plugin-nutserve
=========================

A Domogik (www.domogik.org) plugin monitor UPS (Uninterruptible Power Supplies) through communicat with [NUT project server](http://www.networkupstools.org/).
Create a socket connection with NUT to get UPS informations and report them to domogik sensors.

You must configure as your needs the  NUT library and give parameters connection at plugin..
UPS Status, on mains (line), on battery, connected, lost connection,.... are send to domogik device.

Sensors values for input, output, battery voltage and battery charge are also send to domogik device.
