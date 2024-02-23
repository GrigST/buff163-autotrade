from threading import Thread
from abc import abstractmethod

class BaseNotifier:
    def __init__(self, notifier_cfg):
        self._notifier_cfg = notifier_cfg

    @abstractmethod
    def notify_exception(self, username, exception):
        pass

    @abstractmethod
    def notify_test(self):
        pass

    def start(self):
        pass


class BaseThreadedNotifier(Thread, BaseNotifier):
    THREAD_NAME = 'Base threaded notifier'

    def __init__(self, notifier_cfg):
        Thread.__init__(self, name=self.THREAD_NAME, daemon=True)
        BaseNotifier.__init__(self, notifier_cfg)

    @abstractmethod
    def run(self):
        pass
