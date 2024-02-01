#!/usr/local/bin/python3.8
import sys as mSys
from lib_autobk import *

###############################
# Global Configurations and Constants
sAbout = """
===============================================================
APEX1000 Route Restore v2.0
===============================================================
# Used to bulk configure host route entries from a CSV file
# See documentation for CSV format and required header line
# Enter 'q' at any prompt to exit script

"""
sSnmpRequest	= 'Community String? [{}] : '

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
def YesNo(bValue):
	return 'Y' if (bValue) else 'N'

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('usr-restore-APEX')
	sIniCommunity = oINI.get('APEX', 'Community', fallback='public')

	# Options
	print(sAbout)
	sHostname = Input('Mgmt IP/Hostname? : ')
	sIniCommunity = Input(sSnmpRequest.format(sIniCommunity), False, sIniCommunity)
	sApexName = CallScript('op-verify-APEX', './op_autobk_verify_APEX.py', lsArg=[sHostname, sIniCommunity], bOutIsErr=False)
	if (sApexName is None): raise AutoBkError('APEX not found!')
	if (Input('Is {} the correct APEX? [y] or n : '.format(sApexName), True, True) == False): raise AutoBkError('User quit operation!')
	bUseIndices = Input('Use indices from file? y or [n] : ', True, False)
	if (bUseIndices): print('WARNING! Using indices may overwrite existing entries!')
	else: print('WARNING! All existing entries will be disabled first and may be re-used!')
	sBkPath = Input('Filename? : ')
	print('\n')

	if (Input('Continue? [y] or n : ', True, True) == False): raise AutoBkError('User quit operation!')
	print('\n')
	print ('Restoring...')
	sError = CallScript('op-restore-APEX', './op_autobk_restore_APEX.py', lsArg=[sHostname, sBkPath, sIniCommunity, YesNo(bUseIndices)], iTimeout=300)
	print('\n')
	print('Complete!') if (sError is None) else print('Failure! Check logs for details.')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
