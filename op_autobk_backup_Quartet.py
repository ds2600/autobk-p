#!/usr/local/bin/python3.8
import sys as mSys
from http.client import HTTPConnection
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkUrlQtt	= '/encoder/uploadfs.php'
sQttData	= """--data\nContent-Disposition: form-data; name="download"\n--data--"""
dnGetHdrsQtt = {
	'User-Agent':	'CtrlAutoBk/2.00',
	'Content-Type':	'multipart/form-data; boundary=data',
	'Accept':	'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
}

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-Quartet')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# HTTP Connect to Quartet
	oHttp = HTTPConnection(sDeviceIP, 80)

	# Request backup URL from Quartet
	oR = HttpRequest(oHttp, sBkUrlQtt, dnGetHdrsQtt, bPost=True, bData=False, sMsg=sQttData)
	sLocation = oR.getheader('Location')
	oLog.info(sAt, 'location', sLocation)

	# Get backup file from Quartet
	xData = HttpRequest(oHttp, sLocation, dnGetHdrsQtt, bPost=False, bData=True)
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
