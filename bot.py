# bot.py - основной файл вашего бота

import sqlite3
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ================== БЕЗОПАСНАЯ ЗАГРУЗКА ТОКЕНА ==================
load_dotenv()  # Загружает переменные из файла .env
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Токен теперь берется из переменной окружения

if not TOKEN:
    raise ValueError("ОШИБКА: Токен не найден! Создайте файл .env с TELEGRAM_TOKEN=ваш_токен")

# ================== БАЗА ДАННЫХ ==================
conn = sqlite3.connect("todo.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    completed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ================== КОМАНДЫ БОТА ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я учебный todo-бот.\n"
        "Команды:\n"
        "/add <текст> - добавить задачу\n"
        "/list - все задачи\n"
        "/active - активные задачи\n"
        "/done <id> - отметить выполненной\n"
        "/del <id> - удалить задачу"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Использование: /add купить хлеб")
        return

    cursor.execute(
        "INSERT INTO todos (user_id, text) VALUES (?, ?)",
        (update.effective_user.id, text)
    )
    conn.commit()
    await update.message.reply_text("✅ Задача добавлена")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT id, text, completed FROM todos WHERE user_id=? ORDER BY id",
        (update.effective_user.id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("📭 Список задач пуст")
        return

    msg = "📋 Ваши задачи:\n"
    for task_id, text, completed in rows:
        status = "✅" if completed else "⏳"
        msg += f"{task_id}. {status} {text}\n"
    await update.message.reply_text(msg)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /done 1")
        return

    task_id = context.args[0]
    cursor.execute(
        "UPDATE todos SET completed=1 WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    conn.commit()
    await update.message.reply_text(f"✅ Задача {task_id} выполнена!")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /del 1")
        return

    task_id = context.args[0]
    cursor.execute(
        "DELETE FROM todos WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    conn.commit()
    await update.message.reply_text(f"🗑 Задача {task_id} удалена")

# ================== ЗАПУСК БОТА ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("del", delete))

    print("🤖 Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
