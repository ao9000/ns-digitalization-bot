import os
import re
import telegram
import pytz
import logging
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, ConversationHandler, PicklePersistence

# Define logging settings
logging_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
datefmt='%d/%m/%Y, %H:%M:%S'
handlers = [logging.FileHandler('record.log', mode='a'), logging.StreamHandler()]
level = logging.INFO

# Initialize logging
logging.basicConfig(handlers=handlers, format=logging_format, datefmt=datefmt, level=logging.INFO)

logging.info("Initializing bot")


# Define custom error exception class
class EnvironmentVariableError(Exception):
    """Triggered when environment variables are not loaded before execution of script"""
    pass


# Helper function for formatting user data
def get_user_details(update):
    return f'UserID: {update.effective_user.id}, Name: {update.effective_user.first_name}' \
           f'{f" {update.effective_user.last_name}" if update.effective_user.last_name else ""}' \
           f'{f", Username: {update.effective_user.username}" if update.effective_user.username else ""}'


# Check if environment variables are loaded
logging.info("Checking environment variables")
environment_variables = ["bot_token", "recipient_list"]
# Check if environment variables are loaded
if any(item not in os.environ for item in environment_variables):
    logging.critical("Environment variables not loaded")
    raise EnvironmentVariableError("Environment variables not loaded")

# Check if environment variables are empty
if any(item for item in environment_variables if not os.getenv(item)):
    logging.critical("Environment variables are empty")
    raise EnvironmentVariableError("Environment variables are empty")


# Define & initialize bot
updater = Updater(token=os.getenv("bot_token"), use_context=True, persistence=PicklePersistence(filename='data'))
dispatcher = updater.dispatcher

# Format recipient list
recipient_list = os.getenv('recipient_list').split(",")
logging.info(f'{len(recipient_list)} recipients loaded')


# Commands
# Start command
def start(update, context):
    logging.info(f'{get_user_details(update)}, Action: /start')

    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("/Vehicle_physical_damage")],
        [telegram.KeyboardButton("/Vehicle_unable_to_start")],
        [telegram.KeyboardButton("/Vehicle_tire_issue")]
    ]
    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Send message with keyboard template
    context.bot.send_message(chat_id=update.effective_chat.id, parse_mode="MarkdownV2", reply_markup=keyboard_markup,
                             text="Hello there, what vehicle faults are you reporting?\n"
                                  "Tap the following commands to begin:\n"
                                  "1\.\) /Vehicle\_physical\_damage\n"
                                  "2\.\) /Vehicle\_unable\_to\_start\n"
                                  "3\.\) /Vehicle\_tire\_issue")


start_handler = CommandHandler('start', start)


# Decorator for paginating replies
def PaginationHandlerMeta(func):
    def PaginationHandler(*args, **kwargs):
        # Define separator
        separator = "\n" + ("\-" * 80) + "\n"

        # Get response
        response = func(*args, **kwargs)

        # Find update & context in parameters
        for arg in args:
            if isinstance(arg, telegram.update.Update):
                update = arg
            elif isinstance(arg, telegram.ext.callbackcontext.CallbackContext):
                context = arg

        if len(f"{separator}".join(part for part in response)) > 4096:
            # Construct paginated response
            start_index = 0
            for end_index, _ in enumerate(response, start=1):
                if len(f"{separator}".join(part for part in response[start_index:end_index])) > 4096:
                    # Remove last element and send
                    update.message.reply_text(parse_mode="MarkdownV2", text=f"{separator}".join(part for part in response[start_index:end_index - 1]))

                    # Check if last element
                    if end_index == len(response):
                        # Just send out last element
                        update.message.reply_text(parse_mode="MarkdownV2", text=response[end_index - 1])
                    else:
                        # Go back one index
                        start_index = end_index-1

                elif end_index == len(response):
                    # Last element
                    update.message.reply_text(parse_mode="MarkdownV2", text=f"{separator}".join(part for part in response[start_index:end_index]))
        else:
            # No need to paginate
            update.message.reply_text(parse_mode="MarkdownV2", text=f"{separator}".join(part for part in response))

    return PaginationHandler


# History command
@PaginationHandlerMeta
def history(update, context):
    logging.info(f'{get_user_details(update)}, Action: /history')
    if "history" in context.bot_data:
        return context.bot_data["history"]
    else:
        return ["Empty, go ahead and submit an issue and it will show up here"]


history_handler = CommandHandler('history', history, Filters.user(user_id=set(int(user_id) for user_id in recipient_list)))


# Vehicle physical damage command
# Conversation entry point #1
def vehicle_physical_damage(update, context):
    logging.info(f'{get_user_details(update)}, Action /Vehicle_physical_damage')

    # Prompt user
    update.message.reply_text("What physical damage did the vehicle sustain?")

    return 5


vehicle_physical_damage_handler = CommandHandler('Vehicle_physical_damage', vehicle_physical_damage)


def get_physical_damage(update, context):
    # Save user input
    damage = update.message.text
    context.user_data["physical_damage"] = damage

    logging.info(f'{get_user_details(update)}, Input: {damage}')

    # Prompt user
    update.message.reply_text("What is the vehicle MID number? (Numbers only)")

    return 0


# Vehicle unable to start command
# Conversation entry point #2
def vehicle_unable_to_start(update, context):
    logging.info(f'{get_user_details(update)}, Action: /Vehicle_unable_to_start')

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
    # Save user input
    unable_start_type = update.message.text
    context.user_data["unable_start_type"] = unable_start_type

    logging.info(f'{get_user_details(update)}, Input: {unable_start_type}')

    # Prompt user
    update.message.reply_text("What is the vehicle MID number? (Numbers only)")

    return 0


# Vehicle tire issue command
# Conversation entry point #3
def vehicle_tire_issue(update, context):
    logging.info(f'{get_user_details(update)}, Action: /Vehicle_tire_issue')

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
    # Save user input
    tire_issue_type = update.message.text
    context.user_data["tire_issue_type"] = tire_issue_type

    logging.info(f'{get_user_details(update)}, Input: {tire_issue_type}')

    # Prompt user
    update.message.reply_text("What is the vehicle MID number? (Numbers only)")

    return 0


# Get user information stage
def get_vehicle_mid(update, context):
    # Save user input
    mid = update.message.text
    context.user_data["mid"] = mid

    logging.info(f'{get_user_details(update)}, Input: {mid}')

    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Yes")],
        [telegram.KeyboardButton("No")]
    ]

    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Let user check entered details before sending
    message = update.message.reply_text(f'*Vehicle MID number*: {context.user_data["mid"]}\n'
                                        f'*Issue*: {f"Vehicle Physical Damage" if "physical_damage" in context.user_data else "Vehicle unable to start" if "unable_start_type" in context.user_data else "Vehicle tire issue"}'
                                        f' \({context.user_data["physical_damage"] if "physical_damage" in context.user_data else context.user_data["unable_start_type"] if "unable_start_type" in context.user_data else context.user_data["tire_issue_type"]}\)',
                                        reply_markup=keyboard_markup, parse_mode="MarkdownV2")

    # Prompt user
    update.message.reply_text("Is this correct? (y/n)")

    # Save message object for later use
    context.user_data["issue_summary"] = message

    return 1


# Sending user information & damage details to MTline personnel
def send_details_to_mt_line(update, context):
    # Standardise user input
    confirmation = update.message.text.lower()

    logging.info(f'{get_user_details(update)}, Input: {confirmation}')

    # Check if user input yes
    if confirmation in ["y", "yes"]:
        update.message.reply_text("Sending information to MTLine personnel")

        # Construct message
        text = f'*Datetime*: {context.user_data["issue_summary"].date.astimezone(pytz.timezone("Singapore")).strftime("%d/%m/%Y, %H:%M:%S")}\n'\
               f'*From user*: {get_user_details(update)}\n'\
               f'{context.user_data["issue_summary"].text_markdown_v2}'

        # Send information to specific people(s)
        for chat_id in recipient_list:
            try:
                # Send message
                updater.bot.send_message(chat_id=chat_id, text=text, parse_mode="MarkdownV2")
                logging.info(f"Sent issue to User: {context.bot.get_chat(chat_id)['first_name']}")
            except telegram.error.BadRequest:
                # User have not initialize a chat with bot yet
                logging.warning(f"User: {chat_id} have not talked to the bot before. Skipping.")

        # Save message into history
        if "history" in context.bot_data:
            context.bot_data["history"].append(text)
        else:
            context.bot_data["history"] = [text]
    else:
        logging.info(f'{get_user_details(update)}, Input: No')

        # Exit conversation
        update.message.reply_text("Cancelled")

    # Clear userdata
    context.user_data.clear()

    return ConversationHandler.END


# Error messages
# Invalid command (General)
def error_command_general(update, context):
    logging.info(f'{get_user_details(update)}, Error: Invalid command (General)')
    update.message.reply_text("Invalid. Please provide a valid command\n"
                              "Type /start to get started")


error_command_general_handler = MessageHandler(Filters.all, error_command_general)


# User cancelled conversation
def error_user_cancelled(update, context):
    logging.info(f'{get_user_details(update)}, Action: /exit')

    # Exit conversation
    context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelled\n"
                                                                    "Type /start to get started")

    # Clear userdata
    context.user_data.clear()

    return ConversationHandler.END


# User insufficient input
def error_insufficient_input(update, context):
    logging.info(f'{get_user_details(update)}, Error: Insufficient information provided')
    update.message.reply_text("Invalid. Please provide more information")
    update.message.reply_text("Type /exit to cancel this conversation")


# User invalid input
def error_invalid_input(update, context):
    logging.info(f'{get_user_details(update)}, Error: Incorrect information provided')
    update.message.reply_text("Invalid. Please provide a valid input")
    update.message.reply_text("Type /exit to cancel this conversation")


# User invalid command (Conversational)
def error_command_input(update, context):
    logging.info(f'{get_user_details(update)}, Error: Invalid command (Conversational)')
    update.message.reply_text("Invalid. Please provide a valid command")
    update.message.reply_text("Type /exit to cancel this conversation")


def main():
    # Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            vehicle_physical_damage_handler,
            vehicle_unable_to_start_handler,
            vehicle_tire_issue_handler
        ],
        states={
            # Gathering user information states
            0: [MessageHandler(Filters.regex(r'^[0-9]+$'), get_vehicle_mid)],
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
