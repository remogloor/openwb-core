from unittest.mock import patch, mock_open, MagicMock
import pytest
from subprocess import CalledProcessError

from modules.backup_clouds.nfs.backup_cloud import _run, _is_nfs_mounted, upload_backup
from modules.backup_clouds.nfs.config import NfsBackupCloudConfiguration


class TestRun:
    """Verify _run uses subprocess list form (no shell injection)."""

    @patch("modules.backup_clouds.nfs.backup_cloud.run")
    def test_run_passes_list_to_subprocess(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        result = _run(["sudo", "mkdir", "/mnt/nfs_mount"], 5)
        assert result is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        # First argument must be a list, not a string (prevents shell injection)
        assert isinstance(args[0], list)
        assert args[0] == ["sudo", "mkdir", "/mnt/nfs_mount"]
        # shell must NOT be True
        assert "shell" not in kwargs or kwargs["shell"] is not True

    @patch("modules.backup_clouds.nfs.backup_cloud.run")
    def test_run_raises_on_failure(self, mock_run):
        process = MagicMock(returncode=1, stdout=b"", stderr=b"error")
        mock_run.return_value = process
        process.check_returncode.side_effect = CalledProcessError(1, "cmd")
        with pytest.raises(CalledProcessError):
            _run(["sudo", "mkdir", "/mnt/nfs_mount"], 5)


class TestIsNfsMounted:
    def test_mounted(self):
        mount_content = "192.168.1.1:/share /mnt/nfs_mount nfs rw 0 0\n"
        with patch("builtins.open", mock_open(read_data=mount_content)):
            assert _is_nfs_mounted("192.168.1.1:/share") is True

    def test_not_mounted(self):
        mount_content = "tmpfs /tmp tmpfs rw 0 0\n"
        with patch("builtins.open", mock_open(read_data=mount_content)):
            assert _is_nfs_mounted("192.168.1.1:/share") is False

    def test_file_not_readable(self):
        with patch("builtins.open", side_effect=OSError("permission denied")):
            assert _is_nfs_mounted("192.168.1.1:/share") is False


class TestUploadBackupNoShellInjection:
    """Verify that user-controlled values like nfs_share cannot be used for shell injection."""

    @patch("modules.backup_clouds.nfs.backup_cloud._run")
    @patch("modules.backup_clouds.nfs.backup_cloud._is_nfs_mounted", return_value=False)
    @patch("modules.backup_clouds.nfs.backup_cloud.Path")
    def test_malicious_nfs_share_passed_as_single_argument(self, mock_path, mock_mounted, mock_run):
        mock_path.return_value.is_dir.return_value = False
        mock_run.return_value = True
        config = NfsBackupCloudConfiguration(nfs_share='192.168.1.1:/share"; rm -rf /')
        upload_backup(config, "backup.tar.gz", b"data")

        # The mount call should pass the malicious string as a single list element
        # not as part of a shell-interpreted string
        mount_call = mock_run.call_args_list[1]
        cmd_list = mount_call[0][0]
        assert cmd_list == ['sudo', 'mount', '-t', 'nfs', '192.168.1.1:/share"; rm -rf /', '/mnt/nfs_mount']
