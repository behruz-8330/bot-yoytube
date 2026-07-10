"""
Database qatlami - aiosqlite yordamida asinxron SQLite bazasi bilan ishlash.
Bu yerda 3 ta asosiy jadval bor:
    1. users        - barcha foydalanuvchilar (oddiy va VIP)
    2. admins       - bot adminlari ro'yxati
    3. channels     - majburiy obuna kanallari

Barcha funksiyalar asinxron (async def) qilib yozilgan, chunki aiogram 3.x
to'liq asyncio asosida ishlaydi va bloklovchi (sync) DB chaqiruvlari botni
"muzlatib" qo'yishi mumkin.
"""

import aiosqlite
import datetime
from config import DATABASE_PATH


class Database:
    """SQLite baza bilan ishlash uchun asosiy klass."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Bot ishga tushganda barcha kerakli jadvallarni yaratadi (agar mavjud bo'lmasa)."""
        async with aiosqlite.connect(self.db_path) as db:
            # Foydalanuvchilar jadvali
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_vip INTEGER DEFAULT 0,
                    vip_until TEXT DEFAULT NULL,
                    downloads_today INTEGER DEFAULT 0,
                    last_download_date TEXT DEFAULT NULL,
                    joined_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Adminlar jadvali (super adminlar config.py da, qo'shimcha adminlar shu yerda)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_by INTEGER,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Majburiy obuna kanallari jadvali
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    invite_link TEXT,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    # ------------------- USERS -------------------

    async def add_user(self, user_id: int, username: str | None, full_name: str) -> None:
        """Yangi foydalanuvchini bazaga qo'shadi (agar mavjud bo'lmasa)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name
                """,
                (user_id, username, full_name),
            )
            await db.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        """Foydalanuvchi ma'lumotlarini qaytaradi."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cursor.fetchone()

    async def get_all_users(self) -> list[aiosqlite.Row]:
        """Barcha foydalanuvchilar ro'yxatini qaytaradi (broadcast/statistika uchun)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users")
            return await cursor.fetchall()

    async def count_users(self) -> int:
        """Umumiy foydalanuvchilar sonini qaytaradi."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def set_vip(self, user_id: int, days: int) -> None:
        """Foydalanuvchiga VIP status beradi, `days` kun muddatga."""
        vip_until = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_vip = 1, vip_until = ? WHERE user_id = ?",
                (vip_until, user_id),
            )
            await db.commit()

    async def remove_vip(self, user_id: int) -> None:
        """Foydalanuvchidan VIP statusni olib tashlaydi."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_vip = 0, vip_until = NULL WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()

    async def is_vip_active(self, user_id: int) -> bool:
        """Foydalanuvchining VIP muddati hali tugamaganini tekshiradi."""
        user = await self.get_user(user_id)
        if not user or not user["is_vip"]:
            return False
        if not user["vip_until"]:
            return False
        vip_until = datetime.datetime.fromisoformat(user["vip_until"])
        if vip_until < datetime.datetime.now():
            # Muddati tugagan bo'lsa avtomatik o'chiramiz
            await self.remove_vip(user_id)
            return False
        return True

    async def can_download(self, user_id: int) -> bool:
        """
        Foydalanuvchi bugun yana yuklab olishi mumkinligini tekshiradi.
        VIP foydalanuvchilar uchun cheklov yo'q.
        """
        if await self.is_vip_active(user_id):
            return True

        user = await self.get_user(user_id)
        if not user:
            return True

        today = datetime.date.today().isoformat()
        if user["last_download_date"] != today:
            return True  # Yangi kun boshlandi, hisob nolga tushadi

        return user["downloads_today"] < __import__("config").FREE_USER_DAILY_LIMIT

    async def increment_download_count(self, user_id: int) -> None:
        """Foydalanuvchining bugungi yuklab olishlar sonini +1 qiladi."""
        today = datetime.date.today().isoformat()
        user = await self.get_user(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            if user and user["last_download_date"] == today:
                await db.execute(
                    "UPDATE users SET downloads_today = downloads_today + 1 WHERE user_id = ?",
                    (user_id,),
                )
            else:
                await db.execute(
                    "UPDATE users SET downloads_today = 1, last_download_date = ? WHERE user_id = ?",
                    (today, user_id),
                )
            await db.commit()

    # ------------------- ADMINS -------------------

    async def add_admin(self, user_id: int, added_by: int) -> None:
        """Yangi admin qo'shadi."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)",
                (user_id, added_by),
            )
            await db.commit()

    async def remove_admin(self, user_id: int) -> None:
        """Adminni ro'yxatdan o'chiradi."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_all_admins(self) -> list[int]:
        """Bazadagi barcha adminlar ID ro'yxatini qaytaradi (super adminlarsiz)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM admins")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def is_admin(self, user_id: int) -> bool:
        """Foydalanuvchi admin ekanini tekshiradi (super admin yoki DB admin)."""
        from config import SUPER_ADMINS

        if user_id in SUPER_ADMINS:
            return True
        admins = await self.get_all_admins()
        return user_id in admins

    # ------------------- CHANNELS (majburiy obuna) -------------------

    async def add_channel(self, chat_id: str, title: str, invite_link: str | None) -> None:
        """Majburiy obuna uchun yangi kanal qo'shadi."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO channels (chat_id, title, invite_link) VALUES (?, ?, ?)",
                (chat_id, title, invite_link),
            )
            await db.commit()

    async def remove_channel(self, chat_id: str) -> None:
        """Majburiy obuna kanalini ro'yxatdan o'chiradi."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
            await db.commit()

    async def get_all_channels(self) -> list[aiosqlite.Row]:
        """Barcha majburiy obuna kanallarini qaytaradi."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM channels")
            return await cursor.fetchall()


# Global database instance - barcha handlerlar shu obyektdan foydalanadi
db = Database()
