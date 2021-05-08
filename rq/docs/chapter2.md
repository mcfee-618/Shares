---
theme: github
---
## 历史变迁
RQ(Redis Queue) 是一个非常简洁,轻量级,用于处理后台任务队列的Python库，与celery相比其最大的优势是简单易用，RQ使用Redis队列相关的底层数据，Redis是唯一的broker。RQ的第一个版本0.1.0于2013年完成，当前最新版本是1.8.0，最新版本于2021年发布其github地址：https://github.com/rq/rq ，这次源码分析是0.1.0的版本，早期版本feature少，更易于理解。RQ相关组件如下：
* rq：https://github.com/rq/rq 
* rq-scheduler 定时调度：https://github.com/rq/rq-scheduler
* rq-dashboard 控制台：https://github.com/Parallels/rq-dashboard


## 代码结构

```
├── __init__.py
├── connections.py
├── dummy.py
├── exceptions.py
├── job.py           
├── queue.py         
├── timeouts.py
├── utils.py
├── version.py
└── worker.py
```

核心逻辑基本都在job.py、queue.py和worker.py中，涉及job的入队、生成、持久化，worker的执行job逻辑。

## 目标

1. 熟悉rq基本脉络，从任务入队到最终处理的全部逻辑。
2. 理解rq涉及linux调用，例如进程和信号处理相关。
3. 理解rq涉及redis全部调用操作以及实现方式。
4. 学习rq涉及python的高阶调用和优雅实现。
5. 实现一个简易版本的任务队列系统。


## 基本脉络

* 任务入队

```
## Queue
def enqueue(self, f, *args, **kwargs):
    """Creates a job to represent the delayed function call and enqueues
    it.

    Expects the function to call, along with the arguments and keyword
    arguments.

    The special keyword `timeout` is reserved for `enqueue()` itself and
    it won't be passed to the actual job function.
    """
    if f.__module__ == '__main__':
        raise ValueError(
                'Functions from the __main__ module cannot be processed '
                'by workers.')

    timeout = kwargs.pop('timeout', None)
    job = Job.create(f, *args, connection=self.connection, **kwargs)
    return self.enqueue_job(job, timeout=timeout)

def enqueue_job(self, job, timeout=None, set_meta_data=True):
    """Enqueues a job for delayed execution.

    When the `timeout` argument is sent, it will overrides the default
    timeout value of 180 seconds.  `timeout` may either be a string or
    integer.

    If the `set_meta_data` argument is `True` (default), it will update
    the properties `origin` and `enqueued_at`.
    """
    if set_meta_data:
    job.origin = self.name
    job.enqueued_at = times.now()

    if timeout:
    job.timeout = timeout  # _timeout_in_seconds(timeout)
    else:
    job.timeout = 180  # default

    job.save()  # hmset job信息
    self.push_job_id(job.id) # rpush jobid到queue关联的list
    return job
```
提供方法名 + 参数 ，不支持主模块定义的函数入队，异步调用最终转换了一个job，最后将这个job入队，job后面会以hash结构存储在redis中，然后将jobid rpush到queue关联的list上。

* 执行任务

```
## Worker
def work(self, burst=False):  # noqa
    """Starts the work loop.

    Pops and performs all jobs on the current list of queues.  When all
    queues are empty, block and wait for new jobs to arrive on any of the
    queues, unless `burst` mode is enabled.

    The return value indicates whether any jobs were processed.
    """
    self._install_signal_handlers()

    did_perform_work = False
    self.register_birth()
    self.state = 'starting'
    try:
        while True:
            if self.stopped:
                self.log.info('Stopping on request.')
                break
            self.state = 'idle'
            qnames = self.queue_names()
            self.procline('Listening on %s' % ','.join(qnames))
            self.log.info('')
            self.log.info('*** Listening on %s...' % \
                    green(', '.join(qnames)))
            wait_for_job = not burst
            try:
                result = Queue.dequeue_any(self.queues, wait_for_job, \
                        connection=self.connection)
                if result is None:
                    break
            except UnpickleError as e:
                msg = '*** Ignoring unpickleable data on %s.' % \
                        green(e.queue.name)
                self.log.warning(msg)
                self.log.debug('Data follows:')
                self.log.debug(e.raw_data)
                self.log.debug('End of unreadable data.')
                self.failed_queue.push_job_id(e.job_id)
                continue

            job, queue = result
            self.log.info('%s: %s (%s)' % (green(queue.name),
                blue(job.description), job.id))

            self.state = 'busy'
            self.fork_and_perform_job(job)

            did_perform_work = True
    finally:
        if not self.is_horse:
            self.register_death()
    return did_perform_work
    
def fork_and_perform_job(self, job):
    """Spawns a work horse to perform the actual work and passes it a job.
    The worker will wait for the work horse and make sure it executes
    within the given timeout bounds, or will end the work horse with
    SIGALRM.
    """
    child_pid = os.fork()
    if child_pid == 0:
        self.main_work_horse(job)
    else:
        self._horse_pid = child_pid
        self.procline('Forked %d at %d' % (child_pid, time.time()))
        while True:
            try:
                os.waitpid(child_pid, 0)
                break
            except OSError as e:
                # In case we encountered an OSError due to EINTR (which is
                # caused by a SIGINT or SIGTERM signal during
                # os.waitpid()), we simply ignore it and enter the next
                # iteration of the loop, waiting for the child to end.  In
                # any other case, this is some other unexpected OS error,
                # which we don't want to catch, so we re-raise those ones.
                if e.errno != errno.EINTR:
                    raise
```
Worker的主要方法入口在work中，work方法是一个while true死循环，从queues中dequeue一个job，fork一个进程用于处理job，当前进程wait子进程，等待子进程结束或异常退出才处理下一个job。

* job模块：依赖cPickle实现loads和dumps，用于对象到字符串的转换工作。

```
class Job(object):
    """A Job is just a convenient datastructure to pass around job (meta) data.
    """

    # Job construction
    @classmethod
    def create(cls, func, *args, **kwargs):
        """Creates a new Job instance for the given function, arguments, and
        keyword arguments.
        """
        connection = kwargs.pop('connection', None)
        job = Job(connection=connection)
        job._func_name = '%s.%s' % (func.__module__, func.__name__)
        job._args = args
        job._kwargs = kwargs
        job.description = job.get_call_string()
        return job

    def __init__(self, id=None, connection=None):
    if connection is None:
        connection = get_current_connection()
    self.connection = connection
    self._id = id
    self.created_at = times.now()
    self._func_name = None
    self._args = None
    self._kwargs = None
    self.description = None
    self.origin = None
    self.enqueued_at = None # 可能多次入队
    self.ended_at = None
    self._result = None
    self.exc_info = None
    self.timeout = None
```
包含方法名称(所属模块名+方法名)，参数列表(顺序参数列表+命名参数列表)+ 描述 + 时间(创建+结束+入队时间) + 执行结果(_result) + timeout + 异常信息 + 队列名(origin)。

``` 
## 持久化job到redis
def save(self):
    """Persists the current job instance to its corresponding Redis key."""
    key = self.key

    obj = {}
    obj['created_at'] = times.format(self.created_at, 'UTC')

    if self.func_name is not None:
        obj['data'] = dumps(self.job_tuple)
    if self.origin is not None:
        obj['origin'] = self.origin
    if self.description is not None:
        obj['description'] = self.description
    if self.enqueued_at is not None:
        obj['enqueued_at'] = times.format(self.enqueued_at, 'UTC')
    if self.ended_at is not None:
        obj['ended_at'] = times.format(self.ended_at, 'UTC')
    if self._result is not None:
        obj['result'] = self._result
    if self.exc_info is not None:
        obj['exc_info'] = self.exc_info
    if self.timeout is not None:
        obj['timeout'] = self.timeout

    self.connection.hmset(key, obj)

## 根据id恢复job结构
def refresh(self):  # noqa
    """Overwrite the current instance's properties with the values in the
    corresponding Redis key.

    Will raise a NoSuchJobError if no corresponding Redis key exists.
    """
    key = self.key
    properties = ['data', 'created_at', 'origin', 'description',
            'enqueued_at', 'ended_at', 'result', 'exc_info', 'timeout']
    data, created_at, origin, description, \
            enqueued_at, ended_at, result, \
            exc_info, timeout = self.connection.hmget(key, properties)
    if data is None:
        raise NoSuchJobError('No such job: %s' % (key,))

    def to_date(date_str):
        if date_str is None:
            return None
        else:
            return times.to_universal(date_str)

    self._func_name, self._args, self._kwargs = unpickle(data)
    self.created_at = to_date(created_at)
    self.origin = origin
    self.description = description
    self.enqueued_at = to_date(enqueued_at)
    self.ended_at = to_date(ended_at)
    self._result = result
    self.exc_info = exc_info
    if timeout is None:
        self.timeout = None
    else:
        self.timeout = int(timeout)
```

## redis相关指令

* hash相关：对Job进行结构化存储,涉及hmset和hmget
* list相关：每个queue本质就是一个list，利用rpush、blpop和lop完成入队出队，其中BLOPO是LPOP命令的阻塞版本，当给定列表内没有任何元素可供弹出的时候，连接将被BLPOP命令阻塞，直到等待超时或发现可弹出元素为止，BLPOP是为了避免轮询。
* set相关：sadd和srem用于worker做register_birth和register_death，workers都存储在一个key中。

```
queue1:  job1 + job2 + job3 [list]
job1: id:xxxx , args:xxxx , origin:xxxxx , result:xxxx [hash]
workers: worker1 + worker2 [set]
worker1: birth:xxxx , queues:x1,x2 [hash]
```
## linux相关调用

* 进程相关

```
def fork_and_perform_job(self, job):
    """Spawns a work horse to perform the actual work and passes it a job.
    The worker will wait for the work horse and make sure it executes
    within the given timeout bounds, or will end the work horse with
    SIGALRM.
    """
    child_pid = os.fork()
    if child_pid == 0:
        self.main_work_horse(job)
    else:
        self._horse_pid = child_pid
        self.procline('Forked %d at %d' % (child_pid, time.time()))
        while True:
            try:
                os.waitpid(child_pid, 0)
                break
            except OSError as e:
                # In case we encountered an OSError due to EINTR (which is
                # caused by a SIGINT or SIGTERM signal during
                # os.waitpid()), we simply ignore it and enter the next
                # iteration of the loop, waiting for the child to end.  In
                # any other case, this is some other unexpected OS error,
                # which we don't want to catch, so we re-raise those ones.
                if e.errno != errno.EINTR:
                    raise
```
fork一个子进程用于执行job，父进程阻塞直到子进程完成或者因为超时结束。有一个很重要的逻辑是，当父进程等待子进程的过程中，如果收到了SIGINT信号或SIGTERM信号，父进程会忽略。



## 信号处理

```
def _install_signal_handlers(self):
    """Installs signal handlers for handling SIGINT and SIGTERM
    gracefully.
    """

    def request_force_stop(signum, frame):
        """Terminates the application (cold shutdown).
        """
        self.log.warning('Cold shut down.')

        # Take down the horse with the worker
        if self.horse_pid:
            msg = 'Taking down horse %d with me.' % self.horse_pid
            self.log.debug(msg)
            try:
                os.kill(self.horse_pid, signal.SIGKILL)
            except OSError as e:
                # ESRCH ("No such process") is fine with us
                if e.errno != errno.ESRCH:
                    self.log.debug('Horse already down.')
                    raise
        raise SystemExit()

    def request_stop(signum, frame):
        """Stops the current worker loop but waits for child processes to
        end gracefully (warm shutdown).
        """
        self.log.debug('Got %s signal.' % signal_name(signum))

        signal.signal(signal.SIGINT, request_force_stop)
        signal.signal(signal.SIGTERM, request_force_stop)

        if self.is_horse:
            self.log.debug('Ignoring signal %s.' % signal_name(signum))
            return

        msg = 'Warm shut down. Press Ctrl+C again for a cold shutdown.'
        self.log.warning(msg)
        self._stopped = True
        self.log.debug('Stopping after current horse is finished.')

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
```
父进程收到SIGINT信号后，再一次注册新的信号处理函数并设置状态，再一次发信号才会触发kill。

```
def setup_death_penalty(self):
    """Sets up an alarm signal and a signal handler that raises
    a JobTimeoutException after the timeout amount (expressed in
    seconds).
    """
    signal.signal(signal.SIGALRM, self.handle_death_penalty)
    signal.alarm(self._timeout)
```
设置定时信号及处理函数，alarm(0)代表清除定时器



## 资料

* 中文文档：https://codercharm.github.io/Python-rq-doc-cn/#/zh-cn/queues