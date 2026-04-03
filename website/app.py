import os
import sys
import json
import sqlite3
import secrets
import subprocess
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import bcrypt
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOT_DIR = PROJECT_ROOT / "bot"
sys.path.insert(0, str(BOT_DIR))

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BOT_DIR / "bot.db"

app = FastAPI(title="Discord Bot Dashboard")

app.mount(
    str(BASE_DIR / "static"),
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SECRET_KEY = secrets.token_hex(32)

BOT_PROCESS = None


def init_database():
    try:
        import database as db_module

        db_module.init_db()
    except Exception as e:
        print(f"Database init error: {e}")


init_database()


def get_db():
    if not DB_PATH.exists():
        init_database()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_config():
    config_path = BOT_DIR / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    config_path = BOT_DIR / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


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


async def discord_api_request(method, endpoint, data=None):
    config = get_config()
    token = config.get("discord_token")
    guild_id = config.get("guild_id")

    if not token or not guild_id:
        return None

    url = f"https://discord.com/api/v10{endpoint}"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)

            if response.status_code in [200, 201, 204]:
                return response.json() if response.text else {}
            return {"error": response.text, "status": response.status_code}
    except Exception as e:
        return {"error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if not request.state.user:
        return templates.TemplateResponse("login.html", {"request": request})
    return RedirectResponse("/dashboard")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.state.user:
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

    cursor.execute("SELECT COUNT(*) FROM mod_logs")
    mod_logs_count = cursor.fetchone()[0]

    conn.close()

    stats = {
        "members": guild_data.get("approximate_member_count", 0) if guild_data else 0,
        "channels": len(guild_data.get("channels", [])) if guild_data else 0,
        "roles": len(guild_data.get("roles", [])) if guild_data else 0,
        "open_tickets": open_tickets,
        "custom_commands": custom_commands,
        "total_warns": total_warns,
        "mod_logs": mod_logs_count,
        "server_name": guild_data.get("name", "Unknown") if guild_data else "Unknown",
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "stats": stats,
            "prefix": config.get("prefix", "!"),
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
    response_text = form_data.get("response")

    if not trigger or not response_text:
        raise HTTPException(status_code=400, detail="Missing data")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO custom_commands (trigger, response, created_by) VALUES (?, ?, ?)",
        (trigger, response_text, user),
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

    save_config(config)

    return RedirectResponse("/settings", status_code=302)


@app.get("/moderation", response_class=HTMLResponse)
async def moderation_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "moderation.html", {"request": request, "user": user}
    )


@app.post("/api/ban")
async def api_ban(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    form_data = await request.form()
    user_id = form_data.get("user_id")
    reason = form_data.get("reason", "Не указана")

    if not user_id:
        return JSONResponse({"success": False, "error": "User ID обязателен"})

    result = await discord_api_request(
        "POST",
        f"/guilds/{get_config().get('guild_id')}/bans/{user_id}",
        {"reason": reason},
    )

    if "error" in result:
        return JSONResponse({"success": False, "error": result.get("error", "Ошибка")})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mod_logs (action, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        ("ban", user_id, user, reason, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "message": f"Пользователь {user_id} забанен"})


@app.post("/api/kick")
async def api_kick(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    form_data = await request.form()
    user_id = form_data.get("user_id")
    reason = form_data.get("reason", "Не указана")

    if not user_id:
        return JSONResponse({"success": False, "error": "User ID обязателен"})

    result = await discord_api_request(
        "DELETE", f"/guilds/{get_config().get('guild_id')}/members/{user_id}"
    )

    if "error" in result:
        return JSONResponse({"success": False, "error": result.get("error", "Ошибка")})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mod_logs (action, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        ("kick", user_id, user, reason, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return JSONResponse({"success": True, "message": f"Пользователь {user_id} кикнут"})


@app.post("/api/warn")
async def api_warn(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    form_data = await request.form()
    user_id = form_data.get("user_id")
    reason = form_data.get("reason", "Не указана")

    if not user_id:
        return JSONResponse({"success": False, "error": "User ID обязателен"})

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO warns (user_id, reason, moderator_id, created_at) VALUES (?, ?, ?, ?)",
        (user_id, reason, user, datetime.now().isoformat()),
    )
    cursor.execute(
        "INSERT INTO mod_logs (action, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        ("warn", user_id, user, reason, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return JSONResponse(
        {"success": True, "message": f"Пользователю {user_id} выдано предупреждение"}
    )


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mod_logs ORDER BY id DESC LIMIT 100")
    logs = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "logs.html", {"request": request, "user": user, "logs": logs}
    )


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/login")

    guild_data = await get_discord_guild()
    members = []

    if guild_data:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://discord.com/api/v10/guilds/{get_config().get('guild_id')}/members?limit=1000",
                    headers={
                        "Authorization": f"Bot {get_config().get('discord_token')}"
                    },
                )
                if response.status_code == 200:
                    members = response.json()
        except:
            pass

    return templates.TemplateResponse(
        "users.html", {"request": request, "user": user, "members": members}
    )


@app.get("/api/stats")
async def api_stats(request: Request, user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

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

    return JSONResponse(
        {
            "members": guild_data.get("approximate_member_count", 0)
            if guild_data
            else 0,
            "channels": len(guild_data.get("channels", [])) if guild_data else 0,
            "roles": len(guild_data.get("roles", [])) if guild_data else 0,
            "open_tickets": open_tickets,
            "custom_commands": custom_commands,
            "total_warns": total_warns,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
