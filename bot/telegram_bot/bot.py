from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import json
import os
import database
import sys

from config import TELEGRAM_TOKEN, ADMIN_IDS

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class ModerationState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_reason = State()
    waiting_for_time = State()


class SettingsState(StatesGroup):
    waiting_for_prefix = State()
    waiting_for_max_warns = State()
    waiting_for_ticket_roles = State()
    waiting_for_ticket_categories = State()


def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="🔨 Модерация", callback_data="moderation")],
            [InlineKeyboardButton(text="👥 Забаненные", callback_data="banned_list")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton(text="📝 Логи", callback_data="logs")],
            [InlineKeyboardButton(text="🗑️ Очистить логи", callback_data="clear_logs")],
        ]
    )


def get_moderation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔨 Забанить", callback_data="mod_ban")],
            [InlineKeyboardButton(text="🔓 Разбанить", callback_data="mod_unban")],
            [InlineKeyboardButton(text="👢 Кикнуть", callback_data="mod_kick")],
            [InlineKeyboardButton(text="🔇 Замутить", callback_data="mod_mute")],
            [InlineKeyboardButton(text="⚠️ Варн", callback_data="mod_warn")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")],
        ]
    )


def get_settings_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Префикс команд", callback_data="set_prefix"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Варнов до бана", callback_data="set_max_warns"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎫 Роли тикетов", callback_data="set_ticket_roles"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📂 Категории тикетов", callback_data="set_ticket_categories"
                )
            ],
            [InlineKeyboardButton(text="🔄 Перезагрузка", callback_data="restart_bot")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")],
        ]
    )


def get_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back")],
        ]
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этому боту!")
        return

    await message.answer(
        "👋 Панель управления ботом\n\nВыберите действие:",
        reply_markup=get_main_keyboard(),
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа!")
        return

    help_text = """
📚 Команды Telegram бота:

/start - Главное меню
/help - Список команд

📊 Статистика - Статистика модерации
🔨 Модерация - Управление пользователями
👥 Забаненные - Список банов
⚙️ Настройки - Настройка бота
📝 Логи - История модерации
"""
    await message.answer(help_text)


@dp.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа!", show_alert=True)
        return

    data = callback.data

    if data == "back":
        await state.clear()
        await callback.message.edit_text(
            "👋 Выберите действие:", reply_markup=get_main_keyboard()
        )

    elif data == "stats":
        await show_stats(callback)

    elif data == "moderation":
        await callback.message.edit_text(
            "🔨 Модерация Discord\n\nВыберите действие:",
            reply_markup=get_moderation_keyboard(),
        )

    elif data == "banned_list":
        await show_banned_list(callback)

    elif data == "settings":
        await callback.message.edit_text(
            "⚙️ Настройки бота\n\nВыберите:", reply_markup=get_settings_keyboard()
        )

    elif data == "logs":
        await show_logs(callback)

    elif data == "clear_logs":
        await clear_logs(callback)

    elif data == "confirm_clear":
        import sqlite3

        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "bot.db"))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mod_logs")
        cursor.execute("DELETE FROM warns")
        cursor.execute("DELETE FROM tickets")
        cursor.execute("DELETE FROM ticket_logs")
        conn.commit()
        conn.close()
        await callback.message.edit_text(
            "✅ Логи очищены!", reply_markup=get_main_keyboard()
        )

    elif data == "mod_ban":
        await state.set_state(ModerationState.waiting_for_user_id)
        await state.update_data(action="ban")
        await callback.message.edit_text(
            "🔨 Бан пользователя\n\nВведите ID пользователя:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "mod_unban":
        await state.set_state(ModerationState.waiting_for_user_id)
        await state.update_data(action="unban")
        await callback.message.edit_text(
            "🔓 Разбан пользователя\n\nВведите ID пользователя:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "mod_kick":
        await state.set_state(ModerationState.waiting_for_user_id)
        await state.update_data(action="kick")
        await callback.message.edit_text(
            "👢 Кик пользователя\n\nВведите ID пользователя:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "mod_mute":
        await state.set_state(ModerationState.waiting_for_user_id)
        await state.update_data(action="mute")
        await callback.message.edit_text(
            "🔇 Мут пользователя\n\nВведите ID пользователя:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "mod_warn":
        await state.set_state(ModerationState.waiting_for_user_id)
        await state.update_data(action="warn")
        await callback.message.edit_text(
            "⚠️ Варн пользователя\n\nВведите ID пользователя:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data.startswith("unban_"):
        user_id = data.replace("unban_", "")
        await unban_user(callback, user_id)

    elif data == "set_prefix":
        await state.set_state(SettingsState.waiting_for_prefix)
        await callback.message.edit_text(
            "📝 Изменение префикса\n\nВведите новый префикс:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "set_max_warns":
        await state.set_state(SettingsState.waiting_for_max_warns)
        await callback.message.edit_text(
            "⚠️ Варнов до бана\n\nВведите число (сейчас 3):",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "set_ticket_roles":
        await state.set_state(SettingsState.waiting_for_ticket_roles)
        await callback.message.edit_text(
            "🎫 Роли для тикетов\n\nВведите ID ролей через запятую:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "set_ticket_categories":
        await state.set_state(SettingsState.waiting_for_ticket_categories)
        await callback.message.edit_text(
            "📂 Категории тикетов\n\nВведите через запятую:",
            reply_markup=get_cancel_keyboard(),
        )

    elif data == "restart_bot":
        await callback.message.edit_text(
            "⚠️ Перезагрузка бота...", reply_markup=get_main_keyboard()
        )
        await asyncio.sleep(2)
        await callback.message.answer("🔄 Бот перезагружен!")

    await callback.answer()


@dp.message(ModerationState.waiting_for_user_id)
async def process_moderation_user_id(message: Message, state: FSMContext):
    user_id = message.text.strip()

    if not user_id.isdigit():
        await message.answer("❌ Введите корректный ID!")
        return

    await state.update_data(user_id=user_id)
    data = await state.get_data()
    action = data.get("action")

    if action in ["ban", "kick", "warn"]:
        await state.set_state(ModerationState.waiting_for_reason)
        await message.answer("Введите причину (или - если без причины):")
    elif action == "mute":
        await state.set_state(ModerationState.waiting_for_time)
        await message.answer("Введите время мута (10m, 1h, 1d):")
    else:
        await execute_moderation(message, state)


@dp.message(ModerationState.waiting_for_reason)
async def process_moderation_reason(message: Message, state: FSMContext):
    reason = message.text if message.text != "-" else "Не указана"
    await state.update_data(reason=reason)
    await execute_moderation(message, state)


@dp.message(ModerationState.waiting_for_time)
async def process_moderation_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    await state.update_data(time=time_str)
    await execute_moderation(message, state)


async def execute_moderation(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    action = data.get("action")
    reason = data.get("reason", "Не указана")
    time_str = data.get("time", "")

    result_text = ""
    debug_info = ""

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import discord_bot.bot as discord_module
        import json

        discord_bot_instance = discord_module.bot
        guild = None

        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            guild_id = config.get("guild_id", "")

        debug_info += f"Debug: guild_id={guild_id}\n"

        if guild_id:
            guild = discord_bot_instance.get_guild(int(guild_id))

        debug_info += f"Debug: guild found={guild is not None}\n"

        if not guild:
            await message.answer(
                f"❌ Сервер не найден!\n{debug_info}Проверьте config.json - поле guild_id",
                reply_markup=get_main_keyboard(),
            )
            await state.clear()
            return

        if action == "ban":
            try:
                user = await discord_bot_instance.fetch_user(int(user_id))
                await guild.ban(user, reason=reason)
                database.add_mod_log("ban", user_id, "TG_MODERATOR", reason)
                result_text = f"✅ Пользователь {user.name}#{user.discriminator} забанен!\nПричина: {reason}"
            except Exception as e:
                result_text = f"❌ Ошибка бана: {str(e)}\n\nПроверьте ID пользователя."

        elif action == "unban":
            try:
                user = await discord_bot_instance.fetch_user(int(user_id))
                await guild.unban(user)
                database.add_mod_log("unban", user_id, "TG_MODERATOR", "")
                result_text = "✅ Пользователь разбанен!"
            except Exception as e:
                result_text = f"❌ Ошибка разбана: {str(e)}\n\nВозможно пользователь не был забанен."

        elif action == "kick":
            try:
                member = guild.get_member(int(user_id))
                if member:
                    await member.kick(reason=reason)
                    database.add_mod_log("kick", user_id, "TG_MODERATOR", reason)
                    result_text = f"✅ Пользователь кикнут!\nПричина: {reason}"
                else:
                    result_text = "❌ Пользователь не найден на сервере!\nПроверьте ID."
            except Exception as e:
                result_text = f"❌ Ошибка кика: {str(e)}"

        elif action == "mute":
            try:
                member = guild.get_member(int(user_id))
                if member:
                    import discord

                    overwrites = discord.PermissionOverwrite(
                        send_messages=False
                    )

                    success = 0
                    failed = 0

                    bot_member = guild.me

                    for channel in guild.channels:
                        if isinstance(
                            channel, (discord.TextChannel, discord.VoiceChannel)
                        ):
                            perms = channel.permissions_for(bot_member)
                            if perms.manage_permissions:
                                try:
                                    await channel.set_permissions(
                                        member, overwrites=overwrites
                                    )
                                    success += 1
                                except Exception as e:
                                    failed += 1
                                    print(f"Mute error on {channel.name}: {e}")
                            else:
                                failed += 1

                    database.add_mute(
                        user_id, time_str or "permanent", reason, "TG_MODERATOR"
                    )
                    database.add_mod_log("mute", user_id, "TG_MODERATOR", reason)
                    result_text = f"✅ Пользователь замучен!\nКаналов: {success} успешно, {failed} ошибок\nПричина: {reason}"
                else:
                    result_text = "❌ Пользователь не найден на сервере!"
            except Exception as e:
                result_text = f"❌ Ошибка мута: {str(e)}"

        elif action == "warn":
            try:
                member = guild.get_member(int(user_id))
                if member:
                    database.add_warn(user_id, reason, "TG_MODERATOR")
                    database.add_mod_log("warn", user_id, "TG_MODERATOR", reason)
                    warn_count = database.get_warns_count(user_id)

                    max_warns = 3
                    try:
                        config_path = os.path.join(
                            os.path.dirname(__file__), "..", "config.json"
                        )
                        if os.path.exists(config_path):
                            with open(config_path, "r", encoding="utf-8") as cf:
                                cfg = json.load(cf)
                                max_warns = cfg.get("max_warns", 3)
                    except:
                        max_warns = 3

                    result_text = f"✅ Варн выдан!\nВсего: {warn_count}/{max_warns}\nПричина: {reason}"
                else:
                    result_text = "❌ Пользователь не найден на сервере!\nПроверьте ID."
            except Exception as e:
                result_text = f"❌ Ошибка варна: {str(e)}"

    except Exception as e:
        result_text = f"❌ Общая ошибка: {str(e)}\n\n{debug_info}"

    await message.answer(result_text, reply_markup=get_main_keyboard())
    await state.clear()


@dp.message(SettingsState.waiting_for_prefix)
async def process_prefix(message: Message, state: FSMContext):
    new_prefix = message.text.strip()

    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    config["prefix"] = new_prefix

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    await message.answer(
        f"✅ Префикс изменён на: {new_prefix}", reply_markup=get_main_keyboard()
    )
    await state.clear()


@dp.message(SettingsState.waiting_for_max_warns)
async def process_max_warns(message: Message, state: FSMContext):
    max_warns = message.text.strip()

    if not max_warns.isdigit():
        await message.answer("❌ Введите число!")
        return

    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    config["max_warns"] = int(max_warns)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    await message.answer(
        f"✅ Максимум варнов: {max_warns}", reply_markup=get_main_keyboard()
    )
    await state.clear()


@dp.message(SettingsState.waiting_for_ticket_roles)
async def process_ticket_roles(message: Message, state: FSMContext):
    roles = message.text.strip()

    try:
        role_ids = [int(x.strip()) for x in roles.replace(" ", "").split(",")]

        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["ticket_roles"] = role_ids

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        await message.answer(
            f"✅ Роли тикетов обновлены!", reply_markup=get_main_keyboard()
        )
    except:
        await message.answer("❌ Ошибка! Введите ID через запятую.")

    await state.clear()


@dp.message(SettingsState.waiting_for_ticket_categories)
async def process_ticket_categories(message: Message, state: FSMContext):
    categories = message.text.strip()

    try:
        categories_list = [c.strip() for c in categories.split(",")]

        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["ticket_categories"] = categories_list

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        await message.answer(
            f"✅ Категории обновлены!", reply_markup=get_main_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

    await state.clear()


async def unban_user(callback: CallbackQuery, user_id: str):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import discord_bot.bot as discord_module
        import json

        discord_bot_instance = discord_module.bot

        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            guild_id = config.get("guild_id", "")

        guild = None
        if guild_id:
            guild = discord_bot_instance.get_guild(int(guild_id))

        if guild:
            user = await discord_bot_instance.fetch_user(int(user_id))
            await guild.unban(user)
            database.add_mod_log("unban", user_id, "TG_MODERATOR", "")
            await callback.message.edit_text(
                f"✅ Пользователь разбанен!", reply_markup=get_main_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Сервер не найден!", reply_markup=get_main_keyboard()
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {e}", reply_markup=get_main_keyboard()
        )


async def show_stats(callback: CallbackQuery):
    logs = database.get_mod_logs(100)

    stats_text = "📊 Статистика:\n\n"

    ban_count = sum(1 for log in logs if log[1] == "ban")
    kick_count = sum(1 for log in logs if log[1] == "kick")
    mute_count = sum(1 for log in logs if log[1] == "mute")
    warn_count = sum(1 for log in logs if log[1] == "warn")

    stats_text += f"🔨 Банов: {ban_count}\n"
    stats_text += f"👢 Киков: {kick_count}\n"
    stats_text += f"🔇 Мутов: {mute_count}\n"
    stats_text += f"⚠️ Варнов: {warn_count}\n"

    await callback.message.edit_text(stats_text, reply_markup=get_main_keyboard())


async def show_banned_list(callback: CallbackQuery):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import discord_bot.bot as discord_module
        import json

        discord_bot_instance = discord_module.bot

        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            guild_id = config.get("guild_id", "")

        guild = None
        if guild_id:
            guild = discord_bot_instance.get_guild(int(guild_id))

        if not guild:
            await callback.message.edit_text(
                "❌ Сервер не найден!", reply_markup=get_main_keyboard()
            )
            return

        bans = []
        async for ban in guild.bans():
            bans.append(ban)

        if not bans:
            await callback.message.edit_text(
                "👥 Забаненных нет!", reply_markup=get_main_keyboard()
            )
            return

        keyboard = []
        for ban in bans[:10]:
            user = ban.user
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"❌ {user.name}", callback_data=f"unban_{user.id}"
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])

        await callback.message.edit_text(
            "👥 Список забаненных:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {e}", reply_markup=get_main_keyboard()
        )


async def show_logs(callback: CallbackQuery):
    logs = database.get_mod_logs(20)

    if not logs:
        await callback.message.edit_text(
            "📝 Логи пусты", reply_markup=get_main_keyboard()
        )
        return

    logs_text = "📝 Последние логи:\n\n"

    for log in logs:
        action = log[1]
        user_id = log[2]
        reason = log[4] or "-"

        logs_text += f"🔹 {action.upper()} | {user_id}\nПричина: {reason}\n\n"

    await callback.message.edit_text(logs_text, reply_markup=get_main_keyboard())


async def clear_logs(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗑️ Очистить все логи?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="confirm_clear")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="back")],
            ]
        ),
    )


async def run_bot():
    await dp.start_polling(bot)
