#!/usr/local/bin/python3.8
import os as mOS
import sys as mSys
from datetime import timedelta, datetime, date, time, timezone
from mysql.connector import MySQLConnection
from lib_autobk import *

###############################
# SQL Formatting
sSqlGetExpired	= """
SELECT bk.kSelf, bk.kDevice, bk.sFile, dev.sName
 FROM Backup bk
 LEFT JOIN Device dev ON bk.kDevice=dev.kSelf
 WHERE bk.tExpires<=%s"""
sSqlDelBackup	= "DELETE FROM Backup WHERE kSelf=%s"

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-maintenance')
	dnIniDb = { 'autocommit': True }
	dnIniDb['user']		= oINI.get('Database', 'Usr',  fallback='root')
	dnIniDb['password']	= oINI.get('Database', 'Pwd',  fallback='')
	dnIniDb['database']	= oINI.get('Database', 'DB',   fallback='AutoBk')
	dnIniDb['host']		= oINI.get('Database', 'Host', fallback='localhost')
	sIniDirectory = oINI.get('Backups', 'Directory',   fallback='/backups')
	oLog.info(sAt, 'state', 'running')

	# Connect to database
	oCnx = MySQLConnection(**dnIniDb)
	oCursor = oCnx.cursor(named_tuple=True, buffered=True)
	oLog.info(sAt, 'DB', 'ready')

	# Get current date/time for this cycle
	tNow = datetime.now(tz=timezone.utc).astimezone()

	# Purge expired backups
	oCursor.execute(sSqlGetExpired, (tNow,))
	oLog.info(sAt, 'expiring', oCursor.rowcount)
	for oBk in oCursor.fetchall():
		try:
			# Calculate filepath and remove file
			sBkDir = sSubPath.format(sIniDirectory, str(oBk.kDevice).zfill(10))
			sBkPath = sSubPath.format(sBkDir, oBk.sFile)
			oLog.info(sAt, 'delete', sBkPath)
			if (mOS.path.isfile(sBkPath)): mOS.remove(sBkPath)

			# Remove DB entry
			oCursor.execute(sSqlDelBackup, (oBk.kSelf,))
			oLog.info(sAt, 'purge', 'complete')
		except Exception as oErr:
			# Error caught so we can continue with next in list (in case of permissions issues, etc...)
			oLog.error(sAt, 'purge', oErr)

	# Database cleanup
	oCursor.close()
	oCnx.close()

	oLog.info(sAt, 'state', 'complete')
except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
