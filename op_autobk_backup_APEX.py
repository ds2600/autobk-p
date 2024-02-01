#!/usr/local/bin/python3.8
import sys as mSys
import os as mOS
from easysnmp import Session as SnmpSession
from lib_autobk import *

###############################
# Global Configurations and Constants
sApexNameOID	= ".1.3.6.1.4.1.1166.1.31.1.1.1.2.0"
sRoutePropOID	= ".1.3.6.1.4.1.1166.1.31.10.1.3.1.{}.{}"
sTSRedPropOID	= ".1.3.6.1.4.1.1166.1.31.10.1.6.3.1.{}.{}"
sRouteHeaderCSV	= 'Index,Enabled,Provider,Source,EthType,EthPort,Multicast,Udp,SourceIp1,InSID,OutSID,QAM,PECheck,CopyProtect\n'
sTSRedHeaderCSV	= 'Index,Enabled,Compare,Threshold,EthPortA,EthPortB,MulticastA,MulticastB,UdpA,UdpB,SourceIpA,SourceIpB,AlarmLowA,AlarmLowB\n'
sRouteRowCSV	= "{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n"
sTSRedRowCSV	= "{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n"

###############################
def YesNo(iValue):
	return 'Y' if (iValue == '2') else 'N'

def EthType(iValue):
	return 'GbE' if (iValue == '1') else 'FaE'

def CmpType(iValue):
	return 'Stream' if (iValue == '2') else 'Data'

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-APEX')
	sIniCommunity = oINI.get('APEX', 'Community', fallback='public')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	if (len(mSys.argv) > 3): sIniCommunity = mSys.argv[3]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	# Connect to APEX and retrieve name
	oSnmp = SnmpSession(hostname=sDeviceIP, community=sIniCommunity, version=2)
	sApex = oSnmp.get(sApexNameOID).value
	oLog.info(sAt, 'session', sApex)

	# Create new backup file
	fSave = open(sBkTarget, 'w')
	iRoutes = 0
	iTSReds = 0

	# Write Route table
	fSave.write(sRouteHeaderCSV)
	for iIndex in range(1, 769):
		# Format a list of route property OIDs for the current index to retrieve
		lsRoutePropOID = [
			sRoutePropOID.format(2,iIndex),		# Enabled / Disabled
			sRoutePropOID.format(15,iIndex),	# Provider ID
			sRoutePropOID.format(14,iIndex),	# Source ID
			sRoutePropOID.format(3,iIndex),		# GbE or FastE
			sRoutePropOID.format(4,iIndex),		# GbE port 1-4
			sRoutePropOID.format(6,iIndex),		# Multicast
			sRoutePropOID.format(5,iIndex),		# UDP port
			sRoutePropOID.format(7,iIndex),		# Source Ip
			sRoutePropOID.format(8,iIndex),		# Input Program (SID)
			sRoutePropOID.format(11,iIndex),	# Output Program (SID)
			sRoutePropOID.format(10,iIndex),	# Output QAM port 1-48
			sRoutePropOID.format(9,iIndex),		# PreEncryptCheck
			sRoutePropOID.format(13,iIndex)		# CopyProtection
		]
		lsRouteProp = oSnmp.get(lsRoutePropOID)

		# Write the returned route property values
		if (lsRouteProp[0].value == '2'):
			fSave.write(sRouteRowCSV.format(
				iIndex,							# Index
				YesNo(lsRouteProp[0].value),	# Enabled
				lsRouteProp[1].value,			# Provider
				lsRouteProp[2].value,			# Source
				EthType(lsRouteProp[3].value),	# EthType
				lsRouteProp[4].value,			# Port
				lsRouteProp[5].value,			# Multicast
				lsRouteProp[6].value,			# UDP
				lsRouteProp[7].value,			# SourceIp1
				lsRouteProp[8].value,			# InSID
				lsRouteProp[9].value,			# OutSID
				lsRouteProp[10].value,			# QAM
				YesNo(lsRouteProp[11].value),	# PreEncryptCheck
				lsRouteProp[12].value			# CopyProtection
			))

		iRoutes += 1

	oLog.info(sAt, 'routes', iRoutes)

	# Separate route table from TS redundancy table
	fSave.write('---\n')

	# Write TS Redundancy table
	fSave.write(sTSRedHeaderCSV)
	for iIndex in range(1, 769):
		# Format a list of TS redundancy property OIDs for the current index to retrieve
		lsTSRedPropOID = [
			sTSRedPropOID.format(9,iIndex),		# Enabled / Disabled
			sTSRedPropOID.format(8,iIndex),		# Compare Type (Stream or Data)
			sTSRedPropOID.format(10,iIndex),	# Threshold % (0-100)
			sTSRedPropOID.format(2,iIndex),		# GbE Port
			sTSRedPropOID.format(12,iIndex),	# GbE Port (Sec)
			sTSRedPropOID.format(4,iIndex),		# Multicast
			sTSRedPropOID.format(14,iIndex),	# Multicast (Sec)
			sTSRedPropOID.format(3,iIndex),		# UDP Port
			sTSRedPropOID.format(13,iIndex),	# UDP Port (Sec)
			sTSRedPropOID.format(5,iIndex),		# Source Ip
			sTSRedPropOID.format(15,iIndex),	# Source Ip (Sec)
			sTSRedPropOID.format(6,iIndex),		# Low bps Alarm
			sTSRedPropOID.format(16,iIndex)		# Low bps Alarm (Sec)
		]
		lsTSRedProp = oSnmp.get(lsTSRedPropOID)

		# Write the returned TS redundancy property values
		if (lsTSRedProp[0].value == '2'):
			fSave.write(sTSRedRowCSV.format(
				iIndex,							# Index
				YesNo(lsTSRedProp[0].value),	# Enabled
				CmpType(lsTSRedProp[1].value),	# Compare
				lsTSRedProp[2].value,			# Threshold
				lsTSRedProp[3].value,			# EthPortA
				lsTSRedProp[4].value,			# EthPortB
				lsTSRedProp[5].value,			# MulticastA
				lsTSRedProp[6].value,			# MulticastB
				lsTSRedProp[7].value,			# UdpA
				lsTSRedProp[8].value,			# UdpB
				lsTSRedProp[9].value,			# SourceIpA
				lsTSRedProp[10].value,			# SourceIpB
				lsTSRedProp[11].value,			# AlarmLowA
				lsTSRedProp[12].value			# AlarmLowB
			))

		iTSReds += 1

	oLog.info(sAt, 'ts-redundancy', iTSReds)

	# Close the file
	fSave.close()
	oLog.info(sAt, 'session', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
