#!/usr/local/bin/python3
import sys as mSys
import base64 as mB64
from http.client import HTTPConnection
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkUrlInca = '/sys/svc/core/api/v1/devices/1/configuration.bak'
sBkUrlIncaOld = '/devices/1/configuration.bak' # 1.62 and older

dnGetHdrsInca = {
	'User-Agent':	'CtrlAutoBk/2.00',
	'Content-Type':	'application/x-www-form-urlencoded',
	'Accept':		'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-Inca1')
	sIniUsr = oINI.get('Inca1', 'Usr', fallback='admin')
	sIniPwd = oINI.get('Inca1', 'Pwd', fallback='admin')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	dnGetHdrsInca['Authorization'] = 'Basic ' + mB64.b64encode(sAuthKey.format(sIniUsr, sIniPwd).encode()).decode()

	# HTTP Connect to Inca
	oHttp = HTTPConnection(sDeviceIP, 80)
	oLog.info(sAt, 'session', 'connected')

	# Request config update and download
	xData = HttpRequest(oHttp, sBkUrlInca, dnGetHdrsInca, sFallbackURL=sBkUrlIncaOld)
	oFile = open(sBkTarget, 'wb')
	oFile.write(xData)
	oFile.close()

	# Cleanup, logoff, and disconnect HTTP session
	oHttp.close()

	oLog.info(sAt, 'session', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
