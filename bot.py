from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, RegexHandler, Filters, JobQueue
from telegram import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Chat, User
import random
import time

__token__ = "mytoken"

__are_you_ready__, __is_opponent_ready__, __first_shots__, __second_shots__ = range(4)


def reset(bot, job):
    job.context['chat_data'].pop('duel')
    bot.send_message(job.context['chat_id'], text='Прошла минута, дуэлянты всё ещё не подготовились. Дуэль отменена.', reply_markup=ReplyKeyboardRemove())


def timeout(bot, job):
    job.context['chat_data'].pop('duel')
    bot.send_message(job.context['chat_id'], text=job.context['duelist'].mention_html() + ', отдай револьвер! В следующий раз думай быстрее!', parse_mode='HTML', reply_markup=ReplyKeyboardRemove())


def start_duel(bot, update, job_queue, chat_data):
    chat = update.message.chat
    if 'duel' in chat_data:
        update.message.reply_text('Сейчас уже идёт дуэль.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    duelist1 = update.message.from_user.mention_html()
    args = update.message.parse_entities(['mention', 'text_mention'])
    if len(args) != 1:
        update.message.reply_text('На дуэль можно вызвать строго одного человека.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    duelist2 = list(args.items())[0]
    if duelist2[0].user is None:
        duelist2 = duelist2[1]
    else:
        duelist2 = duelist2[0].user.mention_html()
    update.message.reply_text(duelist1 + ' вызвал ' + duelist2 + ' на дуэль! У дуэлянтов минута на подготовку!', parse_mode='HTML', quote=False, reply_markup=ReplyKeyboardRemove())
    time.sleep(1)
    bot.send_message(chat.id, duelist1 + ', ты готов?', parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[['Готов!']], one_time_keyboard=True, selective=True))
    job = job_queue.run_once(reset, 60, context={'chat_id': chat.id, 'chat_data': chat_data})
    chat_data['duel'] = {'first': duelist1, 'second': duelist2, 'job': job}
    return __are_you_ready__


def one_ready(bot, update, job_queue, chat_data):
    if chat_data['duel']['first'] != update.message.from_user.mention_html():
        return __are_you_ready__
    chat = update.message.chat
    chat_data['duel']['first'] = update.message.from_user
    update.message.reply_text('Отлично!', reply_markup=ReplyKeyboardRemove(), quote=False)
    time.sleep(1)
    bot.send_message(chat.id, chat_data['duel']['second'] + ', ты готов?', parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[['Готов!']], one_time_keyboard=True, selective=True))
    return __is_opponent_ready__


def two_ready(bot, update, job_queue, chat_data):
    chat = update.message.chat
    if chat_data['duel']['second'] != update.message.from_user.mention_html() and chat_data['duel']['second'] != '@' + update.message.from_user.username:
        return __is_opponent_ready__
    chat_data['duel']['second'] = update.message.from_user
    update.message.reply_text('Отлично!', reply_markup=ReplyKeyboardRemove(), quote=False)
    chat_data['duel']['job'].schedule_removal()
    chat_data['duel']['shots'] = 1
    bot.send_message(chat.id, 'Заряжаю револьвер. Стреляет ' + chat_data['duel']['first'].mention_html() + '!',
                     parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[['Стреляю!', 'Не стреляю!']], one_time_keyboard=True, selective=True))
    chat_data['duel']['job'] = job_queue.run_once(timeout, 60, context={'chat_id': chat.id, 'duelist': chat_data['duel']['first'], 'chat_data': chat_data})
    return __first_shots__


def first_shot(bot, update, job_queue, chat_data):
    chat = update.message.chat
    chat_data['duel']['job'].schedule_removal()
    lucky = random.randint(1, 6) > chat_data['duel']['shots']
    if update.message.text == 'Стреляю!':
        if not lucky:
            bot.send_message(chat.id, chat_data['duel']['first'].mention_html() + ' не повезло! Побеждает ' + chat_data['duel']['second'].mention_html() + '!',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    else:
        if lucky:
            bot.send_message(chat.id, chat_data['duel']['first'].mention_html() + ' решил не стрелять.',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            time.sleep(1)
            bot.send_message(chat.id, 'Патрона нет. Значит, побеждает ' + chat_data['duel']['second'].mention_html() + '!',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        else:
            bot.send_message(chat.id, chat_data['duel']['first'].mention_html() + ' решил не стрелять.',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            time.sleep(1)
            bot.send_message(chat.id, 'Интуиция тебя не подвела, ' + chat_data['duel']['first'].mention_html() + ', в каморе действительно был патрон. Ты победил!',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    bot.send_message(chat.id, chat_data['duel']['first'].mention_html() + ' выстрелил и остался жив! Продолжаем игру.',
                     parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
    time.sleep(1)
    bot.send_message(chat.id, 'Стреляет ' + chat_data['duel']['second'].mention_html() + '!',
                     parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[['Стреляю!', 'Не стреляю!']], one_time_keyboard=True, selective=True))
    chat_data['duel']['job'] = job_queue.run_once(timeout, 60, context={'chat_id': chat.id, 'duelist': chat_data['duel']['second'], 'chat_data': chat_data})
    return __second_shots__


def second_shot(bot, update, job_queue, chat_data):
    chat = update.message.chat
    chat_data['duel']['job'].schedule_removal()
    lucky = random.randint(1, 6) > chat_data['duel']['shots']
    if update.message.text == 'Стреляю!':
        if not lucky:
            bot.send_message(chat.id, chat_data['duel']['second'].mention_html() + ' не повезло! Побеждает ' + chat_data['duel']['first'].mention_html() + '!',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    else:
        if lucky:
            bot.send_message(chat.id, chat_data['duel']['second'].mention_html() + ' решил не стрелять.',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            time.sleep(1)
            bot.send_message(chat.id, 'Патрона нет. Значит, побеждает ' + chat_data['duel']['first'].mention_html() + '!',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        else:
            bot.send_message(chat.id, chat_data['duel']['second'].mention_html() + ' решил не стрелять.',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            time.sleep(1)
            bot.send_message(chat.id, 'Интуиция тебя не подвела, ' + chat_data['duel']['second'].mention_html() + ', в каморе действительно был патрон. Ты победил!',
                             parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    bot.send_message(chat.id, chat_data['duel']['second'].mention_html() + ' выстрелил и остался жив! Продолжаем игру.', parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
    time.sleep(1)
    chat_data['duel']['shots'] += 1
    if chat_data['duel']['shots'] == 6:
        bot.send_message(chat.id, 'Кажется, если я добавлю патрон, исход будет очевиден. Что ж, ' +
                         chat_data['duel']['first'].mention_html() + ', предлагаю тебе помириться с ' + chat_data['duel']['second'].mention_html() + '.',
                         parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    bot.send_message(chat.id, 'Заряжаю ещё один патрон! Теперь их ' + str(chat_data['duel']['shots']) + '!', reply_markup=ReplyKeyboardRemove())
    bot.send_message(chat.id, 'Стреляет ' + chat_data['duel']['first'].mention_html() + '!',
                     parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(keyboard=[['Стреляю!', 'Не стреляю!']], one_time_keyboard=True, selective=True))
    chat_data['duel']['job'] = job_queue.run_once(timeout, 60, context={'chat_id': chat.id, 'duelist': chat_data['duel']['first'], 'chat_data': chat_data})
    return __first_shots__


def pigeon(bot, update, job_queue, chat_data):
    update.message.reply_text('Голубь ридонли на сутки. Приятного дня.', quote=False, reply_markup=ReplyKeyboardRemove())


if __name__ == '__main__':
    updater = Updater(__token__)

    updater.dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler(command='duel', callback=start_duel, filters=(Filters.entity('mention') | Filters.entity('text_mention')) & Filters.group, pass_chat_data=True, pass_job_queue=True)],
        states={
            __are_you_ready__: [RegexHandler(pattern='^Готов!$', callback=one_ready, pass_chat_data=True, pass_job_queue=True)],

            __is_opponent_ready__: [RegexHandler(pattern='^Готов!$', callback=two_ready, pass_chat_data=True, pass_job_queue=True)],

            __first_shots__: [RegexHandler(pattern='^(Стреляю!|Не стреляю!)$', callback=first_shot, pass_chat_data=True, pass_job_queue=True)],

            __second_shots__: [RegexHandler(pattern='^(Стреляю!|Не стреляю!)$', callback=second_shot, pass_chat_data=True, pass_job_queue=True)]
        },
        fallbacks=[],
        conversation_timeout=60,
        per_user=False))
    updater.dispatcher.add_handler(CommandHandler('pigeon', pigeon, pass_chat_data=True, pass_job_queue=True))

    updater.start_polling()
    updater.idle()
