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

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def get_user_task_by_number(user_id, task_number):
    """Получить реальный ID задачи по её номеру в списке пользователя"""
    cursor.execute(
        "SELECT id FROM todos WHERE user_id=? ORDER BY id",
        (user_id,)
    )
    rows = cursor.fetchall()
    
    if task_number < 1 or task_number > len(rows):
        return None
    return rows[task_number - 1][0]  # Возвращаем реальный ID

# ================== КОМАНДЫ БОТА ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я учебный todo-бот.\n"
        "Команды:\n"
        "/add <текст> - добавить задачу\n"
        "/list - все задачи\n"
        "/done <номер> - отметить задачу выполненной\n"
        "/del <номер> - удалить задачу\n\n"
        "⚠️ Все номера - из вашего списка (/list)"
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
    for index, (task_id, text, completed) in enumerate(rows, start=1):
        status = "✅" if completed else "⏳"
        msg += f"{index}. {status} {text}\n"
    
    await update.message.reply_text(msg)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /done 1")
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Номер задачи должен быть числом")
        return

    # Получаем реальный ID по номеру в списке пользователя
    real_task_id = get_user_task_by_number(update.effective_user.id, task_number)
    
    if not real_task_id:
        await update.message.reply_text(f"❌ Задачи с номером {task_number} не существует")
        return

    cursor.execute(
        "UPDATE todos SET completed=1 WHERE id=? AND user_id=?",
        (real_task_id, update.effective_user.id)
    )
    conn.commit()
    
    # Получаем текст задачи для подтверждения
    cursor.execute(
        "SELECT text FROM todos WHERE id=?",
        (real_task_id,)
    )
    task_text = cursor.fetchone()[0]
    
    await update.message.reply_text(f"✅ Задача {task_number} выполнена:\n«{task_text}»")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /del 1")
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Номер задачи должен быть числом")
        return

    # Получаем реальный ID по номеру в списке пользователя
    real_task_id = get_user_task_by_number(update.effective_user.id, task_number)
    
    if not real_task_id:
        await update.message.reply_text(f"❌ Задачи с номером {task_number} не существует")
        return

    # Получаем текст перед удалением
    cursor.execute(
        "SELECT text FROM todos WHERE id=? AND user_id=?",
        (real_task_id, update.effective_user.id)
    )
    task_text = cursor.fetchone()[0]

    cursor.execute(
        "DELETE FROM todos WHERE id=? AND user_id=?",
        (real_task_id, update.effective_user.id)
    )
    conn.commit()
    
    await update.message.reply_text(f"🗑 Задача {task_number} удалена:\n«{task_text}»")

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
