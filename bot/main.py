import asyncio
import json
import os
import sys


def check_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    if not os.path.exists(config_path):
        print("\n" + "=" * 50)
        print("   ПЕРВЫЙ ЗАПУСК - НАСТРОЙКА БОТА")
        print("=" * 50 + "\n")
        print("📝 Запустите: python setup.py")
        print("\nДля настройки конфигурации.")
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required = ["discord_token", "telegram_token"]
    missing = [key for key in required if not config.get(key)]

    if missing:
        print(f"\n❌ Отсутствуют настройки: {', '.join(missing)}")
        print("📝 Запустите: python setup.py")
        return False

    return True


async def run_discord():
    from discord_bot.bot import run_bot
    from config import DISCORD_TOKEN

    print("🚀 Запуск Discord бота...")
    await run_bot(DISCORD_TOKEN)


async def run_telegram():
    from telegram_bot.bot import run_bot

    print("🚀 Запуск Telegram бота...")
    await run_bot()


async def main():
    if not check_config():
        return

    import database

    database.init_db()

    print("\n" + "=" * 50)
    print("   DISCORDSER BOT ЗАПУЩЕН")
    print("=" * 50 + "\n")

    await asyncio.gather(run_discord(), run_telegram())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
