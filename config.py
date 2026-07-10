"""
Config module - barcha muhit o'zgaruvchilari (environment variables) shu yerda saqlanadi.
Xavfsizlik uchun BOT_TOKEN va boshqa maxfiy ma'lumotlar .env faylidan o'qiladi,
hech qachon kod ichida "hardcode" qilinmaydi.
"""

import os
from dotenv import load_dotenv

# .env faylini yuklaymiz
load_dotenv()

# --- Majburiy sozlamalar ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN topilmadi! Iltimos .env fayliga BOT_TOKEN=... qo'shing."
    )

# --- Super adminlar (bot kodida o'zgarmas, boshqa adminlar DB orqali qo'shiladi) ---
# .env da: SUPER_ADMINS=123456789,987654321
_super_admins_raw = os.getenv("SUPER_ADMINS", "")
SUPER_ADMINS: list[int] = [
    int(admin_id) for admin_id in _super_admins_raw.split(",") if admin_id.strip().isdigit()
]

# --- Bot username (caption uchun) ---
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "yuklovchi_uzbek_robot")

# --- Fayllar uchun vaqtinchalik papka ---
DOWNLOADS_DIR: str = os.getenv("DOWNLOADS_DIR", "downloads")

# --- Bazadagi fayl nomi ---
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "database/bot_database.db")

# --- Yuklab olish uchun maksimal fayl hajmi (baytlarda), Telegram limiti ~2GB (bot uchun 50MB/2GB) ---
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "2000"))

# --- VIP bo'lmagan foydalanuvchilar uchun kuniga limit ---
FREE_USER_DAILY_LIMIT: int = int(os.getenv("FREE_USER_DAILY_LIMIT", "5"))

# --- VIP narxi (faqat ma'lumot sifatida, /admin panelida ko'rsatish uchun) ---
VIP_PRICE_INFO: str = os.getenv("VIP_PRICE_INFO", "10,000 so'm / oy")

# --- Admin bilan bog'lanish uchun username ---
ADMIN_CONTACT: str = os.getenv("ADMIN_CONTACT", "@admin")

# Papkani oldindan yaratib qo'yamiz (bo'lmasa xatolik chiqmasligi uchun)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
