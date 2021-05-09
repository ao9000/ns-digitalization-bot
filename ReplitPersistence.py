from telegram.ext import BasePersistence
from replit import db, database


class ReplitPersistence(BasePersistence):
    def __init__(self):
        super(ReplitPersistence, self).__init__(store_user_data=False,
                                                store_chat_data=False,
                                                store_bot_data=True)

    def get_bot_data(self):
        if "bot_data" in db:
            return database.to_primitive(db['bot_data'])

        return {}

    def update_bot_data(self, data):
        db["bot_data"] = data

    def get_chat_data(self):
        pass

    def update_chat_data(self, chat_id, data):
        pass

    def get_user_data(self):
        pass

    def update_user_data(self, user_id, data):
        pass

    def get_conversations(self, name):
        pass

    def update_conversation(self, name, key, new_state):
        pass

    def flush(self):
        db.close()
