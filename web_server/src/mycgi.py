import os

num = os.fork()
r, w = os.pipe() ## 使用管道进行通信
if num:
    os.close(w)
    r = os.fdopen(r)
    output = r.read()
    os.wait()
    print(output)
else:
    os.close(r)
    w = os.fdopen(w)
    os.execl("/usr/bin/python","python3","cgi_test.py")
    