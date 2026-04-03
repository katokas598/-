import os
import sys
import json
import secrets
import string
import subprocess
import platform


def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def check_venv():
    return sys.prefix != sys.base_prefix


def create_venv():
    print("\n🟢 Создание виртуального окружения...")

    if os.path.exists("venv"):
        print("   Виртуальное окружение уже существует.")
        return True

    try:
        result = subprocess.run(
            [sys.executable, "-m", "venv", "venv"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("   ✅ Виртуальное окружение создано!")
            return True
        else:
            print(f"   ❌ Ошибка: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def install_requirements():
    print("\n📦 Установка зависимостей...")

    if platform.system() == "Windows":
        pip_path = "venv\\Scripts\\pip"
    else:
        pip_path = "venv/bin/pip"

    try:
        result = subprocess.run(
            f"{pip_path} install -r requirements.txt",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("   ✅ Зависимости установлены!")
            return True
        else:
            print(f"   ❌ Ошибка: {result.stderr[:500]}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def open_port(port):
    print(f"\n🌐 Открытие порта {port}...")

    if platform.system() == "Linux":
        try:
            subprocess.run(["sudo", "ufw", "allow", f"{port}/tcp"], capture_output=True)
            subprocess.run(["sudo", "ufw", "reload"], capture_output=True)
            print(f"   ✅ Порт {port} открыт!")
            return True
        except:
            print(f"   ⚠️ Не удалось открыть порт автоматически.")
            print(f"   💡 Выполните вручную: sudo ufw allow {port}/tcp")
            return False
    else:
        print(f"   ⚠️ Автоматическое открытие портов доступно только на Linux")
        return False


def setup():
    print("\n" + "=" * 60)
    print("   ⚡ НАСТРОЙКА DISCORD BOT + WEB PANEL")
    print("=" * 60)
    print(f"\n🔧 Система: {platform.system()}")
    print(f"🐍 Python: {sys.version.split()[0]}")

    config = {}

    # Выбор домена
    print("\n🌐 Настройки домена:")
    print("   1. zyc-discord.duckdns.org (рекомендуется)")
    print("   2. Другой домен")

    domain_choice = input("   Выберите (1-2): ").strip()

    if domain_choice == "1":
        config["domain"] = "zyc-discord.duckdns.org"
    else:
        config["domain"] = input("   Введите ваш домен: ").strip()

    # Порт
    print("\n🔌 Настройки порта:")
    port_input = input("   Порт (по умолчанию 8000): ").strip()
    config["port"] = port_input if port_input.isdigit() else "8000"

    # Discord токен
    print("\n🤖 Настройки Discord бота:")
    config["discord_token"] = input("   Токен Discord бота: ").strip()

    # Префикс
    print("\n⚙️ Настройки бота:")
    config["prefix"] = input("   Префикс команд (по умолчанию !): ").strip() or "!"

    # ID сервера
    config["guild_id"] = input("   ID Discord сервера: ").strip()

    # Категории тикетов
    print("\n🎫 Категории тикетов:")
    default_categories = "Техподдержка,Жалобы,Предложения,Другое"
    categories_input = input(f"   ({default_categories}): ").strip()
    config["ticket_categories"] = (
        [c.strip() for c in categories_input.split(",")]
        if categories_input
        else [c.strip() for c in default_categories.split(",")]
    )

    # Макс. предупреждений
    print("\n⚠️ Модерация:")
    max_warns = input("   Макс. предупреждений (по умолчанию 3): ").strip()
    config["max_warns"] = int(max_warns) if max_warns.isdigit() else 3

    # Логин/пароль сайта
    print("\n🔐 Настройки сайта:")
    web_login = input("   Логин для сайта (или Enter - будет сгенерирован): ").strip()
    web_password = input(
        "   Пароль для сайта (или Enter - будет сгенерирован): "
    ).strip()

    if not web_login:
        web_login = "admin"
    if not web_password:
        web_password = generate_password()

    config["web_login"] = web_login
    config["web_password"] = web_password

    # Сохранение конфига
    print("\n💾 Сохранение настроек...")

    os.chdir("bot")
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("   ✅ Настройки сохранены!")

    # Создание venv и установка зависимостей
    os.chdir("..")

    if not create_venv():
        print("\n❌ Не удалось создать виртуальное окружение.")
        print("   Попробуйте установить вручную:")
        print("   python3 -m pip install -r requirements.txt")

    install_requirements()

    # Открытие порта
    open_port(config["port"])

    # Запуск инициализации БД
    print("\n🗄️ Инициализация базы данных...")

    if platform.system() == "Windows":
        python_path = "venv\\Scripts\\python"
    else:
        python_path = "venv/bin/python"

    try:
        subprocess.run(
            f'{python_path} -c "import sys; sys.path.insert(0, \\"bot\\"); import database; database.init_db()"',
            shell=True,
            capture_output=True,
        )
        print("   ✅ База данных создана!")
    except:
        print("   ⚠️ База данных будет создана при первом запуске бота")

    # Итог
    print("\n" + "=" * 60)
    print("✅ НАСТРОЙКА ЗАВЕРШЕНА!")
    print("=" * 60)

    print("\n🔐 ДАННЫЕ ДЛЯ ВХОДА НА САЙТ:")
    print(f"   URL: http://{config['domain']}:{config['port']}")
    print(f"   Логин: {web_login}")
    print(f"   Пароль: {web_password}")
    print("=" * 60)

    print("\n📝 Для запуска используйте:")
    print(f"   python run.py")

    print("\n⚠️  Не забудьте добавить бота на сервер с правами:")
    print("   - Administrator")
    print("   - Manage Channels")
    print("   - Manage Roles")
    print("   - Ban Members")
    print("   - Kick Members")
    print("   - Manage Messages")


if __name__ == "__main__":
    setup()
