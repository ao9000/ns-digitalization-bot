import telegram
import os
from telegram.ext import Updater
from telegram.ext import CommandHandler

bot = telegram.Bot(token=os.getenv("BOT_TOKEN", False))
updater = Updater(token=os.getenv("BOT_TOKEN", False), use_context=True)
dispatcher = updater.dispatcher


def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
print(bot.get_me())
updater.start_polling()