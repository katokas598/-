import os
import sys
import json
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import bcrypt
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))

app = FastAPI(title="Discord Bot Dashboard")

BASE_DIR = Path(__file__).resolve().parent
BOT_DIR = BASE_DIR.parent / "bot"
DB_PATH = BOT_DIR / "bot.db"

app.mount(
    str(BASE_DIR / "static"),
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SECRET_KEY = secrets.token_hex(32)


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_config():
    config_path = BOT_DIR / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def verify_user(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM web_users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.verify(password, user["password_hash"]):
        return True
    return False


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_token = request.cookies.get("session_token")
    request.state.user = None

    if session_token:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username FROM web_users WHERE session_token = ?", (session_token,)
        )
        user = cursor.fetchone()
        conn.close()
        if user:
            request.state.user = user["username"]

    response = await call_next(request)
    return response


def get_current_user(request: Request):
    return request.state.user


async def get_discord_guild():
    config = get_config()
    guild_id = config.get("guild_id")
    if not guild_id:
        return None

    token = config.get("discord_token")
    if not token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://discord.com/api/v10/guilds/{guild_id}",
                headers={"Authorization": f"Bot {token}"},
            )
            if response.status_code == 200:
                return response.json()
    except:
        pass
    return None


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    username = request.state.user
    if not username:
        return templates.TemplateResponse("login.html", {"request": request})
    return RedirectResponse("/dashboard")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    username = request.state.user
    if username:
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/login")
async def api_login(request: Request, response: Response):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    config = get_config()
    web_login = config.get("web_login", "admin")
    web_password = config.get("web_password")

    if username == web_login and password == web_password:
        session_token = secrets.token_hex(32)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM web_users WHERE username = ?", (username,))
        if not cursor.fetchone():
            password_hash = bcrypt.hash(password)
            cursor.execute(
                "INSERT INTO web_users (username, password_hash, session_token) VALUES (?, ?, ?)",
                (username, password_hash, session_token),
            )
        else:
            cursor.execute(
                "UPDATE web_users SET session_token = ? WHERE username = ?",
                (session_token, username),
            )
        conn.commit()
        conn.close()

        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=86400 * 7,
            samesite="lax",
        )
        return response

    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Неверный логин или пароль"}
    )


@app.get("/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE web_users SET session_token = NULL WHERE session_token = ?",
            (session_token,),
        )
        conn.commit()
        conn.close()

    response = RedirectResponse("/login")
    response.delete_cookie("session_token")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    config = get_config()

    guild_data = await get_discord_guild()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
    open_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM custom_commands")
    custom_commands = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM warns")
    total_warns = cursor.fetchone()[0]

    conn.close()

    stats = {
        "members": guild_data.get("approximate_member_count", 0) if guild_data else 0,
        "channels": len(guild_data.get("channels", [])) if guild_data else 0,
        "roles": len(guild_data.get("roles", [])) if guild_data else 0,
        "open_tickets": open_tickets,
        "custom_commands": custom_commands,
        "total_warns": total_warns,
        "server_name": guild_data.get("name", "Unknown") if guild_data else "Unknown",
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "prefix": config.get("prefix", "!"),
            "guild_icon": guild_data.get("icon") if guild_data else None,
        },
    )


@app.get("/commands", response_class=HTMLResponse)
async def commands_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_commands ORDER BY id DESC")
    commands = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "commands.html", {"request": request, "user": user, "commands": commands}
    )


@app.post("/api/commands")
async def add_command(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    form_data = await request.form()
    trigger = form_data.get("trigger")
    response = form_data.get("response")

    if not trigger or not response:
        raise HTTPException(status_code=400, detail="Missing data")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO custom_commands (trigger, response, created_by) VALUES (?, ?, ?)",
        (trigger, response, user),
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/commands", status_code=302)


@app.get("/api/commands/{cmd_id}/delete")
async def delete_command(cmd_id: int, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_commands WHERE id = ?", (cmd_id,))
    conn.commit()
    conn.close()

    return RedirectResponse("/commands", status_code=302)


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM welcome_config WHERE id = 1")
    welcome = cursor.fetchone()
    conn.close()

    config = get_config()
    guild_data = await get_discord_guild()

    channels = []
    if guild_data:
        for ch in guild_data.get("channels", []):
            if ch.get("type") == 0:
                channels.append({"id": str(ch["id"]), "name": ch["name"]})

    welcome_data = {
        "enabled": welcome["enabled"] if welcome else 0,
        "channel_id": welcome["channel_id"] if welcome else "",
        "message": welcome["message"]
        if welcome
        else "Добро пожаловать, {user}! Добро пожаловать на сервер {server}!",
    }

    return templates.TemplateResponse(
        "welcome.html",
        {
            "request": request,
            "user": user,
            "welcome": welcome_data,
            "channels": channels,
        },
    )


@app.post("/api/welcome")
async def save_welcome(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    form_data = await request.form()
    channel_id = form_data.get("channel_id", "")
    message = form_data.get("message", "")
    enabled = 1 if form_data.get("enabled") else 0

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO welcome_config (id, channel_id, message, enabled) VALUES (1, ?, ?, ?)",
        (channel_id, message, enabled),
    )
    conn.commit()
    conn.close()

    return RedirectResponse("/welcome", status_code=302)


@app.get("/tickets", response_class=HTMLResponse)
async def tickets_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
    tickets = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "tickets.html", {"request": request, "user": user, "tickets": tickets}
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    config = get_config()

    return templates.TemplateResponse(
        "settings.html", {"request": request, "user": user, "config": config}
    )


@app.post("/api/settings")
async def save_settings(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    form_data = await request.form()
    prefix = form_data.get("prefix", "!")
    ticket_categories = form_data.get("ticket_categories", "")
    max_warns = form_data.get("max_warns", "3")

    config = get_config()
    config["prefix"] = prefix
    config["ticket_categories"] = [
        c.strip() for c in ticket_categories.split(",") if c.strip()
    ]
    config["max_warns"] = int(max_warns)

    config_path = BOT_DIR / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return RedirectResponse("/settings", status_code=302)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
