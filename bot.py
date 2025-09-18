import logging
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Подключение к базе данных
conn = sqlite3.connect('roles.db')
c = conn.cursor()

# Создание таблиц
c.execute('''
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folder_id INTEGER,
        name TEXT,
        occupied INTEGER DEFAULT 0,
        user TEXT,
        FOREIGN KEY(folder_id) REFERENCES folders(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        folder_id INTEGER,
        FOREIGN KEY(folder_id) REFERENCES folders(id)
    )
''')

conn.commit()

async def is_admin(update: Update) -> bool:
    # Проверка, является ли пользователь администратором
    chat_member = await update.effective_chat.get_member(update.effective_user.id)
    return chat_member.status in ['creator', 'administrator']

async def occupy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    role_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            if role[3] == 1:
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" уже занята.')
            else:
                c.execute("UPDATE roles SET occupied = 1, user = ? WHERE id = ?", (update.message.from_user.first_name, role[0]))
                conn.commit()
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" теперь занята {update.message.from_user.first_name}.')
        else:
            await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" не найдена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    role_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            if role[3] == 0:
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" уже свободна.')
            else:
                c.execute("UPDATE roles SET occupied = 0, user = NULL WHERE id = ?", (role[0],))
                conn.commit()
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" теперь свободна.')
        else:
            await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" не найдена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def reserve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    role_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            if role[3] == 1:
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" уже занята.')
            else:
                c.execute("UPDATE roles SET occupied = 1, user = ? WHERE id = ?", (update.message.from_user.first_name, role[0]))
                conn.commit()
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" теперь забронирована {update.message.from_user.first_name}.')
        else:
            await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" не найдена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def role_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT name, occupied FROM roles WHERE folder_id = ?", (folder_id[0],))
        roles = c.fetchall()
        occupied_roles = [role[0] for role in roles if role[1] == 1]
        free_roles = [role[0] for role in roles if role[1] == 0]

        if occupied_roles:
            await update.message.reply_text(f'Занятые роли в папке "{folder_name}": {", ".join(occupied_roles)}')
        else:
            await update.message.reply_text(f'Нет занятых ролей в папке "{folder_name}".')

        if free_roles:
            await update.message.reply_text(f'Свободные роли в папке "{folder_name}": {", ".join(free_roles)}')
        else:
            await update.message.reply_text(f'Нет свободных ролей в папке "{folder_name}".')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def my_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_roles = []
    c.execute("SELECT folders.name, roles.name FROM roles JOIN folders ON roles.folder_id = folders.id WHERE roles.user = ?", (update.message.from_user.first_name,))
    roles = c.fetchall()
    for role in roles:
        user_roles.append(f'{role[0]}: {role[1]}')
    if user_roles:
        await update.message.reply_text(f'Твои роли: {", ".join(user_roles)}')
    else:
        await update.message.reply_text('У тебя нет занятых ролей.')

async def user_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = context.args[0]
    user_roles = []
    c.execute("SELECT folders.name, roles.name FROM roles JOIN folders ON roles.folder_id = folders.id WHERE roles.user = ?", (user_name,))
    roles = c.fetchall()
    for role in roles:
        user_roles.append(f'{role[0]}: {role[1]}')
    if user_roles:
        await update.message.reply_text(f'Роли пользователя {user_name}: {", ".join(user_roles)}')
    else:
        await update.message.reply_text(f'У пользователя {user_name} нет занятых ролей.')

async def assign_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update):
        await update.message.reply_text('Только администраторы могут назначать роли.')
        return

    folder_name = context.args[0]
    role_name = context.args[1]
    user_name = context.args[2]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            if role[3] == 1:
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" уже занята.')
            else:
                c.execute("UPDATE roles SET occupied = 1, user = ? WHERE id = ?", (user_name, role[0]))
                conn.commit()
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" теперь назначена пользователю {user_name}.')
        else:
            await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" не найдена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def remove_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update):
        await update.message.reply_text('Только администраторы могут снимать роли.')
        return

    folder_name = context.args[0]
    role_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            if role[3] == 0:
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" уже свободна.')
            else:
                c.execute("UPDATE roles SET occupied = 0, user = NULL WHERE id = ?", (role[0],))
                conn.commit()
                await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" теперь свободна.')
        else:
            await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" не найдена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def templates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute("SELECT name FROM templates")
    templates = c.fetchall()
    if templates:
        template_list = [template[0] for template in templates]
        await update.message.reply_text(f'Доступные шаблоны: {", ".join(template_list)}')
    else:
        await update.message.reply_text('Нет доступных шаблонов.')

async def save_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    template_name = context.args[0]
    folder_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM templates WHERE name = ?", (template_name,))
        template = c.fetchone()
        if template:
            await update.message.reply_text(f'Шаблон "{template_name}" уже существует.')
        else:
            c.execute("INSERT INTO templates (name, folder_id) VALUES (?, ?)", (template_name, folder_id[0]))
            conn.commit()
            await update.message.reply_text(f'Шаблон "{template_name}" сохранен.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Доступные команды:\n"
        "/occupy <папка> <роль> - Занять роль в папке.\n"
        "/free <папка> <роль> - Освободить роль в папке.\n"
        "/reserve <папка> <роль> - Забронировать роль в папке.\n"
        "/role_list <папка> - Показать список ролей в папке.\n"
        "/my_role - Узнать свои текущие роли.\n"
        "/user_role <имя пользователя> - Узнать роли другого пользователя.\n"
        "/assign_role <папка> <роль> <имя пользователя> - Назначить роль пользователю (только для администраторов).\n"
        "/remove_role <папка> <роль> - Снять роль с пользователя (только для администраторов).\n"
        "/add_role <папка> <роль> - Добавить новую роль в папку.\n"
        "/delete_role <папка> <роль> - Удалить роль из папки.\n"
        "/add_folder <папка> - Создать новую папку.\n"
        "/delete_folder <папка> - Удалить папку.\n"
        "/templates - Показать список доступных шаблонов.\n"
        "/save_template <имя шаблона> <папка> - Сохранить шаблон.\n"
        "/help - Показать список доступных команд."
    )
    await update.message.reply_text(help_text)

async def add_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    role_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            await update.message.reply_text(f'Роль "{role_name}" уже существует в папке "{folder_name}".')
        else:
            c.execute("INSERT INTO roles (folder_id, name) VALUES (?, ?)", (folder_id[0], role_name))
            conn.commit()
            await update.message.reply_text(f'Роль "{role_name}" добавлена в папку "{folder_name}".')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def delete_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    role_name = context.args[1]
    c.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
    folder_id = c.fetchone()
    if folder_id:
        c.execute("SELECT * FROM roles WHERE folder_id = ? AND name = ?", (folder_id[0], role_name))
        role = c.fetchone()
        if role:
            c.execute("DELETE FROM roles WHERE id = ?", (role[0],))
            conn.commit()
            await update.message.reply_text(f'Роль "{role_name}" удалена из папки "{folder_name}".')
        else:
            await update.message.reply_text(f'Роль "{role_name}" в папке "{folder_name}" не найдена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def add_folder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    c.execute("SELECT * FROM folders WHERE name = ?", (folder_name,))
    folder = c.fetchone()
    if folder:
        await update.message.reply_text(f'Папка "{folder_name}" уже существует.')
    else:
        c.execute("INSERT INTO folders (name) VALUES (?)", (folder_name,))
        conn.commit()
        await update.message.reply_text(f'Папка "{folder_name}" создана.')

async def delete_folder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    folder_name = context.args[0]
    c.execute("SELECT * FROM folders WHERE name = ?", (folder_name,))
    folder = c.fetchone()
    if folder:
        c.execute("DELETE FROM folders WHERE id = ?", (folder[0],))
        conn.commit()
        await update.message.reply_text(f'Папка "{folder_name}" удалена.')
    else:
        await update.message.reply_text(f'Папка "{folder_name}" не найдена.')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Я бот для управления ролями. Используй команды для взаимодействия со мной.')

def main() -> None:
    application = Application.builder().token('8292299057:AAHHC9ut47XBf37ugTRWwklk5b34IgY-v-A').build()

    application.add_handler(CommandHandler("occupy", occupy))
    application.add_handler(CommandHandler("free", free))
    application.add_handler(CommandHandler("reserve", reserve))
    application.add_handler(CommandHandler("role_list", role_list))
    application.add_handler(CommandHandler("my_role", my_role))
    application.add_handler(CommandHandler("user_role", user_role))
    application.add_handler(CommandHandler("assign_role", assign_role))
    application.add_handler(CommandHandler("remove_role", remove_role))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("add_role", add_role))
    application.add_handler(CommandHandler("delete_role", delete_role))
    application.add_handler(CommandHandler("add_folder", add_folder))
    application.add_handler(CommandHandler("delete_folder", delete_folder))
    application.add_handler(CommandHandler("templates", templates))
    application.add_handler(CommandHandler("save_template", save_template))
    application.add_handler(CommandHandler("start", start))

    application.run_polling()

if __name__ == "__main__":
    main()
