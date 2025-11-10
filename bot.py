import os
import discord
from discord.ext import commands, tasks
import json
import datetime
import pytz

print("🚀 Запуск бота в Docker...")

token = os.environ.get('DISCORD_TOKEN')
if not token:
    print("❌ ТОКЕН НЕ НАЙДЕН!")
    exit(1)

print("✅ Токен найден")

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@tasks.loop(minutes=5)
async def activity():
    print(f"✅ Активен: {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}")

@bot.event
async def on_ready():
    print(f'🎉 Бот {bot.user} запущен в Docker!')
    if not activity.is_running():
        activity.start()

@bot.command()
async def тест(ctx):
    await ctx.send("✅ Бот работает в Docker!")

@bot.command()
async def добавить(ctx, время: str, *, текст: str):
    await ctx.send(f"✅ Напоминание '{текст}' на {время}!")

bot.run(token)
