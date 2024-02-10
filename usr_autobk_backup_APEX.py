#!/usr/local/bin/python3
import sys as mSys
from datetime import datetime, timezone #, timedelta, date, time
from lib_autobk import *

###############################
# Global Configurations and Constants
sAbout = """
===============================================================
APEX1000 Route Backup v2.0
===============================================================
# Used to backup host route entries to a CSV file
# Enter 'q' at any prompt to exit script

"""
sSnmpRequest	= 'Community String? [{}] : '
sFileRequest	= 'Filename? [{}] : '
sTimeFmt		= '%Y-%m-%d_%H-%M'
sDefaultDir		= '/backups/apex/'
sDefaultFile	= "{}{}_{}.csv"

###############################
def Input(sPrompt, bBool=False, vDefault=None):
	sIn = input(sPrompt)
	if (sIn == 'q'):
		raise AutoBkError('User quit operation!')
	if (sIn == ''):
		if (vDefault is None):
			raise AutoBkError('Operation failed due to missing required input!')
		return vDefault
	if (bBool == True):
		return (sIn == 'y')
	return sIn

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('usr-backup-APEX')
	sIniCommunity = oINI.get('APEX', 'Community', fallback='public')

	# Prepare time for default filename
	tNow = datetime.now(tz=timezone.utc).astimezone()
	sNow = tNow.strftime(sTimeFmt)

	# Options
	print(sAbout)
	sHostname = Input('Mgmt IP/Hostname? : ')
	sIniCommunity = Input(sSnmpRequest.format(sIniCommunity), False, sIniCommunity)
	sBkName = CallScript('op-verify-APEX', './op_autobk_verify_APEX.py', lsArg=[sHostname, sIniCommunity], bOutIsErr=False)
	if (sBkName is None): raise AutoBkError('APEX not found!')
	sBkName = Input('Backup name? [{}] : '.format(sBkName), False, sBkName)
	sSaveFile = sDefaultFile.format(sDefaultDir, sBkName, sNow)
	sBkPath = Input(sFileRequest.format(sSaveFile), False, sSaveFile)
	print('\n')

	if (Input('Continue? [y] or n : ', True, True) == False): raise AutoBkError('User quit operation!')
	print('\n')
	print ('Exporting...')
	sError = CallScript('op-backup-APEX', './op_autobk_backup_APEX.py', lsArg=[sHostname, sBkPath, sIniCommunity], iTimeout=300)
	print('\n')
	print('Complete!') if (sError is None) else print('Failure! Check logs for details.')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
