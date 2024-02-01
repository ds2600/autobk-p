#!/usr/local/bin/python3.8
import sys as mSys
import json
from datetime import datetime
from http.client import HTTPConnection
from bs4 import BeautifulSoup
from lib_autobk import *

###############################
# Global Configurations and Constants
sSonifexUrl = ''
dnGetHdrs = {
	'User-Agent':	'CtrlAutoBk/2.00',
	'Content-Type':	'application/x-www-form-urlencoded',
	'Accept':		'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

###############################
# Helper Functions

dnSonifexBk = {}
oSoup = None

def AppendSelected(sKey, sId):
	global dnSonifexBk, oSoup
	dnSonifexBk[sKey] = [ oSoup.find('select', { 'name':sId }).find_next('option', { 'selected':True }).string ]

def AppendValue(sKey, sId):
	global dnSonifexBk, oSoup
	dnSonifexBk[sKey] = [ oSoup.find('input', { 'name':sId }).get('value') ]

def AppendCheck(sKey, sId):
	global dnSonifexBk, oSoup
	dnSonifexBk[sKey] = [ oSoup.find('input', { 'name':sId,'checked':True }).next_sibling.strip() ]

def AppendIP(sKey, sId0, sId1, sId2, sId3):
	global dnSonifexBk, oSoup
	dnSonifexBk[sKey] = [ '.'.join((
		oSoup.find('input', { 'name':sId0 }).get('value'),
		oSoup.find('input', { 'name':sId1 }).get('value'),
		oSoup.find('input', { 'name':sId2 }).get('value'),
		oSoup.find('input', { 'name':sId3 }).get('value'))) ]

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-PSSend')
	
	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# HTTP Connect to Sonifex
	oHttp = HTTPConnection(sDeviceIP, 80)
	oLog.info(sAt, 'session', 'started')
	oR = HttpRequest(oHttp, sSonifexUrl, dnGetHdrs, bPost=False, bData=False)

	# Parse the HTML response from Sonifex and assign it's values to the dict
	dnSonifexBk = {}
	oSoup = BeautifulSoup(oR.read(), 'html.parser')

	dnSonifexBk['host'] = [ sDeviceIP ]
	dnSonifexBk['generated'] = [ datetime.now().strftime("%d/%m/%Y %H:%M:%S") ]
	AppendSelected('basic_input_source', 'B501')
	AppendSelected('basic_encoding', 'B486')
	AppendSelected('basic_channel', 'B494b7')
	AppendSelected('basic_bitrate_mode', 'B504')
	AppendSelected('basic_bitrate', 'B505')
	AppendSelected('basic_str_mode', 'B352')
	AppendSelected('basic_connection', 'B923')
	AppendSelected('basic_connection_type', 'B527')
	AppendValue('basic_dest_ip_address', 'S944')
	AppendValue('basic_dest_port_no', 'W511')
	AppendIP('adv_net_ip_address', 'B0', 'B1', 'B2', 'B3')
	AppendIP('adv_net_netmask', 'N8B0', 'N8B1', 'N8B2', 'N8B3')
	AppendIP('adv_net_gateway', 'B4', 'B5', 'B6', 'B7')
	AppendIP('adv_net_dns1', 'B64', 'B65', 'B66', 'B67')
	AppendIP('adv_net_dns2', 'B68', 'B69', 'B70', 'B71')
	AppendValue('adv_net_dhcp_hn', 'S98')
	AppendCheck('adv_net_sonicip', 'B277b7')
	AppendSelected('adv_aud_amp_gain', 'B249')
	AppendSelected('adv_aud_emphasis', 'B255b4-5')
	AppendCheck('adv_aud_frame_crc', 'B255b0')
	AppendCheck('adv_aud_bitreservoir', 'B255b2')
	AppendCheck('adv_aud_channel_mode_ext', 'B255b1')
	AppendCheck('adv_aud_copyright_prot', 'B255b7')
	AppendCheck('adv_aud_stream_type', 'B255b6')
	AppendValue('adv_str_own_name', 'S256')
	AppendSelected('adv_str_control_gpi', 'B240')
	AppendSelected('adv_str_active_oc', 'B241')
	AppendSelected('adv_str_send_cc_info', 'B286')
	AppendValue('adv_str_trigger_lvl', 'W492')
	AppendValue('adv_str_pre_trigger', 'W488')
	AppendValue('adv_str_post_trigger', 'W490')
	AppendSelected('adv_str_buffer_underrun', 'B281')
	AppendSelected('adv_str_stream_packet', 'B282')
	AppendValue('adv_str_radio_path', 'S566')
	AppendValue('adv_str_icy_url', 'S291')
	AppendValue('adv_str_icy_genre', 'S535')
	AppendSelected('adv_str_shoutcast', 'B285')
	AppendValue('adv_str_type_service', 'B59b2-7')
	AppendIP('adv_str_snmp_trap', 'B924', 'B925', 'B926', 'B927')
	AppendValue('adv_str_low_lvl_l', 'W928')
	AppendValue('adv_str_low_lvl_r', 'W930')
	AppendValue('adv_str_hi_lvl_l', 'W932')
	AppendValue('adv_str_hi_lvl_r', 'W934')
	AppendValue('adv_str_trap_rep', 'W936')
	AppendValue('adv_str_silence_to', 'W940')

	#####################################	
	
	# Dump dictionary as JSON backup to target file
	oFile = open(sBkTarget, 'w')
	oFile.write(json.dumps(dnSonifexBk, indent=4, sort_keys=False))
	oFile.close()

	# Cleanup, logoff, and disconnect HTTP session
	oHttp.close()

	oLog.info(sAt, 'session', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
