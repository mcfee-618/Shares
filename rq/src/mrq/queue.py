import redis
from .job import *

class Queue:
    
    redis_queue_prefix= "myrq:queue:"
    
    def __init__(self,name="default",connection=None):
        if connection is None:
            connection = redis.Redis(host="127.0.0.1",port=6379,db=0)
        self.name = name
        self.connection = connection
    
    def enqueue_job(self,func,*args,**kwargs):
        kwargs["connection"] = self.connection
        job = Job.create(func,*args,**kwargs)
        job.save()
        self.connection.rpush(f"{self.redis_queue_prefix}{self.name}",f"{job.id}")
    
    def dequeue_job(self):
        queue_name,job_id = self.connection.blpop(f"{self.redis_queue_prefix}{self.name}")
        print(job_id)
        return Job.fetch(connection=self.connection,id=job_id)
        
    
    
    
    