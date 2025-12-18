#импорт стандартного модуля для работы с базой данных SQLite
import sqlite3

#импорт класса Update — он содержит данные о входящем сообщении от Telegram
from telegram import Update

#импорт необходимых компонентов для создания бота
from telegram.ext import (
    ApplicationBuilder,   #создаёт приложение (бота)
    CommandHandler,       #обрабатывает команды (/start, /add и т.д.)
    ContextTypes,         #тип контекста (аргументы, данные бота)
)

#токен Telegram-бота(выдаётся BotFather)
TOKEN = "8256496563:AAGcm2xmzWA6Iqlg_nx8Ry-99h3m2K6WwPM"


#БАЗА ДАННЫХ

#подключаемся к базе данных todo.db
#если файла нет — он будет создан автоматически
#check_same_thread=False — разрешает использовать БД в асинхронном коде
conn = sqlite3.connect("todo.db", check_same_thread=False)

#cursor — объект для выполнения SQL-запросов
cursor = conn.cursor()

#создаём таблицу todos, если она ещё не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  - уникальный ID задачи
    user_id INTEGER,                       - ID пользователя Telegram
    text TEXT,                             - текст задачи
    completed BOOLEAN DEFAULT 0,           - статус выполнения (0 - не выполнено, 1 - выполнено)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  - время создания задачи
)
""")


conn.commit()


#КОМАНДЫ 


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "Я todo-бот.\n\n"
        "Доступные команды:\n"
        "/add <текст> — добавить задачу\n"
        "/list — список всех задач\n"
        "/active — список активных задач\n"
        "/done — список выполненных задач\n"
        "/done <id> — отметить задачу выполненной\n"
        "/undo <id> — вернуть задачу в активные\n"
        "/del <id> — удалить задачу\n"
        "/clear_completed — удалить все выполненные задачи"
    )



async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("❗ Использование: /add текст")
        return

    cursor.execute(
        "INSERT INTO todos (user_id, text) VALUES (?, ?)",
        (
            update.effective_user.id,
            text
        )
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

    msg = "📋 Все задачи:\n"
    for task_id, text, completed in rows:
        status = "✅" if completed else "⏳"
        msg += f"{task_id}. {status} {text}\n"

    await update.message.reply_text(msg)



async def active_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT id, text FROM todos WHERE user_id=? AND completed=0 ORDER BY id",
        (update.effective_user.id,)
    )

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("🎉 Нет активных задач! Все выполнено!")
        return

    msg = "⏳ Активные задачи:\n"
    for task_id, text in rows:
        msg += f"{task_id}. {text}\n"

    await update.message.reply_text(msg)



async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        
        cursor.execute(
            "SELECT id, text FROM todos WHERE user_id=? AND completed=1 ORDER BY id",
            (update.effective_user.id,)
        )

        rows = cursor.fetchall()

        if not rows:
            await update.message.reply_text("📭 Нет выполненных задач")
            return

        msg = "✅ Выполненные задачи:\n"
        for task_id, text in rows:
            msg += f"{task_id}. {text}\n"

        await update.message.reply_text(msg)
        return

    
    task_id = context.args[0]
    
    # Проверяем, существует ли задача
    cursor.execute(
        "SELECT id FROM todos WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    
    task_exists = cursor.fetchone()
    
    if not task_exists:
        await update.message.reply_text("❌ Задача не найдена")
        return
    
    
    cursor.execute(
        "UPDATE todos SET completed=1 WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    
    
    cursor.execute(
        "SELECT text FROM todos WHERE id=?",
        (task_id,)
    )
    
    task_text = cursor.fetchone()[0]
    conn.commit()
    
    await update.message.reply_text(f"✅ Задача выполнена:\n{task_text}")



async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Использование: /undo id")
        return

    task_id = context.args[0]
    
    
    cursor.execute(
        "SELECT id, completed FROM todos WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    
    task = cursor.fetchone()
    
    if not task:
        await update.message.reply_text("❌ Задача не найдена")
        return
    
    if task[1] == 0:  # Если задача уже активна
        await update.message.reply_text("ℹ️ Эта задача уже активна")
        return
    
    
    cursor.execute(
        "UPDATE todos SET completed=0 WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    
    
    cursor.execute(
        "SELECT text FROM todos WHERE id=?",
        (task_id,)
    )
    
    task_text = cursor.fetchone()[0]
    conn.commit()
    
    await update.message.reply_text(f"↩️ Задача возвращена в активные:\n{task_text}")



async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Использование: /del id")
        return

    task_id = context.args[0]
    
    
    cursor.execute(
        "SELECT text FROM todos WHERE id=? AND user_id=?",
        (task_id, update.effective_user.id)
    )
    
    task = cursor.fetchone()
    
    if not task:
        await update.message.reply_text("❌ Задача не найдена")
        return

    cursor.execute(
        "DELETE FROM todos WHERE id=? AND user_id=?",
        (
            task_id,
            update.effective_user.id
        )
    )

    conn.commit()
    await update.message.reply_text(f"🗑 Задача удалена:\n{task[0]}")



async def clear_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    cursor.execute(
        "SELECT COUNT(*) FROM todos WHERE user_id=? AND completed=1",
        (update.effective_user.id,)
    )
    
    count = cursor.fetchone()[0]
    
    if count == 0:
        await update.message.reply_text("✅ Нет выполненных задач для удаления")
        return
    
    
    cursor.execute(
        "DELETE FROM todos WHERE user_id=? AND completed=1",
        (update.effective_user.id,)
    )
    
    conn.commit()
    await update.message.reply_text(f"🧹 Удалено {count} выполненных задач")




def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("active", active_tasks))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("undo", undo))
    app.add_handler(CommandHandler("del", delete))
    app.add_handler(CommandHandler("clear_completed", clear_completed))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()