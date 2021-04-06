import os
from telegram.ext import Updater
from telegram.ext import CommandHandler

# Define bot
updater = Updater(token=os.getenv("bot_token"), use_context=True)
dispatcher = updater.dispatcher


# Commands
# Start command
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode="MarkdownV2",
                             text="*What can this bot do?*\n"
                                  "This is a platform for all vehicle fault reporting\. Users can update the vehicle "
                                  "management team about the fault they are facing with thier vehicle\. Vehicle "
                                  "management team will then contact the user to solve thier issue\.")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

if __name__ == '__main__':
    updater.start_polling()
