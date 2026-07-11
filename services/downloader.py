import asyncio
import os
import uuid
import logging
import yt_dlp
from dataclasses import dataclass
from config import DOWNLOADS_DIR, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

@dataclass
class DownloadResult:
    """Yuklab olingan media haqida ma'lumot saqlovchi klass."""
    success: bool
    file_path: str | None = None
    title: str | None = None
    error: str | None = None
    is_audio: bool = False  # Xatolik tuzatildi

class MediaDownloader:
    def __init__(self, downloads_dir: str = DOWNLOADS_DIR):
        self.downloads_dir = downloads_dir

    def _get_ydl_opts(self, output_template: str, audio_only: bool = False, url: str = "") -> dict:
        """
        URL ni tekshirib, YouTube uchun alohida, boshqalar uchun standart sozlamalar qaytaradi.
        """
        base_opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": MAX_FILE_SIZE_MB * 1024 * 1024,
            "retries": 5,
        }
        
        # YouTube uchun maxsus sozlamalar
        if "youtube" in url or "youtu.be" in url:
            base_opts.update({
                "extractor_args": {"youtube": {"player_client": ["android"]}}
            })

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
        unique_id = uuid.uuid4().hex[:10]
        output_template = os.path.join(self.downloads_dir, f"{unique_id}_%(title).50s.%(ext)s")
        
        ydl_opts = self._get_ydl_opts(output_template, audio_only, url)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                if audio_only:
                    base, _ = os.path.splitext(file_path)
                    file_path = base + ".mp3"

                return DownloadResult(success=True, file_path=file_path, title=info.get("title"), is_audio=audio_only)
        except Exception as e:
            logger.error(f"Yuklash xatosi: {e}")
            return DownloadResult(success=False, error=str(e), is_audio=audio_only)

    async def download(self, url: str, audio_only: bool = False) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, url, audio_only)

# Global instance
downloader = MediaDownloader()
