import time
import json
import uuid
import importlib
import signal
from .exception import *

class JobStatus:
    
    pending = "pending"
    running = "running"
    failed = "failed"
    finished = "finished"
    timeout = "timeout"

class Job:
    
    redis_job_prefix = "myrq:job:"
    
    def __init__(self,connection) -> None:
        self.connection = connection 
        self._func_name = None
        self._args = None
        self._kwargs = None
        self._status = None
        self._timeout = 60
        self.id = None
    
    @classmethod
    def create(cls,func,*args,**kwargs):
        connection = kwargs.pop('connection', None)
        timeout = kwargs.pop('timeout',None)
        print(timeout)
        job = Job(connection=connection)
        job._func_name = '%s.%s' % (func.__module__, func.__name__)
        job._args = args
        job._kwargs = kwargs
        job._status = JobStatus.pending
        job.id = uuid.uuid4()
        if timeout:
            job._timeout = timeout 
        return job
    
    @classmethod
    def fetch(cls,connection,id):
        job_info = connection.hgetall(f'{cls.redis_job_prefix}{id}')
        if not job_info:
            return None
        job = Job(connection)
        job.id = id
        job.loads(job_info['func'])
        job._timeout = int(job_info['timeout'])
        return job
        
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self,status):
        self._status = status
        self.connection.hset(f'{self.redis_job_prefix}{self.id}',"status",status)
        
    @property
    def func(self):
        func_name = self._func_name
        if func_name is None:
            return None

        module_name, func_name = func_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)
        
    def perform_job(self):
        self.register_signal_handlers()
        self.status = JobStatus.running
        result = None
        try:
            result = self.func(*self._args,**self._kwargs)
        except TimeoutException:
            self.status = JobStatus.timeout
        except Exception as e:
            self.status = JobStatus.failed
        else:
            self.status = JobStatus.finished
        return result
        
    def dumps(self):
        obj = {}
        obj['func_name'] = self._func_name
        obj['args'] = self._args
        obj['kwargs'] = self._kwargs
        return json.dumps(obj)
    
    def loads(self,func_json):
        obj = json.loads(func_json)
        self._func_name = obj.pop("func_name",None)
        self._args = obj.pop("args",None)
        self._kwargs = obj.pop("kwargs",None)
        
    def save(self):
        obj = {}
        obj['created_at'] = int(time.time())
        obj['func'] = self.dumps()
        obj['status'] = self._status
        obj['timeout'] = self._timeout
        pipe = self.connection.pipeline(transaction=False)
        pipe.hmset(f'{self.redis_job_prefix}{self.id}',obj)
        pipe.expire(f'{self.redis_job_prefix}{self.id}',3600)
        pipe.execute()
        
    def register_signal_handlers(self):
        print(self._timeout)
        def handle_alarm_signal():    
            raise TimeoutException()
        signal.signal(signal.SIGALRM,handle_alarm_signal)
        signal.alarm(self._timeout)