#!/usr/local/bin/python3
import sys as mSys
import xml.etree.ElementTree as mXml
from datetime import timedelta, datetime, date, time, timezone
from http.client import HTTPConnection
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkSrcCAP	= '/usr/cp/DeviceConfig/AutoBk.zip'
sBkZipCAP	= 'AutoBk.zip'
sCapTimeFmt = '%a %b %d %H:%M:%S %Z %Y'
sCapRpcLogon = """\
<?xml version="1.0" encoding="UTF-8"?>
<request id="G1000" origin="gui" destination="device" command="add" category="login" time="{}" protocol-version="4.0" platform-name="CAP-1000" type="push">
	<user name="{}" password="{}" authentication="embedded" />
</request>
"""
sCapRpcBackup = """\
<?xml version="1.0" encoding="UTF-8"?>
<request id="G1001" origin="gui" destination="device" command="update" category="config" time="{0}" protocol-version="4.0" platform-name="CAP-1000" sid="{1}">
	<path>
		<manager id="{2}" />
		<farmer id="{2}" />
	</path>
	<farmer id="{2}" restore-config="false" targetZipFile="{3}" />
</request>
"""
sCapRpcErase = """\
<?xml version="1.0" encoding="UTF-8"?>
<request id="G1002" origin="gui" destination="device" command="remove" category="file" time="{0}" protocol-version="4.0" platform-name="CAP-1000" sid="{1}">
	<path>
		<manager id="{2}" />
		<farmer id="{2}" />
	</path>
	<file dir="/usr/cp/DeviceConfig" file-name="{3}" />
</request>
"""
sCapRpcLogoff = """\
<?xml version="1.0" encoding="UTF-8"?>
<request id="G1003" origin="gui" destination="device" command="remove" category="login" time="{}" protocol-version="4.0" platform-name="CAP-1000" sid="{}" />
"""
dnRpcHdrsCAP = {
	'Content-Type':	'text/xml',
	'Cache-Control':'no-cache',
	'Pragma':		'no-cache',
	'User-Agent':   'CtrlAutoBk/2.00',
	'Accept':  		'text/html, image/gif, image/jpeg, *; q=.2, */*; q=.2',
	'Connection':	'keep-alive',
}
dnXfrHdrsCAP = {
	'filetransfer-command':	'get',
	'Content-Type':	'multipart-formdata',
	'User-Agent':   'CtrlAutoBk/2.00',
	'Accept':  		'text/html, image/gif, image/jpeg, *; q=.2, */*; q=.2',
	'Connection':	'keep-alive',
}

###############################
# Sends an XML/RPC request message to a CAP-1000, checks for errors and returns the response XML
def CapHttpRpc(oHttpCnx, sXml):
	# Send HTTP RPC request message and parse the result as XML
	xData = HttpRequest(oHttpCnx, '/xmlrq', dnRpcHdrsCAP, bPost=True, sMsg=sXml)
	oXresponse = mXml.fromstring(xData)
	oXreason = oXresponse.find('reason')

	if (oXreason is not None and oXreason.attrib.get('err-code') != 'OK'):
		raise AutoBkError('Reason: {}'.format(oXreason.text))

	return oXresponse

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-CAP')
	sIniUsr = oINI.get('CAP', 'Usr', fallback='Admin')
	sIniPwd = oINI.get('CAP', 'Pwd', fallback='')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	tNow = datetime.now(tz=timezone.utc).astimezone()
	sNowCap = tNow.strftime(sCapTimeFmt)	# HTTP formated time for CAP RPC calls

	# HTTP Connect to CAP-1000
	oHttp = HTTPConnection(sDeviceIP, 8080)

	# Logon to CAP to get session ID and local manager name
	oXresponse = CapHttpRpc(oHttp, sCapRpcLogon.format(sNowCap, sIniUsr, sIniPwd))
	oXsession = oXresponse.find('session')
	sCapSID = oXsession.attrib.get('sid')
	sCapManager = oXsession.attrib.get('manager-id')
	oLog.info(sAt, 'session', sCombo.format(sCapManager, sCapSID))

	# Request config update
	CapHttpRpc(oHttp, sCapRpcBackup.format(sNowCap, sCapSID, sCapManager, sBkZipCAP))
	oLog.info(sAt, 'update', 'complete')

	# Request config download
	dnXfrHdrsCAP['filetransfer-name'] = sBkSrcCAP
	dnXfrHdrsCAP['filetransfer-sid'] = sCapSID
	xData = HttpRequest(oHttp, '/filetransfer', dnXfrHdrsCAP, bPost=True)
	oFile = open(sBkTarget, 'wb')
	oFile.write(xData)
	oFile.close()
	oLog.info(sAt, 'transfer', 'complete')

	# Cleanup, logoff, and disconnect HTTP session
	CapHttpRpc(oHttp, sCapRpcErase.format(sNowCap, sCapSID, sCapManager, sBkZipCAP))
	CapHttpRpc(oHttp, sCapRpcLogoff.format(sNowCap, sCapSID))
	oHttp.close()

	oLog.info(sAt, 'session', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
