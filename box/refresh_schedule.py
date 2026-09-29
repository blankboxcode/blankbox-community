"""One refresh batch at a time, with the configured quiet interval after completion."""
class RefreshSchedule:
    def __init__(self):
        self.next_run = None
        self.pending = []
        self.finishing = False
        self.cooldown = 0

    def next_task(self, now, interval, tasks, busy):
        had_pending=bool(self.pending)
        self.pending = [task for task in self.pending if task in tasks]
        if had_pending and not self.pending:self.finishing=True
        if not tasks:
            self.next_run = None
            self.pending.clear()
            self.finishing = False
            return None
        if self.finishing:
            if busy:
                return None
            self.finishing = False
            self.next_run = now + interval
        if self.next_run is None:
            self.next_run = now + interval
        if now >= self.next_run and not self.pending and not busy:
            self.pending = list(tasks)
        if busy or now < self.cooldown or not self.pending:
            return None
        return self.pending[0]

    def dispatched(self, now):
        self.pending.pop(0)
        self.cooldown = now + 5
        if not self.pending:
            self.finishing = True

    def retry(self, now):
        self.cooldown = now + 30
