import os
import telegram
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters

# Define bot
updater = Updater(token=os.getenv("bot_token"), use_context=True)
dispatcher = updater.dispatcher


# Commands
# Start command
def start(update, context):
    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("/Vehicle_physical_damage")]
    ]
    keyboard_markup = telegram.ReplyKeyboardMarkup(choices)

    # Send message
    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode="MarkdownV2", reply_markup=keyboard_markup,
                             text="Hello there, what vehicle faults are you reporting?\n"
                                  "Tap the following commands to begin:\n"
                                  "1\.\) /Vehicle\_physical\_damage")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


# Error message for invalid commands
def error_message(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


error_handler = MessageHandler(Filters.command, error_message)
dispatcher.add_handler(error_handler)




if __name__ == '__main__':
    updater.start_polling()
