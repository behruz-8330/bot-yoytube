"""
Guruh handlerlari.

Guruhga (yoki superguruhga) tashlangan har qanday https havolasini avtomatik
tutib oladi, yt-dlp orqali yuklaydi va "Video @yuklovchi_uzbek_robot tomonidan
yuklandi" caption bilan o'sha guruhga yuboradi.

Eslatma: Guruhlarda majburiy obuna middleware'i ishlamaydi (chunki bu shaxsiy
foydalanuvchi tekshiruvi), shuning uchun guruh funksiyasi alohida router orqali
boshqariladi.
"""

import logging
import re

from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.types import Message, FSInputFile

from config import BOT_USERNAME
from services.downloader import downloader
from utils.cleanup import remove_file

logger = logging.getLogger(__name__)
router = Router(name="group_handlers")

URL_PATTERN = re.compile(r"https?://[^\s]+")

# Faqat guruh va superguruh chatlarida ishlaydi
router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))


@router.message(F.text.regexp(URL_PATTERN.pattern))
async def handle_group_link(message: Message) -> None:
    """Guruhga tashlangan havolani ushlab, videoni yuklab beradi."""
    url_match = URL_PATTERN.search(message.text)
    if not url_match:
        return
    url = url_match.group(0)

    status_message = await message.reply("⏳ Video yuklanmoqda...")

    result = await downloader.download(url)

    if not result.success:
        await status_message.edit_text(f"❌ Xatolik: {result.error}")
        return

    try:
        caption = f"🎬 Video @{BOT_USERNAME} tomonidan yuklandi"
        video_file = FSInputFile(result.file_path)

        if result.is_audio:
            await message.reply_audio(audio=video_file, caption=caption)
        else:
            await message.reply_video(video=video_file, caption=caption, supports_streaming=True)

        await status_message.delete()

    except Exception as e:
        logger.exception(f"Guruhda faylni yuborishda xatolik: {e}")
        await status_message.edit_text("❌ Faylni yuborishda xatolik yuz berdi.")
    finally:
        # XOTIRA BOSHQARUVI: fayl har doim serverdan o'chiriladi
        remove_file(result.file_path)
