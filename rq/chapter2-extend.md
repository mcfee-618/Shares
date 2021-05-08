## 信号回顾

信号是进程间的一种通信方式，与其他进程间通信方式（例如管道、共享内存等）相比，信号所能传递的信息比较粗糙，只是一个整数。但正是由于传递的信息量少，信号也更便于管理和使用。

Python 中使用 signal 模块来处理信号相关的操作，定义如下：
```
signal.signal(signalnum, handler)
signal.getsignal(signalnum)
```
signalnum 为某个信号，handler 为该信号的处理函数。进程可以无视信号，可以采取默认操作，还可以自定义操作。当 handler 为 signal.SIG_IGN 时，信号被无视（ignore）；当 handler 为 singal.SIG_DFL，进程采取默认操作（default）；当 handler 为一个函数名时，进程采取函数中定义的操作。

* 发送信号
```
os.kill(pid, sid)
os.killpg(pgid, sid)
```

* 定时发信号

```
signal.alarm(2)
```

备注：多线程环境下使用信号，只有 main thread 可以设置 signal 的 handler，也只有它能接收到 signal。

## 信号扩展

Python 信号处理程序不会在低级（ C ）信号处理程序中执行。相反，低级信号处理程序设置一个标志，告诉 virtual machine 稍后执行相应的 Python 信号处理程序（例如在下一个 bytecode 指令）。Python 信号处理程序总是会在主 Python 主解释器的主线程中执行，即使信号是在另一个线程中接收的。 这意味着信号不能被用作线程间通信的手段。


## EINTR

* 慢调用与EINTR：如果进程在一个慢系统调用(slow system call)中阻塞时，当捕获到某个信号且相应信号处理函数返回时，这个系统调用被中断，调用返回错误，设置errno为EINTR（相应的错误描述为Interrupted system call）。永远阻塞的系统调用是指调用永远无法返回，多数网络支持函数都属于这一类。如：若没有客户连接到服务器上，那么服务器的accept调用就会一直阻塞。

* 处理方式：人为重启被中断的系统调用 或 忽略信号。

* python处理EINTR：exception InterruptedError当系统调用被输入信号中断时将被引发。 对应于 errno EINTR。在 Python3.5更改: 当系统调用被某个信号中断时，Python 现在会重试系统调用，除非该信号的处理程序引发了其它异常 (原理参见 PEP 475) 而不是引InterruptedError。

* pep475：标准库中提供的系统调用包装器在使用EINTR失败时应该自动重试，以减轻应用程序代码这样做的负担。如果信号处理程序成功返回，Python包装器将自动重试系统调用，下列这种冗余代码不会再出现了。

    ```
    ## python2写法
    while True:
        try:
            data = file.read(size)
            break
        except InterruptedError:
            continue
    
    ## python3写法
    while True:
         data = file.read(size)
    ```

## 不可重入函数【中断处理程序破坏了上一次调用的相关数据】

所谓可重入函数是指那种在其执行的半途中可以再次被调用而不破坏前次调用相关数据的函数。再次调用这种函数的原因可能是函数的递归调用——函数还未退出便又调用自身，或者是函数在执行过程中被信号中断，而信号句柄中恰恰也要调用此函数；也可能是多线程或多进程的代码共享——多个线程或进程并行地执行同一个函数。


如果一个函数的各个实例的程序代码相同并且各自只修改自己独立的数据空间，这个函数在执行过程中的再次调用（即同时存在的多个实例）就不会破坏上一次调用相关的数据。因此可重入函数必须满足如下三个条件：
1）不修改自身代码。
2）只修改自己的局部数据。
3）不调用其他任何非可重入函数。


## 相关链接

* Signal：https://juejin.cn/post/6844903733466251272

* EINTR：https://blog.csdn.net/junlon2006/article/details/80403737

* Retry system calls failing with EINTR：https://www.python.org/dev/peps/pep-0475/

