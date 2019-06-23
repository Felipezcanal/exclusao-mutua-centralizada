from multiprocessing import Process, Lock
import os
import time
import random
import socket
import _thread
import pprint

mutex = Lock()

def processInfo(name):
    print('name: ', name)
    print('module name: ', __name__)
    print('parent process: ', os.getppid())
    print('process id: ', os.getpid())

def processFunction(name,addr,port):
    time.sleep(1)
    #processInfo(name)
    #print('args: ', name, addr, port)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((addr, port))

    while(True):
        s.sendall(b'request')
        response = s.recv(1024)
        if response is not None:
            if response == b'approved':
                print("cliente "+name+" recebeu approved")
                time.sleep(1)
                s.sendall(b'release')
                time.sleep(1)
                print("deu release")

def onConnection(clientsocket,addr,queue,mutex):
    #global mutex
    while True:
        data = clientsocket.recv(1024)
        print("data",data)
        if data == b'request':
            if mutex.acquire(False) and len(queue) == 0:
                clientsocket.sendall(b'approved')
            else:
                queue.append(clientsocket)
                while(True):
                    if queue[0] == clientsocket:
                        break
                print('antes do acquire')
                mutex.acquire()
                print('depois do acquire')
                clientsocket.sendall(b'approved')
                queue.pop(0)
        if data == b'release':
            print("recebeu release")
            mutex.release()
        if data == b'die':
            break
    clientsocket.close()

if __name__ == '__main__':

    #processInfo('main')
    numberOfProcessess = 5

    addr = 'localhost'
    port = 9092 + random.randint(0,100)
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((addr,port))
    serversocket.listen()

    processess = []
    for i in range(numberOfProcessess):
        p = Process(target=processFunction, args=('p'+str(i),addr,port))
        processess.append(p)

    for i in range(len(processess)):
        processess[i].start()

    queue = []
    while True:
       conn, caddr = serversocket.accept()
       _thread.start_new_thread(onConnection,(conn,caddr,queue,mutex))
    serversocket.close()
