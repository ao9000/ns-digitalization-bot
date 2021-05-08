import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, InlineQueryHandler
from telegram.utils.helpers import escape_markdown

# Define bot
updater = Updater(token=os.getenv("bot_token"), use_context=True)
dispatcher = updater.dispatcher

# Initialize bot_data
if "acknowledged" not in dispatcher.bot_data:
    dispatcher.bot_data["acknowledged"] = []


# Helper functions
def get_acknowledge_inline_button():
    inline_button = [
        [
            InlineKeyboardButton("Acknowledge", callback_data='Acknowledge')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(inline_button)

    return reply_markup


def get_menu_inline_button():
    inline_button = [
        [
            InlineKeyboardButton("Publish", switch_inline_query="adas"),
            InlineKeyboardButton("Acknowledge", callback_data='Acknowledge')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(inline_button)

    return reply_markup


def handle_inline_query(update, context):
    query = update.inline_query

    print(query)

    results = [
        InlineQueryResultArticle(
            id="123",
            title="Forward Poll",
            input_message_content=InputTextMessageContent(message_text="ELLO")
        )
    ]

    update.inline_query.answer(results)


inline_query_handler = InlineQueryHandler(handle_inline_query)


# Commands
# Start command
def start(update, context):
    # Define template
    text = f"*Recall\!*\n\n"\
           f"Acknowledged\:"

    update.message.reply_text(text=text,
                              parse_mode="MarkdownV2",
                              reply_markup=get_menu_inline_button())


start_handler = CommandHandler('start', start)


def inline_button_callback(update, context):
    # Save query parameters
    query = update.callback_query

    # Edit message to add user into acknowledged list
    if query.data == "Acknowledge":
        # Check if user is already acknowledged
        if (userid := query.from_user.id) not in context.bot_data["acknowledged"]:
            # Get name of the user who pressed button
            user = f'{query.from_user.first_name} {query.from_user.last_name if query.from_user.last_name else ""}'

            # Get previous message text
            prev_text = query.message.text_markdown_v2

            # Append name into list
            new_text = f'{prev_text}\n' \
                       f'{len(context.bot_data["acknowledged"])+1}\. {user}'
            query.edit_message_text(text=new_text, parse_mode="MarkdownV2", reply_markup=get_acknowledge_inline_button())

            # Add userid into acknowledged list
            context.bot_data["acknowledged"].append(userid)

            # Answer query first to finish loading bar
            query.answer(text="Successfully acknowledged")

        else:
            # User is already acknowledged
            query.answer(text="Already acknowledged")


inline_button_handler = CallbackQueryHandler(inline_button_callback)


dispatcher.add_handler(inline_button_handler)
dispatcher.add_handler(inline_query_handler)
dispatcher.add_handler(start_handler)


def main():
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
