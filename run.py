import os
import re
import telegram
import pytz
import logging
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, ConversationHandler, PicklePersistence


class EnvironmentVariableError(Exception):
    """Triggered when environment variables are not loaded before execution of script"""
    pass


# Define logging level
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logging.info("Checking environment variables")
# Check if environment variables are loaded
environment_variables = ["bot_token", "recipient_list"]

if any(item not in os.environ for item in environment_variables):
    raise EnvironmentVariableError("Environment variables not loaded")

# Check if environment variables are not empty
if any(item for item in environment_variables if not os.getenv(item)):
    raise EnvironmentVariableError("Environment variables are empty")


# Define & initialize bot
updater = Updater(token=os.getenv("bot_token"), use_context=True, persistence=PicklePersistence(filename='data'))
dispatcher = updater.dispatcher

# Format recipient list
recipient_list = os.getenv('recipient_list').split(",")
logging.info(f'Recipient list loaded, {len(recipient_list)} recipients detected')


# Commands
# Start command
def start(update, context):
    logging.info(f'Start command was called by {update.effective_user.name}')
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


# History command
def history(update, context):
    separator = "\n"+("\-"*80)+"\n"
    if "history" in context.bot_data:
        context.bot.send_message(chat_id=update.effective_chat.id, parse_mode="MarkdownV2",
                                 text=f'{f"{separator}".join(message for message in context.bot_data["history"])}')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Empty, go ahead and submit an issue and it will show up here')


history_handler = CommandHandler('history', history, Filters.user(user_id=set(int(user_id) for user_id in recipient_list)))


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

    update.message.reply_text("What is the vehicle license plate number?")

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

    update.message.reply_text("What is the vehicle license plate number?")

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

    return 7


vehicle_tire_issue_handler = CommandHandler('vehicle_tire_issue', vehicle_tire_issue)


def get_vehicle_tire_issue_type(update, context):
    tire_issue_type = update.message.text
    context.user_data["tire_issue_type"] = tire_issue_type

    update.message.reply_text("What is the vehicle license plate number?")

    return 0


# Get user information stage
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
    message = update.message.reply_text(f'*License plate number*: {context.user_data["mid"]}\n'
                                        f'*Issue*: {f"Vehicle Physical Damage" if "physical_damage" in context.user_data else "Vehicle unable to start" if "unable_start_type" in context.user_data else "Vehicle tire issue"}'
                                        f' \({context.user_data["physical_damage"] if "physical_damage" in context.user_data else context.user_data["unable_start_type"] if "unable_start_type" in context.user_data else context.user_data["tire_issue_type"]}\)',
                                        reply_markup=keyboard_markup, parse_mode="MarkdownV2")

    update.message.reply_text("Is this correct? (y/n)")

    # Save message object for later use
    context.user_data["issue_summary"] = message

    return 1


# Sending user information & damage details to MTline personnel
def send_details_to_mt_line(update, context):
    confirmation = update.message.text.lower()
    if confirmation in ["y", "yes"]:
        update.message.reply_text("Sending information to MTLine personnel")

        # Construct message
        text = f'*Datetime*: {context.user_data["issue_summary"].date.astimezone(pytz.timezone("Singapore")).strftime("%d/%m/%Y, %H:%M:%S")}\n'\
               f'*From user*: {update.message.from_user["first_name"]} {update.message.from_user["last_name"]} \(@{update.message.from_user["username"]}\)\n'\
               f'{context.user_data["issue_summary"].text_markdown_v2}'

        # Send information to specific people
        for chat_id in recipient_list:
            try:
                updater.bot.send_message(chat_id=chat_id, text=text, parse_mode="MarkdownV2")
            except telegram.error.BadRequest:
                # User have not initialize a chat with bot yet
                print(f"User: {chat_id} have not talked to the bot before. Skipping.")

        # Save message into history
        if "history" in context.bot_data:
            context.bot_data["history"].append(text)
        else:
            context.bot_data["history"] = [text]
    else:
        # Exit conversation
        update.message.reply_text("Cancelled")

    # Clear userdata
    context.user_data.clear()

    return ConversationHandler.END


# Error messages
def error_command_general(update, context):
    update.message.reply_text("Invalid. Please provide a valid command")


error_command_general_handler = MessageHandler(Filters.command, error_command_general)


def error_user_cancelled(update, context):
    # Exit conversation
    context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelled")

    # Clear userdata
    context.user_data.clear()

    return ConversationHandler.END


def error_insufficient_input(update, context):
    update.message.reply_text("Invalid. Please provide more information")
    update.message.reply_text("Type /exit to cancel this conversation")


def error_invalid_input(update, context):
    update.message.reply_text("Invalid. Please provide a valid input")
    update.message.reply_text("Type /exit to cancel this conversation")


def error_command_input(update, context):
    update.message.reply_text("Invalid. Please provide a valid command")
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
            0: [MessageHandler(Filters.regex(re.compile(r'^([1-9]+MID)$', re.IGNORECASE)), get_vehicle_mid)],
            1: [MessageHandler((Filters.text & ~Filters.command & Filters.regex(re.compile(r'^(Yes|Y|No|N)$', re.IGNORECASE))), send_details_to_mt_line)],
            # Physical damage states
            5: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_physical_damage)],
            # Unable to start states
            6: [MessageHandler(Filters.regex(re.compile(r'^((Unable to crank)|(Crank but not starting)|(Totally no response))$', re.IGNORECASE)), get_unable_to_start_type)],
            # Tire issue states
            7: [MessageHandler(Filters.regex(re.compile(r'^((Air leak)|(Flat)|(Burst))$', re.IGNORECASE)), get_vehicle_tire_issue_type)]
        },
        fallbacks=[
            # User cancelled command
            MessageHandler((Filters.command & Filters.regex(re.compile(r'^(/exit)$', re.IGNORECASE))), error_user_cancelled),
            # Regex to match any character below 4 character count
            MessageHandler(Filters.regex(r'^.{1,4}$'), error_insufficient_input),
            # Match other commands
            MessageHandler((Filters.command & ~Filters.regex(re.compile(r'^(/exit)$', re.IGNORECASE))), error_command_input),
            # Match other invalid inputs
            MessageHandler((Filters.text & ~Filters.command), error_invalid_input)
        ]
    )

    # Add handlers
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(history_handler)
    dispatcher.add_handler(error_command_general_handler)

    # Start bot, stop when interrupted
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
