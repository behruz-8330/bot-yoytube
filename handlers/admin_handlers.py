"""
Admin panel handlerlari.

/admin buyrug'i orqali quyidagi imkoniyatlar mavjud:
    - Statistika (foydalanuvchilar soni)
    - Adminlar ro'yxatini boshqarish (qo'shish/o'chirish)
    - VIP foydalanuvchilarni qo'shish/o'chirish
    - Majburiy obuna kanallarini sozlash (qo'shish/o'chirish)

FSM (Finite State Machine) - aiogram'ning holat boshqaruvi - foydalanuvchidan
ketma-ket ma'lumot so'rash uchun ishlatiladi (masalan, avval "kimni admin qilish
kerak?" so'raladi, keyin foydalanuvchi ID yuboradi).
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.models import db

logger = logging.getLogger(__name__)
router = Router(name="admin_handlers")


class IsAdminFilter(BaseFilter):
    """
    aiogram uchun maxsus (custom) asinxron filter.
    F.func bilan async funksiyalarni tekshirib bo'lmagani uchun BaseFilter'dan
    meros olib, o'z filterimizni yaratamiz - shu orqali handler faqat
    admin foydalanuvchilar uchun ishga tushadi.
    """

    async def __call__(self, message: Message) -> bool:
        return await db.is_admin(message.from_user.id)


# --- FSM holatlar ---
class AdminStates(StatesGroup):
    waiting_for_new_admin_id = State()
    waiting_for_remove_admin_id = State()
    waiting_for_vip_user_id = State()
    waiting_for_vip_days = State()
    waiting_for_remove_vip_id = State()
    waiting_for_channel_id = State()


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Asosiy admin panel klaviaturasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_manage_admins")],
            [InlineKeyboardButton(text="💎 VIP foydalanuvchilar", callback_data="admin_manage_vip")],
            [InlineKeyboardButton(text="📢 Majburiy obuna kanallari", callback_data="admin_manage_channels")],
        ]
    )


@router.message(Command("admin"), IsAdminFilter())
async def cmd_admin(message: Message) -> None:
    """/admin buyrug'i - faqat adminlar uchun ochiladigan panel."""
    await message.answer("🛠 <b>Admin panelga xush kelibsiz!</b>", reply_markup=get_admin_panel_keyboard())


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message) -> None:
    """Admin bo'lmagan foydalanuvchi /admin buyrug'ini yuborsa."""
    await message.answer("⛔ Sizda bu buyruqdan foydalanish huquqi yo'q.")


# ------------------- STATISTIKA -------------------

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery) -> None:
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    total_users = await db.count_users()
    admins = await db.get_all_admins()
    channels = await db.get_all_channels()

    text = (
        "📊 <b>Bot statistikasi:</b>\n\n"
        f"👤 Jami foydalanuvchilar: <b>{total_users}</b>\n"
        f"🛡 Qo'shimcha adminlar: <b>{len(admins)}</b>\n"
        f"📢 Majburiy obuna kanallari: <b>{len(channels)}</b>"
    )
    await callback.message.answer(text)
    await callback.answer()


# ------------------- ADMINLARNI BOSHQARISH -------------------

@router.callback_query(F.data == "admin_manage_admins")
async def callback_manage_admins(callback: CallbackQuery) -> None:
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    admins = await db.get_all_admins()
    admin_list = "\n".join([f"• <code>{admin_id}</code>" for admin_id in admins]) or "Hozircha qo'shimcha admin yo'q."

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin")],
            [InlineKeyboardButton(text="➖ Adminni o'chirish", callback_data="remove_admin")],
        ]
    )
    await callback.message.answer(f"🛡 <b>Adminlar ro'yxati:</b>\n\n{admin_list}", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "add_admin")
async def callback_add_admin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("🆔 Yangi adminning Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_new_admin_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_new_admin_id)
async def process_add_admin(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID yuboring.")
        return

    new_admin_id = int(message.text.strip())
    await db.add_admin(new_admin_id, added_by=message.from_user.id)
    await message.answer(f"✅ Foydalanuvchi <code>{new_admin_id}</code> admin etib tayinlandi.")
    await state.clear()


@router.callback_query(F.data == "remove_admin")
async def callback_remove_admin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("🆔 O'chiriladigan adminning Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_remove_admin_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_remove_admin_id)
async def process_remove_admin(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID yuboring.")
        return

    admin_id = int(message.text.strip())
    await db.remove_admin(admin_id)
    await message.answer(f"✅ Foydalanuvchi <code>{admin_id}</code> adminlikdan olib tashlandi.")
    await state.clear()


# ------------------- VIP BOSHQARUVI -------------------

@router.callback_query(F.data == "admin_manage_vip")
async def callback_manage_vip(callback: CallbackQuery) -> None:
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ VIP qo'shish", callback_data="add_vip")],
            [InlineKeyboardButton(text="➖ VIP o'chirish", callback_data="remove_vip")],
        ]
    )
    await callback.message.answer("💎 <b>VIP foydalanuvchilarni boshqarish:</b>", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "add_vip")
async def callback_add_vip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("🆔 VIP qilinadigan foydalanuvchining Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_vip_user_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_vip_user_id)
async def process_vip_user_id(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID yuboring.")
        return

    await state.update_data(vip_user_id=int(message.text.strip()))
    await message.answer("📅 Necha kunlik VIP berilsin? (masalan: 30)")
    await state.set_state(AdminStates.waiting_for_vip_days)


@router.message(AdminStates.waiting_for_vip_days)
async def process_vip_days(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, faqat kunlar sonini (raqam) yuboring.")
        return

    data = await state.get_data()
    user_id = data["vip_user_id"]
    days = int(message.text.strip())

    await db.set_vip(user_id, days)
    await message.answer(f"✅ Foydalanuvchi <code>{user_id}</code> ga <b>{days} kunlik</b> VIP berildi.")
    await state.clear()


@router.callback_query(F.data == "remove_vip")
async def callback_remove_vip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("🆔 VIP dan mahrum qilinadigan foydalanuvchi ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_remove_vip_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_remove_vip_id)
async def process_remove_vip(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID yuboring.")
        return

    user_id = int(message.text.strip())
    await db.remove_vip(user_id)
    await message.answer(f"✅ Foydalanuvchi <code>{user_id}</code> dan VIP status olib tashlandi.")
    await state.clear()


# ------------------- KANALLARNI BOSHQARISH -------------------

@router.callback_query(F.data == "admin_manage_channels")
async def callback_manage_channels(callback: CallbackQuery) -> None:
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    channels = await db.get_all_channels()
    channel_list = "\n".join([f"• {ch['title']} (<code>{ch['chat_id']}</code>)" for ch in channels]) or "Hozircha kanal yo'q."

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")],
            [InlineKeyboardButton(text="➖ Kanalni o'chirish", callback_data="remove_channel")],
        ]
    )
    await callback.message.answer(f"📢 <b>Majburiy obuna kanallari:</b>\n\n{channel_list}", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    text = (
        "📢 Kanal username yoki ID raqamini yuboring.\n\n"
        "<b>Muhim:</b> Bot o'sha kanalda <u>admin</u> bo'lishi shart!\n"
        "Format: <code>@kanal_username</code> yoki <code>-1001234567890</code>"
    )
    await callback.message.answer(text)
    await state.set_state(AdminStates.waiting_for_channel_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_channel_id)
async def process_add_channel(message: Message, state: FSMContext) -> None:
    chat_id_input = message.text.strip()

    try:
        # Kanal haqida ma'lumot olish orqali bot admin ekanligini ham tekshiramiz
        chat = await message.bot.get_chat(chat_id_input)
        invite_link = chat.invite_link

        if not invite_link and chat.username:
            invite_link = f"https://t.me/{chat.username}"

        await db.add_channel(chat_id=str(chat.id), title=chat.title or chat.username, invite_link=invite_link)
        await message.answer(f"✅ Kanal <b>{chat.title}</b> majburiy obuna ro'yxatiga qo'shildi.")

    except Exception as e:
        logger.warning(f"Kanal qo'shishda xatolik: {e}")
        await message.answer(
            "❌ Kanal topilmadi yoki bot u yerda admin emas. "
            "Iltimos, botni kanalga admin qilib qo'shib, qaytadan urinib ko'ring."
        )

    await state.clear()


@router.callback_query(F.data == "remove_channel")
async def callback_remove_channel_list(callback: CallbackQuery) -> None:
    """O'chirish uchun mavjud kanallarni tugmalar shaklida ko'rsatadi."""
    channels = await db.get_all_channels()
    if not channels:
        await callback.answer("Hozircha kanal yo'q.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(text=f"❌ {ch['title']}", callback_data=f"delch_{ch['chat_id']}")]
        for ch in channels
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("delch_"))
async def callback_remove_channel_confirm(callback: CallbackQuery) -> None:
    """Tanlangan kanalni majburiy obuna ro'yxatidan o'chiradi."""
    chat_id = callback.data.removeprefix("delch_")
    await db.remove_channel(chat_id)
    await callback.message.edit_text(f"✅ Kanal ro'yxatdan o'chirildi.")
    await callback.answer()
