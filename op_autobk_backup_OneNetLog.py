#!/usr/local/bin/python3.8
import sys as mSys
import base64 as mB64
import re as mRE
from http.client import HTTPConnection
from bs4 import BeautifulSoup
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkUrlEAS	= '/dasdec_originated_events/{}'
sEasUrl		= '/dasdec/dasdec.csp'
sEasLogin	= 'login_user={}&login_password={}'
sEasCreate	= """\
cachenum={}&csp_page_L0=Decoder&csp_page_L1=OrigFwrded&csp_page_L2=&csp_page_L3=&csp_ScrollPos=82&csp_reset_session_time=on&\
csp_selected_button=AlertRange&csp_selected_button_option=2days&csp_selected_button_label=Past+2+Days+Alerts&csp_selected_button_instance=&\
csp_Logout=&csp_uploaded_fname=&csp_editing_state=&csp_changed_state=&csp_changed_state_OK_button=&event_offset=&Pinned_Header_CheckState=&\
DecoderSubmenu=OrigFwrded&Alert_Table_Select=Expired&AlertRange=120days&ExpScrollFIPSList_CheckState=&ExpScrollFIPSList=1"""
dnGetHdrsEAS = {
	'User-Agent':	'CtrlAutoBk/2.00',
	'Content-Type':	'application/x-www-form-urlencoded',
	'Accept':		'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Cookie':		'session_id=',
}

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-OneNetLog')
	sIniUsr = oINI.get('OneNetLog', 'Usr', fallback='AutoBk')
	sIniPwd = oINI.get('OneNetLog', 'Pwd', fallback='ODt5F53A')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	dnGetHdrsEAS['Authorization'] = 'Basic ' + mB64.b64encode(sAuthKey.format(sIniUsr, sIniPwd).encode()).decode()

	# HTTP Connect to OneNet
	oHttp = HTTPConnection(sDeviceIP, 80)

	# Logon to OneNet to get session ID
	oR = HttpRequest(oHttp, sEasUrl, dnGetHdrsEAS, bPost=True, bData=False, sMsg=sEasLogin.format(sIniUsr, sIniPwd))
	lsCookie = oR.getheader('Set-Cookie').split(',')
	sEasSID = lsCookie[1][12:] if (len(lsCookie) >= 2) else None
	if (sEasSID is None): raise AutoBkError('Authentication Failed!')
	oLog.info(sAt, 'session', sEasSID)

	# Find cachenum (required by EAS v4+)
	oSoup = BeautifulSoup(oR.read(), 'html.parser').find('input', { 'name':'cachenum' })
	sCacheNum = oSoup.get('value') if (oSoup is not None) else ''
	oLog.info(sAt, 'cachenum', sCacheNum)

	# Update session cookies for next call
	dnGetHdrsEAS['Cookie'] = 'session_id={}; csp_user={}'.format(sEasSID, sIniUsr)

	# Request 120 day log file creation and get new session ID
	oR = HttpRequest(oHttp, sEasUrl, dnGetHdrsEAS, bPost=True, bData=False, sMsg=sEasCreate.format(sCacheNum))
	lsCookie = oR.getheader('Set-Cookie').split(',')
	sEasSID = lsCookie[0][12:] if (len(lsCookie) >= 1) else None
	if (sEasSID is None): raise AutoBkError('Authentication Failed!')
	oLog.info(sAt, 'session', sEasSID)

	# Update session cookies for final call
	dnGetHdrsEAS['Cookie'] = 'session_id={}; csp_user={}'.format(sEasSID, sIniUsr)

	# Search for filename in response
	sResponse = oR.read().decode('utf-8', errors='replace')
	sCreatedFile = mRE.search('(report[1-9][1-9]?\\.txt)', sResponse).group(1)
	oLog.info(sAt, 'created', sCreatedFile)

	# Request backup download
	xData = HttpRequest(oHttp, sBkUrlEAS.format(sCreatedFile), dnGetHdrsEAS)
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
