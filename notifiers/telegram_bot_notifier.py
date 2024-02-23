from telebot import TeleBot

from .base_notifier import BaseThreadedNotifier

class TelegramBotNotifier(BaseThreadedNotifier):
    THREAD_NAME = 'Telegram notifier'

    def __init__(self, notifier_cfg):
        super().__init__(notifier_cfg)
        self.bot = TeleBot(notifier_cfg['token'], threaded=False)

        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            if message.from_user.id not in self._notifier_cfg['whitelist']:
                # self.bot.send_message(message.chat.id, 'You are not in whitelist')
                return
                
            self.bot.send_message(message.chat.id, 'Success')

        @self.bot.message_handler(commands=['getid'])
        def getid_command(message):
            self.bot.send_message(message.chat.id, f'Your id: {message.from_user.id}')

    def notify(self, message: str):
        for user in self._notifier_cfg['whitelist']:
            try:
                self.bot.send_message(user, message)

            except Exception as e:
                print(f'Failed to send notification to user {user}: {e}')

    def notify_exception(self, username, exception):
        self.notify(f'An exception occurred with a user {username}: {exception}')

    def notify_test(self):
        self.notify('Test notification')

    def run(self):
        print('Start telegram bot polling')
        self.bot.polling()
