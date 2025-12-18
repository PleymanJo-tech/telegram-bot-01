import sqlite3
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден в .env файле!")

# База данных
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
        "/list - все задачи с вашей нумерацией\n"
        "/done <id> - отметить выполненной (используйте ID из /list)\n"
        "/del <id> - удалить задачу (используйте ID из /list)"
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

    msg = "📋 Ваши задачи (цифра слева - ваш номер для команд):\n"
    # Ключевое изменение: enumerate создает локальную нумерацию 1,2,3...
    for index, (task_id, text, completed) in enumerate(rows, start=1):
        status = "✅" if completed else "⏳"
        msg += f"{index}. {status} {text}\n"
        msg += f"   ID для команд: {task_id}\n\n"
    
    msg += "💡 Используйте ID из строки выше для /done и /del"
    await update.message.reply_text(msg)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /done <ID>\nПосмотреть ID задач: /list")
        return

    task_id = context.args[0]
    cursor.execute(
        "UPDATE todos SET completed=1 WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    conn.commit()
    
    # Получаем текст задачи для подтверждения
    cursor.execute(
        "SELECT text FROM todos WHERE id=?",
        (task_id,)
    )
    task = cursor.fetchone()
    
    if task:
        await update.message.reply_text(f"✅ Задача выполнена:\n«{task[0]}»")
    else:
        await update.message.reply_text("❌ Задача не найдена. Проверьте ID через /list")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /del <ID>\nПосмотреть ID задач: /list")
        return

    task_id = context.args[0]
    
    # Сначала получаем текст задачи
    cursor.execute(
        "SELECT text FROM todos WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    task = cursor.fetchone()
    
    if not task:
        await update.message.reply_text("❌ Задача не найдена. Проверьте ID через /list")
        return

    # Удаляем задачу
    cursor.execute(
        "DELETE FROM todos WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    conn.commit()
    await update.message.reply_text(f"🗑 Задача удалена:\n«{task[0]}»")

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
