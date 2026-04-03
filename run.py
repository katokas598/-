"""
Discord Bot with Web Dashboard
==============================
Автор: Discord Bot Developer
Версия: 1.0.0

Запуск:
    python setup.py           - Настройка бота и сайта
    python run.py            - Запуск всего (бот + сайт)

или отдельно:
    python bot/main.py       - Запуск только бота
    cd website && python -m uvicorn app:app --host 0.0.0.0 --port 8000
"""

import os
import sys


def main():
    print("\n" + "=" * 60)
    print("   DISCORDSER BOT + WEB DASHBOARD")
    print("=" * 60)
    print("\nВыберите действие:")
    print("1. 🚀 Настроить бота и сайт")
    print("2. ▶️  Запустить всё")
    print("3. 🎮 Запустить только бота")
    print("4. 🌐 Запустить только сайт")
    print("5. ❌ Выход")

    choice = input("\n>> ").strip()

    if choice == "1":
        os.system("python setup.py")
    elif choice == "2":
        print("\n🚀 Запуск бота и сайта...")
        print("=" * 60)
        print("📝 Сайт будет доступен по адресу: http://localhost:8000")
        print("=" * 60 + "\n")

        import threading
        import subprocess

        def run_bot():
            os.chdir("bot")
            subprocess.run([sys.executable, "main.py"])

        def run_website():
            import time

            time.sleep(3)
            os.chdir("website")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8000",
                ]
            )

        bot_thread = threading.Thread(target=run_bot, daemon=True)
        site_thread = threading.Thread(target=run_website, daemon=True)

        bot_thread.start()
        site_thread.start()

        try:
            bot_thread.join()
        except KeyboardInterrupt:
            print("\n🛑 Остановка...")

    elif choice == "3":
        print("\n🎮 Запуск бота...")
        os.chdir("bot")
        os.system("python main.py")

    elif choice == "4":
        print("\n🌐 Запуск сайта...")
        print("📝 Сайт будет доступен по адресу: http://localhost:8000")
        os.chdir("website")
        os.system("python -m uvicorn app:app --host 0.0.0.0 --port 8000")

    else:
        print("\n👋 До свидания!")


if __name__ == "__main__":
    main()
