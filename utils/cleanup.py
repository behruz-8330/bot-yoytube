"""
Cleanup utility - yuklab olingan vaqtinchalik fayllarni serverdan o'chirish uchun.

Diskni to'ldirib yubormaslik uchun har bir video/audio foydalanuvchiga
yuborilgandan so'ng darhol o'chiriladi. Bundan tashqari, botni qayta ishga
tushirishda "downloads" papkasida qolib ketgan eski fayllarni ham tozalash
imkoniyati mavjud (masalan, bot kutilmaganda o'chib qolgan holatlar uchun).
"""

import os
import logging
import time

from config import DOWNLOADS_DIR

logger = logging.getLogger(__name__)


def remove_file(file_path: str) -> None:
    """
    Berilgan fayl yo'lini xavfsiz tarzda o'chiradi.
    Fayl mavjud bo'lmasa yoki o'chirishda xatolik yuzaga kelsa, dastur to'xtab qolmaydi -
    faqat log yoziladi.
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Vaqtinchalik fayl o'chirildi: {file_path}")
    except OSError as e:
        logger.error(f"Faylni o'chirishda xatolik ({file_path}): {e}")


def cleanup_old_files(max_age_hours: int = 6) -> None:
    """
    'downloads' papkasidagi belgilangan soatdan eski bo'lgan barcha fayllarni o'chiradi.
    Bu funksiya bot ishga tushganda yoki vaqti-vaqti bilan (scheduler orqali) chaqirilishi mumkin,
    masalan bot kutilmagan tarzda to'xtab qolgan hollarda qolib ketgan fayllarni tozalash uchun.
    """
    if not os.path.exists(DOWNLOADS_DIR):
        return

    now = time.time()
    max_age_seconds = max_age_hours * 3600
    removed_count = 0

    for filename in os.listdir(DOWNLOADS_DIR):
        file_path = os.path.join(DOWNLOADS_DIR, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                remove_file(file_path)
                removed_count += 1

    if removed_count:
        logger.info(f"Eski fayllar tozalandi: {removed_count} ta fayl o'chirildi.")
