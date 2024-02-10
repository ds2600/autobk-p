#!/usr/local/bin/python3
import sys as mSys
from datetime import datetime, time
from lib_autobk import *

###############################

try:
	dtNow = datetime.now()
	sDateTime = dtNow.strftime("%d/%m/%Y %H:%M:%S")

	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-FakeDevice')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	oLog.info(sAt, 'session', 'connected')

	# Request config update and download

	oFile = open(sBkTarget, 'w')
	oFile.write(sDateTime)
	oFile.close()

	# Cleanup, logoff, and disconnect HTTP session
	oLog.info(sAt, 'session', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)

