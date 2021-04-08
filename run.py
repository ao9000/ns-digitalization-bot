import os
import telegram
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, ConversationHandler


# Commands
# Start command
def start(update, context):
    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("/Vehicle_physical_damage")]
    ]
    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Send message
    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode="MarkdownV2", reply_markup=keyboard_markup,
                             text="Hello there, what vehicle faults are you reporting?\n"
                                  "Tap the following commands to begin:\n"
                                  "1\.\) /Vehicle\_physical\_damage")


start_handler = CommandHandler('start', start)


# Vehicle physical damage command
# Conversation entry point
def vehicle_physical_damage(update, context):
    # Prompt user
    update.message.reply_text("What physical damage did the vehicle sustain?")

    return 1


vehicle_physical_damage_handler = CommandHandler('Vehicle_physical_damage', vehicle_physical_damage)


def get_physical_damage(update, context):
    damage = update.message.text
    context.user_data["physical_damage"] = damage

    if len(damage) < 4:
        update.message.reply_text("Please provide more details")
        return vehicle_physical_damage(update, context)

    update.message.reply_text("Alright, May I know your name?")

    return 2


def get_name(update, context):
    name = update.message.text
    context.user_data["name"] = name

    print(context.user_data["physical_damage"])
    print(context.user_data["name"])

    return ConversationHandler.END


# Error message for invalid commands
def error_message(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


error_handler = MessageHandler(Filters.command, error_message)


def main():
    # Define bot
    updater = Updater(token=os.getenv("bot_token"), use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[vehicle_physical_damage_handler],
        states={
            1: [MessageHandler(Filters.text, get_physical_damage)],
            2: [MessageHandler(Filters.text, get_name)]
        },
        fallbacks=[]
    )

    # Add handlers
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(start_handler)
    # dispatcher.add_handler(error_handler)

    # Start bot, stop when interrupted
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
