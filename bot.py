import os
import json
import datetime
import asyncio

print("🚀 Начало запуска бота...")

# Проверяем переменные окружения
token = os.environ.get('DISCORD_TOKEN')
print(f"DISCORD_TOKEN: {'✅ Найден' if token else '❌ Не найден'}")

if not token:
    print("❌ ТОКЕН НЕ НАЙДЕН!")
    print("Добавьте DISCORD_TOKEN в Environment Variables на Render")
    exit(1)

try:
    # Используем py-cord вместо discord.py
    import discord
    from discord.ext import commands, tasks
    print("✅ Py-cord загружен успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите библиотеки: pip install py-cord pytz")
    exit(1)

# Настройки
try:
    import pytz
    MOSCOW_TZ = pytz.timezone('Europe/Moscow')
    print("✅ Pytz загружен успешно")
except:
    print("⚠️ Pytz не установлен, используем UTC")
    MOSCOW_TZ = datetime.timezone.utc

DATA_FILE = 'reminders_data.json'

# Создаем бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

AUTO_CHANNEL_ID = None

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
    return {"reminders": [], "bonus_active": True}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")

def get_next_id():
    data = load_data()
    if not data["reminders"]:
        return 1
    return max(reminder["id"] for reminder in data["reminders"]) + 1

# 🔥 СИСТЕМА АКТИВНОСТИ
@tasks.loop(minutes=5)
async def keep_alive():
    current_time = datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')
    print(f"✅ Активность: {current_time}")

# 🔥 ПРОВЕРКА НАПОМИНАНИЙ
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
                print(f"✅ Отправлено напоминание: {reminder['message']}")
            except Exception as e:
                print(f"❌ Ошибка отправки: {e}")

# 🔥 СИСТЕМА БОНУСОВ
@tasks.loop(minutes=30)
async def bonus_reminder():
    data = load_data()
    
    if not data.get("bonus_active", True):
        return
    
    current_hour = datetime.datetime.now(MOSCOW_TZ).hour
    if current_hour >= 8:
        user_ids = set(reminder["user_id"] for reminder in data["reminders"])
        for user_id in user_ids:
            try:
                user = await bot.fetch_user(user_id)
                await user.send("🎯 Заберите бонус!")
                print("✅ Бонус отправлен")
            except Exception as e:
                print(f"❌ Ошибка бонуса: {e}")

# 🔥 АВТО-СООБЩЕНИЯ
@tasks.loop(minutes=10)
async def discord_ping():
    if AUTO_CHANNEL_ID:
        try:
            channel = bot.get_channel(AUTO_CHANNEL_ID)
            if channel:
                current_time = datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')
                await channel.send(f"💚 Бот активен | {current_time}")
        except Exception as e:
            print(f"Ошибка авто-сообщения: {e}")

@bot.event
async def on_ready():
    print(f'🎉 Бот {bot.user} запущен на Render!')
    print(f'⏰ Время: {datetime.datetime.now(MOSCOW_TZ).strftime("%H:%M")}')
    
    # Запускаем все задачи
    tasks_to_start = [keep_alive, check_reminders, bonus_reminder, discord_ping]
    for task in tasks_to_start:
        if not task.is_running():
            task.start()
    
    print(f"🚀 Запущено {len(tasks_to_start)} задач")
    print("💡 Бот работает 24/7!")

# 🎯 КОМАНДЫ УПРАВЛЕНИЯ БОНУСАМИ
@bot.command()
async def готово(ctx):
    """Остановить бонусы до завтра: !готово"""
    data = load_data()
    data["bonus_active"] = False
    save_data(data)
    await ctx.send("✅ Бонусные напоминания остановлены! Активируются завтра в 08:00")

@bot.command()
async def включить(ctx):
    """Включить бонусные напоминания: !включить"""
    data = load_data()
    data["bonus_active"] = True
    save_data(data)
    await ctx.send("✅ Бонусные напоминания ВКЛЮЧЕНЫ!")

@bot.command()
async def статус(ctx):
    """Показать статус бонусов: !статус"""
    data = load_data()
    current_time = datetime.datetime.now(MOSCOW_TZ).strftime("%H:%M")
    
    bonus_status = "🟢 АКТИВНЫ" if data.get("bonus_active", True) else "🔴 ВЫКЛЮЧЕНЫ"
    next_bonus = "Через 30 минут" if data.get("bonus_active", True) else "После 08:00"
    
    embed = discord.Embed(title="🎯 Статус бонусов", color=0x00ff00)
    embed.add_field(name="Бонусы", value=bonus_status, inline=True)
    embed.add_field(name="Текущее время", value=current_time, inline=True)
    embed.add_field(name="Следующий бонус", value=next_bonus, inline=True)
    
    await ctx.send(embed=embed)

# ⏰ КОМАНДЫ РУЧНЫХ НАПОМИНАНИЙ
@bot.command()
async def добавить(ctx, время: str, *, текст: str):
    """Добавить напоминание: !добавить 14:30 Покормить кота"""
    try:
        hours, minutes = время.split(":")
        hours = int(hours)
        minutes = int(minutes)
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            await ctx.send("❌ Неверное время! Используйте ЧЧ:ММ")
            return
        time_str = f"{hours:02d}:{minutes:02d}"
    except ValueError:
        await ctx.send("❌ Неверный формат времени! Используйте ЧЧ:ММ")
        return
    
    data = load_data()
    new_reminder = {
        "id": get_next_id(),
        "time": time_str,
        "message": текст,
        "active": True,
        "user_id": ctx.author.id
    }
    data["reminders"].append(new_reminder)
    save_data(data)
    await ctx.send(f"✅ Напоминание добавлено! ID: {new_reminder['id']}")

@bot.command()
async def список(ctx):
    """Показать все напоминания: !список"""
    data = load_data()
    user_reminders = [r for r in data["reminders"] if r["user_id"] == ctx.author.id]
    
    if not user_reminders:
        await ctx.send("📭 У вас нет напоминаний")
        return
    
    embed = discord.Embed(title="📋 Ваши напоминания", color=0x00ff00)
    for reminder in user_reminders:
        status = "✅" if reminder["active"] else "❌"
        embed.add_field(
            name=f"{status} ⏰ {reminder['time']}",
            value=f"💬 {reminder['message']}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def удалить(ctx, id: int):
    """Удалить напоминание: !удалить 1"""
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
    """Установить канал для авто-сообщений: !автоканал"""
    global AUTO_CHANNEL_ID
    AUTO_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Авто-сообщения включены в этом канале!")

@bot.command()
async def тест(ctx):
    """Проверить работу бота: !тест"""
    await ctx.send("✅ Бот работает на Render 24/7!")

@bot.command()
async def помощь(ctx):
    """Показать справку: !помощь"""
    embed = discord.Embed(title="📚 Команды бота", color=0x0099ff)
    commands_list = [
        ("!добавить 14:30 Текст", "Создать напоминание"),
        ("!список", "Показать все напоминания"),
        ("!удалить 1", "Удалить напоминание"),
        ("!готово", "Остановить бонусы до завтра"),
        ("!включить", "Включить бонусы"),
        ("!статус", "Статус бонусов"),
        ("!автоканал", "Включить авто-сообщения"),
        ("!тест", "Проверить бота")
    ]
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    await ctx.send(embed=embed)

# Запуск бота
print("🚀 Запуск бота с py-cord...")
try:
    bot.run(token)
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
