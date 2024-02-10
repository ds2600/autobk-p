#!/usr/local/bin/python3
import sys as mSys
from datetime import timedelta, datetime, date, time, timezone
from mysql.connector import MySQLConnection
from lib_autobk import *

###############################
# SQL Formatting
sSqlGetDisabled	= """
SELECT s.kSelf
 FROM Schedule s
 LEFT JOIN Device dev ON s.kDevice=dev.kSelf AND s.sState='Auto'
 WHERE dev.iAutoDay=0"""
sSqlGetMissing	= """
SELECT dev.kSelf, dev.sName, dev.iAutoDay, dev.iAutoHour, dev.iAutoWeeks
 FROM Device dev
 LEFT JOIN Schedule s ON s.kDevice=dev.kSelf AND s.sState='Auto'
 WHERE dev.iAutoDay!=0 AND s.kSelf IS NULL"""
sSqlAddAuto		= "INSERT INTO Schedule SET kDevice=%s, sState='Auto', tTime=%s"
sSqlDelExpired	= "DELETE FROM Schedule WHERE sState IN ('Fail','Complete') AND tTime<=%s"
sSqlDelDisabled	= "DELETE FROM Schedule WHERE kSelf=%s"

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-scheduling')
	dnIniDb = { 'autocommit': True }
	dnIniDb['user']		= oINI.get('Database', 'Usr',  fallback='root')
	dnIniDb['password']	= oINI.get('Database', 'Pwd',  fallback='')
	dnIniDb['database']	= oINI.get('Database', 'DB',   fallback='AutoBk')
	dnIniDb['host']		= oINI.get('Database', 'Host', fallback='localhost')
	iIniExpireDays = oINI.getint('Backups', 'ExpireDays', fallback=30) # number of days after an auto backup when it will be purged from system
	oLog.info(sAt, 'state', 'running')

	# Connect to database
	oCnx = MySQLConnection(**dnIniDb)
	oCursor = oCnx.cursor(named_tuple=True, buffered=True)
	oLog.info(sAt, 'DB', 'ready')

	# Get current date/time for this cycle
	tNow = datetime.now(tz=timezone.utc).astimezone()

	# Purge expired Schedules (Fails and Completes)
	oCursor.execute(sSqlDelExpired, (tNow - timedelta(days=iIniExpireDays),))
	oLog.info(sAt, 'expired', oCursor.rowcount)

	# Purge disabled Schedules
	oCursor.execute(sSqlGetDisabled)
	oLog.info(sAt, 'disabled', oCursor.rowcount)
	for oSchedule in oCursor.fetchall():
		oCursor.execute(sSqlDelDisabled, (oSchedule.kSelf,))

	# Schedule missing auto-backups
	oCursor.execute(sSqlGetMissing)
	oLog.info(sAt, 'pending', oCursor.rowcount)
	for oDevice in oCursor.fetchall():
		# Calculate the next weekday for auto-backup
		tSchedule = NextWeekday(tNow, oDevice.iAutoDay, oDevice.iAutoHour, oDevice.iAutoWeeks)
		oCursor.execute(sSqlAddAuto, (oDevice.kSelf, tSchedule))
		oLog.info(sAt, 'next', sCombo.format(oDevice.sName, tSchedule))

	# Database cleanup
	oCursor.close()
	oCnx.close()

	oLog.info(sAt, 'state', 'complete')
except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
