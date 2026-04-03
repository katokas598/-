import os

SITE_HOST = "0.0.0.0"
SITE_PORT = 8000
SECRET_KEY = "discord-bot-dashboard-secret-key-change-in-production"

BOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot")
DB_PATH = os.path.join(BOT_DIR, "bot.db")
CONFIG_PATH = os.path.join(BOT_DIR, "config.json")
