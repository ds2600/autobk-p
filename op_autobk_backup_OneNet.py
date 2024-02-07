#!/usr/local/bin/python3.8
import sys as mSys
import base64 as mB64
from http.client import HTTPConnection
from bs4 import BeautifulSoup
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkUrlEAS	= '/dasdec_config_files/{}'
sEasUrl		= '/dasdec/dasdec.csp'
sEasLogin	= 'login_user={}&login_password={}'
sEasCreate	= """\
cachenum={}&csp_page_L0=Setup&csp_page_L1=Server&csp_page_L2=Configuration+Mgmt&csp_page_L3=&csp_ScrollPos=0&csp_reset_session_time=on&\
csp_selected_button=Setup_Server_MakeBackupCfg&csp_selected_button_option=&csp_selected_button_label=&csp_selected_button_instance=&\
csp_Logout=&csp_uploaded_fname=&csp_editing_state=&csp_changed_state=&csp_changed_state_OK_button=&event_offset=&Pinned_Header_CheckState=&\
SetupSubmenu=Server&Setup_Cfg_File_List=&Setup_Cfg_File_Rename_Field=&Server_Install_Cfg_File_Audio_CheckState=&Server_Install_Cfg_File_EMailTo_CheckState="""
dnGetHdrsEAS = {
	'User-Agent':	'CtrlAutoBk/2.00',
	'Content-Type':	'application/x-www-form-urlencoded',
	'Accept':		'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
	'Cookie':		'session_id=',
}

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-OneNet')
	sIniUsr = oINI.get('OneNet', 'Usr', fallback='AutoBk')
	sIniPwd = oINI.get('OneNet', 'Pwd', fallback='ODt5F53A')

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

	# Request backup creation and get new session ID
	oR = HttpRequest(oHttp, sEasUrl, dnGetHdrsEAS, bPost=True, bData=False, sMsg=sEasCreate.format(sCacheNum))
	lsCookie = oR.getheader('Set-Cookie').split(',')
	sEasSID = lsCookie[0][12:] if (len(lsCookie) >= 1) else None
	if (sEasSID is None): raise AutoBkError('Authentication Failed!')
	oLog.info(sAt, 'session', sEasSID)

	# Update session cookies for final call
	dnGetHdrsEAS['Cookie'] = 'session_id={}; csp_user={}'.format(sEasSID, sIniUsr)

	# Search for filename in response
	oSoup = BeautifulSoup(oR.read(), 'html.parser').find('input', { 'id':'Setup_Cfg_File_Rename_Field' })
	if (oSoup is None): raise AutoBkError('Backup Failed!')
	sCreatedFile = oSoup.get('value')
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
