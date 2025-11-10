import os
import discord
from discord.ext import commands, tasks
import json
import datetime
import pytz

print("🚀 Запуск бота на Render...")

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

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"reminders": [], "bonus_active": True}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

@tasks.loop(minutes=5)
async def activity():
    print(f"✅ Активность: {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}")

@bot.event
async def on_ready():
    print(f'🎉 Бот {bot.user} запущен!')
    if not activity.is_running():
        activity.start()

@bot.command()
async def тест(ctx):
    await ctx.send("✅ Бот работает на Render!")

@bot.command()
async def добавить(ctx, время: str, *, текст: str):
    data = load_data()
    data["reminders"].append({
        "time": время, "text": текст, "user_id": ctx.author.id
    })
    save_data(data)
    await ctx.send(f"✅ Напоминание '{текст}' на {время} добавлено!")

@bot.command()
async def список(ctx):
    data = load_data()
    user_reminders = [r for r in data["reminders"] if r["user_id"] == ctx.author.id]
    if user_reminders:
        msg = "📋 Ваши напоминания:\n" + "\n".join([f"⏰ {r['time']}: {r['text']}" for r in user_reminders])
        await ctx.send(msg)
    else:
        await ctx.send("📭 У вас нет напоминаний")

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

print("🔧 Запуск...")
bot.run(token)
