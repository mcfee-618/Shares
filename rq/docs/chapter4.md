---
theme: github
---
## 从0到1实现简易的异步任务系统

异步任务系统的的三要素是job、queue和worker，利用queue生成一个job，然后持久化到redis里，worker读取redis得到job，然后执行job。

## 代码结构

```
-- job.py
-- queue.py
-- worker.py
-- dummmy.py 
-- exeception.py
```

## 源代码

* job.py

```
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
```

* queue.py

```
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
        return Job.fetch(connection=self.connection,id=job_id)
```

* worker.py

```
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
            result = job.perform_job()
```

## 奇淫巧技

* property可用于对属性的封装，如果要封装所有的属性可以用__setitem__方法。
* 善用raise必要的时刻抛出异常。
* 利用importlib.import_module动态加载模块，利用方法的_module_属性获取模块名称。

