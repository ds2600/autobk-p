#!/usr/local/bin/python3.8
import sys as mSys
import signal as mSig
from datetime import timedelta, datetime, date, time, timezone
from lib_autobk import *

###############################
# Handles SIGTERM and initiates shutdown
def StopRunning(iSig=None, oFrame=None):
	global bRunning
	bRunning = False
	oLog.warning(sAt, 'state', 'stopping')

###############################
try:
	bRunning = True
	# Handles service control stopping signal
	mSig.signal(mSig.SIGTERM, StopRunning)

	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('srvc-autobk', bRotate=True)
	iIniSleepDuration	= oINI.getint('Tasks', 'SleepDuration', fallback=60)	# 1min - how long to sleep between cycles
	iIniMaintenanceHz	= oINI.getint('Tasks', 'MaintenanceHz', fallback=86400)	# 24hr - number of seconds between maintenance operations
	iIniSchedulingHz	= oINI.getint('Tasks', 'SchedulingHz',  fallback=300)	# 5min - number of seconds between scheduling operations
	iIniAutoBackupsHz	= oINI.getint('Tasks', 'AutoBackupsHz', fallback=900)	# 15min - number of seconds between auto-backup operations
	iIniCallTimeout		= oINI.getint('Tasks', 'CallTimeout',   fallback=300)	# 5min - how long to wait for the auto-backup operation to complete
	oLog.info(sAt, 'state', 'running')

	# Run Forever (continuous looping service)
	tNow = datetime.now(tz=timezone.utc).astimezone()
	tMaintenance = tScheduling = tAutoBackups = tNow

	while (bRunning):
		# Maintenance Operation
		if (tNow >= tMaintenance):
			CallScript('maintenance', './op_autobk_maintenance.py')
			tMaintenance = tNow + timedelta(seconds=iIniMaintenanceHz)

		# Scheduling Operation
		if (tNow >= tScheduling):
			CallScript('scheduling', './op_autobk_scheduling.py')
			tScheduling = tNow + timedelta(seconds=iIniSchedulingHz)

		# Automatic Backups Operation
		if (tNow >= tAutoBackups):
			CallScript('autobackups', './op_autobk_backups.py', iTimeout=iIniCallTimeout)
			tAutoBackups = tNow + timedelta(seconds=iIniAutoBackupsHz)

		# Sleep for a while but wake on SIGTERM
		if (mSig.sigtimedwait([mSig.SIGTERM], iIniSleepDuration) is not None): StopRunning()
		tNow = datetime.now(tz=timezone.utc).astimezone()

	oLog.info(sAt, 'state', 'stopped')
except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	mSys.exit(1)
