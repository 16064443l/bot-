import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        achievement TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT,
        user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        reward TEXT
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

async def gain_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if user:
        new_experience = user[3] + 10  # Добавьте логику для расчета опыта
        if new_experience >= user[2] * 100:  # Простая система уровней
            new_level = user[2] + 1
            c.execute("UPDATE users SET level = ?, experience = 0 WHERE user_id = ?", (new_level, user_id))
            await update.message.reply_text(f'Вы получили новый уровень! Теперь вы на уровне {new_level}!')
        else:
            c.execute("UPDATE users SET experience = ? WHERE user_id = ?", (new_experience, user_id))
            await update.message.reply_text(f'Вы получили опыт и теперь на уровне {user[2]}!')
    else:
        c.execute("INSERT INTO users (user_id, level, experience) VALUES (?, 1, 10)", (user_id,))
        await update.message.reply_text(f'Вы начали с уровня 1!')

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    c.execute("SELECT achievement FROM achievements WHERE user_id = ?", (user_id,))
    achievements = c.fetchall()
    if achievements:
        achievement_list = [achievement[0] for achievement in achievements]
        await update.message.reply_text(f'Ваши достижения: {", ".join(achievement_list)}')
    else:
        await update.message.reply_text('У вас нет достижений.')

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    role_name = context.args[0]
    user_id = update.message.from_user.id
    c.execute("SELECT * FROM votes WHERE role_name = ? AND user_id = ?", (role_name, user_id))
    vote = c.fetchone()
    if vote:
        await update.message.reply_text(f'Вы уже голосовали за роль "{role_name}"!')
    else:
        c.execute("INSERT INTO votes (role_name, user_id) VALUES (?, ?)", (role_name, user_id))
        conn.commit()
        await update.message.reply_text(f'Вы проголосовали за роль "{role_name}"!')

async def reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Добавьте логику для отправки напоминаний пользователям
    await update.message.reply_text(f'Напоминание: у вас есть занятые роли, которые нужно освободить!')

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    city = context.args[0]
    # Добавьте логику для получения погоды из API
    await update.message.reply_text(f'Погода в {city}: {weather_info}')

async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    # Добавьте логику для отображения доступных квестов
    await update.message.reply_text(f'Ваши квесты: {", ".join(user_quests)}')

async def create_quest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update):
        await update.message.reply_text('Только администраторы могут создавать квесты.')
        return

    quest_name = context.args[0]
    quest_description = context.args[1]
    quest_reward = context.args[2]
    c.execute("SELECT * FROM quests WHERE name = ?", (quest_name,))
    quest = c.fetchone()
    if quest:
        await update.message.reply_text(f'Квест "{quest_name}" уже существует.')
    else:
        c.execute("INSERT INTO quests (name, description, reward) VALUES (?, ?, ?)", (quest_name, quest_description, quest_reward))
        conn.commit()
        await update.message.reply_text(f'Квест "{quest_name}" создан.')

async def quest_board(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute("SELECT * FROM quests")
    quests = c.fetchall()
    if quests:
        quest_list = []
        for quest in quests:
            quest_list.append(f'**{quest[1]}**\nОписание: {quest[2]}\nНаграда: {quest[3]}')
        await update.message.reply_text('\n\n'.join(quest_list), parse_mode='Markdown')
    else:
        await update.message.reply_text('Нет доступных квестов.')

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    c.execute("SELECT level, experience FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if user:
        level = user[0]
        experience = user[1]
        await update.message.reply_text(f'Ваш профиль:\nУровень: {level}\nОпыт: {experience}')
    else:
        await update.message.reply_text('Ваш профиль не найден.')

async def list_folders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute("SELECT name FROM folders")
    folders = c.fetchall()
    if folders:
        folder_list = [folder[0] for folder in folders]
        await update.message.reply_text(f'Доступные папки: {", ".join(folder_list)}')
    else:
        await update.message.reply_text('Нет доступных папок.')

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
        "/gain_experience - Получить опыт.\n"
        "/achievements - Показать ваши достижения.\n"
        "/vote <роль> - Проголосовать за роль.\n"
        "/reminders - Получить напоминания.\n"
        "/weather <город> - Получить погоду.\n"
        "/quests - Показать доступные квесты.\n"
        "/create_quest <название> <описание> <награда> - Создать квест (только для администраторов).\n"
        "/quest_board - Показать доску с квестами.\n"
        "/profile - Показать ваш профиль.\n"
        "/list_folders - Показать список доступных папок.\n"
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
    keyboard = [
        [InlineKeyboardButton("Список папок", callback_data='list_folders')],
        [InlineKeyboardButton("Список ролей", callback_data='role_list')],
        [InlineKeyboardButton("Мои роли", callback_data='my_role')],
        [InlineKeyboardButton("Профиль", callback_data='profile')],
        [InlineKeyboardButton("Доска квестов", callback_data='quest_board')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привет! Я бот для управления ролями. Используй команды или кнопки для взаимодействия со мной.', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'list_folders':
        await list_folders(query, context)
    elif query.data == 'role_list':
        await role_list(query, context)
    elif query.data == 'my_role':
        await my_role(query, context)
    elif query.data == 'profile':
        await profile(query, context)
    elif query.data == 'quest_board':
        await quest_board(query, context)

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
    application.add_handler(CommandHandler("gain_experience", gain_experience))
    application.add_handler(CommandHandler("achievements", achievements))
    application.add_handler(CommandHandler("vote", vote))
    application.add_handler(CommandHandler("reminders", reminders))
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("quests", quests))
    application.add_handler(CommandHandler("create_quest", create_quest))
    application.add_handler(CommandHandler("quest_board", quest_board))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("list_folders", list_folders))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == "__main__":
    main()
