import contextlib
import io
import unittest
from unittest.mock import MagicMock, patch

import download_transcript


VIDEO_IDS = ["abcdefghijk", "lmnopqrstuv", "12345678901"]


class ChannelVideosUrlTests(unittest.TestCase):
    def test_converts_handle_to_videos_url(self):
        self.assertEqual(
            download_transcript.channel_videos_url("@example"),
            "https://www.youtube.com/@example/videos",
        )

    def test_replaces_other_channel_tab(self):
        self.assertEqual(
            download_transcript.channel_videos_url(
                "https://www.youtube.com/@example/shorts"
            ),
            "https://www.youtube.com/@example/videos",
        )


class FetchChannelVideoIdsTests(unittest.TestCase):
    @patch("download_transcript.yt_dlp.YoutubeDL")
    def test_limits_channel_to_latest_videos(self, youtube_dl):
        instance = youtube_dl.return_value.__enter__.return_value
        instance.extract_info.return_value = {
            "entries": [{"id": video_id} for video_id in VIDEO_IDS[:2]]
        }

        result = download_transcript.fetch_channel_video_ids("@example", 2)

        self.assertEqual(result, VIDEO_IDS[:2])
        self.assertEqual(youtube_dl.call_args.args[0]["playlistend"], 2)
        instance.extract_info.assert_called_once_with(
            "https://www.youtube.com/@example/videos", download=False
        )

    @patch("download_transcript.yt_dlp.YoutubeDL")
    def test_fetches_all_channel_videos_without_playlist_limit(self, youtube_dl):
        instance = youtube_dl.return_value.__enter__.return_value
        instance.extract_info.return_value = {
            "entries": [{"id": video_id} for video_id in VIDEO_IDS]
        }

        result = download_transcript.fetch_channel_video_ids("@example", None)

        self.assertEqual(result, VIDEO_IDS)
        self.assertNotIn("playlistend", youtube_dl.call_args.args[0])


class ParseArgsTests(unittest.TestCase):
    def test_channel_requires_latest_or_all(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                download_transcript.parse_args(["--channel", "@example"])

    def test_latest_must_be_positive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                download_transcript.parse_args(["--channel", "@example", "--latest", "0"])


class MainChannelTests(unittest.TestCase):
    @patch("download_transcript.process_video")
    @patch("download_transcript.fetch_channel_video_ids")
    def test_processes_each_latest_channel_video(self, fetch_ids, process_video):
        fetch_ids.return_value = VIDEO_IDS[:2]

        with contextlib.redirect_stderr(io.StringIO()):
            result = download_transcript.main(
                ["--channel", "@example", "--latest", "2", "--no-title"]
            )

        self.assertEqual(result, 0)
        fetch_ids.assert_called_once_with("@example", 2)
        self.assertEqual(
            [call.args[0] for call in process_video.call_args_list],
            VIDEO_IDS[:2],
        )

    @patch("download_transcript.process_video")
    @patch("download_transcript.fetch_channel_video_ids")
    def test_all_passes_no_limit(self, fetch_ids, process_video):
        fetch_ids.return_value = VIDEO_IDS

        with contextlib.redirect_stderr(io.StringIO()):
            result = download_transcript.main(["--channel", "@example", "--all"])

        self.assertEqual(result, 0)
        fetch_ids.assert_called_once_with("@example", None)
        self.assertEqual(process_video.call_count, 3)


if __name__ == "__main__":
    unittest.main()
