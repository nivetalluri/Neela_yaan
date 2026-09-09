from .mission_manager import now
class CommunicationManager:
    def __init__(self,storage): self.storage=storage;self.last=None
    def transmit(self,connected):
        # Ground-link emulation, not an actual satellite modem.
        if connected:
            n=self.storage.counts()['pending']
            if n:
                self.storage.event('SATELLITE TRANSMISSION STARTED',f'{n} buffered packets • simulated link')
                self.storage.db.execute('UPDATE samples SET sent=1 WHERE sent=0');self.storage.db.commit();self.last=now()
                self.storage.event('SATELLITE TRANSMISSION COMPLETED',f'{n} packets delivered to simulated sink')
        return {**self.storage.counts(),'last_transmission':self.last,'transport':'SIMULATED SATELLITE SINK'}
