"""
Majburiy obuna middleware'i.

Har bir foydalanuvchi botdan foydalanishdan oldin, admin tomonidan belgilangan
barcha kanallarga a'zo bo'lganini tekshiradi. Agar biror kanalga a'zo bo'lmasa,
foydalanuvchiga obuna bo'lish tugmalari va "✅ Tekshirish" tugmasi bilan xabar yuboriladi.

Eslatma: Admin buyruqlari (/admin) va admin foydalanuvchilar bu tekshiruvdan ozod qilinadi,
aks holda admin o'zi ham botdan foydalana olmay qolishi mumkin.
"""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from database.models import db

logger = logging.getLogger(__name__)


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy obunani tekshiruvchi middleware klassi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Faqat shaxsiy (private) chatlardagi Message va CallbackQuery uchun tekshiramiz
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        # Adminlar majburiy obunadan ozod qilinadi
        if await db.is_admin(user.id):
            return await handler(event, data)

        channels = await db.get_all_channels()
        if not channels:
            # Hech qanday majburiy kanal sozlanmagan bo'lsa, tekshiruvsiz o'tkazamiz
            return await handler(event, data)

        bot = data["bot"]
        not_subscribed = []

        for channel in channels:
            chat_id = channel["chat_id"]
            try:
                member = await bot.get_chat_member(chat_id=chat_id, user_id=user.id)
                if member.status in ("left", "kicked"):
                    not_subscribed.append(channel)
            except TelegramBadRequest as e:
                # Bot kanalda admin bo'lmasa yoki kanal ID xato bo'lsa shu yerga tushadi
                logger.warning(f"Kanal tekshirishda xatolik ({chat_id}): {e}")
                continue

        if not_subscribed:
            keyboard_buttons = []
            for channel in not_subscribed:
                link = channel["invite_link"] or f"https://t.me/{str(channel['chat_id']).lstrip('@')}"
                keyboard_buttons.append(
                    [InlineKeyboardButton(text=f"📢 {channel['title']}", url=link)]
                )
            keyboard_buttons.append(
                [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")]
            )
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

            text = (
                "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>\n\n"
                "A'zo bo'lgach, \"✅ Tekshirish\" tugmasini bosing."
            )

            if isinstance(event, Message):
                await event.answer(text, reply_markup=markup)
            elif isinstance(event, CallbackQuery):
                await event.answer("Siz hali barcha kanallarga a'zo bo'lmagansiz!", show_alert=True)
                await event.message.answer(text, reply_markup=markup)
            return  # Handlerga uzatilmaydi - foydalanuvchi obuna bo'lishi kerak

        return await handler(event, data)
