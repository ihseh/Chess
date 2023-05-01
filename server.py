import socket
import threading
import time
import random
import json
import string
import pymysql
from database import *

connection = pymysql.connect(
	host = "chesswithfriends.cwqryofoppjg.us-east-2.rds.amazonaws.com",
	port = 3306,
	user = "admin",
	password = "password",
	db = "chesswithfriends"
)

cursor = connection.cursor()

# print(alter(cursor,connection))
# print(selectTableFields("tblGames",cursor))

HEADER = 64
PORT = 8080
# SERVER = '3.15.33.221'
# SERVER = '3.142.120.7'
# SERVER = '3.145.148.56'
SERVER = '3.20.76.52'
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT" 

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #choose socket family and type
server.bind(('0.0.0.0',8080)) #bind server to address

def send(msg, sock):
	message = msg.encode(FORMAT)
	msg_length = len(message)
	send_length = str(msg_length).encode(FORMAT)
	send_length += b' ' * (HEADER - len(send_length))
	try:
		sock.send(send_length)
		# print(f"sent {send_length}")
		sock.send(message)
		# print(f"sent {message}")
		print(f"sent: {message}")
	except:
		print("CLIENT NOT CONNECTED")

playerDic = {} #dictionary of player classes. Key = playerName (identifying key). Value = player object

class Player:
	def __init__(self, name, sock):
		self.name = name #name string
		self.sock = sock #socket object
		self.connected = True

def addGame(p1,p2,p1color):
	#set players, based on color choice
	if p1color == "white":
		player1 = p1
		player2 = p2
	elif p1color == "black":
		player1 = p2
		player2 = p1
	elif p1color == "random":
		rand = random.randint(0,1)
		if rand == 0:
			player1 = p1
			player2 = p2
		else:
			player1 = p2
			player2 = p1
	gameID = insertNewGame(player1,player2,cursor,connection)
	print(f"GAME ID : {gameID}")
	return (gameID,player1,player2)

def addInvite(fromPlayer, toPlayer, colorChoice): #pass in names as strings
	#add invite to database
	inviteID = insertNewGameInvite(fromPlayer, toPlayer, colorChoice, cursor, connection)
	#retrieve invite info
	inviteInfo = selectGameInviteByID(inviteID,cursor)
	# return invite.id
	return inviteInfo

#call addInvite
#send invite to recieving player
def invitePlayer(spec):
	#check if player is a real player
	if spec[0] == spec[2]:
		send(f"INVALIDINVITESELF",playerDic[spec[0]].sock)
	elif verifyUser(spec[2], cursor):
		inviteInfo = addInvite(spec[0], spec[2], spec[3])
		ID = inviteInfo[0]
		fromPlayer = inviteInfo[1]
		toPlayer = inviteInfo[2]
		#send to recieving player
		if toPlayer in playerDic:
			connected = playerDic[toPlayer].connected
			if connected:
				send(f"NEWINVITE,{fromPlayer},{ID}",playerDic[toPlayer].sock)
		send(f"VALIDINVITE",playerDic[fromPlayer].sock)
	else:
		send(f"INVALIDINVITE",playerDic[spec[0]].sock)

def acceptInvite(spec):
	player = spec[0]
	ID = int(spec[2])
	updateAcceptInvite(ID,cursor,connection)

	inviteInfo = selectGameInviteByID(ID,cursor)
	player1 = inviteInfo[1]
	p1color = inviteInfo[7]
	player2 = inviteInfo[2]
	gameInfo = addGame(player1,player2,p1color)
	gameID = gameInfo[0]
	p1 = gameInfo[1]
	p2 = gameInfo[2]
	if p1 in playerDic:
		p1Obj = playerDic[p1]
		p1connected = p1Obj.connected
	else:
		p1connected = False
	if p2 in playerDic:
		p2Obj = playerDic[p2]
		p2connected = p2Obj.connected
	else:
		p2connected = False
	if p1connected:
		send(f"NEWGAME,{p2}, {str(gameID)},white,{p2connected}",p1Obj.sock)
	if p2connected:
		send(f"NEWGAME,{p1}, {str(gameID)},black,{p1connected}",p2Obj.sock)

	
def rejectInvite(spec):
	player = spec[0]
	ID = int(spec[2])
	updateRejectInvite(ID,cursor,connection)

def abortGame(spec):
	resigningPlayerName = spec[0]
	ID = int(spec[2])
	winningPlayerName = spec[3]

	updateGameCompletionStatus(ID,1,cursor,connection)
	updateGameWinner(ID,winningPlayerName,cursor,connection)
	updateGameLoser(ID,resigningPlayerName,cursor,connection)
	updateUserLosses(resigningPlayerName,1,cursor,connection)
	updateUserWins(winningPlayerName,1,cursor,connection)

	if resigningPlayerName in playerDic:
		if playerDic[resigningPlayerName].connected:
			send(f"RESIGNLOSS,{str(ID)}",playerDic[resigningPlayerName].sock)
	if winningPlayerName in playerDic:
		if playerDic[winningPlayerName].connected:
			send(f"RESIGNWIN,{str(ID)}",playerDic[winningPlayerName].sock)

def movePiece(spec, msgStr):
	#Send to client
	sendingPlayer = spec[0]
	ind = str(msgStr).index("{")
	jsonStr = msgStr[int(ind):]
	gameObj = json.loads(jsonStr)
	ID = gameObj["id"]

	#Attempt to send to other player, if in playerDic. 
	#If other player isn't connected, the try/except in send() will catch it
	try:
		recievingPlayer = playerDic[gameObj["player2"]]
		sendToOther = True
	except:
		print("Recieving player not in playerDic")
		sendToOther = False


	updateGameState(ID,jsonStr,cursor,connection) #update gamestate in database
	
	if sendToOther:
		send(f"NEWMOVE,{ID},{jsonStr}",recievingPlayer.sock) #send to recieving player


def endGame(spec): #spec: ClientName, MATE, ID, winning color
	# if spec[0] in playerDic:
	# 	player = playerDic[spec[0]]
	ID = int(spec[2])
	# game = player.games[ID]
	print(f"ID = {ID}")
	game = selectGameByID(ID,cursor)
	p1 = game[1]
	p2 = game[2]
	if spec[3] == "black":
		winner = p1
		loser = p2
	else:
		winner = p2
		loser = p1
	
	#update stats in database
	updateGameCompletionStatus(ID,1,cursor,connection)
	updateGameWinner(ID,winner,cursor,connection)
	updateGameLoser(ID,loser,cursor,connection)
	updateUserLosses(loser,1,cursor,connection)
	updateUserWins(winner,1,cursor,connection)

	#send checkmate message to each player
	if winner in playerDic:
		send(f"WIN,{str(ID)}",playerDic[winner].sock)
	if loser in playerDic:
		send(f"LOSE,{str(ID)}",playerDic[loser].sock)

#update player's client with invites and games upon reconnecting to server
def updateOnReconnect(playerName):
	if playerName in playerDic:
		player = playerDic[playerName]
		#Send Invites
		invites = selectIncomingGameInvites(playerName,cursor)
		for inv in invites:
			ID = inv[0]
			fromPlayerName = inv[1]
			send(f"NEWINVITE,{fromPlayerName},{ID}", player.sock)

		#Send games
		games = selectCurrentGames(playerName,cursor)
		for game in games:
			ID = game[0]
			p1 = game[1]
			p2 = game[2]
			gameState = game[3]

			if playerName == p1:
				otherPlayerName = p2
				color = "white"
			else:
				otherPlayerName = p1
				color = "black"
			try:
				otherConnected = playerDic[otherPlayerName].connected
			except:
				otherConnected = False
			print(otherConnected)
			send(f"NEWGAME,{otherPlayerName}, {str(ID)},{color},{otherConnected}",player.sock)
			if gameState: #Should return false if string is empty, rather than a json string. If needed, check length too
				send(f"SETGAME, {gameState}",player.sock)

			if otherConnected:
				#send opponents yellow dot
				send(f"YELLOWDOT,{ID}",playerDic[otherPlayerName].sock)

#given player object and game ID, returns other player object #NO LONGER USED
def getOtherPlayer(player, ID):
	if player.games[ID].player1 is player:
		return player.games[ID].player2
	else:
		return player.games[ID].player1

#update connection status, send to other players
def notifyDisconnect(playerName):
	global playerDic
	try:
		playerDic[playerName].connected = False
		# player.connected = False
		games = selectCurrentGames(playerName,cursor)
		for game in games:
			ID = game[0]
			if playerName == game[1]:
				otherPlayer = game[2]
			elif playerName == game[2]:
				otherPlayer = game[1]
			try:
				if playerDic[otherPlayer].connected:
					send(f"DISC,{ID}",playerDic[otherPlayer].sock)
			except:
				print(f"Failed. Couldn't access other player for game {ID}")
	except: 
		print("Failed. Couldn't access disconnecting player.")

def checkLogin(username,password,sock):
	username = username.lower()
	#verify login
	print(alter(cursor,connection))
	validLogin = verifyPassword(username.rstrip(),password.rstrip(),cursor)
	
	if validLogin:
		if username not in playerDic: #if new player
			playerDic[username] = Player(username,sock) #add player to player dic
		elif username in playerDic: #if player is reconnecting
			playerDic[username].sock = sock #update socket
		
		playerDic[username].connected = True
		#send player valid login
		send(f"VALIDLOGIN,{username}",sock)
		#update player's invites and current games
		updateOnReconnect(username)
		
	else:
		send(f"INVALIDLOGIN,{username}",sock)

def yellowDot(fromPlayer, toPlayer, ID):
	if toPlayer in playerDic:
		if playerDic[toPlayer].connected:
			send(f"YELLOWDOT,{ID}",playerDic[toPlayer].sock)

def greenDot(fromPlayer, toPlayer, ID):
	if toPlayer in playerDic:
		if playerDic[toPlayer].connected:
			send(f"GREENDOT,{ID}",playerDic[toPlayer].sock)

#handles individual connection between client and server
def handle_client(conn, addr):
	print(f"[NEW CONNECTION] {addr} connected.")
	connected = True
	while connected:
		try:
			msg_length = conn.recv(HEADER).decode(FORMAT) # recv blocks until message from client is recieved.
			if msg_length: #if there is a message. True if not first time connecting
				msg_length = int(msg_length)
				msg = conn.recv(msg_length).decode(FORMAT)
				while len(msg) < msg_length:
					extra = conn.recv(1).decode(FORMAT)
					msg += extra
				spec = msg.split(',')
				if spec[0] == DISCONNECT_MESSAGE:
					connected = False
					print(f"{addr} ({spec[1]}) Disconected")
					# conn.send(DISCONNECT_MESSAGE.encode(FORMAT))
					send(DISCONNECT_MESSAGE, conn)
					notifyDisconnect(spec[1])
				elif spec[0] == "LOGIN":
					checkLogin(spec[1].rstrip(),spec[2].rstrip(),conn)
				else:
					# print(f"[{addr}] {msg}")
					# conn.send("Message recieved\n".encode(FORMAT))
					print(f"recieved {msg}")
					process(conn, msg)
		except:
			print("Invalid input ignored")
	conn.close() #close current connection after client has disconnected

#handle new connections
def start():
	server.listen() #listen for new connections
	print(f"Server is listening on {SERVER}")
	while True:
		conn, addr = server.accept() #blocks - waits for a new connection to server. When new connection occurs, store socket object (conn) and address (addr)
		#start new thread
		thread = threading.Thread(target = handle_client, args = (conn, addr))
		thread.start()
		print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")

def process(sock, msg): #socket object, message
	spec = msg.split(',') #split string message into list
		
	if(len(spec)>1):
		if(spec[1] == "INVITE"):#client is sending a new game invitation
			invitePlayer(spec)

		elif(spec[1] == "ACCEPT"): #Client accepted game invite
			acceptInvite(spec)

		elif(spec[1] == "REJECT"): #client rejected game invitation
			rejectInvite(spec)

		elif(spec[1] == "ABORT"):
			abortGame(spec)

		elif(spec[1] == "MOVE"):
			movePiece(spec, msg)
		
		elif(spec[1] == "MATE"):
			endGame(spec)

		elif(spec[1] == "LEFTGAMEVIEW"):
			yellowDot(spec[0],spec[2], spec[3])
		
		elif(spec[1] == "ENTEREDGAMEVIEW"):
			greenDot(spec[0],spec[2],spec[3])

def main():
	print("STARTING server")
	start()

main()