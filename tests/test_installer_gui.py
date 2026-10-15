import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from installer_gui import (
    check_dir_is_installation,
    find_existing_installation,
    InstallerAPI,
    APP_VERSION
)

class TestInstallerGUI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_check_dir_nonexistent(self):
        is_inst, ver = check_dir_is_installation(os.path.join(self.temp_dir.name, "does_not_exist"))
        self.assertFalse(is_inst)
        self.assertIsNone(ver)

    def test_check_dir_empty(self):
        is_inst, ver = check_dir_is_installation(self.temp_dir.name)
        self.assertFalse(is_inst)
        self.assertIsNone(ver)

    def test_check_dir_with_exe(self):
        exe_path = os.path.join(self.temp_dir.name, "SDN_Downloader.exe")
        with open(exe_path, "w") as f:
            f.write("mock_exe")
        is_inst, ver = check_dir_is_installation(self.temp_dir.name)
        self.assertTrue(is_inst)
        self.assertIsNone(ver)

    def test_check_dir_with_version_json(self):
        vjson_path = os.path.join(self.temp_dir.name, "version.json")
        with open(vjson_path, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0.6", "name": "SDN Downloader Ultra"}, f)
        is_inst, ver = check_dir_is_installation(self.temp_dir.name)
        self.assertTrue(is_inst)
        self.assertEqual(ver, "1.0.6")

    def test_api_get_install_info(self):
        api = InstallerAPI()
        info = api.get_install_info()
        self.assertIn("install_dir", info)
        self.assertIn("is_update", info)
        self.assertIn("existing_version", info)
        self.assertIn("app_version", info)
        self.assertEqual(info["app_version"], APP_VERSION)

    def test_api_start_install_no_double_append(self):
        api = InstallerAPI()
        existing_path = self.temp_dir.name
        # Create version.json so it's treated as existing install
        with open(os.path.join(existing_path, "version.json"), "w", encoding="utf-8") as f:
            json.dump({"version": "1.0.6"}, f)

        with patch.object(api, '_run_installation') as mock_run:
            api.start_install(existing_path, create_desktop=False)
            self.assertEqual(api.install_dir, existing_path)
            self.assertTrue(api.is_update)

if __name__ == '__main__':
    unittest.main()
