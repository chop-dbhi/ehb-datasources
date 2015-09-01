from abc import ABCMeta, abstractmethod


class RecordListener(object):
    '''
    Base class for all record listeners
    '''
    __metaclass = ABCMeta

    RECORD_CREATION = 0
    RECORD_UPDATE = 1
    RECORD_DELETE = 2

    @abstractmethod
    def notify_on(self):
        '''
        Returns a traversable object (e.g. list, tuple) of integers indicating
        event types for which the listener should be notified
        '''
        pass


class RecordCreatedListener(RecordListener):
    '''
    Abstract class for implementing record creation listeners. The intent of
    the listener is to allow a listening driver to perform actions when a
    notifying driver creates a new record
    '''

    __metaclass = ABCMeta

    def __init__(self, listener=None, listener_rec_id=None):
        '''
        Inputs:
            * listener - driver listening for the notification
            * listener_rec_id - specific record id that may be used in tandem
                with the notifier_rec_id
        '''
        self.listener = listener
        self.listener_rec_id = listener_rec_id

    def set_listener(self, listener):
        self.listener = listener

    def set_listener_rec_id(self, rec_id):
        self.listener_rec_id = rec_id

    @abstractmethod
    def notify(self, notifier, notifier_rec_id):
        '''
        Inputs:
            * notifier - the driver that has created the new record
            * notifier_rec_id - the id of the new record
        '''
        pass

    def notify_on(self):
        return [self.RECORD_CREATION]
