import os
import re
import telegram
from pytz import timezone
import logging
import datetime
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, ConversationHandler, PicklePersistence

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


# Helper function for formatting user data
def get_user_details(update):
    return f'*UserID:* {update.effective_user.id}, *Name:* {update.effective_user.first_name}' \
           f'{f" {update.effective_user.last_name}" if update.effective_user.last_name else ""}' \
           f'{f", *Username:* {update.effective_user.username}" if update.effective_user.username else ""}'


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


# Commands
# History command
@PaginationHandlerMeta
def history(update, context):
    logging.info(f'{get_user_details(update)}, Action: /history')
    if "history" in context.bot_data:
        return context.bot_data["history"]
    else:
        return ["Empty, go ahead and submit a fault and it will show up here"]


history_handler = CommandHandler('history', history, Filters.user(user_id=set(int(user_id) for user_id in recipient_list)))


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
    # Define keyboard choices
    choices = [
        [telegram.KeyboardButton("Yes")],
        [telegram.KeyboardButton("No")]
    ]

    keyboard_markup = telegram.ReplyKeyboardMarkup(choices, one_time_keyboard=True)

    # Let user check entered details before sending
    message = update.message.reply_text(f'*Type of fault*: {context.user_data["type_of_fault"]}\n'
                                        f'*Description*: {context.user_data["description_of_fault"]}\n'
                                        f'*Location*: {context.user_data["location_of_fault"]}',
                                        reply_markup=keyboard_markup, parse_mode="MarkdownV2")

    # Prompt user
    update.message.reply_text("Is this correct? (y/n)")

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
        # Construct message
        text = f'*Datetime*: {context.user_data["fault_summary"].date.astimezone(tz).strftime("%d/%m/%Y, %H:%M:%S")}\n'\
               f'{get_user_details(update)}\n'\
               f'{context.user_data["fault_summary"].text_markdown_v2}'

        update.message.reply_text("Sending information to Maintenance clerks")

        # Send information to specific people(s)
        for chat_id in recipient_list:
            try:
                # Send message
                updater.bot.send_message(chat_id=chat_id, text=text, parse_mode="MarkdownV2")
                logging.info(f"Sent fault details to User: {context.bot.get_chat(chat_id)['first_name']}")
            except telegram.error.BadRequest:
                # User have not initialize a chat with bot yet
                logging.warning(f"User: {chat_id} have not talked to the bot before. Skipping.")

        update.message.reply_text("Done\n"
                                  "Type /start to submit another fault")

        # Save message into history
        if "history" in context.bot_data:
            context.bot_data["history"].append(text)
        else:
            context.bot_data["history"] = [text]
    else:
        logging.info(f'{get_user_details(update)}, Input: No')

        # Exit conversation
        update.message.reply_text("Cancelled\n"
                                  "Type /start to submit a new fault")

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
                                                                    "Type /start to submit a new fault")

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


def main():
    # Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            new_fault_handler
        ],
        states={
            # Gathering user information states
            0: [MessageHandler((Filters.text & ~Filters.command & Filters.regex(re.compile(r'^(Yes|Y|No|N)$', re.IGNORECASE))), send_details_to_maintenance_clerks)],
            # Type of fault
            5: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_type_of_fault)],
            # Description of fault
            6: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_description_of_fault)],
            # Location of fault
            7: [MessageHandler((Filters.text & ~Filters.command & ~Filters.regex(r'^.{1,4}$')), get_location_of_fault)]
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
    dispatcher.add_handler(error_command_general_handler)

    # Start bot, stop when interrupted
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
