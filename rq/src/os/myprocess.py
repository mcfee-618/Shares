import os,signal,errno,time

def register_signal_handlers():
    
    def sigint_handler(signum, frame):
        print("received signal")
    signal.signal(signal.SIGINT,sigint_handler)
    
def fork_and_perform_job():
    pid = os.fork()
    if pid:
        while True:
            try:
                x=22
                os.waitpid(pid,0)
                print("parent end")
                break
            except OSError as err:
                print(OSError)
                if err.errno == errno.EINTR:
                    exit()        
    else:
        time.sleep(5)
        print(33)

if __name__=="__main__":
    register_signal_handlers()
    fork_and_perform_job()