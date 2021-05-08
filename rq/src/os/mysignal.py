import signal
import time

def register_signal_handlers():
    i=0
    def sigint_handler(signum, frame):
        nonlocal i
        if i>=1:
            exit()
        i+=1
        print("CTRL C")
        print(frame.f_code)
    
    j=0
    def alarm_handler(signum,frame):
        nonlocal j
        if j>=2:
            return
        else:
            print("时钟响了")
    signal.signal(signal.SIGINT,sigint_handler)
    signal.signal(signal.SIGALRM,alarm_handler)


def main():
    register_signal_handlers()
    signal.alarm(2)
    func=signal.getsignal(signal.SIGINT)
    while True:
        time.sleep(2)

if __name__=="__main__":
   main()