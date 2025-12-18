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
    deleted BOOLEAN DEFAULT 0,           -- НОВОЕ ПОЛЕ: 1 = задача удалена
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ 
def get_user_task_by_number(user_id, task_number):
    """Получить реальный ID задачи по её номеру в списке пользователя (включая удалённые)"""
    cursor.execute(
        "SELECT id FROM todos WHERE user_id=? ORDER BY id",
        (user_id,)
    )
    rows = cursor.fetchall()
    
    if task_number < 1 or task_number > len(rows):
        return None
    return rows[task_number - 1][0]

def get_all_user_tasks(user_id):
    """Получить все задачи пользователя (включая удалённые)"""
    cursor.execute(
        "SELECT id, text, completed, deleted FROM todos WHERE user_id=? ORDER BY id",
        (user_id,)
    )
    return cursor.fetchall()

def get_active_user_tasks(user_id):
    """Получить только активные задачи (не удалённые)"""
    cursor.execute(
        "SELECT id, text, completed FROM todos WHERE user_id=? AND deleted=0 ORDER BY id",
        (user_id,)
    )
    return cursor.fetchall()

# КОМАНДЫ БОТА 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я todo-бот, учебный проект Леонида .\n\n"
        "📌 **Особенности:**\n"
        "• Номера задач НЕ меняются при удалении\n"
        "• Удалённые задачи остаются в списке как '✅ УДАЛЕНО'\n"
        "• Когда все задачи будут выполнены, используйте /clear_done\n\n"
        "📋 **Команды:**\n"
        "/add <текст> - добавить задачу\n"
        "/list - список всех задач\n"
        "/done <номер> - отметить выполненной\n"
        "/del <номер> - 'закрыть' задачу (оставить в списке)\n"
        "/clear_done - очистить ВЕСЬ список (только если все задачи выполнены или удалены)"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Пример: /add купить хлеб")
        return

    cursor.execute(
        "INSERT INTO todos (user_id, text) VALUES (?, ?)",
        (update.effective_user.id, text)
    )
    conn.commit()
    
    tasks = get_all_user_tasks(update.effective_user.id)
    task_number = len(tasks)
    
    await update.message.reply_text(f"✅ Задача {task_number} добавлена:\n«{text}»")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_all_user_tasks(update.effective_user.id)

    if not tasks:
        await update.message.reply_text("📭 Список задач пуст")
        return

    msg = "📋 Ваши задачи (номера НЕ меняются!):\n"
    all_completed_or_deleted = True
    
    for index, (task_id, text, completed, deleted) in enumerate(tasks, start=1):
        if deleted:
            status = "🗑️ УДАЛЕНО"
            msg += f"{index}. {status}\n"
        elif completed:
            status = "✅ ВЫПОЛНЕНО"
            msg += f"{index}. {status} ~~{text}~~\n"
        else:
            status = "⏳ АКТИВНА"
            msg += f"{index}. {status} {text}\n"
            all_completed_or_deleted = False
    
    if all_completed_or_deleted and tasks:
        msg += "\n🎉 Все задачи завершены! Можно очистить список: /clear_done"
    
    await update.message.reply_text(msg)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /done 1")
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Номер задачи должен быть числом")
        return

    real_task_id = get_user_task_by_number(update.effective_user.id, task_number)
    
    if not real_task_id:
        await update.message.reply_text(f"❌ Задачи с номером {task_number} не существует")
        return
    
    # Проверяем, не удалена ли уже задача
    cursor.execute(
        "SELECT deleted FROM todos WHERE id=?",
        (real_task_id,)
    )
    if cursor.fetchone()[0] == 1:
        await update.message.reply_text(f"ℹ️ Задача {task_number} уже удалена")
        return

    cursor.execute(
        "UPDATE todos SET completed=1 WHERE id=? AND user_id=?",
        (real_task_id, update.effective_user.id)
    )
    conn.commit()
    
    cursor.execute("SELECT text FROM todos WHERE id=?", (real_task_id,))
    task_text = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"✅ Задача {task_number} выполнена!\n"
        f"«{task_text}»\n\n"
        f"🏆 Отличная работа!"
    )

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /del 1")
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Номер задачи должен быть числом")
        return

    real_task_id = get_user_task_by_number(update.effective_user.id, task_number)
    
    if not real_task_id:
        await update.message.reply_text(f"❌ Задачи с номером {task_number} не существует")
        return
    
    # Получаем статус задачи
    cursor.execute(
        "SELECT text, completed FROM todos WHERE id=?",
        (real_task_id,)
    )
    task_text, completed = cursor.fetchone()
    
    if completed:
        praise = "🎉 И она уже была выполнена! Двойная победа!"
    else:
        praise = "🔥 Бывает, не все планы реализуются. Главное - движение!"

    
    cursor.execute(
        "UPDATE todos SET deleted=1 WHERE id=? AND user_id=?",
        (real_task_id, update.effective_user.id)
    )
    conn.commit()
    
    await update.message.reply_text(
        f"🗑️ Задача {task_number} удалена:\n"
        f"«{task_text}»\n\n"
        f"{praise}\n\n"
        f"💡 Место {task_number} в списке останется пустым."
    )

async def clear_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет ВЕСЬ список, если все задачи выполнены или удалены"""
    tasks = get_all_user_tasks(update.effective_user.id)
    
    if not tasks:
        await update.message.reply_text("📭 Список и так пуст!")
        return
    
    
    all_done = all(task[2] == 1 or task[3] == 1 for task in tasks)
    
    if not all_done:
        await update.message.reply_text(
            "❌ Нельзя очистить список!\n"
            "Ещё есть активные задачи. Сначала выполните или удалите их все.\n"
            "Проверьте: /list"
        )
        return
    
    
    completed_count = sum(1 for task in tasks if task[2] == 1)
    deleted_count = sum(1 for task in tasks if task[3] == 1)
    
    
    cursor.execute(
        "DELETE FROM todos WHERE user_id=?",
        (update.effective_user.id,)
    )
    conn.commit()
    
    await update.message.reply_text(
        f"🧹 Весь список очищен!\n\n"
        f"📊 Статистика этого списка:\n"
        f"• Выполнено задач: {completed_count}\n"
        f"• Отменено задач: {deleted_count}\n"
        f"• Всего пунктов: {len(tasks)}\n\n"
        f"🎯 Чистый лист! Можно начинать новый список: /add <задача>"
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("del", delete))
    app.add_handler(CommandHandler("clear_done", clear_done))

    print("🤖 Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
