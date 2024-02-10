#!/usr/local/bin/python3
import sys as mSys
from easysnmp import Session as SnmpSession

try:
	# Load arguments
	if (len(mSys.argv) != 3): raise Exception('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sIniCommunity = mSys.argv[2]

	# Get APEX name and output
	oSnmp = SnmpSession(hostname=sDeviceIP, community=sIniCommunity, version=2)
	print(oSnmp.get(".1.3.6.1.4.1.1166.1.31.1.1.1.2.0").value, end='')

except Exception as oErr:
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
