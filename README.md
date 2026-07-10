# 🎬 Media Yuklovchi Telegram Bot

aiogram 3.x va yt-dlp asosida qurilgan, production-ready media yuklovchi bot.

## 📁 Loyiha strukturasi

```
media_bot/
├── main.py                      # Bot entry point
├── config.py                    # Sozlamalar (.env dan o'qiydi)
├── requirements.txt
├── .env.example                 # .env namunasi
├── handlers/
│   ├── user_handlers.py         # /start, VIP, shaxsiy chat havolalar
│   ├── admin_handlers.py        # /admin panel (FSM asosida)
│   └── group_handlers.py        # Guruhdagi havolalarni yuklash
├── database/
│   └── models.py                # aiosqlite: users, admins, channels
├── middlewares/
│   └── subscription_check.py    # Majburiy obuna middleware
├── services/
│   └── downloader.py            # yt-dlp + ffmpeg logikasi
└── utils/
    └── cleanup.py                # Vaqtinchalik fayllarni tozalash
```

## ⚙️ O'rnatish

1. **Python 3.11+** va **ffmpeg** o'rnatilgan bo'lishi kerak:
   ```bash
   sudo apt update && sudo apt install ffmpeg -y
   ```

2. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

3. `.env.example` faylini `.env` nomiga nusxalab, o'z ma'lumotlaringizni kiriting:
   ```bash
   cp .env.example .env
   ```
   - `BOT_TOKEN` — @BotFather'dan olingan token
   - `SUPER_ADMINS` — sizning Telegram ID raqamingiz (vergul bilan ajratib bir nechta yozish mumkin)

4. Botni ishga tushiring:
   ```bash
   python main.py
   ```

## 🔑 Asosiy imkoniyatlar

- **/start** — VIP sotib olish va Majburiy obuna tugmalari bilan.
- **/admin** — Faqat adminlar uchun boshqaruv paneli:
  - Statistika
  - Adminlarni qo'shish/o'chirish
  - VIP foydalanuvchilarni qo'shish/o'chirish (muddat bilan)
  - Majburiy obuna kanallarini sozlash
- **Majburiy obuna** — Har bir shaxsiy foydalanuvchi belgilangan kanallarga a'zo bo'lmasa botdan foydalana olmaydi.
- **Guruh funksiyasi** — Guruhga tashlangan havola avtomatik yuklab olinadi va yuboriladi.
- **Xotira boshqaruvi** — Har bir yuklangan fayl yuborilgach avtomatik o'chiriladi.

## ⚠️ Muhim eslatmalar

- Botni majburiy obuna kanaliga **admin** qilib qo'shishni unutmang, aks holda a'zolikni tekshira olmaydi.
- `MemoryStorage` FSM uchun ishlatilgan — production muhitda ko'p yuk bo'lsa, `RedisStorage`ga o'tish tavsiya etiladi.
- Katta hajmdagi videolarni yuklashda serverning disk va RAM resurslarini nazorat qiling.
- `.env` faylini hech qachon ochiq repository'ga yubormang.

## 📜 Litsenziya

Ushbu kod ta'lim va shaxsiy loyihalar uchun taqdim etilgan. Video/audio kontentni yuklab olishda
mualliflik huquqi qonunlariga va tegishli platformalarning foydalanish shartlariga rioya qiling.
