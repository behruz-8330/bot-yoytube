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
    success: bool
    file_path: str | None = None
    title: str | None = None
    error: str | None = None

class MediaDownloader:
    def __init__(self, downloads_dir: str = DOWNLOADS_DIR):
        self.downloads_dir = downloads_dir

    async def download(self, url: str) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, url)

    def _download_sync(self, url: str) -> DownloadResult:
        unique_id = uuid.uuid4().hex[:10]
        output_template = os.path.join(self.downloads_dir, f"{unique_id}_%(title).50s.%(ext)s")
        
        # ENG BARQAROR SOZLAMALAR
        ydl_opts = {
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "noplaylist": True,
            "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "extractor_args": {"youtube": {"player_client": "android"}},
            "max_filesize": MAX_FILE_SIZE_MB * 1024 * 1024
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                return DownloadResult(success=True, file_path=file_path, title=info.get("title"))
        except Exception as e:
            logger.error(f"Yuklash xatosi: {e}")
            return DownloadResult(success=False, error=str(e))

downloader = MediaDownloader()
