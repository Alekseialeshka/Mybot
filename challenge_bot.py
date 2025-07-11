import telebot
import random
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from telegram import Update
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from random import choice
from telegram.error import BadRequest
from telebot import types, TeleBot
from random import shuffle
from pyexpat.errors import messages
from telebot.types import Message
import time
import threading

API_TOKEN = '7905486303:AAH7VdvwWzp4eIeq3T30uXmPMDeLTSIlN5A'
bot = telebot.TeleBot('7905486303:AAH7VdvwWzp4eIeq3T30uXmPMDeLTSIlN5A')

ADMIN_ID = 5587077591  # ID администратора


# Функция для удаления сообщения через 5 секунд
def delete_message(chat_id, message_id):
    time.sleep(5)
    bot.delete_message(chat_id, message_id)


# Команда для бана пользователя
@bot.message_handler(commands=['ban'])
def ban_user(message):
    # Проверяем, что пользователь является администратором
    if message.from_user.id not in [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]:
        bot.reply_to(message, "У вас нет прав для бана пользователей.")
        return

    # Проверяем, что команда была использована с упоминанием пользователя
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        try:
            bot.ban_chat_member(message.chat.id, user_id)
            ban_message = bot.reply_to(message,
                                       f"Пользователь {message.reply_to_message.from_user.first_name} был забанен.")

            # Запускаем поток для удаления сообщения через 5 секунд
            threading.Thread(target=delete_message, args=(message.chat.id, ban_message.message_id)).start()
        except Exception as e:
            bot.reply_to(message, f"Ошибка при бане пользователя: {str(e)}")
    else:
        bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите забанить.")


# Словарь для хранения статусов доступа пользователей
user_access = {}
# Словарь для хранения уведомлений о запрете
notification_sent = {}
# Словарь для хранения ID сообщений с вопросами
question_messages = {}

# Вопросы
questions = {
    'Сколько будет 2 + 2?': ['3', '4', '5'],
    'Какой цвет у неба?': ['Зеленый', 'Синий', 'Красный'],
    'Сколько дней в неделе?': ['5', '6', '7']
}

current_question = None
current_answers = []


@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        welcome_msg = bot.send_message(message.chat.id,
                                       f'Добро пожаловать, {new_member.first_name}! Вы сейчас в режиме наблюдателя.')

        # Запускаем поток для удаления сообщения через 5 секунд
        threading.Thread(target=delete_welcome_message, args=(message.chat.id, welcome_msg.message_id)).start()

        # Устанавливаем статус доступа для нового участника
        user_access[new_member.id] = {'vhod': False}  # По умолчанию доступ запрещен
        notification_sent[new_member.id] = False  # Уведомление еще не отправлено
        # Удаляем возможность отправки сообщений
        bot.restrict_chat_member(message.chat.id, new_member.id, can_send_messages=False)

        # Запускаем вопрос для нового пользователя
        start_question(message, new_member.id)


def delete_welcome_message(chat_id, message_id):
    time.sleep(5)  # Задержка на 5 секунд
    bot.delete_message(chat_id, message_id)  # Удаляем сообщение


def start_question(message, user_id):
    global current_question, current_answers
    current_question = choice(list(questions.keys()))
    current_answers = questions[current_question]

    markup = types.InlineKeyboardMarkup()
    for answer in current_answers:
        markup.add(types.InlineKeyboardButton(answer, callback_data=answer))

    question_msg = bot.send_message(message.chat.id, current_question, reply_markup=markup)
    question_messages[user_id] = question_msg.message_id  # Сохраняем ID сообщения с вопросом


@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    global current_question

    if current_question:
        correct_answer = '4' if current_question == 'Сколько будет 2 + 2?' else\
        'Синий' if current_question == 'Какой цвет у неба?' else\
        '7'


    user_id = call.from_user.id

    if call.data == correct_answer:
       bot.answer_callback_query(call.id, "Верно!")
       user_access[user_id]['vhod'] = True  # Разрешаем пользователю писать в чат
       bot.restrict_chat_member(call.message.chat.id, user_id, can_send_messages=True)  # Разрешаем отправку сообщений

    # Удаляем сообщение с вопросом
       bot.delete_message(call.message.chat.id, question_messages[user_id])
       del question_messages[user_id]  # Удаляем ID сообщения из словаря

    else:
       bot.answer_callback_query(call.id, "Не верно! Вы будете удалены из группы.")
       # Удаляем пользователя из группы
       bot.kick_chat_member(call.message.chat.id, user_id)
       # Удаляем сообщение с вопросом (если оно еще существует)
    if user_id in question_messages:
       bot.delete_message(call.message.chat.id, question_messages[user_id])
       del question_messages[user_id]  # Удаляем ID сообщения из словаря

# Сбрасываем текущий вопрос
current_question = None


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    if user_id in user_access and not user_access[user_id]['vhod']:
        if not notification_sent[user_id]:
            bot.send_message(message.chat.id,
                             'Вы находитесь в режиме наблюдателя. Пожалуйста, ответьте на вопрос, чтобы получить доступ к отправке сообщений.')
            notification_sent[user_id] = True  # Помечаем уведомление как отправленное


# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Словарь для хранения сообщений пользователей
user_messages = defaultdict(list)

# Функция для обработки сообщений
def message_handler(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    current_time = datetime.now()

    # Добавляем текущее время сообщения в список сообщений пользователя
    user_messages[user_id].append(current_time)

    # Удаляем старые сообщения (более 5 секунд назад)
    user_messages[user_id] = [msg_time for msg_time in user_messages[user_id] if msg_time > current_time - timedelta(seconds=5)]

    # Проверяем количество сообщений за последние 5 секунд
    if len(user_messages[user_id]) > 10:
        context.bot.kick_chat_member(update.message.chat.id, user_id)
        context.bot.send_message(chat_id=update.message.chat.id,
                                 text=f"{update.message.from_user.first_name}, вы были кикнуты за спам!")

        # Очищаем записи пользователя после кика
        del user_messages[user_id]
bot.polling(none_stop=True)


