import os
import json
import secrets
import string


def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def setup():
    print("\n" + "=" * 50)
    print("   НАСТРОЙКА DISCORDSER BOT + WEBSITE")
    print("=" * 50 + "\n")

    config = {}

    print("📝 Введите данные для настройки:\n")

    print("1. Discord бот:")
    config["discord_token"] = input("   Токен Discord бота: ").strip()

    print("\n2. Telegram бот:")
    config["telegram_token"] = input("   Токен Telegram бота: ").strip()

    print("\n3. Настройки бота:")
    config["prefix"] = input("   Префикс команд (по умолчанию !): ").strip() or "!"

    print("\n4. Администраторы (через запятую, Telegram ID):")
    admins_input = input("   Telegram ID администраторов: ").strip()
    config["admin_ids"] = [
        int(x.strip()) for x in admins_input.split(",") if x.strip().isdigit()
    ]

    print("\n5. ID Discord сервера (для тикетов):")
    config["guild_id"] = input("   ID сервера: ").strip()

    print("\n6. Категории тикетов (через запятую):")
    default_categories = "Техподдержка,Жалобы,Предложения,Другое"
    categories_input = input(f"   ({default_categories}): ").strip()
    config["ticket_categories"] = (
        categories_input.split(",")
        if categories_input
        else default_categories.split(",")
    )

    config["ticket_categories"] = [c.strip() for c in config["ticket_categories"]]

    print("\n" + "-" * 50)
    print("7. Настройки сайта:")
    print("-" * 50)
    
    web_login = input("   Логин для сайта (или Enter - будет сгенерирован): ").strip()
    web_password = input("   Пароль для сайта (или Enter - будет сгенерирован): ").strip()
    
    if not web_login:
        web_login = "admin"
    if not web_password:
        web_password = generate_password()
    
    config["web_login"] = web_login
    config["web_password"] = web_password

    with open("config.json", "w", encoding="utf-8) as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("✅ Настройки сохранены в config.json")
    print("=" * 50)
    print("\n🔐 ДАННЫЕ ДЛЯ ВХОДА НА САЙТ:")
    print(f"   Логин: {web_login}")
    print(f"   Пароль: {web_password}")
    print("=" * 50)
    print("\n📝 Для запуска бота используйте: python main.py")
    print("📝 Для запуска сайта используйте: python -m uvicorn website.app:app --host 0.0.0.0 --port 8000")
    print("\n⚠️  Не забудьте добавить бота на сервер с нужными правами!")


if __name__ == "__main__":
    setup()
