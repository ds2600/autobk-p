#!/usr/local/bin/python3
import sys as mSys
import os as mOS
from collections import namedtuple
from easysnmp import Session as SnmpSession
from lib_autobk import *

###############################
# Global Configurations and Constants
sApexNameOID	= ".1.3.6.1.4.1.1166.1.31.1.1.1.2.0"
sApexSaveOID	= ".1.3.6.1.4.1.1166.1.31.1.1.1.1.0"
sRoutePropOID	= ".1.3.6.1.4.1.1166.1.31.10.1.3.1.{}.{}"
sRouteApplyOID	= ".1.3.6.1.4.1.1166.1.31.10.1.2.1.2.{}"
sTSRedPropOID	= ".1.3.6.1.4.1.1166.1.31.10.1.6.3.1.{}.{}"
sTSRedApplyOID	= ".1.3.6.1.4.1.1166.1.31.10.1.6.2.1.2.{}"
sErrorField		= "ERROR! - Missing required field {} in file!"

###############################
def YesNo(sValue):
	return 2 if (sValue == 'Y') else 1

def EthType(sValue):
	return 1 if (sValue == 'GbE') else 0

def CmpType(sValue):
	return 2 if (sValue == 'Stream') else 1

def TrueFalse(sValue):
	return True if (sValue == 'Y') else False

def QamIndex(sValue):
	if (sValue.isdigit()): return int(sValue)
	return (int(sValue[0]) * 8) + ord(sValue[1]) - 72

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-restore-APEX')
	sIniCommunity = oINI.get('APEX', 'Community', fallback='public')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	if (len(mSys.argv) > 3): sIniCommunity = mSys.argv[3]
	bUseIndices = TrueFalse(mSys.argv[4]) if (len(mSys.argv) > 4) else False
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Restore
	# Connect to APEX and retrieve name
	oSnmp = SnmpSession(hostname=sDeviceIP, community=sIniCommunity, version=2)
	sApex = oSnmp.get(sApexNameOID).value
	oLog.info(sAt, 'session', sApex)

	# Prepare APEX
	if (not bUseIndices):
		# Disable all routes and TS redundancies on APEX to avoid conflicts
		for iIndex in range(1, 769):
			lsRoutePropOID = [
				(sRoutePropOID.format(2,iIndex),	1,	'INTEGER'),	# Disabled
				(sRouteApplyOID.format(iIndex),		2,	'INTEGER')	# Applies config
			]
			lsTSRedPropOID = [
				(sTSRedPropOID.format(9,iIndex),	1,	'INTEGER'),	# Disabled
				(sTSRedApplyOID.format(iIndex),		2,	'INTEGER')	# Applies config
			]
			oSnmp.set_multiple(lsRoutePropOID)
			oSnmp.set_multiple(lsTSRedPropOID)

		oLog.info(sAt, 'existing-indices', 'disabled')

	# Open restore file
	fFrom = open(sBkTarget, 'r')
	dcRedSourceTS = {}

	# Get Route header fields from CSV
	lssField = fFrom.readline().replace(' ', '').strip().split(',')
	lssDefault = []

	# Swap alternate names with correct ones
	if ('Prov' in lssField):			lssField[lssField.index('Prov')] = 'Provider'
	if ('GbE' in lssField):				lssField[lssField.index('GbE')] = 'EthPort'
	if ('Port' in lssField):			lssField[lssField.index('Port')] = 'EthPort'
	if ('UDP' in lssField):				lssField[lssField.index('UDP')] = 'Udp'
	if ('PrimarySrcIP' in lssField):	lssField[lssField.index('PrimarySrcIP')] = 'SourceIp1'
	if ('BackupSrcIP' in lssField):		lssField[lssField.index('BackupSrcIP')] = 'SourceIp2'
	if ('Pgm' in lssField):				lssField[lssField.index('Pgm')] = 'InSID'

	# Validate required fields are available and set defaults
	if ('Index' not in lssField):
		if (bUseIndices):				raise AutoBkError(sErrorField.format('Index'))
	if ('Enabled' not in lssField):		lssField.append('Enabled'),lssDefault.append('Y')
	if ('Provider' not in lssField):	lssField.append('Provider'),lssDefault.append(1)
	if ('Source' not in lssField):		raise AutoBkError(sErrorField.format('Source'))
	if ('EthType' not in lssField):		lssField.append('EthType'),lssDefault.append('GbE')
	if ('EthPort' not in lssField):		lssField.append('EthPort'),lssDefault.append(1)
	if ('Multicast' not in lssField):	raise AutoBkError(sErrorField.format('Multicast'))
	if ('Udp' not in lssField):			lssField.append('Udp'),lssDefault.append(5000)
	if ('SourceIp1' not in lssField):	lssField.append('SourceIp1'),lssDefault.append('0.0.0.0')
	if ('SourceIp2' not in lssField):	lssField.append('SourceIp2'),lssDefault.append(None)
	if ('InSID' not in lssField):		raise AutoBkError(sErrorField.format('InSID'))
	if ('OutSID' not in lssField):		lssField.append('OutSID'),lssDefault.append(None)
	if ('QAM' not in lssField):			raise AutoBkError(sErrorField.format('QAM'))
	if ('PECheck' not in lssField):		lssField.append('PECheck'),lssDefault.append('N')
	if ('CopyProtect' not in lssField):	lssField.append('CopyProtect'),lssDefault.append(2)

	# Build Route structure
	ApexRoute = namedtuple('ApexRoute', lssField, defaults=lssDefault)
	oLog.info(sAt, 'route-header', 'validated')

	# Restore routes to APEX
	iRoute = 0
	iIndex = 1
	while (sLine := fFrom.readline()):
		sLine = sLine.strip()		# remove whitespace and new-lines
		if (sLine == ''): continue	# Skip empty lines
		if (sLine == '---'): break	# Next table

		oRoute = ApexRoute(*(sLine.split(',')))
		iRoute += 1
		iIndex = int(oRoute.Index) if (bUseIndices) else iRoute

		if (oRoute.Provider == '' or oRoute.Source == ''):
			oLog.info(sAt, 'routes', 'skipping index {}'.format(iIndex))
			continue

		if (oRoute.SourceIp2 and oRoute.SourceIp1 != oRoute.SourceIp2):
			dcRedSourceTS[oRoute.Multicast] = oRoute

		lsRoutePropOID = [
			(sRoutePropOID.format(2,iIndex),	YesNo(oRoute.Enabled),	'INTEGER'),	# Enabled / Disabled
			(sRoutePropOID.format(15,iIndex),	oRoute.Provider,		'INTEGER'),	# Provider ID
			(sRoutePropOID.format(14,iIndex),	oRoute.Source,			'INTEGER'),	# Source ID
			(sRoutePropOID.format(3,iIndex),	EthType(oRoute.EthType),'INTEGER'),	# GbE or FastE
			(sRoutePropOID.format(4,iIndex),	oRoute.EthPort,			'INTEGER'),	# GbE port 1-4
			(sRoutePropOID.format(6,iIndex),	oRoute.Multicast,		'IPADDR'),	# Multicast IP
			(sRoutePropOID.format(5,iIndex),	oRoute.Udp,				'INTEGER'),	# UDP port
			(sRoutePropOID.format(7,iIndex),	oRoute.SourceIp1,		'IPADDR'),	# Source IP
			(sRoutePropOID.format(8,iIndex),	oRoute.InSID,			'INTEGER'),	# Input Program (SID)
			(sRoutePropOID.format(11,iIndex),	oRoute.OutSID or
												oRoute.InSID,			'INTEGER'),	# Output Program (SID)
			(sRoutePropOID.format(10,iIndex),	QamIndex(oRoute.QAM),	'INTEGER'),	# Output QAM port 1-48
			(sRoutePropOID.format(9,iIndex),	YesNo(oRoute.PECheck),	'INTEGER'),	# PreEncryptCheck
			(sRoutePropOID.format(13,iIndex),	oRoute.CopyProtect,		'INTEGER'),	# CopyProtection
			(sRouteApplyOID.format(iIndex),	2,							'INTEGER')	# Applies config
		]
		oSnmp.set_multiple(lsRoutePropOID)

	oLog.info(sAt, 'routes', 'restored {}'.format(iRoute))

	if (sLine == '---'):
		# Get TS Redundancy header fields from CSV
		lssField = fFrom.readline().replace(' ', '').strip().split(',')
		lssDefault = []

		# Validate required fields are available and set defaults
		if ('Index' not in lssField):
			if (bUseIndices):				raise AutoBkError(sErrorField.format('Index'))
		if ('Enabled' not in lssField):		lssField.append('Enabled'),lssDefault.append('Y')
		if ('Compare' not in lssField):		lssField.append('Compare'),lssDefault.append(2)
		if ('Threshold' not in lssField):	lssField.append('Threshold'),lssDefault.append(90)
		if ('EthPortA' not in lssField):	lssField.append('EthPortA'),lssDefault.append(1)
		if ('EthPortB' not in lssField):	lssField.append('EthPortB'),lssDefault.append(None)
		if ('MulticastA' not in lssField):	raise AutoBkError(sErrorField.format('MulticastA'))
		if ('MulticastB' not in lssField):	lssField.append('MulticastB'),lssDefault.append(None)
		if ('UdpA' not in lssField):		lssField.append('UdpA'),lssDefault.append(5000)
		if ('UdpB' not in lssField):		lssField.append('UdpB'),lssDefault.append(None)
		if ('SourceIpA' not in lssField):	lssField.append('SourceIp1'),lssDefault.append('0.0.0.0')
		if ('SourceIpB' not in lssField):	lssField.append('SourceIpB'),lssDefault.append(None)
		if ('AlarmLowA' not in lssField):	lssField.append('AlarmLowA'),lssDefault.append(0)
		if ('AlarmLowB' not in lssField):	lssField.append('AlarmLowB'),lssDefault.append(None)

		# Build TS Redundancy structure
		ApexTSRed = namedtuple('ApexTSRed', lssField, defaults=lssDefault)
		oLog.info(sAt, 'ts-redundancy-header', 'validated')

		# Restore TS redundancies to APEX
		iTSRed = 0
		while (sLine := fFrom.readline()):
			sLine = sLine.strip()		# remove whitespace and new-lines
			if (sLine == ''): continue	# Skip empty lines
			if (sLine == '---'): break	# Next table

			oTSRed = ApexTSRed(*(sLine.split(',')))
			iTSRed += 1
			iIndex = int(oTSRed.Index) if (bUseIndices) else iTSRed
			lsTSRedPropOID = [
				(sTSRedPropOID.format(9,iIndex),	YesNo(oTSRed.Enabled),	'INTEGER'),	# Enabled
				(sTSRedPropOID.format(8,iIndex),	CmpType(oTSRed.Compare),'INTEGER'),	# Compare type
				(sTSRedPropOID.format(10,iIndex),	oTSRed.Threshold,		'INTEGER'),	# Threshold for failover
				(sTSRedPropOID.format(2,iIndex),	oTSRed.EthPortA,		'INTEGER'),	# GbE port
				(sTSRedPropOID.format(12,iIndex),	oTSRed.EthPortB or
													oTSRed.EthPortA,		'INTEGER'),
				(sTSRedPropOID.format(4,iIndex),	oTSRed.MulticastA,		'IPADDR'),	# Multicast IP
				(sTSRedPropOID.format(14,iIndex),	oTSRed.MulticastB or
													oTSRed.MulticastA,		'IPADDR'),
				(sTSRedPropOID.format(3,iIndex),	oTSRed.UdpA,			'INTEGER'),	# UDP port
				(sTSRedPropOID.format(13,iIndex),	oTSRed.UdpB or
													oTSRed.UdpA,			'INTEGER'),
				(sTSRedPropOID.format(5,iIndex),	oTSRed.SourceIpA,		'IPADDR'),	# Source IP
				(sTSRedPropOID.format(15,iIndex),	oTSRed.SourceIpB or
													oTSRed.SourceIpA,		'IPADDR'),
				(sTSRedPropOID.format(6,iIndex),	oTSRed.AlarmLowA,		'INTEGER'),	# Alarm Low bps
				(sTSRedPropOID.format(16,iIndex),	oTSRed.AlarmLowB or
													oTSRed.AlarmLowA,		'INTEGER'),
				(sTSRedPropOID.format(11,iIndex),	1,						'INTEGER'),	# State
				(sTSRedApplyOID.format(iIndex),		2,						'INTEGER')	# Applies config
			]
			oSnmp.set_multiple(lsTSRedPropOID)

		oLog.info(sAt, 'ts-redundancy', 'restored {}'.format(iTSRed))

	elif (dcRedSourceTS):
		# Auto TS Redundancies
		iIndex = 0
		for oRoute in dcRedSourceTS.values():
			iIndex += 1
			lsTSRedPropOID = [
				(sTSRedPropOID.format(9,iIndex),	2,	'INTEGER'),	# Enabled
				(sTSRedPropOID.format(8,iIndex),	2,	'INTEGER'),	# Compare type (2 = Stream, 1 = Data)
				(sTSRedPropOID.format(10,iIndex),	90,	'INTEGER'),	# Threshold for failover (0-100)
				(sTSRedPropOID.format(2,iIndex),	oRoute.EthPort,		'INTEGER'),	# GbE port 1-4
				(sTSRedPropOID.format(12,iIndex),	oRoute.EthPort,		'INTEGER'),
				(sTSRedPropOID.format(4,iIndex),	oRoute.Multicast,	'IPADDR'),	# Multicast IP
				(sTSRedPropOID.format(14,iIndex),	oRoute.Multicast,	'IPADDR'),
				(sTSRedPropOID.format(3,iIndex),	oRoute.Udp,			'INTEGER'),	# UDP port
				(sTSRedPropOID.format(13,iIndex),	oRoute.Udp,			'INTEGER'),
				(sTSRedPropOID.format(5,iIndex),	oRoute.SourceIp1,	'IPADDR'),	# Source IP1
				(sTSRedPropOID.format(15,iIndex),	oRoute.SourceIp2,	'IPADDR'),	# Source IP2
				(sTSRedPropOID.format(6,iIndex),	0,	'INTEGER'),	# Alarm Low bps (0 disables)
				(sTSRedPropOID.format(16,iIndex),	0,	'INTEGER'),
				(sTSRedPropOID.format(11,iIndex),	1,	'INTEGER'),	# State (1 = active, 2 = suspended)
				(sTSRedApplyOID.format(iIndex),		2,	'INTEGER')	# Applies config
			]
			oSnmp.set_multiple(lsTSRedPropOID)

		oLog.info(sAt, 'ts-redundancy-auto', 'restored {}'.format(iIndex))

	# Commit changes to APEX and save
	fFrom.close()
	oSnmp.set(sApexSaveOID, 2, snmp_type='INTEGER')
	oLog.info(sAt, 'session', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
