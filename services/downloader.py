"""
Downloader service - yt-dlp yordamida video/audio yuklab olish logikasi.
"""

import asyncio
import os
import uuid
import logging
from dataclasses import dataclass

import yt_dlp

from config import DOWNLOADS_DIR, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Yuklab olingan media haqida ma'lumot saqlovchi klass."""
    success: bool
    file_path: str | None = None
    title: str | None = None
    error: str | None = None
    is_audio: bool = False


class MediaDownloader:
    """yt-dlp asosida ishlaydigan yuklovchi klass."""

    def __init__(self, downloads_dir: str = DOWNLOADS_DIR):
        self.downloads_dir = downloads_dir

    def _get_ydl_opts(self, output_template: str, audio_only: bool = False) -> dict:
        """
        yt-dlp uchun sozlamalar (options) lug'atini qaytaradi.
        Android client va user_agent yordamida blokirovkalarni aylanib o'tadi.
        """
        base_opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": MAX_FILE_SIZE_MB * 1024 * 1024,
            "retries": 10,
            "socket_timeout": 60,
            # Eng samarali sozlamalar
            "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "extractor_args": {"youtube": {"player_client": "android"}},
        }

        if audio_only:
            base_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            base_opts.update({
                "format": "best[ext=mp4]/best",
                "merge_output_format": "mp4",
            })

        return base_opts

    def _download_sync(self, url: str, audio_only: bool = False) -> DownloadResult:
        """
        Bloklovchi (synchronous) yuklab olish funksiyasi.
        """
        unique_id = uuid.uuid4().hex[:10]
        output_template = os.path.join(self.downloads_dir, f"{unique_id}_%(title).50s.%(ext)s")

        ydl_opts = self._get_ydl_opts(output_template, audio_only)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if "entries" in info:
                    info = info["entries"][0]

                file_path = ydl.prepare_filename(info)

                if audio_only:
                    base, _ = os.path.splitext(file_path)
                    file_path = base + ".mp3"

                if not os.path.exists(file_path):
                    return DownloadResult(success=False, error="Fayl yuklab olingandan so'ng topilmadi.")

                title = info.get("title", "Nomsiz media")
                return DownloadResult(success=True, file_path=file_path, title=title, is_audio=audio_only)

        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"yt-dlp DownloadError: {e}")
            return DownloadResult(success=False, error="Video yuklab bo'lmadi. Havolani tekshiring.")
        except Exception as e:
            logger.exception(f"Kutilmagan xatolik yuklashda: {e}")
            return DownloadResult(success=False, error="Kutilmagan xatolik yuz berdi.")

    async def download(self, url: str, audio_only: bool = False) -> DownloadResult:
        """
        Asinxron wrapper.
        """
        return await asyncio.to_thread(self._download_sync, url, audio_only)


# Global instance
downloader = MediaDownloader()
