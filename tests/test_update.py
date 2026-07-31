import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class FakeReleaseResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SilentUpdateTests(unittest.TestCase):
    def setUp(self):
        self.api = object.__new__(main.DownloaderBridgeAPI)
        self.api.latest_update_info = None
        self.api._update_download_active = False
        self.api._update_restart_started = False
        self.api.pending_update_path = None
        self.api.pending_update_kind = None
        self.api.pending_update_sha256 = None
        self.api.pending_update_size = None
        self.api._window = None

    def test_update_check_prefers_portable_asset_and_keeps_installer_fallback(self):
        payload = {
            "tag_name": "v99.0.0",
            "html_url": "https://github.com/example/release",
            "assets": [
                {
                    "name": main.WINDOWS_INSTALLER_ASSET,
                    "browser_download_url": "https://github.com/example/setup.exe",
                    "digest": "sha256:" + ("a" * 64),
                    "size": 200,
                },
                {
                    "name": main.WINDOWS_PORTABLE_ASSET,
                    "browser_download_url": "https://github.com/example/portable.exe",
                    "digest": "sha256:" + ("b" * 64),
                    "size": 100,
                },
            ],
        }
        with mock.patch("urllib.request.urlopen", return_value=FakeReleaseResponse(payload)):
            result = self.api.check_app_update()

        self.assertTrue(result["has_update"])
        self.assertEqual(result["update_kind"], "portable")
        self.assertEqual(result["download_url"], "https://github.com/example/portable.exe")
        self.assertEqual(result["portable_sha256"], "b" * 64)
        self.assertEqual(result["installer_sha256"], "a" * 64)

    def test_package_selection_uses_silent_installer_only_when_direct_replace_is_blocked(self):
        update_info = {
            "portable_url": "https://github.com/example/portable.exe",
            "portable_sha256": "1" * 64,
            "portable_size": 10,
            "installer_url": "https://github.com/example/setup.exe",
            "installer_sha256": "2" * 64,
            "installer_size": 20,
        }
        with mock.patch.object(self.api, "_can_replace_current_executable", return_value=True):
            direct = self.api._select_update_package(update_info)
        with mock.patch.object(self.api, "_can_replace_current_executable", return_value=False):
            fallback = self.api._select_update_package(update_info)

        self.assertEqual(direct["kind"], "portable")
        self.assertEqual(fallback["kind"], "installer")

    def test_portable_updater_is_hidden_and_restarts_same_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / main.WINDOWS_PORTABLE_ASSET
            update = Path(directory) / "SDN_Update_Portable.exe"
            target.write_bytes(b"MZtarget")
            update.write_bytes(b"MZupdate")

            with (
                mock.patch.object(main.sys, "frozen", True, create=True),
                mock.patch.object(main.sys, "executable", str(target)),
                mock.patch.object(self.api, "_can_replace_current_executable", return_value=True),
                mock.patch("main.shutil.which", return_value=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"),
                mock.patch("main.os.path.isfile", return_value=True),
                mock.patch("main.subprocess.Popen") as popen,
            ):
                self.api._launch_portable_updater(update)

            command = popen.call_args.args[0]
            kwargs = popen.call_args.kwargs
            self.assertIn("-WindowStyle", command)
            self.assertIn("Hidden", command)
            self.assertIn("-TargetPath", command)
            self.assertEqual(command[command.index("-TargetPath") + 1], str(target))
            self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)

            script_path = Path(command[command.index("-File") + 1])
            script_text = script_path.read_text(encoding="utf-8-sig")
            self.assertIn("Wait-Process", script_text)
            self.assertIn("Move-Item -LiteralPath $UpdatePath", script_text)
            self.assertIn("Start-Process -FilePath $TargetPath", script_text)
            script_path.unlink(missing_ok=True)

    def test_installer_fallback_uses_no_visible_wizard_and_same_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / main.WINDOWS_PORTABLE_ASSET
            setup = Path(directory) / main.WINDOWS_INSTALLER_ASSET
            target.write_bytes(b"MZtarget")
            setup.write_bytes(b"MZsetup")

            with (
                mock.patch.object(main.sys, "frozen", True, create=True),
                mock.patch.object(main.sys, "executable", str(target)),
                mock.patch("main.subprocess.Popen") as popen,
            ):
                self.api._launch_silent_installer(setup)

            command = popen.call_args.args[0]
            self.assertIn("/VERYSILENT", command)
            self.assertIn("/SUPPRESSMSGBOXES", command)
            self.assertIn("/LANG=arabic", command)
            self.assertIn(f"/DIR={target.parent}", command)
            self.assertEqual(popen.call_args.kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)

    def test_restart_dispatches_verified_portable_update_then_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            update = Path(directory) / "SDN_Update_Portable.exe"
            update.write_bytes(b"MZ" + os.urandom(1024 * 1024))
            self.api.pending_update_path = str(update)
            self.api.pending_update_kind = "portable"
            self.api.pending_update_sha256 = main.hashlib.sha256(update.read_bytes()).hexdigest()
            self.api.pending_update_size = update.stat().st_size

            with (
                mock.patch.object(self.api, "_launch_portable_updater") as launcher,
                mock.patch("main.time.sleep"),
                mock.patch("main.os._exit") as exit_process,
            ):
                result = self.api.restart_and_apply_update(str(update))

            self.assertTrue(result["success"])
            launcher.assert_called_once_with(update.resolve())
            exit_process.assert_called_once_with(0)

    def test_restart_rejects_a_download_modified_after_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            update = Path(directory) / "SDN_Update_Portable.exe"
            update.write_bytes(b"MZ" + os.urandom(1024 * 1024))
            self.api.pending_update_path = str(update)
            self.api.pending_update_kind = "portable"
            self.api.pending_update_sha256 = main.hashlib.sha256(update.read_bytes()).hexdigest()
            self.api.pending_update_size = update.stat().st_size
            update.write_bytes(update.read_bytes()[:-1] + b"X")

            with mock.patch.object(self.api, "_launch_portable_updater") as launcher:
                result = self.api.restart_and_apply_update(str(update))

            self.assertFalse(result["success"])
            self.assertIn("بصمة", result["error"])
            launcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
