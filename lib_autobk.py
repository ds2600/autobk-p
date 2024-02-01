#!/usr/local/bin/python3.8
import logging as mLog
from logging import Formatter, FileHandler
from logging.handlers import RotatingFileHandler
from configparser import RawConfigParser
from subprocess import Popen, PIPE
from datetime import timedelta, datetime, time

## Exceptions
class AutoBkError(Exception): pass

###############################
# Global Configurations and Constants
oLog		= mLog.getLogger() # root logger
sAt			= 'autobk:%s=%s'
sCombo		= '{} @ {}'
sAuthKey	= '{}:{}'
sSubPath	= "{}/{}"
sSqlTimeFmt	= '%Y-%m-%d %H:%M:%S'

###############################
# Loads the configuration file and logger
def LoadConfig(sMod, *, sIniFile='./autobk.ini', bRotate=False):
	global oLog, sAt
	# Parse Config File
	oINI = RawConfigParser()
	oINI.read([sIniFile])

	# Load Logging config
	sIni = 'Logging'
	sLogFile = oINI.get(sIni, 'File', fallback='./autobk.log')
	iLogSize = oINI.getint(sIni, 'MaxSize', fallback=64000)
	iLogCount = oINI.getint(sIni, 'Count', fallback=3)
	sLogLevel = oINI.get(sIni, 'Level', fallback=mLog.INFO)
	sAt = sMod + ':%s=%s'

	# Logging Components
	oF = Formatter('%(asctime)s - %(message)s', sSqlTimeFmt)
	oH = RotatingFileHandler(sLogFile, 'a', iLogSize, iLogCount) if bRotate else FileHandler(sLogFile)
	oH.setFormatter(oF)

	# Setup Loggers
	oLog.setLevel(mLog.WARNING)
	oLog.addHandler(oH)
	oLog = mLog.getLogger('AutoBk') # Switch to local logger to avoid spam from other modules
	oLog.setLevel(sLogLevel)
	oLog.addHandler(oH)
	oLog.propagate = False

	return (oINI, oLog, sAt)

###############################
# Returns the next iWeekday@iHour from tFrom
def NextWeekday(tFrom, iWeekday, iHour, iWeeks=1):
	iOffset = iWeekday - tFrom.isoweekday()
	if (iOffset > 0): iWeeks -= 1
	iOffset += iWeeks * 7
	return datetime.combine(tFrom + timedelta(days=iOffset), time(hour=iHour), tFrom.tzinfo)

###############################
# Executes a script in a new process and waits for completion
def CallScript(sName, sScript, *, lsArg=None, iTimeout=60, bOutIsErr=True):
	# Prepare arguments for process call
	lsParam = ['python3.8', sScript]
	if (lsArg is not None): lsParam += lsArg

	# Execute script
	oLog.info(sAt, sName, 'calling')
	oProc = Popen(lsParam, stdout=PIPE, text=True)
	sOut = None

	# Wait for completion
	try:
		(sOut, sErr) = oProc.communicate(timeout=iTimeout)
	except Exception as oErr:
		oLog.error(sAt, sName, 'timeout')
		oProc.kill()

	if (oProc.returncode == 0):
		oLog.info(sAt, sName, 'complete')
		return None if (bOutIsErr) else sOut
	else:
		oLog.error(sAt, sName, 'failed')
		return sOut if (bOutIsErr) else None

###############################
# Sends an HTTP request and returns the response
def HttpRequest(oHttpCnx, sURL, dnHdrs, *, bPost=False, bData=True, sMsg=None, sFallbackURL=None):
	# Send HTTP transfer request message to get a file
	oHttpCnx.request('POST' if (bPost) else 'GET', sURL, sMsg, dnHdrs)
	oResponse = oHttpCnx.getresponse()
	if (oResponse.status == 200 or oResponse.status == 302):
		return oResponse.read() if bData else oResponse
	elif (oResponse.status == 404 and sFallbackURL is not None):
		oResponse.read() # Must read all data before trying fallback
		return HttpRequest(oHttpCnx, sFallbackURL, dnHdrs, bPost=bPost, bData=bData, sMsg=sMsg)
	else:
		raise AutoBkError('Bad HTTP Response: {}'.format(oResponse.status))
