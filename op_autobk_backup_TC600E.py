#!/usr/local/bin/python3.8
import sys as mSys
import base64 as mB64
import ssl as mSSL
from ssl import SSLContext
from http.client import HTTPSConnection
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkUrlTC600E	= '/dl?view=Configuration_Config_Import-Export&widget=0&row=0&col=1'
dnGetHdrsTC600E = {
	'User-Agent':		'CtrlAutoBk/2.00',
	'Accept':			'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Accept-Encoding':	'gzip,deflate,br',
	'Accept-Language':	'en-US,en;q=0.5',
	'Connection':		'keep-alive'
}

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-TC600E')
	sIniUsr = oINI.get('TC600E', 'Usr', fallback='admin')
	sIniPwd = oINI.get('TC600E', 'Pwd', fallback='@lat1cBB')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	dnGetHdrsTC600E['Authorization'] = 'Basic ' + mB64.b64encode(sAuthKey.format(sIniUsr, sIniPwd).encode()).decode()

	# HTTP Connect to TC600E
	oHttp = HTTPSConnection(sDeviceIP, 443, context=SSLContext(mSSL.PROTOCOL_TLSv1))
	oLog.info(sAt, 'session', 'established')

	# Logon to TC600E to get session ID
	oR = HttpRequest(oHttp, sBkUrlTC600E, dnGetHdrsTC600E, bData=False)
	lsCookie = oR.getheader('Set-Cookie').split(',')
	xDrain = oR.read() # probably not needed
	sSID = lsCookie[0][:21] if (len(lsCookie) >= 1) else None
	if (sSID is None): raise AutoBkError('Authentication Failed!')
	dnGetHdrsTC600E['Cookie'] = sSID
	oLog.info(sAt, 'session', sSID)

	# Request backup XML
	xData = HttpRequest(oHttp, sBkUrlTC600E, dnGetHdrsTC600E)
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
