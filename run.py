import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, InlineQueryHandler, ChosenInlineResultHandler
from telegram.utils.helpers import escape_markdown

# Define bot
updater = Updater(token=os.getenv("bot_token"), use_context=True)
dispatcher = updater.dispatcher


# Helper functions
def get_menu_inline_buttons(admin, poll_id):
    if admin:
        inline_button = [
            [
                InlineKeyboardButton("Publish", switch_inline_query=poll_id),
            ]
        ]
    else:
        inline_button = [
            [
                InlineKeyboardButton("Acknowledge", callback_data=f"{poll_id} acknowledged")
            ]
        ]

    inline_keyboard_markup = InlineKeyboardMarkup(inline_button)

    return inline_keyboard_markup


def inline_query_publish_callback(update, context):
    query = update.inline_query

    if query.query in context.bot_data:
        # Retrieve inline message tied to the user
        message = context.bot_data[query.query]
        # Get owner id from original message
        owner_id = str(message.chat.id)

        results = [
            InlineQueryResultArticle(
                id=message.message_id,
                title="Publish Poll",
                input_message_content=InputTextMessageContent(message_text=message.text_markdown_v2,
                                                              parse_mode="MarkdownV2"),
                reply_markup=get_menu_inline_buttons(admin=False, poll_id=owner_id)
            )
        ]

        update.inline_query.answer(results)


inline_query_publish_callback_handler = InlineQueryHandler(inline_query_publish_callback)


def inline_button_acknowledge_callback(update, context):
    query = update.callback_query

    # Unpack callback data
    poll_id, action = query.data.split(" ")

    # Acknowledge the user
    if action == "acknowledged":
        # Check if user is already acknowledged
        if (userid := query.from_user.id) not in context.bot_data[f"{poll_id}_acknowledged"]:
            # Acknowledge user
            # Get name of the user who pressed button
            user = f'{query.from_user.first_name} {query.from_user.last_name if query.from_user.last_name else ""}'

            # Get previous message text
            prev_text = context.bot_data[poll_id].text_markdown_v2

            # Append name into list
            new_text = f'{prev_text}\n' \
                       f'{len(context.bot_data[f"{poll_id}_acknowledged"])+1}\. {user}'

            query.edit_message_text(text=new_text, parse_mode="MarkdownV2", reply_markup=get_menu_inline_buttons(admin=False, poll_id=poll_id))

            # Add userid into acknowledged list
            context.bot_data[f"{poll_id}_acknowledged"].append(userid)

            query.answer(text="Acknowledged successfully")
        else:
            # User is already acknowledged
            query.answer(text="Already acknowledged")


inline_button_acknowledge_handler = CallbackQueryHandler(inline_button_acknowledge_callback)


# Commands
# Start command
def start(update, context):
    # Get poll owner chat id
    owner_id = str(update.message.chat.id)

    # Define template
    text = f"*Recall\!*\n\n"\
           f"Acknowledged\:"

    # Send message
    message = update.message.reply_text(text=text,
                                        parse_mode="MarkdownV2",
                                        reply_markup=get_menu_inline_buttons(admin=True, poll_id=owner_id)
                                        )

    # Store message object. Tied to the requester
    context.bot_data[owner_id] = message
    # Initialize the acknowledged list
    context.bot_data[f"{owner_id}_acknowledged"] = []


start_handler = CommandHandler('start', start)


dispatcher.add_handler(inline_button_acknowledge_handler)
dispatcher.add_handler(inline_query_publish_callback_handler)

dispatcher.add_handler(start_handler)


def main():
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
