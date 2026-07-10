"""
Oddiy foydalanuvchilar uchun handlerlar:
    - /start buyrug'i (VIP sotib olish va Majburiy obuna tugmalari bilan)
    - "✅ Tekshirish" callback (majburiy obunani qayta tekshirish)
    - Shaxsiy chatda yuborilgan havolalardan video yuklab berish
"""

import logging
import re

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from config import BOT_USERNAME, VIP_PRICE_INFO, ADMIN_CONTACT, FREE_USER_DAILY_LIMIT
from database.models import db
from services.downloader import downloader
from utils.cleanup import remove_file

logger = logging.getLogger(__name__)
router = Router(name="user_handlers")

# Har qanday http(s) havolani aniqlash uchun regex
URL_PATTERN = re.compile(r"https?://[^\s]+")


def get_start_keyboard() -> InlineKeyboardMarkup:
    """/start uchun asosiy inline klaviatura: VIP sotib olish va Majburiy obuna."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 VIP sotib olish", callback_data="buy_vip")],
            [InlineKeyboardButton(text="📢 Majburiy obuna kanallari", callback_data="show_channels")],
            [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help_info")],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """/start buyrug'ini qayta ishlash - foydalanuvchini bazaga qo'shadi va menyu chiqaradi."""
    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    text = (
        f"👋 Assalomu alaykum, <b>{message.from_user.full_name}</b>!\n\n"
        "🎬 Men YouTube, Instagram, TikTok, Twitter/X kabi platformalardan "
        "video va audio yuklab beruvchi botman.\n\n"
        "📎 Menga havola yuboring - men video yoki audio faylni yuklab beraman.\n\n"
        f"🆓 Bepul foydalanuvchilar uchun kuniga <b>{FREE_USER_DAILY_LIMIT} ta</b> yuklash limiti bor.\n"
        "💎 VIP foydalanuvchilar uchun limit yo'q!"
    )
    await message.answer(text, reply_markup=get_start_keyboard())


@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery) -> None:
    """
    Majburiy obunani "✅ Tekshirish" tugmasi orqali qayta tekshirish.
    Middleware bu callbackni ushlab qoladi - agar shu yergacha yetib kelsa,
    demak foydalanuvchi allaqachon barcha kanallarga a'zo bo'lgan.
    """
    await callback.answer("✅ Rahmat! Endi botdan bemalol foydalanishingiz mumkin.", show_alert=True)
    await callback.message.delete()


@router.callback_query(F.data == "buy_vip")
async def callback_buy_vip(callback: CallbackQuery) -> None:
    """VIP sotib olish haqida ma'lumot beradi."""
    text = (
        "💎 <b>VIP obuna afzalliklari:</b>\n\n"
        "✅ Cheksiz video/audio yuklash\n"
        "✅ Yuqori tezlikda ishlov berish\n"
        "✅ Navbatsiz xizmat ko'rsatish\n\n"
        f"💰 Narxi: <b>{VIP_PRICE_INFO}</b>\n\n"
        f"📞 Sotib olish uchun adminga murojaat qiling: {ADMIN_CONTACT}"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "show_channels")
async def callback_show_channels(callback: CallbackQuery) -> None:
    """Majburiy obuna kanallari ro'yxatini ko'rsatadi."""
    channels = await db.get_all_channels()
    if not channels:
        await callback.answer("Hozircha majburiy obuna kanallari yo'q.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"📢 {ch['title']}",
            url=ch["invite_link"] or f"https://t.me/{str(ch['chat_id']).lstrip('@')}",
        )]
        for ch in channels
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("📢 <b>Quyidagi kanallarga a'zo bo'ling:</b>", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "help_info")
async def callback_help(callback: CallbackQuery) -> None:
    """Yordam ma'lumotini ko'rsatadi."""
    text = (
        "ℹ️ <b>Botdan foydalanish bo'yicha ko'rsatma:</b>\n\n"
        "1️⃣ Video havolasini (YouTube, Instagram, TikTok, Twitter/X) yuboring.\n"
        "2️⃣ Bot avtomatik ravishda videoni yuklab, sizga yuboradi.\n"
        "3️⃣ Guruhlarda ham botni ishlatishingiz mumkin - shunchaki havolani tashlang.\n\n"
        f"❓ Savol bo'lsa: {ADMIN_CONTACT}"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(F.text.regexp(URL_PATTERN.pattern))
async def handle_link(message: Message) -> None:
    """
    Shaxsiy chatda yuborilgan havolani qayta ishlaydi:
    yt-dlp orqali yuklab oladi, foydalanuvchiga yuboradi va faylni serverdan o'chiradi.
    """
    url_match = URL_PATTERN.search(message.text)
    if not url_match:
        return
    url = url_match.group(0)

    user_id = message.from_user.id

    # Kunlik limitni tekshirish (VIP bo'lmaganlar uchun)
    if not await db.can_download(user_id):
        await message.answer(
            f"⚠️ Sizning bugungi bepul yuklash limitingiz ({FREE_USER_DAILY_LIMIT} ta) tugadi.\n"
            "💎 Cheksiz yuklash uchun VIP sotib oling: /start orqali \"VIP sotib olish\" tugmasini bosing."
        )
        return

    status_message = await message.answer("⏳ Video yuklanmoqda, biroz kuting...")

    result = await downloader.download(url)

    if not result.success:
        await status_message.edit_text(f"❌ Xatolik: {result.error}")
        return

    try:
        caption = f"🎬 {result.title}\n\n📥 @{BOT_USERNAME} orqali yuklab olindi"
        video_file = FSInputFile(result.file_path)

        if result.is_audio:
            await message.answer_audio(audio=video_file, caption=caption)
        else:
            await message.answer_video(video=video_file, caption=caption, supports_streaming=True)

        await db.increment_download_count(user_id)
        await status_message.delete()

    except Exception as e:
        logger.exception(f"Faylni yuborishda xatolik: {e}")
        await status_message.edit_text(
            "❌ Faylni yuborishda xatolik yuz berdi. Ehtimol fayl juda katta (Telegram limiti: 2GB)."
        )
    finally:
        # XOTIRA BOSHQARUVI: fayl yuborilgach yoki xatolik bo'lsa ham serverdan o'chiriladi
        remove_file(result.file_path)
