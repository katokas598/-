import discord
from discord.ext import commands
import database
from config import PREFIX, GUILD_ID
from datetime import datetime, timedelta
import json
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Discord бот запущен: {bot.user}")
    print(f"📝 Префикс: {PREFIX}")

    database.init_db()
    print("✅ База данных инициализирована")

    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            bot.ticket_categories = config.get(
                "ticket_categories", ["Техподдержка", "Жалобы", "Предложения", "Другое"]
            )
            bot.guild_id = config.get("guild_id", "")
    else:
        bot.ticket_categories = ["Техподдержка", "Жалобы", "Предложения", "Другое"]
        bot.guild_id = ""


@bot.event
async def on_member_join(member):
    welcome_config = database.get_welcome_config()
    if welcome_config and welcome_config[3]:
        channel_id = welcome_config[1]
        message_template = welcome_config[2]
        if channel_id:
            channel = member.guild.get_channel(int(channel_id))
            if channel:
                message = message_template.replace("{user}", member.mention)
                message = message.replace("{username}", member.name)
                message = message.replace("{server}", member.guild.name)
                message = message.replace(
                    "{member_count}", str(member.guild.member_count)
                )
                await channel.send(message)

    mute = database.get_mute(str(member.id))
    if mute:
        overwrites = discord.PermissionOverwrite(send_messages=False)
        for channel in member.guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                try:
                    await channel.set_permissions(member, overwrites=overwrites)
                except:
                    pass


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return

    cmd_prefix = PREFIX
    if message.content.startswith(cmd_prefix):
        await bot.process_commands(message)
        return

    cmd_trigger = message.content.split()[0] if message.content else ""
    custom_cmd = database.get_custom_command(cmd_trigger)
    if custom_cmd:
        await message.channel.send(custom_cmd[2])

    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Отсутствует обязательный аргумент: `{error.param.name}`")
    else:
        print(f"Error: {error}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    if member == ctx.author:
        await ctx.send("❌ Вы не можете забанить себя!")
        return
    if member.top_role >= ctx.author.top_role:
        await ctx.send("❌ Вы не можете забанить этого пользователя!")
        return

    await member.ban(reason=reason)
    database.add_mod_log(
        "ban", str(member.id), str(ctx.author.id), reason or "Не указано"
    )

    embed = discord.Embed(title="✅ Пользователь забанен", color=discord.Color.red())
    embed.add_field(name="Пользователь", value=member.mention)
    embed.add_field(name="Причина", value=reason or "Не указана")
    embed.add_field(name="Модератор", value=ctx.author.mention)
    await ctx.send(embed=embed)


@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав для бана!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Пользователь не найден!")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, member_id: int):
    try:
        user = await bot.fetch_user(member_id)
        await ctx.guild.unban(user)
        database.add_mod_log("unban", str(member_id), str(ctx.author.id))

        embed = discord.Embed(
            title="✅ Пользователь разбанен", color=discord.Color.green()
        )
        embed.add_field(name="Пользователь", value=f"<@{member_id}>")
        embed.add_field(name="Модератор", value=ctx.author.mention)
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("❌ Пользователь не найден в бане!")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    if member == ctx.author:
        await ctx.send("❌ Вы не можете кикнуть себя!")
        return
    if member.top_role >= ctx.author.top_role:
        await ctx.send("❌ Вы не можете кикнуть этого пользователя!")
        return

    await member.kick(reason=reason)
    database.add_mod_log(
        "kick", str(member.id), str(ctx.author.id), reason or "Не указано"
    )

    embed = discord.Embed(title="✅ Пользователь кикнут", color=discord.Color.orange())
    embed.add_field(name="Пользователь", value=member.mention)
    embed.add_field(name="Причина", value=reason or "Не указана")
    embed.add_field(name="Модератор", value=ctx.author.mention)
    await ctx.send(embed=embed)


@bot.command(name="mute")
async def mute(ctx, member: discord.Member, time: str = None, *, reason=None):
    if member == ctx.author:
        await ctx.send("❌ Вы не можете замутить себя!")
        return
    if member.top_role >= ctx.author.top_role:
        await ctx.send("❌ Вы не можете замутить этого пользователя!")
        return

    mute_duration = None
    if time:
        try:
            if time.endswith("m"):
                mute_duration = timedelta(minutes=int(time[:-1]))
            elif time.endswith("h"):
                mute_duration = timedelta(hours=int(time[:-1]))
            elif time.endswith("d"):
                mute_duration = timedelta(days=int(time[:-1]))
            else:
                mute_duration = timedelta(minutes=int(time))
        except ValueError:
            await ctx.send("❌ Неверный формат времени! Используйте: 10m, 1h, 1d")
            return

    overwrites = discord.PermissionOverwrite(send_messages=False)

    success = 0
    failed = 0
    failed_channels = []

    bot_member = ctx.guild.me

    for channel in ctx.guild.channels:
        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            perms = channel.permissions_for(bot_member)
            if perms.manage_permissions:
                try:
                    await channel.set_permissions(member, overwrites=overwrites)
                    success += 1
                except Exception as e:
                    failed += 1
                    print(f"Mute error on {channel.name}: {e}")
            else:
                failed += 1
                failed_channels.append(channel.name)

    if mute_duration:
        end_time = (datetime.now() + mute_duration).isoformat()
        database.add_mute(
            str(member.id), end_time, reason or "Не указано", str(ctx.author.id)
        )
    else:
        database.add_mute(
            str(member.id), "permanent", reason or "Не указано", str(ctx.author.id)
        )

    database.add_mod_log(
        "mute", str(member.id), str(ctx.author.id), reason or "Не указано"
    )

    duration_str = f"{time}" if time else "навсегда"
    embed = discord.Embed(title="✅ Пользователь замучен", color=discord.Color.orange())
    embed.add_field(name="Пользователь", value=member.mention)
    embed.add_field(name="Длительность", value=duration_str)
    embed.add_field(name="Причина", value=reason or "Не указана")
    embed.add_field(name="Модератор", value=ctx.author.mention)
    embed.add_field(name="Каналов", value=f"{success} успешно, {failed} ошибок")
    await ctx.send(embed=embed)


@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member):
    database.remove_mute(str(member.id))

    overwrites = discord.PermissionOverwrite(send_messages=None)

    success = 0
    failed = 0

    bot_member = ctx.guild.me

    for channel in ctx.guild.channels:
        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
            perms = channel.permissions_for(bot_member)
            if perms.manage_permissions:
                try:
                    await channel.set_permissions(member, overwrites=overwrites)
                    success += 1
                except Exception as e:
                    failed += 1
                    print(f"Unmute error on {channel.name}: {e}")
            else:
                failed += 1

    database.add_mod_log("unmute", str(member.id), str(ctx.author.id))

    embed = discord.Embed(title="✅ Пользователь размучен", color=discord.Color.green())
    embed.add_field(name="Пользователь", value=member.mention)
    embed.add_field(name="Модератор", value=ctx.author.mention)
    embed.add_field(name="Каналов", value=f"{success} успешно, {failed} ошибок")
    await ctx.send(embed=embed)


@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    database.add_warn(str(member.id), reason or "Не указано", str(ctx.author.id))
    database.add_mod_log(
        "warn", str(member.id), str(ctx.author.id), reason or "Не указано"
    )

    warn_count = database.get_warns_count(str(member.id))

    max_warns = 3
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                max_warns = config.get("max_warns", 3)
    except:
        max_warns = 3

    if warn_count >= max_warns:
        await member.ban(reason=f"Автобан: {max_warns} предупреждения")
        database.add_mod_log(
            "auto_ban", str(member.id), "SYSTEM", f"{max_warns} предупреждений"
        )

        embed = discord.Embed(title="🔨 АВТОБАН!", color=discord.Color.red())
        embed.add_field(name="Пользователь", value=member.mention)
        embed.add_field(name="Причина", value=f"{max_warns} предупреждений")
        embed.add_field(name="Последнее предупреждение", value=reason or "Не указано")
    else:
        embed = discord.Embed(
            title="⚠️ Предупреждение выдано", color=discord.Color.yellow()
        )
        embed.add_field(name="Пользователь", value=member.mention)
        embed.add_field(name="Причина", value=reason or "Не указана")
        embed.add_field(name="Предупреждений", value=f"{warn_count}/{max_warns}")

    await ctx.send(embed=embed)


@bot.command(name="clearwarns")
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    count = database.clear_warns(str(member.id))
    database.add_mod_log("clear_warns", str(member.id), str(ctx.author.id))

    embed = discord.Embed(
        title="✅ Предупреждения очищены", color=discord.Color.green()
    )
    embed.add_field(name="Пользователь", value=member.mention)
    embed.add_field(name="Удалено", value=f"{count} предупреждений")
    await ctx.send(embed=embed)


@bot.command(name="warns")
@commands.has_permissions(kick_members=True)
async def warns(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    warns = database.get_warns(str(member.id))

    if not warns:
        embed = discord.Embed(
            title=f"Предупреждения {member.name}",
            description="Нет предупреждений!",
            color=discord.Color.green(),
        )
    else:
        embed = discord.Embed(
            title=f"Предупреждения {member.name}", color=discord.Color.yellow()
        )
        for w in warns:
            embed.add_field(
                name=f"Предупреждение #{w[0]}",
                value=f"Причина: {w[2]}\nМодератор: <@{w[3]}>\nДата: {w[4][:10]}",
            )

    await ctx.send(embed=embed)


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount < 1 or amount > 1000:
        await ctx.send("❌ Количество должно быть от 1 до 1000!")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    embed = discord.Embed(title="✅ Сообщения удалены", color=discord.Color.green())
    embed.add_field(name="Удалено", value=f"{len(deleted)} сообщений")
    embed.add_field(name="Канал", value=ctx.channel.mention)
    embed.add_field(name="Модератор", value=ctx.author.mention)
    await ctx.send(embed=embed, delete_after=5)


@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    embed = discord.Embed(title="🔒 Канал заблокирован", color=discord.Color.red())
    embed.add_field(name="Канал", value=ctx.channel.mention)
    embed.add_field(name="Модератор", value=ctx.author.mention)
    await ctx.send(embed=embed)


@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    embed = discord.Embed(title="🔓 Канал разблокирован", color=discord.Color.green())
    embed.add_field(name="Канал", value=ctx.channel.mention)
    embed.add_field(name="Модератор", value=ctx.author.mention)
    await ctx.send(embed=embed)


@bot.command(name="cmds")
async def help_command(ctx):
    embed = discord.Embed(title="📚 Список команд", color=discord.Color.blue())

    embed.add_field(
        name="Основные команды",
        value=f"""
{PREFIX}ping - Проверить бота
{PREFIX}serverinfo - Информация о сервере
{PREFIX}userinfo - Информация о пользователе
{PREFIX}invite - Приглашение на сервер
{PREFIX}ticket - Создать тикет
{PREFIX}cmds - Показать это сообщение
        """,
        inline=False,
    )

    embed.add_field(
        name="Модерация (администраторы)",
        value=f"""
{PREFIX}ban <@user> [причина] - Забанить пользователя
{PREFIX}unban <id> - Разбанить пользователя
{PREFIX}kick <@user> [причина] - Кикнуть пользователя
{PREFIX}mute <@user> [время] [причина] - Замутить пользователя
{PREFIX}unmute <@user> - Размутить пользователя
{PREFIX}warn <@user> [причина] - Выдать предупреждение
{PREFIX}warns <@user> - Показать предупреждения
{PREFIX}clearwarns <@user> - Очистить предупреждения
{PREFIX}clear <количество> - Очистить сообщения
{PREFIX}lock - Заблокировать канал
{PREFIX}unlock - Разблокировать канал
        """,
        inline=False,
    )

    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Задержка", value=f"{latency} мс")
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f"📊 Информация о сервере: {guild.name}", color=discord.Color.blue()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

    embed.add_field(name="ID", value=guild.id)
    embed.add_field(name="Участников", value=guild.member_count)
    embed.add_field(name="Каналов", value=len(guild.channels))
    embed.add_field(name="Ролей", value=len(guild.roles))
    embed.add_field(name="Создан", value=guild.created_at.strftime("%d.%m.%Y"))

    await ctx.send(embed=embed)


@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    roles = [role.mention for role in member.roles[1:]]
    roles_str = ", ".join(roles) if roles else "Нет"

    embed = discord.Embed(
        title=f"👤 Информация о пользователе: {member.name}", color=member.color
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)

    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Никнейм", value=member.display_name)
    embed.add_field(name="Роли", value=roles_str)
    embed.add_field(
        name="Присоединился",
        value=member.joined_at.strftime("%d.%m.%Y")
        if member.joined_at
        else "Неизвестно",
    )
    embed.add_field(name="Создал аккаунт", value=member.created_at.strftime("%d.%m.%Y"))

    await ctx.send(embed=embed)


@bot.command(name="invite")
async def invite(ctx):
    invite_link = await ctx.channel.create_invite(max_age=86400, max_uses=100)
    embed = discord.Embed(title="🔗 Приглашение на сервер", color=discord.Color.green())
    embed.add_field(name="Ссылка", value=invite_link)
    await ctx.send(embed=embed)


@bot.command(name="ticket")
async def ticket_command(ctx, category: str = None):
    await ctx.message.delete()

    categories = getattr(
        bot, "ticket_categories", ["Техподдержка", "Жалобы", "Предложения", "Другое"]
    )

    if category and category not in categories:
        await ctx.send(
            f"❌ Неизвестная категория. Доступные: {', '.join(categories)}",
            delete_after=10,
        )
        return

    guild = ctx.guild
    category_obj = discord.utils.get(guild.categories, name="🎫 Тикеты")

    if not category_obj:
        category_obj = await guild.create_category("🎫 Тикеты")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            ticket_roles = config.get("ticket_roles", [])
            for role_id in ticket_roles:
                role = guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True
                    )

    channel_name = f"ticket-{ctx.author.name.lower()}-{ctx.author.id}"
    existing = discord.utils.get(guild.channels, name=channel_name)

    if existing:
        await ctx.send("❌ У вас уже есть открытый тикет!", delete_after=10)
        return

    channel = await guild.create_text_channel(
        channel_name, category=category_obj, overwrites=overwrites
    )

    ticket_category = category or "Другое"
    ticket_id = database.create_ticket(
        str(ctx.author.id), str(channel.id), ticket_category
    )

    embed = discord.Embed(
        title=f"🎫 Тикет #{ticket_id}",
        description=f"Категория: **{ticket_category}**\n\nОпишите вашу проблему. Модератор скоро ответит.",
        color=discord.Color.blue(),
    )
    embed.set_footer(text=f"Пользователь: {ctx.author}")

    await channel.send(embed=embed)

    await ctx.send(f"✅ Тикет создан: {channel.mention}", delete_after=10)


@bot.command(name="closeticket")
@commands.has_permissions(manage_channels=True)
async def closeticket(ctx):
    ticket = database.get_ticket_by_channel(str(ctx.channel.id))

    if not ticket:
        await ctx.send("❌ Это не тикет канал!")
        return

    await ctx.send("🔒 Тикет будет закрыт через 5 секунд...")
    await asyncio.sleep(5)

    database.close_ticket(str(ctx.channel.id))

    embed = discord.Embed(
        title="✅ Тикет закрыт",
        description="Спасибо за обращение!",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)

    await asyncio.sleep(3)
    await ctx.channel.delete()


@bot.command(name="addcommand")
async def addcommand(ctx, trigger: str, *, response: str):
    existing = database.get_custom_command(trigger)
    if existing:
        await ctx.send("❌ Такая команда уже существует!")
        return

    database.add_custom_command(trigger, response, str(ctx.author.id))
    await ctx.send(f"✅ Команда `{trigger}` создана!")


@bot.command(name="delcommand")
async def delcommand(ctx, trigger: str):
    existing = database.get_custom_command(trigger)
    if not existing:
        await ctx.send("❌ Команда не найдена!")
        return

    database.delete_custom_command(trigger)
    await ctx.send(f"✅ Команда `{trigger}` удалена!")


@bot.command(name="mycommands")
async def mycommands(ctx):
    commands = database.get_custom_commands()
    if not commands:
        await ctx.send("📝 Нет созданных команд.")
        return

    embed = discord.Embed(title="💬 Ваши команды", color=discord.Color.blue())
    for cmd in commands:
        embed.add_field(name=f"`{cmd[1]}`", value=cmd[2][:100], inline=False)

    await ctx.send(embed=embed)


async def run_bot(token):
    await bot.start(token)
