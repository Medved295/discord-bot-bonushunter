import discord
from discord.ext import commands, tasks
import datetime
import pytz
import json
import os
import asyncio

# Настройки
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
DATA_FILE = 'reminders_data.json'

# Создаем бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Переменные
AUTO_CHANNEL_ID = None

# Загрузка данных
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
    return {"reminders": [], "bonus_active": True, "bonus_permanent_off": False}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def get_next_id():
    data = load_data()
    if not data["reminders"]:
        return 1
    return max(reminder["id"] for reminder in data["reminders"]) + 1

# 🔥 ПРОСТАЯ АКТИВНОСТЬ ДЛЯ RENDER
@tasks.loop(minutes=5)
async def keep_alive():
    print(f"✅ Render активность: {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}")

# СИСТЕМА НАПОМИНАНИЙ
@tasks.loop(minutes=1)
async def check_reminders():
    data = load_data()
    if not data["reminders"]:
        return
    
    moscow_time = datetime.datetime.now(MOSCOW_TZ)
    current_time = moscow_time.strftime("%H:%M")
    
    for reminder in data["reminders"]:
        if (reminder["time"] == current_time and 
            reminder["active"] and 
            moscow_time.hour >= 8):
            
            try:
                user = await bot.fetch_user(reminder["user_id"])
                await user.send(f"⏰ Напоминание: {reminder['message']}")
                print(f"✅ Отправлено: {reminder['message']}")
            except Exception as e:
                print(f"❌ Ошибка: {e}")

# СИСТЕМА БОНУСОВ
@tasks.loop(minutes=30)
async def bonus_reminder():
    data = load_data()
    
    if data.get("bonus_permanent_off", False):
        return
    
    if not data.get("bonus_active", True):
        return
    
    moscow_time = datetime.datetime.now(MOSCOW_TZ)
    current_hour = moscow_time.hour
    
    if current_hour >= 8:
        user_ids = set(reminder["user_id"] for reminder in data["reminders"])
        for user_id in user_ids:
            try:
                user = await bot.fetch_user(user_id)
                await user.send("🎯 Заберите бонус!")
                print(f"✅ Бонус отправлен")
            except Exception as e:
                print(f"❌ Ошибка бонуса: {e}")

# АВТОАКТИВАЦИЯ БОНУСОВ
@tasks.loop(minutes=1)
async def check_morning_time():
    data = load_data()
    moscow_time = datetime.datetime.now(MOSCOW_TZ)
    
    if (moscow_time.hour == 8 and moscow_time.minute == 0 and 
        not data.get("bonus_permanent_off", False)):
        data["bonus_active"] = True
        save_data(data)
        print("🔔 Бонусы активированы (08:00)")

# АВТО-СООБЩЕНИЯ
@tasks.loop(minutes=10)
async def discord_ping():
    if AUTO_CHANNEL_ID:
        try:
            channel = bot.get_channel(AUTO_CHANNEL_ID)
            if channel:
                current_time = datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')
                await channel.send(f"💚 Render активен | {current_time}")
        except Exception as e:
            print(f"Ошибка авто-сообщения: {e}")

# ЗАПУСК БОТА
@bot.event
async def on_ready():
    print(f'🎉 Бот {bot.user} запущен на Render!')
    print(f'⏰ Время: {datetime.datetime.now(MOSCOW_TZ).strftime("%H:%M")}')
    
    # Запускаем все задачи
    tasks_to_start = [keep_alive, check_reminders, bonus_reminder, check_morning_time, discord_ping]
    for task in tasks_to_start:
        if not task.is_running():
            task.start()
    
    print(f"🚀 Запущено {len(tasks_to_start)} задач")
    print("💡 Бот работает 24/7 на Render!")

# 🎯 КОМАНДЫ БОТА (остаются без изменений)
@bot.command()
async def готово(ctx):
    data = load_data()
    if data.get("bonus_permanent_off", False):
        await ctx.send("🚫 Бонусы отключены НАВСЕГДА! Используйте !включить")
        return
    data["bonus_active"] = False
    save_data(data)
    await ctx.send("✅ Бонусы остановлены до завтра!")

@bot.command()
async def отключить(ctx):
    data = load_data()
    data["bonus_active"] = False
    data["bonus_permanent_off"] = True
    save_data(data)
    await ctx.send("🚫 Бонусы отключены НАВСЕГДА!")

@bot.command()
async def включить(ctx):
    data = load_data()
    data["bonus_active"] = True
    data["bonus_permanent_off"] = False
    save_data(data)
    await ctx.send("✅ Бонусы ВКЛЮЧЕНЫ!")

@bot.command()
async def статус(ctx):
    data = load_data()
    moscow_time = datetime.datetime.now(MOSCOW_TZ)
    
    if data.get("bonus_permanent_off", False):
        bonus_status = "🔴 ОТКЛЮЧЕНЫ НАВСЕГДА"
        next_bonus = "Никогда (!включить)"
    elif data.get("bonus_active", True):
        bonus_status = "🟢 АКТИВНЫ"
        next_bonus = "Через 30 минут"
    else:
        bonus_status = "🟡 ВЫКЛЮЧЕНЫ ДО 08:00"
        next_bonus = "Завтра в 08:00"
    
    embed = discord.Embed(title="🎯 Статус бонусов", color=0x00ff00)
    embed.add_field(name="Бонусы", value=bonus_status, inline=True)
    embed.add_field(name="Время", value=moscow_time.strftime("%H:%M"), inline=True)
    embed.add_field(name="Следующий бонус", value=next_bonus, inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def добавить(ctx, время: str, *, текст: str):
    try:
        hours, minutes = время.split(":")
        hours, minutes = int(hours), int(minutes)
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            data = load_data()
            new_id = max([r["id"] for r in data["reminders"]]) + 1 if data["reminders"] else 1
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
            status = "✅" if reminder["active"] else "❌"
            embed.add_field(name=f"{status} {reminder['time']}", value=reminder['message'], inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("📭 У вас нет напоминаний")

@bot.command()
async def удалить(ctx, id: int):
    data = load_data()
    for reminder in data["reminders"]:
        if reminder["id"] == id and reminder["user_id"] == ctx.author.id:
            data["reminders"].remove(reminder)
            save_data(data)
            await ctx.send(f"✅ Напоминание удалено!")
            return
    await ctx.send("❌ Напоминание не найдено")

@bot.command()
async def автоканал(ctx):
    global AUTO_CHANNEL_ID
    AUTO_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Авто-сообщения включены в этом канале!")

@bot.command()
async def тест(ctx):
    await ctx.send("✅ Бот работает на Render 24/7!")

@bot.command()
async def помощь(ctx):
    embed = discord.Embed(title="📚 Команды бота", color=0x0099ff)
    commands_list = [
        ("!готово", "Остановить бонусы до завтра"),
        ("!отключить", "Отключить бонусы навсегда"),
        ("!включить", "Включить бонусы"),
        ("!статус", "Статус бонусов"),
        ("!добавить 14:30 Текст", "Добавить напоминание"),
        ("!список", "Показать напоминания"),
        ("!удалить 1", "Удалить напоминание"),
        ("!автоканал", "Включить авто-сообщения"),
        ("!тест", "Проверить бота")
    ]
    for cmd in commands_list:
        embed.add_field(name=cmd[0], value=cmd[1], inline=False)
    await ctx.send(embed=embed)

print("🚀 Запуск бота на Render...")
token = os.environ.get('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("❌ Токен не найден!")
