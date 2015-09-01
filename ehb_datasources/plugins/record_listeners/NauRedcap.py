from Base import RecordCreatedListener

import ehb_datasources.drivers.nautilus.driver as naumod
import ehb_datasources.drivers.redcap.driver as redcapmod


class RCListener(RecordCreatedListener):

    def notify(self, notifier, notifier_rec_id):
        '''
        Inputs:
            * notifier - the driver that has created the new record
            * notifier_rec_id - the id of the new record
        '''
        notifier_type = type(notifier)
        listener_type = type(self.listener)

        # Nothing to do if both records haven't been created yet
        if not (notifier_rec_id and self.listener_rec_id):
            return

        cond1 = (
            notifier_type == naumod.ehbDriver or
            notifier_type == redcapmod.ehbDriver
        )
        cond2 = (
            listener_type == naumod.ehbDriver or
            listener_type == redcapmod.ehbDriver
        )
        cond3 = not (listener_type == notifier_type)

        # If these aren't the right driver types leave
        if not (cond1 and cond2 and cond3):
            return

        naudriver = None
        nau_rec_id = None
        red_cap_id = None

        if(notifier_type == naumod.ehbDriver):
            naudriver = notifier
            nau_rec_id = notifier_rec_id
            red_cap_id = self.listener_rec_id
        else:
            naudriver = self.listener
            nau_rec_id = self.listener_rec_id
            red_cap_id = notifier_rec_id

        naudriver.update(nau_sub_path='sdg',
                         fldvals={'EXTERNAL_REFERENCE': red_cap_id, },
                         name=nau_rec_id)
