from redis import connection
import sys
sys.path.append("..")
import redis
from mrq.job import *
from mrq.dummy import *
from mrq.worker import *


def create(num):
    for i in range(num):
        connection=redis.Redis(host="127.0.0.1",port=6379,db=0,decode_responses=True)
        queue = Queue(connection=connection)
        queue.enqueue_job(fib,0)

def perform():
    worker = Worker(connection=redis.Redis(host="127.0.0.1",port=6379,db=0,decode_responses=True))
    worker.run_forever()

if __name__ == "__main__":
   mode = sys.argv[1]
   if mode == "create":
       create(100)
   elif mode == "perform":
       perform()