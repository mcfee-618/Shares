import socket,os,signal,time,sys

def register_signal_handlers():
    
    def sigint_handler(signum, frame):
        print("signal ctrl c")
        time.sleep(2)
    signal.signal(signal.SIGINT,sigint_handler)


def run_server():
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0",8654))
    sock.listen(10)
    while True:
        conn,addr = sock.accept()
        print(addr)
        conn.close()

def run_client():
    while True:
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.connect(("0.0.0.0",8654))
        time.sleep(0.01)


if __name__=="__main__":
    if sys.argv[1]=="server":
        register_signal_handlers()
        run_server()
    else:
        run_client()