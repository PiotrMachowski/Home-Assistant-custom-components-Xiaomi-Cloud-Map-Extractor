import random


class Backoff:
    """Exponential backoff with jitter."""

    def __init__(self, min_sleep, max_sleep):
        self.min_sleep = min_sleep
        self.sleep = min_sleep
        self.max_sleep = max_sleep

    def backoff(self):
        self.sleep = min(self.max_sleep, random.uniform(self.min_sleep, self.sleep * 3))
        return self.sleep
