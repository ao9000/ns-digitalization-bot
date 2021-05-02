import os
import re
import telegram
from pytz import timezone
import logging
import datetime
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, ConversationHandler, PicklePersistence
from webserver import keep_alive
from telegram.utils.helpers import escape_markdown

# Initialize logging
# Define timezone
tz = timezone('Asia/Singapore')
logging.Formatter.converter = lambda *args: datetime.datetime.now(tz).timetuple()

# Modify root logger
logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
datefmt = '%d/%m/%Y, %H:%M:%S'
handlers = [logging.FileHandler('record.log', mode='a'), logging.StreamHandler()]
level = logging.INFO

logging.basicConfig(handlers=handlers, format=logging_format, datefmt=datefmt, level=logging.INFO)


# Define custom error exception class
class EnvironmentVariableError(Exception):
    """Triggered when environment variables are not loaded before execution of script"""
    pass


# Helper functions
# Formatting user data for display
def display_user_details(update):
    response = f'*Name:* [{escape_markdown(text=update.effective_user.first_name, version=2)}](tg://user?id={update.effective_user.id})'\
               f'{f" [{escape_markdown(text=update.effective_user.last_name, version=2)}](tg://user?id={update.effective_user.id})" if update.effective_user.last_name else ""}'\
               f'{f", *Username:* [{escape_markdown(text=update.effective_user.username, version=2)}](https://t.me/{update.effective_user.username})" if update.effective_user.username else ""}'
    return response


# Formatting user data for logging
def get_user_details(update):
    response = f'UserID: {update.effective_user.id}, Name: {update.effective_user.first_name}'\
               f'{f" {update.effective_user.last_name}" if update.effective_user.last_name else ""}'\
               f'{f", Username: {update.effective_user.username}" if update.effective_user.username else ""}'
    return response


# Get latest fault running number and returns a new fault number
def get_fault_index(context):
    # Both dicts are not empty
    if all(context.bot_data[dict_name] for dict_name in ["active_history", "resolved_history"]):
        index = len(context.bot_data['active_history']) + len(context.bot_data['resolved_history'])
    elif context.bot_data["active_history"]:
        index = len(context.bot_data["active_history"])
    elif context.bot_data["resolved_history"]:
        index = len(context.bot_data["resolved_history"])
    else:
        # Both dict empty
        index = 0

    return index + 1


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

# Initialize bot_data dicts
if "active_history" not in dispatcher.bot_data:
    dispatcher.bot_data['active_history'] = {}
if "resolved_history" in dispatcher.bot_data:
    dispatcher.bot_data['resolved_history'] = {}

# Format recipient list
recipient_list = os.getenv('recipient_list').split(",")
logging.info(f'{len(recipient_list)} recipients loaded')


# Decorator for paginating replies
def PaginationHandlerMeta(func):
    def PaginationHandler(*args, **kwargs):
        # Define separator
        separator = "\n\n\n"

        # Get response
        response = func(*args, **kwargs)

        # Find update & context in parameters
        for arg in args:
            if isinstance(arg, telegram.update.Update):
                update = arg
            elif isinstance(arg, telegram.ext.callbackcontext.CallbackContext):
                context = arg

        if isinstance(response, dict):
            # Dict, need to check for pagination
            if len(f"{separator}".join(part for part in response.values())) > 4096:
                # Get key references
                keys = list(response.keys())
                # Construct paginated response
                start_index = 0
                for end_index, _ in enumerate(keys, start=1):
                    if len(f"{separator}".join(response[key] for key in keys[start_index:end_index])) > 4096:
                        # Remove last element and send
                        update.message.reply_text(parse_mode="MarkdownV2", text=f"{separator}".join(
                            response[key] for key in keys[start_index:end_index - 1]))

                        # Check if last element
                        if end_index == len(response):
                            # Just send out last element
                            update.message.reply_text(parse_mode="MarkdownV2", text=response[keys[end_index - 1]])
                        else:
                            # Go back one index
                            start_index = end_index - 1

                    elif end_index == len(response):
                        # Last element without exceeding message character count
                        update.message.reply_text(parse_mode="MarkdownV2", text=f"{separator}".join(
                            response[key] for key in keys[start_index:end_index]))
            else:
                # No need to paginate
                update.message.reply_text(parse_mode="MarkdownV2", text=f"{separator}".join(part for part in response.values()))
        else:
            # String, single output, no need paginate
            update.message.reply_text(parse_mode="MarkdownV2", text=response)

        return ConversationHandler.END

    return PaginationHandler


# Commands
# History command
def history(update, context):
    logging.info(f'{get_user_details(update)}, Action: /history')

    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Active")],
        [telegram.KeyboardButton("Resolved")],
    ]

    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Prompt user for active or resolved fault history
    update.message.reply_text(f"Choose *active* or *resolved* fault history", reply_markup=keyboard_markup, parse_mode="MarkdownV2")

    return 100


history_handler = CommandHandler('history', history, Filters.user(user_id=set(int(user_id) for user_id in recipient_list)))


@PaginationHandlerMeta
def get_history_version(update, context):
    # Standardise user input
    history_version = update.message.text.lower()

    # Logging
    logging.info(f'{get_user_details(update)}, Input: {history_version}')

    if history_version == "active":
        if context.bot_data["active_history"]:
            return context.bot_data["active_history"]
        else:
            return "No active faults, go ahead and submit a new fault and it will show up here"
    else:
        # Resolved history
        if context.bot_data["resolved_history"]:
            return context.bot_data["resolved_history"]
        else:
            return "No resolved faults, go ahead and mark an active fault as resolved and it will show up here"


def mark_resolve_active_fault(update, context):
    # Handle user input
    fault_id = context.args

    if not fault_id:
        logging.info(f'{get_user_details(update)}, Error: No arguments provided')
        # Empty list
        update.message.reply_text("No arguments provided, please provide a valid fault id")
    elif "".join(word for word in fault_id).strip().isdigit():
        logging.info(f'{get_user_details(update)}, Input: {fault_id}')

        # Integer passed, proceed to execute function
        fault_id = int("".join(word for word in fault_id).strip())
        # Move fault from active dict to resolved dict
        try:
            context.bot_data["resolved_history"][fault_id] = context.bot_data["active_history"].pop(fault_id)
            logging.info(f'{get_user_details(update)}, Fault id: {fault_id} marked as resolved')

            # Update everyone in the recipient list
            for chat_id in recipient_list:
                try:
                    # Send message
                    updater.bot.send_message(chat_id=chat_id, text=f"Fault id: {fault_id} has been marked as resolved")
                    logging.info(f"Sent resolved fault notification to: {context.bot.get_chat(chat_id)['first_name']}")
                except telegram.error.BadRequest:
                    # User have not initialize a chat with bot yet
                    logging.warning(f"User: {chat_id} have not talked to the bot before. Skipping.")
        except KeyError:
            # Key not found in active history dict
            update.message.reply_text("No such active fault id")
            logging.info(f'{get_user_details(update)}, Error: Non integer argument provided')
    else:
        # Other data type passed, error
        update.message.reply_text("Unexpected arguments provided, please provide a valid fault id")
        logging.info(f'{get_user_details(update)}, Error: Invalid arguments provided')


mark_resolve_active_fault_handler = CommandHandler('resolved', mark_resolve_active_fault, Filters.user(user_id=set(int(user_id) for user_id in recipient_list)))


# Start command
# Conversation entry point #1
def start(update, context):
    logging.info(f'{get_user_details(update)}, Action: /start')

    # Prompt user
    update.message.reply_text("Type of fault?")

    return 5


new_fault_handler = CommandHandler('start', start)


def get_type_of_fault(update, context):
    # Save user input
    type_of_fault = update.message.text
    context.user_data["type_of_fault"] = type_of_fault

    logging.info(f'{get_user_details(update)}, Input: {type_of_fault}')

    # Prompt user
    update.message.reply_text("Description of fault?")

    return 6


def get_description_of_fault(update, context):
    # Save user input
    description_of_fault = update.message.text
    context.user_data["description_of_fault"] = description_of_fault

    logging.info(f'{get_user_details(update)}, Input: {description_of_fault}')

    # Prompt user
    update.message.reply_text("Location of fault? (Blk no, level, room no etc)")

    return 7


def get_location_of_fault(update, context):
    # Save user input
    location_of_fault = update.message.text
    context.user_data["location_of_fault"] = location_of_fault

    logging.info(f'{get_user_details(update)}, Input: {location_of_fault}')

    # Generating fault summary message
    # Let user check entered details before sending
    response = f'*Type of fault:* {escape_markdown(text=context.user_data["type_of_fault"], version=2)}\n'\
               f'*Description:* {escape_markdown(text=context.user_data["description_of_fault"], version=2)}\n'\
               f'*Location:* {escape_markdown(text=context.user_data["location_of_fault"], version=2)}'
    message = update.message.reply_text(text=response, parse_mode="MarkdownV2")

    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Yes")],
        [telegram.KeyboardButton("No")]
    ]

    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Prompt user
    update.message.reply_text("Is this correct? (y/n)", reply_markup=keyboard_markup)

    # Save message object for later use
    context.user_data["fault_summary"] = message
    
    return 0


# Sending user information & damage details to Maintenance personnel
def send_details_to_maintenance_clerks(update, context):
    # Standardise user input
    confirmation = update.message.text.lower()

    logging.info(f'{get_user_details(update)}, Input: {confirmation}')

    # Check if user input yes
    if confirmation in ["y", "yes"]:
        # Get running number for fault id
        # Combine len for both resolved & active fault records to find id
        fault_id = get_fault_index(context)

        # Construct message
        response = f'*Fault ID:* {fault_id}\n'\
                   f'*Datetime:* {context.user_data["fault_summary"].date.astimezone(tz).strftime("%d/%m/%Y, %H:%M:%S")}\n'\
                   f'{display_user_details(update)}\n'\
                   f'{context.user_data["fault_summary"].text_markdown_v2}'

        # Send information to specific people(s)
        for chat_id in recipient_list:
            try:
                # Send message
                updater.bot.send_message(chat_id=chat_id, text=f"New fault has been submitted!")
                updater.bot.send_message(chat_id=chat_id, text=response, parse_mode="MarkdownV2")
                logging.info(f"Sent fault details to User: {context.bot.get_chat(chat_id)['first_name']}")
            except telegram.error.BadRequest:
                # User have not initialize a chat with bot yet
                logging.warning(f"User: {chat_id} have not talked to the bot before. Skipping.")

        update.message.reply_text("Fault submitted, we will attend to you shortly")
        update.message.reply_text("Type /start to submit another fault")

        # Save message into history
        context.bot_data['active_history'][fault_id] = response

        logging.info(f'Saved new fault id: {fault_id} to bot_data')
    else:
        # Exit conversation
        update.message.reply_text("Cancelled")
        update.message.reply_text("Type /start to submit a new fault")

    # Clear userdata
    context.user_data.clear()

    return ConversationHandler.END


# Error messages
# Invalid command (General)
def error_command_general(update, context):
    logging.info(f'{get_user_details(update)}, Error: Invalid command (General)')
    update.message.reply_text("Invalid. Please provide a valid command")
    update.message.reply_text("Type /start to get started")


error_command_general_handler = MessageHandler(Filters.all, error_command_general)


# User cancelled conversation
def error_user_cancelled(update, context):
    logging.info(f'{get_user_details(update)}, Action: /exit')

    # Exit conversation
    update.message.reply_text("Cancelled")
    update.message.reply_text("Type /start to submit a new fault")

    # Clear userdata
    context.user_data.clear()

    return ConversationHandler.END


# User insufficient input
def error_insufficient_input(update, context):
    logging.info(f'{get_user_details(update)}, Error: Insufficient information provided')
    update.message.reply_text("Invalid. Please provide more information")
    update.message.reply_text("Type /exit to cancel this conversation")


# User invalid command (Conversational)
def error_command_input(update, context):
    logging.info(f'{get_user_details(update)}, Error: Invalid command (Conversational)')
    update.message.reply_text("Invalid. Please provide a valid command")
    update.message.reply_text("Type /exit to cancel this conversation")


# Define conversation handler
conv_handler = ConversationHandler(
    entry_points=[
        new_fault_handler,
        history_handler
    ],
    states={
        # Gathering user information states
        0: [MessageHandler((Filters.text & ~Filters.command & Filters.regex(re.compile(r'^(Yes|Y|No|N)$', re.IGNORECASE))), send_details_to_maintenance_clerks)],
        # Type of fault
        5: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_type_of_fault)],
        # Description of fault
        6: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_description_of_fault)],
        # Location of fault
        7: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_location_of_fault)],
        # Selecting history version
        100: [MessageHandler(Filters.text & ~Filters.command & Filters.regex(re.compile(r'^(Active|Resolved)$', re.IGNORECASE)), get_history_version)]
    },
    fallbacks=[
        # User cancelled command
        MessageHandler((Filters.command & Filters.regex(re.compile(r'^(/exit)$', re.IGNORECASE))), error_user_cancelled),
        # Regex to match any character below 4 character count
        MessageHandler(Filters.regex(r'^.{1,4}$'), error_insufficient_input),
        # Match other commands
        MessageHandler((Filters.command & ~Filters.regex(re.compile(r'^(/exit)$', re.IGNORECASE))), error_command_input)
    ]
)

# Add handlers
dispatcher.add_handler(conv_handler)
dispatcher.add_handler(history_handler)
dispatcher.add_handler(mark_resolve_active_fault_handler)
dispatcher.add_handler(error_command_general_handler)
# Start bot, stop when interrupted
keep_alive()
updater.start_polling()
updater.idle()
