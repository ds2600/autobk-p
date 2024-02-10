#!/usr/local/bin/python3
import sys as mSys
import base64 as mB64
from http.client import HTTPConnection
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkUrlVista	= '/cgi/config_import_export.cgi?download=1&action=Download+Configuration+File'
dnGetHdrsVista = {
	'User-Agent':		'CtrlAutoBk/2.00',
	'Accept':			'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Language':	'en-us,en;q=0.5',
	'Accept-Encoding':	'gzip, deflate',
	'DNT':				1,
	'Connection':		'keep-alive',
	'Upgrade-Insecure-Requests': 1,
}

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-Vista')
	sIniUsr = oINI.get('Vista', 'Usr', fallback='root')
	sIniPwd = oINI.get('Vista', 'Pwd', fallback='Vista')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	dnGetHdrsVista['Authorization'] = 'Basic ' + mB64.b64encode(sAuthKey.format(sIniUsr, sIniPwd).encode()).decode()

	# HTTP Connect to CableVista
	oHttp = HTTPConnection(sDeviceIP, 80)
	oLog.info(sAt, 'session', 'connected')

	# Request config update and download
	xData = HttpRequest(oHttp, sBkUrlVista, dnGetHdrsVista)
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
