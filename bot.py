import os
import discord
from discord.ext import commands, tasks
import json
import datetime
import pytz

print("🚀 Запуск бота на Railway...")

# Проверка токена
token = os.environ.get('DISCORD_TOKEN')
if not token:
    print("❌ ТОКЕН НЕ НАЙДЕН!")
    exit(1)

print("✅ Токен найден")

# Настройки
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
DATA_FILE = 'data.json'

# Бот
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

AUTO_CHANNEL_ID = None

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {"reminders": [], "bonus_active": True}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_next_id():
    data = load_data()
    if not data["reminders"]:
        return 1
    return max(reminder["id"] for reminder in data["reminders"]) + 1

# Активность
@tasks.loop(minutes=5)
async def keep_alive():
    print(f"✅ Активность: {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}")

# Напоминания
@tasks.loop(minutes=1)
async def check_reminders():
    data = load_data()
    if not data["reminders"]:
        return
    
    current_time = datetime.datetime.now(MOSCOW_TZ).strftime("%H:%M")
    
    for reminder in data["reminders"]:
        if (reminder["time"] == current_time and 
            reminder["active"] and 
            datetime.datetime.now(MOSCOW_TZ).hour >= 8):
            
            try:
                user = await bot.fetch_user(reminder["user_id"])
                await user.send(f"⏰ Напоминание: {reminder['message']}")
                print(f"✅ Отправлено: {reminder['message']}")
            except:
                pass

# Бонусы
@tasks.loop(minutes=30)
async def bonus_reminder():
    data = load_data()
    if data.get("bonus_active", True) and datetime.datetime.now(MOSCOW_TZ).hour >= 8:
        user_ids = set(reminder["user_id"] for reminder in data["reminders"])
        for user_id in user_ids:
            try:
                user = await bot.fetch_user(user_id)
                await user.send("🎯 Заберите бонус!")
            except:
                pass

# Авто-сообщения
@tasks.loop(minutes=10)
async def discord_ping():
    global AUTO_CHANNEL_ID
    if AUTO_CHANNEL_ID:
        try:
            channel = bot.get_channel(AUTO_CHANNEL_ID)
            if channel:
                current_time = datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')
                await channel.send(f"💚 Railway активен | {current_time}")
        except:
            pass

@bot.event
async def on_ready():
    print(f'🎉 Бот {bot.user} запущен на Railway!')
    
    # Запускаем задачи
    tasks_to_start = [keep_alive, check_reminders, bonus_reminder, discord_ping]
    for task in tasks_to_start:
        if not task.is_running():
            task.start()
    
    print("💡 Бот работает 24/7!")

# Команды
@bot.command()
async def готово(ctx):
    data = load_data()
    data["bonus_active"] = False
    save_data(data)
    await ctx.send("✅ Бонусы остановлены до завтра!")

@bot.command()
async def включить(ctx):
    data = load_data()
    data["bonus_active"] = True
    save_data(data)
    await ctx.send("✅ Бонусы ВКЛЮЧЕНЫ!")

@bot.command()
async def добавить(ctx, время: str, *, текст: str):
    try:
        hours, minutes = время.split(":")
        hours, minutes = int(hours), int(minutes)
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            data = load_data()
            new_id = get_next_id()
            data["reminders"].append({
                "id": new_id, "time": f"{hours:02d}:{minutes:02d}", 
                "message": текст, "active": True, "user_id": ctx.author.id
            })
            save_data(data)
            await ctx.send(f"✅ Напоминание добавлено! ID: {new_id}")
    except:
        await ctx.send("❌ Ошибка! Используйте: !добавить 14:30 Текст")

@bot.command()
async def список(ctx):
    data = load_data()
    user_reminders = [r for r in data["reminders"] if r["user_id"] == ctx.author.id]
    if user_reminders:
        embed = discord.Embed(title="📋 Ваши напоминания", color=0x00ff00)
        for reminder in user_reminders:
            embed.add_field(name=f"⏰ {reminder['time']}", value=reminder['message'], inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("📭 У вас нет напоминаний")

@bot.command()
async def автоканал(ctx):
    global AUTO_CHANNEL_ID
    AUTO_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Авто-сообщения включены!")

@bot.command()
async def тест(ctx):
    await ctx.send("✅ Бот работает на Railway 24/7!")

print("🔧 Запуск бота...")
bot.run(token)
