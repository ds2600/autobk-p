#!/usr/local/bin/python3
import os as mOS
import sys as mSys
from datetime import timedelta, datetime, date, time, timezone
from mysql.connector import MySQLConnection
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkTimeFmt	= '%Y-%m-%d_%H-%M'
sBkTarget	= "{0}_backup_{1}.{2}"
sBkPy		= './op_autobk_backup_{}.py'
sBkMod		= 'bk-{}'

###############################
# SQL Formatting
sSqlGetReady	= """
SELECT dev.kSelf, dev.sName, dev.sIP, dev.sType, dev.iAutoWeeks, s.kSelf kSchedule, s.sState, s.iAttempt, s.sComment
 FROM Schedule s
 LEFT JOIN Device dev ON s.kDevice=dev.kSelf
 WHERE s.sState IN ('Auto','Manual') AND s.tTime<=%s"""
sSqlSetDone		= "UPDATE Schedule SET sState='Complete' WHERE kSelf=%s"
sSqlSetFail		= "UPDATE Schedule SET sState='Fail', iAttempt=%s, sComment=%s WHERE kSelf=%s"
sSqlSetRetry	= "UPDATE Schedule SET tTime=%s, iAttempt=%s WHERE kSelf=%s"
sSqlAddBackup	= "INSERT INTO Backup SET kDevice=%s, tComplete=%s, tExpires=%s, sFile=%s, sComment=%s"

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-autobackups')
	dnIniDb = { 'autocommit': True }
	dnIniDb['user']		= oINI.get('Database', 'Usr',  fallback='root')
	dnIniDb['password']	= oINI.get('Database', 'Pwd',  fallback='')
	dnIniDb['database']	= oINI.get('Database', 'DB',   fallback='AutoBk')
	dnIniDb['host']		= oINI.get('Database', 'Host', fallback='localhost')
	sIniDirectory	= oINI.get('Backups', 'Directory', fallback='/backups')
	iIniExpireDays	= oINI.getint('Backups', 'ExpireDays', fallback=30)   # number of days after an auto backup when it will be purged from system
	iIniRetryCount	= oINI.getint('Backups', 'RetryCount', fallback=4)
	iIniRetryWait	= oINI.getint('Backups', 'RetryWait',  fallback=3600) # 60min - how long to wait before making another attempt
	iIniCallTimeout	= oINI.getint('Backups', 'CallTimeout',fallback=300)  # 5min - how long to wait for an individual backup operation to complete
	dnIniExt = {} # File extensions for device types
	for (sOption, sValue) in oINI.items('Extensions'): dnIniExt[sOption] = sValue
	oLog.info(sAt, 'state', 'running')

	# Connect to database
	oCnx = MySQLConnection(**dnIniDb)
	oCursor = oCnx.cursor(named_tuple=True, buffered=True)
	oLog.info(sAt, 'DB', 'ready')

	# Get current date/time
	tNow = datetime.now(tz=timezone.utc).astimezone()
	sNowBk = tNow.strftime(sBkTimeFmt)		# Shortened SQL time version used for filenames

	# Perform backup for each scheduled device
	oCursor.execute(sSqlGetReady, (tNow,))
	oLog.info(sAt, 'pending', oCursor.rowcount)
	for oDevice in oCursor.fetchall():
		try:
			# Calculate filenames and directory paths
			sBkFile = sBkTarget.format(oDevice.sName.lower(), sNowBk, dnIniExt[oDevice.sType.lower()])
			sBkDir = sSubPath.format(sIniDirectory, str(oDevice.kSelf).zfill(10))
			sBkPath = sSubPath.format(sBkDir, sBkFile)
			oLog.info(sAt, 'processing', sCombo.format(oDevice.sName, oDevice.sIP))
			oLog.info(sAt, 'target', sBkPath)
			iAttempt = oDevice.iAttempt + 1

			# Create backup directory if it does not exist
			if (mOS.path.isdir(sBkDir) == False):
				oLog.info(sAt, 'mkdir', sBkDir)
				mOS.mkdir(sBkDir)

			# Perform Backup
			# - only required arguments are IP and path
			sError = CallScript(sBkMod.format(oDevice.sType), sBkPy.format(oDevice.sType), lsArg=[oDevice.sIP, sBkPath], iTimeout=iIniCallTimeout)

			# Update DB
			if (sError is None):
				# Complete
				if (oDevice.sState == 'Auto'):
					# Auto
					tExpires = tNow + timedelta(days=iIniExpireDays * oDevice.iAutoWeeks)
					oCursor.execute(sSqlAddBackup, (oDevice.kSelf, tNow, tExpires, sBkPath, oDevice.sComment))
					oLog.info(sAt, 'expires', tExpires)
				else:
					# Manual
					oCursor.execute(sSqlAddBackup, (oDevice.kSelf, tNow, None, sBkPath, None))

				# Update Schedule
				oCursor.execute(sSqlSetDone, (oDevice.kSchedule,))
				oLog.info(sAt, 'backup', 'complete')
			elif (iAttempt < iIniRetryCount):
				# Retry
				tRetry = tNow + timedelta(seconds=iIniRetryWait)
				oCursor.execute(sSqlSetRetry, (tRetry, iAttempt, oDevice.kSchedule))
				oLog.info(sAt, 'retry', tRetry)
			else:
				# Failure
				oCursor.execute(sSqlSetFail, (iAttempt, sError[:120], oDevice.kSchedule)) # cap error length just in case
				oLog.info(sAt, 'backup', 'failed')
		except Exception as oErr:
			# Error caught so we can continue with next in list (in case of permissions issues, missing files, etc...)
			oLog.error(sAt, 'backup', oErr)

	# Database cleanup
	oCursor.close()
	oCnx.close()

	oLog.info(sAt, 'state', 'complete')
except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
