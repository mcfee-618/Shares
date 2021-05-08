from redis import connection
from .job import *
from .queue import *

class Worker:
    
    def __init__(self,connection,queue_name="default"): 
        self.queue_name = queue_name
        self.connection = connection
        self.queue:Queue = Queue(name=queue_name,connection=connection)
    
    
    def run_forever(self):
        while True:
            job = self.queue.dequeue_job()
            if job is None:
                continue
            print(job)
            result = job.perform_job()
            print(result)

        
    
    