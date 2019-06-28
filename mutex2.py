from multiprocessing import Process, Lock
import os
import time
import random
import socket
import _thread
import pprint
import threading

def processFunction(ownId,coordId,addr,port):
	time.sleep(1)

	# print('args: ', ownId, coordId, addr, port)

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((addr, port))
	response = s.recv(1024).decode()

	# print(response)
	r = response.split('_')[1:]
	addresses = []
	for i in range(len(r)):
		addresses.append(r[i].split('-'))
		addresses[i][0] = int(addresses[i][0])
		addresses[i][2] = int(addresses[i][2])

	s.close()
	time.sleep(1)

	# print('parte 1 funcionou')
	time.sleep(1)

	id = [ownId,coordId]

	# print('iniciando requisições',id)
	cond = []
	cond.append(True)

	electionStart = [time.time()]
	requestingThread = [threading.Thread(target=requestFunction, args=(id,addresses,cond,electionStart))]
	if(id[0]!=id[1]):
		requestingThread[0].start()

	queue = []
	mutex = Lock()
	mutexQueue = Lock()

	myAddr = []
	for i in range(len(addresses)):
		if addresses[i][0] == ownId:
			myAddr = addresses[i]
			break

	conSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	conSock.bind((myAddr[1],myAddr[2]))
	conSock.listen()

	connectionThreads = []
	stopThread = False
	i = 0

	while(True):
		conn, caddr = conSock.accept()
		# stopThread.append(False)
		t = threading.Thread(target=connectionFunction, args=(lambda:stopThread,conn,mutex,queue,id,addresses,requestingThread,cond,electionStart,mutexQueue))
		t.start()
		connectionThreads.append(t)
		i += 1

def connectionFunction(stopThread,s,mutex,queue,id,addresses,requestingThread,cond,electionStart,mutexQueue):
	while (not stopThread()):
		data = s.recv(1024).decode()
		if data == 'request' and id[0] == id[1]:
			print('answering request ',id)
			if mutex.acquire(False) and len(queue) == 0:
				s.sendall('approved'.encode())
			else:

				mutexQueue.acquire()
				queue.append(s)
				mutexQueue.release()

				IamTheNext=False

				while(not stopThread()):
					mutexQueue.acquire()
					if len(queue) == 0:
						mutexQueue.release()
						break
					elif queue[0] == s:
						mutexQueue.release()
						IamTheNext = True
					elif IamTheNext == True and queue[0] != s:
						mutexQueue.release()
						break
					else:
						mutexQueue.release()

                #print('antes do acquire')
				if mutex.acquire(False):
					s.sendall('approved'.encode())
				else:
					s.sendall('fault'.encode())
                #print('depois do acquire')

		if data == 'release':
			print('answering release ',id)
			mutex.release()
			if len(queue)>0:
				mutexQueue.acquire()
				queue.pop(0)
				mutexQueue.release()

		if data.find('election') != -1:
			print('answering election ',id)
			eleId = int(data[9:])
			if id[0] > eleId:
				s.sendall('ok'.encode())
				electionFunction(id,addresses,electionStart)
			else:
				s.sendall('notok'.encode())

		if data.find('newcoord') != -1:
			for i in range(len(addresses)):
				if addresses[i][0] == id[1]:
					del(addresses[i])
					break
			id[1] = int(data[9:])
			print('newcoord ',id)
			cond[0] = False
			requestingThread[0]=threading.Thread(target=requestFunction, args=(id,addresses,cond,electionStart))
			if(id[0]!=id[1]):
				cond[0] = True
				requestingThread[0].start()




def requestFunction(id,addresses,cond,electionStart):
	time.sleep(1)
	coordAddr = []
	for i in range(len(addresses)):
		if addresses[i][0] == id[1]:
			coordAddr = addresses[i]
			break

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((coordAddr[1], coordAddr[2]))
	a = 0
	while(cond[0]):
		s.sendall('request'.encode())
		print('sending request ',id)
		response = s.recv(1024).decode()
		if response is not None:
			if response == 'approved':
				a+=1
				if(a>3):
					time.sleep(1)
					electionFunction(id,addresses,electionStart)
					cond[0] = False
					time.sleep(1)
					a = 0
				else:
					#print("cliente "+name+" recebeu approved")
					time.sleep(1)
					s.sendall('release'.encode())
					time.sleep(1)
					#print("deu release")
			elif response == 'fault':
				electionFunction(id,addresses,electionStart)
				cond[0] = False
		else:
			print('esse erro nao deveria acontecer 0001')

def electionFunction(id,addresses,electionStart):
	if time.time() - electionStart[-1] > 5:
		electionStart.append(time.time())
		IamNewCoord = True
		for i in range(len(addresses)):
			if addresses[i][0] != id[0] and addresses[i][0] != id[1]:
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect((addresses[i][1], addresses[i][2]))
				s.sendall(('election_'+str(id[0])).encode())
				response = s.recv(1024).decode()
				if response == 'ok':
					IamNewCoord = False
				elif response != 'notok':
					print('esse erro nao deveria acontecer 0002')
				s.close()

		if IamNewCoord:
			for i in range(len(addresses)):
				if addresses[i][0] != id[0] and addresses[i][0] != id[1]:
					s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					s.connect((addresses[i][1], addresses[i][2]))
					s.sendall(('newcoord_'+str(id[0])).encode())
					s.close()

			id[1] = id[0]


if __name__ == '__main__':
	numberOfP = 8

	addr = 'localhost'
	port = 9092 + random.randint(0,100)
	serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serversocket.bind((addr,port))
	serversocket.listen()

	processess = []
	for i in range(1,numberOfP+1):
		p = Process(target=processFunction, args=(i,1,addr,port))
		processess.append(p)

	for i in range(len(processess)):
		processess[i].start()

	message = "addr_"
	info = []

	for i in range(len(processess)):
		# threading.Thread(target=loop1_10, args=()).start()
		conn, caddr = serversocket.accept()
		info.append([conn,caddr])
		message += str(i+1)+'-'+caddr[0]+'-'+str(caddr[1])+'_'
	message = message[:-1]

	for i in range(len(info)):
		info[i][0].sendall(message.encode())
		info[i][0].close()

	#join









#
# função da thread de conexão(variaveis):
# 	recebe mensagem
# 	se mensagem de eleição:
# 		se meu id for maior que o id da mensagem
# 			responde ok
# 			faço meu election
# 		senão
# 			respondo não ok
#
# 	se mensagem de requisição:
# 		lógica de requisição
# ================================================
#
#
# função da thread de requisição de recurso(variaveis):
# 	loop(True):
# 		solicito para o coordenador o recurso
# 		aguardar resposta
# 			se falha
# 				election
# 			se aprovado
# 				utilizar recurso
# 				enviar liberação
# 				sleep
#
# função election:
# 	manda mensagem de election com meu id para todos processos
# 	se eu receber não ok de todos sou o novo coord
#
# ====================================================
# from multiprocessing import Process, Lock
# import os
# import time
# import random
# import socket
# import _thread
# import pprint
#
# mutex = Lock()
#
# def processInfo(name):
#     print('name: ', name)
#     print('module name: ', __name__)
#     print('parent process: ', os.getppid())
#     print('process id: ', os.getpid())
#
# def processFunction(name,addr,port):
#     time.sleep(1)
#     #processInfo(name)
#     #print('args: ', name, addr, port)
#
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.connect((addr, port))
#
#     while(True):
#         s.sendall(b'request')
#         response = s.recv(1024)
#         if response is not None:
#             if response == b'approved':
#                 print("cliente "+name+" recebeu approved")
#                 time.sleep(1)
#                 s.sendall(b'release')
#                 time.sleep(1)
#                 print("deu release")
#
# def onConnection(clientsocket,addr,queue,mutex):
#     #global mutex
#     while True:
#         data = clientsocket.recv(1024)
#         print("data",data)
#         if data == b'request':
#             if mutex.acquire(False) and len(queue) == 0:
#                 clientsocket.sendall(b'approved')
#             else:
#                 queue.append(clientsocket)
#                 while(True):
#                     if queue[0] == clientsocket:
#                         break
#                 print('antes do acquire')
#                 mutex.acquire()
#                 print('depois do acquire')
#                 clientsocket.sendall(b'approved')
#                 queue.pop(0)
#         if data == b'release':
#             print("recebeu release")
#             mutex.release()
#         if data == b'die':
#             break
#     clientsocket.close()
#
# if __name__ == '__main__':
#
#     #processInfo('main')
#     numberOfProcessess = 5
#
#     addr = 'localhost'
#     port = 9092 + random.randint(0,100)
#     serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     serversocket.bind((addr,port))
#     serversocket.listen()
#
#     processess = []
#     for i in range(numberOfProcessess):
#         p = Process(target=processFunction, args=('p'+str(i),addr,port))
#         processess.append(p)
#
#     for i in range(len(processess)):
#         processess[i].start()
#
#     queue = []
#     while True:
#        conn, caddr = serversocket.accept()
#        _thread.start_new_thread(onConnection,(conn,caddr,queue,mutex))
#     serversocket.close()
