import logging
import json
import sqlite3
import datetime as dt
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler

# TOKEN for Telegram-bot is necessary
BOT_TOKEN = '7596957066:AAH5kPuJH1823dvaoIbaEYB7T79Y9oP-P78'

# logging in
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# mark_ups making
keyboard_for_menu = [[KeyboardButton('/get'), KeyboardButton('/send')],
                     [KeyboardButton('Инструктаж'), KeyboardButton('/change')]]

data = []

markup_menu = ReplyKeyboardMarkup(keyboard_for_menu)

stop_button = [['/stop']]
markup_stop = ReplyKeyboardMarkup(stop_button)

next_button = [['Продолжить']]
markup_next = ReplyKeyboardMarkup(next_button)

# database connection
connection = sqlite3.connect("homework_database.sqlite")
cursor = connection.cursor()


class ActiveHomework:
    def __init__(self):
        self.homework = ''
        self.date = ()
        self.subject = ''
        self.class_of_user = 0
        self.letter_of_class = ''


class NoHomeworkError(Exception):
    pass


async def text_answer(updater, context):
    if updater.message.text == 'Инструктаж':
        await updater.message.reply_text('Отправьте команду /get для того чтобы получить домашнее задание')
        await updater.message.reply_text('Отправьте команду /send для того чтобы отправить домашнее задание')
        await updater.message.reply_text('Отправьте команду /change для того чтобы сменить свой класс')
        await updater.message.reply_text('Команда /stop прервёт любую операцию')
    else:
        await updater.message.reply_text('Запрос не принят')


async def start(updater, context):
    # Adding new users to client's database
    try:
        chat_id = updater.message.chat.id
        first_name = updater.message.chat.first_name
        username = updater.message.chat.username
        if updater.message.chat.id not in list(map(lambda x: x[0], cursor.execute('''SELECT telegram_id FROM users''').fetchall())):
            cursor.execute('''INSERT INTO users(name, telegram_id, username) VALUES(?, ?, ?)''',
                           (first_name, chat_id, username))
            connection.commit()
            await updater.message.reply_text(f'Привет {first_name}! Я телеграм-бот, работающий на ГБОУ'
                                             f' УР Лицей №41, предназначен для помощи лицеистам получать домашнее задание')
            await updater.message.reply_text(f'Чтобы было проще сразу скажи в каком классе ты учишься, напиши цифру класса '
                                             f'и букву через пробел', reply_markup=markup_stop)
            return 1
        else:
            await updater.message.reply_text(f'Привет {first_name}, похоже ты у нас уже был, если ты забыл как '
                                             f'работать со мной то просто вызови инструкцию', reply_markup=markup_menu)
    except Exception as e:
        await error(updater, context, e)


async def change(updater, context):
    await updater.message.reply_text('Чтобы сменить класс напиши цифру класса и букву класса через пробел',
                                     reply_markup=markup_stop)
    return 1


async def class_asking(updater, context):
    # Getting class of user and rewrite if needed
    try:
        user_class = updater.message.text.split()
        if user_class[0] in data.keys():
            if user_class[1] in data[user_class[0]]:
                cursor.execute('''UPDATE users SET (class, letter_of_class) = (?, ?) WHERE telegram_id = ?''',
                               (user_class[0], user_class[1].lower(), updater.message.chat.id))
                connection.commit()
                await updater.message.reply_text(f'Класс изменён на {user_class[0]} {user_class[1]}', reply_markup=markup_menu)
                return ConversationHandler.END
            else:
                await updater.message.reply_text('Некорректный ввод, попробуйте ещё раз, цифру, букву, через пробел, '
                                                 'в русской раскладке')
                return 1
        else:
            await updater.message.reply_text('Некорректный ввод, попробуйте ещё раз, цифру, букву, через пробел, '
                                             'в русской раскладке')
            return 1
    except Exception as e:
        await error(updater, context, e)


async def stop(updater, context):
    # Function to stop any conversations
    await updater.message.reply_text('OK', reply_markup=markup_menu)
    return ConversationHandler.END


async def error(updater, context, mistake):
    # Function to show errors
    await updater.message.reply_text('Извините, произошла ошибка', reply_markup=markup_menu)
    print(mistake)


async def send(updater, context):
    # Command function to start uploading_homework_handler
    await updater.message.reply_text('Напишите на какое число вы бы хотели отправить дз', reply_markup=markup_stop)
    await updater.message.reply_text('Пишите через дату в формате ДД.ММ.ГГГГ')
    homework.date = None
    return 2


async def getting_date(updater, context):  # Function to get date and to ask subject
    try:
        global data
        if updater.message.text == 'Продолжить':
            new_date = dt.date(homework.date[2], homework.date[1], homework.date[0])
        else:
            string_date = updater.message.text.split('.')
            if len(string_date) != 3:
                raise Exception
            print(string_date)
            new_date = dt.date(int(string_date[2]), int(string_date[1]), int(string_date[0]))
            homework.date = (int(string_date[0]), int(string_date[1]), int(string_date[2]))

            user_class = cursor.execute('''SELECT class, letter_of_class FROM users WHERE telegram_id = ?''',
                                        (updater.message.chat.id,)).fetchall()
            homework.class_of_user, homework.letter_of_class = user_class[0][0], user_class[0][1]

            if homework.class_of_user is None or homework.letter_of_class is None:
                await updater.message.reply_text('У вас не указан класс, поэтому напиши цифру класса и букву класса '
                                                 'через пробел')
                return 1
        if new_date.weekday() == 6:
            await updater.message.reply_text('Выходной, введите другую дату')
            return 2
        else:
            lessons = data[str(homework.class_of_user)][homework.letter_of_class][str(new_date.weekday() + 1)]
            print(lessons)
            await updater.message.reply_text('Отлично, теперь выберите урок на который запланировано дз',
                                             reply_markup=ReplyKeyboardMarkup(lessons))
            return 3
    except Exception as e:
        print(e, )
        await updater.message.reply_text('Некорректная дата')
        await updater.message.reply_text('Попробуйте ещё раз')
        return 2


async def class_asking_in_dialog(updater, context):
    # Getting class of user and rewrite if needed
    try:
        user_class = updater.message.text.split()
        if user_class[0] in data.keys():
            if user_class[1] in data[user_class[0]]:
                await updater.message.reply_text('Нажмите продолжить', reply_markup=markup_next)
                homework.class_of_user, homework.letter_of_class = user_class[0], user_class[1]
                return 2
            else:
                await updater.message.reply_text('Некорректный ввод, попробуйте ещё раз, цифру, букву, через пробел, '
                                                 'в русской раскладке')
                return 1
        else:
            await updater.message.reply_text('Некорректный ввод, попробуйте ещё раз, цифру, букву, через пробел, '
                                             'в русской раскладке')
            return 1
    except Exception as e:
        await error(updater, context, e)


async def asking_subject(updater, context):  # Function to get subject and to ask for homework
    try:
        await updater.message.reply_text('Отправьте дз', reply_markup=markup_stop)
        homework.subject = updater.message.text
        return 4
    except Exception as e:
        await error(updater, context, e)


async def asking_homework(updater, context):  # Function to get homework and to upload it
    try:
        homework.homework = updater.message.text
        cursor.execute('''INSERT INTO homework(homework, date, month, year, subject, class, letter_of_class) 
                             VALUES(?, ?, ?, ?, ?, ?, ?)''', (homework.homework, homework.date[0], homework.date[1],
                                                              homework.date[2], homework.subject, homework.class_of_user,
                                                              homework.letter_of_class))
        connection.commit()
        await updater.message.reply_text('Домашнее задание отправлено', reply_markup=markup_menu)
        return ConversationHandler.END
    except Exception as e:
        print(e)
        await updater.message.reply_text('Попробуйте ещё раз')
        return 4


async def get(updater, context):  # Command function to start downloading_homework_handler
    await updater.message.reply_text('Напишите за какое число вы бы хотели получить дз', reply_markup=markup_stop)
    await updater.message.reply_text('Пишите через дату в формате ДД.ММ.ГГГГ')
    return 2


async def getting_date_to_get(updater, context):  # Function to get date and to ask subject
    try:
        global data
        if updater.message.text == 'Продолжить':
            new_date = dt.date(homework.date[2], homework.date[1], homework.date[0])
        else:
            string_date = updater.message.text.split('.')
            if len(string_date) != 3:
                raise Exception
            new_date = dt.date(int(string_date[2]), int(string_date[1]), int(string_date[0]))
            homework.date = (int(string_date[0]), int(string_date[1]), int(string_date[2]))

            user_class = cursor.execute('''SELECT class, letter_of_class FROM users WHERE telegram_id = ?''',
                                        (updater.message.chat.id,)).fetchall()
            homework.class_of_user, homework.letter_of_class = user_class[0][0], user_class[0][1]

            if homework.class_of_user is None or homework.letter_of_class is None:
                await updater.message.reply_text('У вас не указан класс, поэтому напиши цифру класса и букву класса '
                                                 'через пробел')
                return 1
        if new_date.weekday() == 6:
            await updater.message.reply_text('Выходной, введите другую дату')
            return 2
        else:
            lessons = data[str(homework.class_of_user)][homework.letter_of_class][str(new_date.weekday() + 1)]
            await updater.message.reply_text('Отлично, теперь выберите урок на который запланировано дз',
                                             reply_markup=ReplyKeyboardMarkup(lessons))
            return 3
    except Exception as e:
        print(e)
        await updater.message.reply_text('Некорректная дата')
        await updater.message.reply_text('Попробуйте ещё раз')
        return 2


async def asking_subject_to_get(updater, context):  # Function to get subject and to download homework and to send it
    try:
        homework.subject = updater.message.text
        print(homework.date[0], homework.date[1], homework.date[2], homework.class_of_user, homework.letter_of_class,
              homework.subject)
        downloaded_homework = cursor.execute('''SELECT homework FROM homework WHERE date = ? and month = ? and year = ? 
        and class = ? and letter_of_class = ? and subject = ?''', (homework.date[0], homework.date[1],
                                                                   homework.date[2], homework.class_of_user,
                                                                   homework.letter_of_class, homework.subject)).fetchone()
        if downloaded_homework is None:
            raise NoHomeworkError
        await updater.message.reply_text(downloaded_homework[0], reply_markup=markup_menu)
        return ConversationHandler.END
    except NoHomeworkError:
        await updater.message.reply_text('Дз нет', reply_markup=markup_menu)
        return ConversationHandler.END
    except Exception as e:
        await error(updater, context, e)
        return ConversationHandler.END


def initialization():  # Starting function
    # opening txt form
    global data
    with open('9_classes.json', encoding='utf-8') as json_file:
        data = json.load(json_file)[0]
    for clas in data.keys():
        for key in data[clas].keys():
            for day in data[clas][key].keys():
                data[clas][key][day] = list(map(lambda x: [KeyboardButton(x)], data[clas][key][day]))


    # Making an application of Telegram-bot
    application = Application.builder().token(BOT_TOKEN).build()

    # A handler for asking user about his class
    entry_or_change_class_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('change', change)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_asking)]},
        fallbacks=[CommandHandler('stop', stop)]
    )

    # A handler for uploading homework to database
    uploading_homework_handler = ConversationHandler(
        entry_points=[CommandHandler('send', send)],
        states={2: [MessageHandler(filters.TEXT & ~filters.COMMAND, getting_date)],
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_asking_in_dialog)],
                3: [MessageHandler(filters.TEXT & ~filters.COMMAND, asking_subject)],
                4: [MessageHandler(filters.TEXT & ~filters.COMMAND, asking_homework)]},
        fallbacks=[CommandHandler('stop', stop)]
    )

    # A handler for getting homework from database
    downloading_homework_handler = ConversationHandler(
        entry_points=[CommandHandler('get', get)],
        states={2: [MessageHandler(filters.TEXT & ~filters.COMMAND, getting_date_to_get)],
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, class_asking_in_dialog)],
                3: [MessageHandler(filters.TEXT & ~filters.COMMAND, asking_subject_to_get)]},
        fallbacks=[CommandHandler('stop', stop)]
    )

    # A handler for text messages out dialogs
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, text_answer)

    # Registration of handlers
    # ВНИМАНИЕ очень важен порядок: может съедать текстовый handler
    application.add_handler(entry_or_change_class_handler)
    application.add_handler(uploading_homework_handler)
    application.add_handler(downloading_homework_handler)
    application.add_handler(text_handler)
    application.run_polling()


if __name__ == '__main__':
    homework = ActiveHomework()
    initialization()
