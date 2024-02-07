#!/usr/local/bin/python3.8
import sys as mSys
import pysftp as mSFTP
from lib_autobk import *

###############################
# Global Configurations and Constants
sBkSrcDCM	= '/tmp/archive.tar.gz'
sBkCmdDCM	= """\
cd /settings && \
/bin/tar -ch \
--exclude=24c64.bin \
--exclude=backup-eth0.ip-settings \
--exclude=backup-eth3.ip-settings \
--exclude=eth0.ip-settings \
--exclude=eth3.ip-settings \
--exclude=internal \
--exclude=kcfg.bin \
--exclude=license.txt \
--exclude=psk.txt \
--exclude=setkey.conf \
. | \
gzip -c -n > /tmp/archive.tar.gz"""

###############################
try:
	# Configuration and Logging
	(oINI, oLog, sAt) = LoadConfig('op-backup-DCM')
	sIniUsr = oINI.get('DCM', 'Usr', fallback='AutoBk')
	sIniPwd = oINI.get('DCM', 'Pwd', fallback='@ut0BkS3rv!ce')

	# Load arguments
	if (len(mSys.argv) < 3): raise AutoBkError('Missing arguments')
	sDeviceIP = mSys.argv[1]
	sBkTarget = mSys.argv[2]
	oLog.info(sAt, 'host', sDeviceIP)
	oLog.info(sAt, 'path', sBkTarget)

	# Perform Backup
	# SFTP to DCM and run backup command
	cnopts = mSFTP.CnOpts()
	cnopts.hostkeys = None
	oSftp = mSFTP.Connection(host=sDeviceIP, username=sIniUsr, password=sIniPwd, cnopts=cnopts)
	oLog.info(sAt, 'sftp', 'connected')
	oSftp.execute(sBkCmdDCM)								# backup cmd
	oSftp.get(sBkSrcDCM, sBkTarget, preserve_mtime=True)	# download
	oSftp.remove(sBkSrcDCM)									# cleanup
	oSftp.close()
	oLog.info(sAt, 'sftp', 'complete')

except Exception as oErr:
	if (oLog is not None): oLog.error(sAt, 'unknown', oErr)
	print(str(oErr)) # used by calling thread to get error message
	mSys.exit(1)
