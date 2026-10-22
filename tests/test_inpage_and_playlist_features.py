# -*- coding: utf-8 -*-
import unittest
import os
import json
import tempfile
from pathlib import Path
from main import DownloaderBridgeAPI, YouTubeBrowserBridge


class TestInPageAndPlaylistFeatures(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sdn_test_features_")
        self.api = DownloaderBridgeAPI()
        self.api.save_dir = self.temp_dir

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bridge_methods(self):
        bridge = YouTubeBrowserBridge(self.api)
        # Test duplicate check on non-existent
        dup = bridge.check_duplicate("https://www.youtube.com/watch?v=unique123", "Unique Video Title")
        self.assertFalse(dup['is_duplicate'])

        # Test send to main
        res = bridge.send_to_main("https://www.youtube.com/watch?v=unique123", auto_playlist_select=True)
        self.assertTrue(res['success'])

    def test_check_duplicate_url_and_title(self):
        # Add item to history
        sample_path = os.path.join(self.temp_dir, "MySong.mp3")
        Path(sample_path).write_text("dummy")

        self.api.add_history({
            'title': 'Awesome Song Title',
            'quality': 'MP3',
            'type': 'audio',
            'filepath': sample_path,
            'url': 'https://www.youtube.com/watch?v=song12345',
            'date': '2026-10-17T02:00:00+03:00'
        })

        # Check duplicate by URL
        dup1 = self.api.check_duplicate(url='https://www.youtube.com/watch?v=song12345')
        self.assertTrue(dup1['is_duplicate'])

        # Check duplicate by Title
        dup2 = self.api.check_duplicate(title='Awesome Song Title')
        self.assertTrue(dup2['is_duplicate'])

        # Check duplicate by file exists in save_dir
        dup3 = self.api.check_duplicate(title='MySong')
        self.assertTrue(dup3['is_duplicate'])

        # Regression test: non-media files like 1.jpg or unrelated titles must NOT trigger duplicate
        sample_img = os.path.join(self.temp_dir, "1.jpg")
        Path(sample_img).write_text("dummy")
        dup_img = self.api.check_duplicate(title='فيديو جديد رقم 1')
        self.assertFalse(dup_img['is_duplicate'])

        dup_diff = self.api.check_duplicate(title='Episode 2')
        self.assertFalse(dup_diff['is_duplicate'])

    def test_play_file_nonexistent(self):
        res = self.api.play_file(os.path.join(self.temp_dir, "nonexistent.mp4"))
        self.assertFalse(res['success'])

    def test_mixed_playlist_option_structure(self):
        option = {
            'type': 'mixed',
            'mixed_playlist': True,
            'playlist_video_items': [1, 2, 3],
            'playlist_audio_items': [4, 5],
            'playlist_items': [1, 2, 3, 4, 5],
            'playlist_count': 5,
            'media_title': 'Test Playlist'
        }
        self.assertTrue(option['mixed_playlist'])
        self.assertEqual(len(option['playlist_video_items']), 3)
    def test_playlist_item_details_option_structure(self):
        option = {
            'type': 'video',
            'is_playlist': True,
            'playlist_items': [1, 2],
            'playlist_item_details': [
                {'index': 1, 'title': 'Track 1', 'url': 'https://www.youtube.com/watch?v=aaa111bbb22'},
                {'index': 2, 'title': 'Track 2', 'url': 'https://www.youtube.com/watch?v=ccc333ddd44'},
            ],
            'playlist_count': 2,
            'media_title': 'Mix Playlist'
        }
        self.assertTrue(option['is_playlist'])
        self.assertEqual(len(option['playlist_item_details']), 2)
        self.assertEqual(option['playlist_item_details'][0]['title'], 'Track 1')

    def test_clean_url_mix_preserves_both_video_and_playlist(self):
        from downloader import clean_url
        url = "https://www.youtube.com/watch?v=ndCI8DIM86w&list=RDndCI8DIM86w"
        cleaned = clean_url(url, keep_mix_playlist=True)
        self.assertIn("v=ndCI8DIM86w", cleaned)
        self.assertIn("list=RDndCI8DIM86w", cleaned)

    def test_format_aware_duplicate_checking(self):
        # 1. Video exists: allow audio, reject video
        vid_path = os.path.join(self.temp_dir, "Matrix_Trailer.mp4")
        Path(vid_path).write_text("dummy video")

        # Querying as video must trigger duplicate
        dup_vid = self.api.check_duplicate(title="Matrix Trailer", target_type="video")
        self.assertTrue(dup_vid['is_duplicate'])

        # Querying as audio MUST NOT trigger duplicate (user permitted mp3 when video exists)
        dup_aud = self.api.check_duplicate(title="Matrix Trailer", target_type="audio")
        self.assertFalse(dup_aud['is_duplicate'])

        # 2. Audio exists: allow video, reject audio
        aud_path = os.path.join(self.temp_dir, "Podcast_Ep1.mp3")
        Path(aud_path).write_text("dummy audio")

        # Querying as audio must trigger duplicate
        dup_aud2 = self.api.check_duplicate(title="Podcast Ep1", target_type="audio")
        self.assertTrue(dup_aud2['is_duplicate'])

        # Querying as video MUST NOT trigger duplicate (user permitted video when mp3 exists)
        dup_vid2 = self.api.check_duplicate(title="Podcast Ep1", target_type="video")
        self.assertFalse(dup_vid2['is_duplicate'])

    def test_playlist_session_lifecycle(self):
        # Temporary custom session file for isolation
        custom_session_file = os.path.join(self.temp_dir, "test_playlist_session.json")
        orig_getter = self.api._get_playlist_session_file
        self.api._get_playlist_session_file = staticmethod(lambda: custom_session_file)

        try:
            # Initially no session
            check_init = self.api.get_unfinished_playlist_session()
            self.assertFalse(check_init['has_session'])

            # Save session
            session_data = {
                'url': 'https://www.youtube.com/playlist?list=PL12345',
                'playlist_title': 'My 30 Videos Playlist',
                'playlist_count': 30,
                'completed_count': 12,
                'completed_items': [{'index': i, 'title': f'Item {i}'} for i in range(1, 13)],
                'remaining_indices': list(range(13, 31)),
                'mode': 'video',
                'save_dir': self.temp_dir,
                'option': {'type': 'video', 'ext': 'mp4'}
            }
            self.api._save_playlist_session(session_data)

            # Check unfinished session detected
            check_saved = self.api.get_unfinished_playlist_session()
            self.assertTrue(check_saved['has_session'])
            sess = check_saved['session']
            self.assertEqual(sess['playlist_title'], 'My 30 Videos Playlist')
            self.assertEqual(sess['completed_count'], 12)
            self.assertEqual(sess['remaining_count'], 18)
            self.assertEqual(sess['total_count'], 30)

            # Discard session
            disc = self.api.discard_unfinished_playlist_session()
            self.assertTrue(disc['discarded'])

            # Verify no longer active
            check_after = self.api.get_unfinished_playlist_session()
            self.assertFalse(check_after['has_session'])
        finally:
            self.api._get_playlist_session_file = orig_getter


if __name__ == '__main__':
    unittest.main()

