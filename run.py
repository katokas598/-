#!/usr/bin/env python3
"""
Discord Bot with Web Dashboard
================================
Автозапуск с виртуальным окружением
"""

import os
import sys
import json
import subprocess
import platform
import time
import signal


def get_venv_python():
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "python")
    return os.path.join("venv", "bin", "python")


def get_venv_pip():
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "pip")
    return os.path.join("venv", "bin", "pip")


def check_venv():
    return os.path.exists("venv") and os.path.exists(get_venv_python())


def install_deps():
    if not check_venv():
        print("\n🟢 Создаю виртуальное окружение...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("   ✅ Виртуальное окружение создано!")
        except:
            print("   ❌ Ошибка создания venv")
            return False

    print("\n📦 Установка зависимостей...")
    try:
        pip = get_venv_pip()
        subprocess.run([pip, "install", "-r", "requirements.txt"], check=True)
        print("   ✅ Зависимости установлены!")
        return True
    except:
        print("   ⚠️ Зависимости уже установлены или ошибка")
        return True


def get_config():
    try:
        with open("bot/config.json", "r") as f:
            return json.load(f)
    except:
        return {"domain": "localhost", "port": "8000"}


def run_bot():
    python = get_venv_python()

    print("\n🎮 Запуск Discord бота...")

    if platform.system() == "Windows":
        process = subprocess.Popen(
            [python, "bot/main.py"], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        process = subprocess.Popen(
            [python, "bot/main.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return process


def run_website():
    python = get_venv_python()

    print("\n🌐 Запуск веб-сайта...")

    if platform.system() == "Windows":
        process = subprocess.Popen(
            [
                python,
                "-m",
                "uvicorn",
                "website.app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=os.getcwd(),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = subprocess.Popen(
            [
                python,
                "-m",
                "uvicorn",
                "website.app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return process


def main():
    print("\n" + "=" * 60)
    print("   🚀 ЗАПУСК DISCORD BOT + WEB PANEL")
    print("=" * 60)

    # Проверка и установка зависимостей
    if not install_deps():
        print("\n❌ Не удалось установить зависимости")
        return

    # Загрузка конфига
    config = get_config()
    domain = config.get("domain", "localhost")
    port = config.get("port", "8000")

    # Запуск процессов
    bot_process = run_bot()
    time.sleep(2)
    website_process = run_website()

    print("\n" + "=" * 60)
    print("✅ ВСЁ ЗАПУЩЕНО!")
    print("=" * 60)
    print(f"\n🌐 Откройте в браузере:")
    print(f"   http://{domain}:{port}")
    print(f"\n🔐 Логин и пароль указаны при настройке")
    print("=" * 60)
    print("\nДля остановки нажмите Ctrl+C")
    print("=" * 60)

    try:
        # Ожидание с обработкой Ctrl+C
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")

        # Остановка процессов
        if platform.system() == "Windows":
            bot_process.terminate()
            website_process.terminate()
        else:
            bot_process.terminate()
            website_process.terminate()

        print("✅ Остановлено!")


if __name__ == "__main__":
    main()
