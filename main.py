"""
Bot uchun asosiy ishga tushirish (entry point) fayli.

Bu yerda:
    - Bot va Dispatcher obyektlari yaratiladi
    - Barcha routerlar (handlers) ro'yxatga olinadi
    - Middleware'lar ulanadi
    - Baza ishga tushiriladi
    - Bot polling rejimida ishga tushadi

Ishga tushirish: python main.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.models import db
from middlewares.subscription_check import SubscriptionMiddleware
from utils.cleanup import cleanup_old_files

# Handlerlar (routerlar)
from handlers import user_handlers, admin_handlers, group_handlers

# --- Logging sozlamalari ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Botni ishga tushiruvchi asosiy asinxron funksiya."""

    # Bot obyekti - parse_mode HTML qilib belgilangan, shunda barcha xabarlarda
    # <b>, <i>, <code> kabi teglardan foydalanish mumkin
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Dispatcher - FSM holatlari uchun xotirada saqlovchi (MemoryStorage) ishlatilmoqda.
    # Katta production loyihalarda buni RedisStorage bilan almashtirish tavsiya etiladi,
    # chunki MemoryStorage bot qayta ishga tushganda barcha holatlarni yo'qotadi.
    dp = Dispatcher(storage=MemoryStorage())

    # --- Bazani ishga tushirish ---
    await db.init_db()
    logger.info("Baza muvaffaqiyatli ishga tushirildi.")

    # --- Eski vaqtinchalik fayllarni tozalash (bot qayta ishga tushganda) ---
    cleanup_old_files(max_age_hours=6)

    # --- Middleware'larni ulash ---
    # Faqat admin va guruh handlerlaridan tashqari, oddiy foydalanuvchi
    # xabarlari uchun majburiy obuna middleware'ini ulaymiz
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # --- Routerlarni ro'yxatga olish ---
    # MUHIM: tartib muhim! Guruh routeri birinchi bo'lishi kerak (chat turi bo'yicha
    # filterlangan), keyin admin, keyin oddiy foydalanuvchi routeri (eng keng qamrovli).
    dp.include_router(group_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    # --- Botni ishga tushirish (eski update'larni tashlab, faqat yangilarini olish) ---
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot ishga tushdi va so'rovlarni kutmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
