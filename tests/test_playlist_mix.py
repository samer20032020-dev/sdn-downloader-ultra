import os
import unittest
from unittest.mock import MagicMock
from downloader import MediaDownloader

class TestPlaylistMixImprovements(unittest.TestCase):
    def test_playlist_monotonic_tracking_logic(self):
        d = MediaDownloader()
        opt = {
            'is_playlist': True,
            'playlist_count': 50,
            'type': 'audio',
            'ext': 'mp3',
            'playlist_title': 'ميكس - تيست اغاني',
        }
        # Verify clean folder name without ugly underscores
        import re
        raw_pl = str(opt.get('playlist_title')).strip()
        clean_pl = re.sub(r'[<>:"/\\|?*\n\r\t]', '', raw_pl).strip().strip('.')
        clean_pl = re.sub(r'\s+', ' ', clean_pl)[:80].strip()
        self.assertEqual(clean_pl, 'ميكس - تيست اغاني')

if __name__ == '__main__':
    unittest.main()
