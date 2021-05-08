## Python高阶使用

Python是语法糖很多的高级语言，而且很多是Python语言独有的。RQ作为流行的分布式任务框架，也使用了Python的很多语法糖，通过阅读源码帮助理解如何更好的使用这些语法糖以及魔术方法。


## propery

* 描述：@property 语法糖提供了比 property() 函数更简洁直观的写法。被 @property 装饰的方法是获取属性值的方法，被装饰方法的名字会被用做 属性名。被 @属性名.setter 装饰的方法是设置属性值的方法。被 @属性名.deleter 装饰的方法是删除属性值的方法。

```
## Job

    @property
    def func_name(self):
        return self._func_name

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        module_name, func_name = func_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs
```

* 总结：@property用于封装复杂的细节，自定义获取属性，设置属性，删除属性操作行为。

## 装饰器

装饰器除了用于方法还可以用于类，对方法进行装饰和对类进行装饰。

```
@total_ordering
class Queue(object):
    redis_queue_namespace_prefix = 'rq:queue:'


def total_ordering(cls):
    """Class decorator that fills in missing ordering methods"""
    # Find user-defined comparisons (not those inherited from object).
    roots = {op for op in _convert if getattr(cls, op, None) is not getattr(object, op, None)}
    if not roots:
        raise ValueError('must define at least one ordering operation: < > <= >=')
    root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
    for opname, opfunc in _convert[root]:
        if opname not in roots:
            opfunc.__name__ = opname
            setattr(cls, opname, opfunc)
    return cls
```

## 上下文管理器

上下文管理器是Python特有的，主要是为了简化代码操作，使得代码变得简洁便于维护，减少冗余代码，复用性更强。

```
## 原始写法
try:
    VAR = XXXXX
except xxx as e：
    PASS
finally:
    DO SOMETHING

## 上下文管理器写法
with EXPR as VAR:
    BLOCK
```
这里就是一个标准的上下文管理器的使用逻辑，稍微解释一下其中的运行逻辑：

（1）执行EXPR语句，获取上下文管理器（Context Manager）

（2）调用上下文管理器中的__enter__方法，该方法执行一些预处理工作。

（3）这里的as VAR可以省略，如果不省略，则将__enter__方法的返回值赋值给VAR。

（4）执行代码块BLOCK，这里的VAR可以当做普通变量使用。

（5）最后调用上下文管理器中的的__exit__方法。

（6）__exit__方法有三个参数：exc_type, exc_val, exc_tb。如果代码块BLOCK发生异常并退出，那么分别对应异常的type、value 和 traceback。否则三个参数全为None。如果__exit__()方法返回值为false，则异常会被重新抛出；如果其返回值为true，则视为异常已经被处理，程序继续执行。

```
class death_pentalty_after(object):
    def __init__(self, timeout):
        self._timeout = timeout

    def __enter__(self):
        self.setup_death_penalty()

    def __exit__(self, type, value, traceback):
        # Always cancel immediately, since we're done
        try:
            self.cancel_death_penalty()
        except JobTimeoutException:
            pass
        return False

    def handle_death_penalty(self, signum, frame):
        raise JobTimeoutException('Job exceeded maximum timeout '
                'value (%d seconds).' % self._timeout)

    def setup_death_penalty(self):
        signal.signal(signal.SIGALRM, self.handle_death_penalty)
        signal.alarm(self._timeout)

    def cancel_death_penalty(self):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
```

RQ中使用上下文管理器用于作业的超时管理，配合signal模块完成作业的超时时间控制，开始时注册信号处理程序，设置定时信号，结束时取消定时信号并忽略信号，下面是具体使用的代码。

```
def perform_job(self, job):
    """Performs the actual work of a job.  Will/should only be called
    inside the work horse's process.
    """
    self.procline('Processing %s from %s since %s' % (
        job.func_name,
        job.origin, time.time()))

    try:
        with death_pentalty_after(job.timeout or 180):
            rv = job.perform()
    except Exception as e:
        fq = self.failed_queue
        self.log.exception(red(str(e)))
        self.log.warning('Moving job to %s queue.' % fq.name)

        fq.quarantine(job, exc_info=traceback.format_exc())
        return False

    if rv is None:
        self.log.info('Job OK')
    else:
        self.log.info('Job OK, result = %s' % (yellow(unicode(rv)),))

    if rv is not None:
        p = self.connection.pipeline()
        p.hset(job.key, 'result', dumps(rv))
        p.expire(job.key, self.rv_ttl)
        p.execute()
    else:
        # Cleanup immediately
        job.delete()
```

