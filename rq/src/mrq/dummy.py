"""
Some dummy tasks that are well-suited for generating load for testing purposes.
"""
import time
import random


def do_nothing():
    pass


def sleep(secs):
    time.sleep(secs)


def endless_loop():
    while True:
        time.sleep(1)


def div_by_zero():
    1 / 0


def fib(n):
    if n <= 1:
        time.sleep(2)
        return 1
    else:
        return fib(n - 2) + fib(n - 1)


def random_failure():
    if random.choice([True, False]):
        class RandomError(Exception):
            pass
        raise RandomError('Ouch!')
    return 'OK'
