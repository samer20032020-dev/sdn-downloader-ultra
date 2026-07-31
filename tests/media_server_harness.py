"""Manual browser-test harness for the tokenized local media server."""

import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


def run():
    filepath = os.environ["SDN_TEST_MEDIA_FILE"]
    api = object.__new__(main.DownloaderBridgeAPI)
    api._media_server = None
    api._media_port = None
    api._media_lock = threading.Lock()
    api._media_tokens = {}
    api._media_path_tokens = {}
    api._media_prepare_lock = threading.Lock()
    api._media_cache_dir = None
    main.MediaHTTPHandler.bridge_api = api
    api._start_local_media_server()
    prepared = api.prepare_media_playback(filepath)
    if not prepared.get("ok"):
        raise RuntimeError(prepared.get("error") or "Could not prepare media")
    print(prepared["url"], flush=True)
    try:
        while True:
            time.sleep(30)
    finally:
        if api._media_server:
            api._media_server.shutdown()
            api._media_server.server_close()


if __name__ == "__main__":
    run()
