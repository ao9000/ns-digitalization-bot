import os
import telegram
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, ConversationHandler

# Define & initialize bot
updater = Updater(token=os.getenv("bot_token"), use_context=True)
dispatcher = updater.dispatcher


# Commands
# Start command
def start(update, context):
    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("/Vehicle_physical_damage")],
        [telegram.KeyboardButton("/Vehicle_unable_to_start")],
        [telegram.KeyboardButton("/Vehicle_tire_issue")]
    ]
    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Send message
    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode="MarkdownV2", reply_markup=keyboard_markup,
                             text="Hello there, what vehicle faults are you reporting?\n"
                                  "Tap the following commands to begin:\n"
                                  "1\.\) /Vehicle\_physical\_damage\n"
                                  "2\.\) /Vehicle\_unable\_to\_start\n"
                                  "3\.\) /Vehicle\_tire\_issue")


start_handler = CommandHandler('start', start)


# Vehicle physical damage command
# Conversation entry point
def vehicle_physical_damage(update, context):
    # Prompt user
    update.message.reply_text("What physical damage did the vehicle sustain?")

    return 5


vehicle_physical_damage_handler = CommandHandler('Vehicle_physical_damage', vehicle_physical_damage)


def get_physical_damage(update, context):
    damage = update.message.text
    context.user_data["physical_damage"] = damage

    update.message.reply_text("May I know your name?")

    return 0


# Get user information stage
def get_name(update, context):
    name = update.message.text
    context.user_data["name"] = name

    update.message.reply_text("What is the vehicle license plate number?")

    return 1


def get_vehicle_mid(update, context):
    mid = update.message.text
    context.user_data["mid"] = mid

    # Let user check entered details before sending
    update.message.reply_text(f'Name: {context.user_data["name"]}\n'
                              f'Physical damage: {context.user_data["physical_damage"]}\n'
                              f'License plate number: {context.user_data["mid"]}')

    update.message.reply_text("Is this correct? (y/n)")

    return 2


def send_details_to_mt_line(update, context):
    confirmation = update.message.text.lower()
    if confirmation in ["y", "yes"]:
        # Send information to specific people
        update.message.reply_text("Sending information to MTLine personnel")
        for chat_id in [814323433]:
            updater.bot.send_message(chat_id=chat_id,
                                     text=f'Name: {context.user_data["name"]}\n'
                                          f'Physical damage: {context.user_data["physical_damage"]}\n'
                                          f'License plate number: {context.user_data["mid"]}')
    else:
        # Exit conversation
        update.message.reply_text("Cancelled")
        return ConversationHandler.END


# Error messages
def error_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


error_command_handler = MessageHandler(Filters.command, error_command)


def error_insufficient_information(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid. Please provide more information.")


def main():
    conv_handler = ConversationHandler(
        entry_points=[vehicle_physical_damage_handler],
        states={
            0: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_name)],
            1: [MessageHandler(Filters.regex(r'([1-9]+MID)$'), get_vehicle_mid)],
            2: [MessageHandler(Filters.text, send_details_to_mt_line)],
            5: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_physical_damage)]
        },
        fallbacks=[
            # Match commands
            MessageHandler(Filters.command, error_command),
            # Regex to match any character below 4 character count
            MessageHandler(Filters.regex(r'^.{1,4}$'), error_insufficient_information)
        ]
    )

    # Add handlers
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(CommandHandler("send", send_details_to_mt_line))
    # dispatcher.add_handler(error_handler)

    # Start bot, stop when interrupted
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
