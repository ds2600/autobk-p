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
sSqlGetLatestHash = "SELECT backupHash FROM Backup WHERE kDevice=%s ORDER BY tComplete DESC LIMIT 1"
sSqlGetLatestVers = "SELECT MAX(versionNumber) AS VersionNumber FROM BackupVersion WHERE kDevice=%s"
sSqlSetDone		= "UPDATE Schedule SET sState='Complete', sComment=%s WHERE kSelf=%s"
sSqlSetFail		= "UPDATE Schedule SET sState='Fail', iAttempt=%s, sComment=%s WHERE kSelf=%s"
sSqlSetRetry	= "UPDATE Schedule SET tTime=%s, iAttempt=%s WHERE kSelf=%s"
sSqlAddBackup	= "INSERT INTO Backup SET kDevice=%s, tComplete=%s, tExpires=%s, sFile=%s, sComment=%s, backupHash=%s"
sSqlAddVersion = "INSERT INTO BackupVersion SET kBackup=%s, kDevice=%s, versionNumber=%s, sComment=%s"


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
				bDuplicateHash = False
				sDatabaseComment = ''
				# Get hash of previous backup file
				oDeviceCursor = oCnx.cursor(named_tuple=True, buffered=True)
				oDeviceCursor.execute(sSqlGetLatestHash, (oDevice.kSelf,))

				# Calculate hashes of new backup and compare to previous
				sNewHash = FileHash(sBkPath)
				if (oDeviceCursor.rowcount > 0):
					# Compare hash to previous backup
					oRow = oDeviceCursor.fetchone()
					if (oRow.backupHash == sNewHash):
						# Duplicate
						sDatabaseComment = 'Duplicate'
						oLog.info(sAt, 'backup', 'duplicate')
						mOS.remove(sBkPath)
						bDuplicateHash = True
					else:
						bDuplicateHash = False
				if (bDuplicateHash == False):
					# Complete, schedule next backup if this one was automatic
					if (oDevice.sState == 'Auto'):
						# Auto
						tExpires = tNow + timedelta(days=iIniExpireDays * (1 if oDevice.iAutoWeeks == 0 else oDevice.iAutoWeeks))
						oCursor.execute(sSqlAddBackup, (oDevice.kSelf, tNow, tExpires, sBkPath, sDatabaseComment, sNewHash))
						oLog.info(sAt, 'expires', tExpires)
					else:
						# Manual
						oCursor.execute(sSqlAddBackup, (oDevice.kSelf, tNow, None, sBkPath, None, sNewHash))
					oLog.info(sAt, 'new-hash', sNewHash)
					# New Version
					oDeviceCursor.execute(sSqlGetLatestVers, (oDevice.kSelf,))
					oRow = oDeviceCursor.fetchone()
					if oRow is not None and oRow.VersionNumber is not None:
						iVersion = oRow.VersionNumber + 1
					else:
						iVersion = 1  
					# Add Version
					oLog.info(sAt, 'new-version', iVersion)
					oDeviceCursor.execute(sSqlAddVersion, (oCursor.lastrowid, oDevice.kSelf, iVersion, 'New Version'))
					oDeviceCursor.close()
					sDatabaseComment = 'v{}'.format(iVersion)
					oLog.info(sAt, 'backup', 'new backup')
				# Update Schedule with complete
				oCursor.execute(sSqlSetDone, (sDatabaseComment, oDevice.kSchedule,))
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
