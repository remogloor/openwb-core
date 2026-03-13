#!/usr/bin/env python3
import logging
from subprocess import PIPE, CalledProcessError, run
from typing import List
from pathlib import Path

from modules.backup_clouds.nfs.config import NfsBackupCloud, NfsBackupCloudConfiguration
from modules.common.abstract_device import DeviceDescriptor

log = logging.getLogger(__name__)
nfs_mount = '/mnt/nfs_mount'


# run command as subprocess with timeout, some exception handling and logging
def _run(cmd: List[str], timeout: float) -> bool:
    cmd_str = ' '.join(cmd)
    log.info('backup-nfs: cmd ' + cmd_str + ': starting')
    try:
        p = run(cmd, timeout=timeout, stdout=PIPE, stderr=PIPE)
        p.check_returncode()
    except CalledProcessError as e:
        log.exception('backup-nfs: cmd ' + cmd_str + ', Fail: error code: '
                      + str(e.returncode) + ', stderr: ' + p.stderr.decode('utf-8'))
        raise e
    if p.stdout.decode('utf-8') is not None and p.stdout.decode('utf-8') != '':
        log.info('backup-nfs: cmd ' + cmd_str + ': Success, stdout: [' + p.stdout.decode('utf-8') + ']')
    else:
        log.info('backup-nfs: cmd ' + cmd_str + ': Success')
    return True


def _is_nfs_mounted(nfs_share: str) -> bool:
    """Check if the given NFS share is already mounted by reading /proc/mounts."""
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                if nfs_share in line:
                    return True
    except OSError:
        log.warning('backup-nfs: could not read /proc/mounts')
    return False


def upload_backup(config: NfsBackupCloudConfiguration, backup_filename: str, backup_file: bytes) -> None:
    nfs_share = config.nfs_share

    # create nfs mount folder if not existent
    p = Path(nfs_mount)
    if p.is_dir():
        log.warning('nfs mount folder ' + nfs_mount + ' exists - reuse it')
        rc = True
    else:
        rc = _run(['sudo', 'mkdir', nfs_mount], 5)

    # check if nfs is mounted already
    if rc:
        if _is_nfs_mounted(nfs_share):
            log.warning('nfs share seems to be mounted - reuse it')
        else:
            rc = _run(['sudo', 'mount', '-t', 'nfs', nfs_share, nfs_mount], 10)

    # copy backup file to nfs share
    if rc:
        rc = _run(['sudo', 'cp', '/var/www/html/openWB/data/backup/' + backup_filename,
                   nfs_mount + '/' + backup_filename], 5)

    # umount nfs share
    if rc:
        rc = _run(['sudo', 'umount', nfs_mount], 5)

    # remove mount point
    if rc:
        rc = _run(['sudo', 'rmdir', nfs_mount], 5)


def create_backup_cloud(config: NfsBackupCloud):
    def updater(backup_filename: str, backup_file: bytes):
        upload_backup(config.configuration, backup_filename, backup_file)
    return updater


device_descriptor = DeviceDescriptor(configuration_factory=NfsBackupCloud)
