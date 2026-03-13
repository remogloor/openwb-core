from unittest.mock import patch, MagicMock
from modules.monitoring.zabbix.api import create_config, create_monitoring, set_value
from modules.monitoring.zabbix.config import Zabbix, ZabbixConfiguration


class TestSetValue:
    def test_set_existing_value(self):
        lines = ["Server=old\n", "Other=val\n"]
        set_value(lines, "Server", "new")
        assert lines == ["Server=new\n", "Other=val\n"]

    def test_append_new_value(self):
        lines = ["Other=val\n"]
        set_value(lines, "Server", "new")
        assert lines == ["Other=val\n", "Server=new\n"]


class TestCreateConfigNoShellInjection:
    """Verify create_config uses subprocess.run with list form (no shell injection via os.system)."""

    @patch("modules.monitoring.zabbix.api.open", create=True)
    @patch("modules.monitoring.zabbix.api.subprocess")
    def test_uses_subprocess_run_not_os_system(self, mock_subprocess, mock_file):
        mock_file.return_value.__enter__ = MagicMock()
        mock_file.return_value.__exit__ = MagicMock(return_value=False)
        mock_file.return_value.__enter__.return_value.readlines.return_value = []

        config = Zabbix(configuration=ZabbixConfiguration(
            destination_host="host", hostname="name", psk_identifier="id", psk_key="key"
        ))
        create_config(config)

        # subprocess.run should be called with list arguments, not shell strings
        for call in mock_subprocess.run.call_args_list:
            args = call[0][0]
            assert isinstance(args, list), f"Expected list argument, got: {type(args)}"
            assert args[0] == "sudo"


class TestCreateMonitoringNoShellInjection:
    """Verify create_monitoring uses subprocess.run with list form."""

    @patch("modules.monitoring.zabbix.api.create_config")
    @patch("modules.monitoring.zabbix.api.subprocess")
    def test_start_uses_subprocess_run(self, mock_subprocess, mock_create_config):
        config = Zabbix(configuration=ZabbixConfiguration())
        monitoring = create_monitoring(config)
        monitoring.start_monitoring()

        # All subprocess.run calls should use list form
        for call in mock_subprocess.run.call_args_list:
            args = call[0][0]
            assert isinstance(args, list), f"Expected list argument, got: {type(args)}"

    @patch("modules.monitoring.zabbix.api.subprocess")
    def test_stop_uses_subprocess_run(self, mock_subprocess):
        config = Zabbix(configuration=ZabbixConfiguration())
        monitoring = create_monitoring(config)
        monitoring.stop_monitoring()

        for call in mock_subprocess.run.call_args_list:
            args = call[0][0]
            assert isinstance(args, list), f"Expected list argument, got: {type(args)}"
