import os
import re
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
# Conversation entry point #1
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


# Vehicle unable to start command
# Conversation entry point #2
def vehicle_unable_to_start(update, context):
    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Unable to crank")],
        [telegram.KeyboardButton("Crank but not starting")],
        [telegram.KeyboardButton("Totally no response")]
    ]
    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Prompt user
    update.message.reply_text("What type of problem?", reply_markup=keyboard_markup)

    return 6


vehicle_unable_to_start_handler = CommandHandler('Vehicle_unable_to_start', vehicle_unable_to_start)


def get_unable_to_start_type(update, context):
    unable_start_type = update.message.text
    context.user_data["unable_start_type"] = unable_start_type

    update.message.reply_text("May I know your name?")

    return 0


# Vehicle tire issue command
# Conversation entry point #3
def vehicle_tire_issue(update, context):
    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Air leak")],
        [telegram.KeyboardButton("Flat")],
        [telegram.KeyboardButton("Burst")]
    ]
    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Prompt user
    update.message.reply_text("What happen to the tire?", reply_markup=keyboard_markup)

    return 6


vehicle_tire_issue_handler = CommandHandler('vehicle_tire_issue', vehicle_tire_issue)


def get_vehicle_tire_issue_type(update, context):
    tire_issue_type = update.message.text
    context.user_data["tire_issue_type"] = tire_issue_type

    update.message.reply_text("May I know your name?")

    return 7


# Get user information stage
def get_name(update, context):
    name = update.message.text
    context.user_data["name"] = name

    update.message.reply_text("What is the vehicle license plate number?")

    return 1


def get_vehicle_mid(update, context):
    mid = update.message.text
    context.user_data["mid"] = mid

    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Yes")],
        [telegram.KeyboardButton("No")]
    ]

    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Let user check entered details before sending
    update.message.reply_text(f'Name: {context.user_data["name"]}\n'
                              f'Physical damage: {context.user_data["physical_damage"]}\n'
                              f'License plate number: {context.user_data["mid"]}',
                              reply_markup=keyboard_markup)

    update.message.reply_text("Is this correct? (y/n)")

    return 2


def send_details_to_mt_line(update, context):
    print(context.user_data.items())
    confirmation = update.message.text.lower()
    if confirmation in ["y", "yes"]:
        update.message.reply_text("Sending information to MTLine personnel")

        # Send information to specific people
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
    update.message.reply_text("Sorry, I didn't understand that command")


error_command_handler = MessageHandler(Filters.command, error_command)


def error_user_cancelled(update, context):
    # Exit conversation
    context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelled")

    return ConversationHandler.END


def error_insufficient_input(update, context):
    update.message.reply_text("Invalid. Please provide more information")
    update.message.reply_text("Type /exit to cancel this conversation")


def error_invalid_input(update, context):
    update.message.reply_text("Invalid. Please provide a valid input")
    update.message.reply_text("Type /exit to cancel this conversation")


def main():
    conv_handler = ConversationHandler(
        entry_points=[
            vehicle_physical_damage_handler,
            vehicle_unable_to_start_handler,
            vehicle_tire_issue_handler
        ],
        states={
            # Gathering user information states
            0: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_name)],
            1: [MessageHandler(Filters.regex(re.compile(r'^([1-9]+MID)$', re.IGNORECASE)), get_vehicle_mid)],
            2: [MessageHandler((Filters.text & ~Filters.command & Filters.regex(re.compile(r'^(Yes|Y|No|N)$', re.IGNORECASE))), send_details_to_mt_line)],
            # Physical damage states
            5: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_physical_damage)],
            # Unable to start states
            6: [MessageHandler(Filters.regex(re.compile(r'^((Unable to crank)|(Crank but not starting)|(Totally no response))$', re.IGNORECASE)), get_unable_to_start_type)],
            # Tire issue states
            7: [MessageHandler(Filters.regex(re.compile(r'^((Air leak")|(Flat)|(Burst))$', re.IGNORECASE)), get_vehicle_tire_issue_type)]
        },
        fallbacks=[
            # User cancelled command
            MessageHandler((Filters.command & Filters.regex(re.compile(r'^(/exit)$', re.IGNORECASE))), error_user_cancelled),
            # Regex to match any character below 4 character count
            MessageHandler(Filters.regex(r'^.{1,4}$'), error_insufficient_input),
            # Match other commands
            MessageHandler((Filters.command & ~Filters.regex(re.compile(r'^(/exit)$', re.IGNORECASE))), error_command),
            # Match other invalid inputs
            MessageHandler((Filters.text & ~Filters.command), error_invalid_input)
        ]
    )

    # Add handlers
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(start_handler)
    # dispatcher.add_handler(error_command_handler)

    # Start bot, stop when interrupted
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
