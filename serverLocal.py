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

# cursor.execute("SELECT * FROM tblGames")
# print(selectCurrentGames("astem1",cursor))
print(alter(cursor,connection))
# print(selectTableFields("tblGames",cursor))

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"

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
		self.games = {} #Dictionary of current games. key = id, value = game object
		self.invitesRecieved = {} #dictionary of invites they have recieved. key = id, value = invite object

class Square():
    def __init__(self, xCoord, yCoord, x, y):
        self.x = x
        self.y = y

class Piece():
    def __init__(self, color, type, square):
        self.color = color
        self.type = type
        self.hasMoved = False
        self.location = square

class Game:
	def __init__(self, ID, firstPlayer, secondPlayer, colorChoice):
		self.id = ID
		#set players, according to color choice
		if colorChoice == "white":
			print("white")
			self.player1 = firstPlayer #player object. access name with self.player1.name. player1 = white, player2 = black
			self.player2 = secondPlayer
		elif colorChoice == "black":
			print("black")
			self.player2 = firstPlayer
			self.player1 = secondPlayer
		elif colorChoice == "random":
			print("random")
			rand = random.randint(0,1)
			if rand == 1:
				self.player1 = firstPlayer
				self.player2 = secondPlayer
			else:
				self.player2 = firstPlayer
				self.player1 = secondPlayer
		self.turn = "white"
		self.pieces = {}
		self.jsonState = None

class Invite:
	def __init__(self, fromPlayer, toPlayer, colorChoice):
		self.id = random.randint(0,1000) #generate random ID
		self.fromPlayer = fromPlayer #player object. access name with self.fromPlayer.name
		self.toPlayer = toPlayer
		self.colorChoice = colorChoice

def addGame(p1,p2,p1color):
	# player1 = playerDic[player].invitesRecieved[ID].fromPlayer
	# player2 = playerDic[player].invitesRecieved[ID].toPlayer
	# game = Game(ID, player1, player2, playerDic[player].invitesRecieved[ID].colorChoice) #create game object
	# player1.games[game.id] = game #add game object to gameList for each player. Both values in player game dic reference the same game
	# player2.games[game.id] = game
	# return game.id
	
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


#create new invite object and add to toPlayer's list of recieved invites
#return invite ID (randomly generated)
def addInvite(fromPlayer, toPlayer, colorChoice): #pass in names as strings
	# fromPlayerObj = playerDic[fromPlayer]
	# toPlayerObj = playerDic[toPlayer]
	# invite = Invite(fromPlayerObj, toPlayerObj, colorChoice)
	# toPlayerObj.invitesRecieved[invite.id] = invite #add invite to recieving player's invitesRecieved

	#add invite to database
	inviteID = insertNewGameInvite(fromPlayer, toPlayer, colorChoice, cursor, connection)
	#retrieve invite info
	inviteInfo = selectGameInviteByID(inviteID,cursor)

	# return invite.id
	return inviteInfo

#remove invite from player's list of invites. NO LONGER USED
def removeInvite(ID, toPlayer):
	toPlayer = playerDic[toPlayer]
	del toPlayer.invitesRecieved[ID]

#call addInvite
#send invite to recieving player
def invitePlayer(spec):
	#check if player is a real player
	if spec[0] == spec[2]:
		send(f"INVALIDINVITESELF",playerDic[spec[0]].sock)
	elif verifyUser(spec[2], cursor):
		# inviteID = addInvite(spec[0], spec[2], spec[3]) #add invite to player's dic of invites
		# # playerDic[spec[2]].sock.send(f"NEWINVITE,{str(spec[0])},{str(inviteID)}".encode(FORMAT)) #send player the invite. FORMAT: NEWINVITE, FromPlayer, InviteID
		# send(f"NEWINVITE,{str(spec[0])},{str(inviteID)}", playerDic[spec[2]].sock)
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

	#add game to each player's dic of games. Arguments: playerName, inviteID
	# addGame(player, ID)
	#remove invite
	# removeInvite(ID, player) #INVITE WAS TO "player"
	#send both players the game
	# game = playerDic[player].games[ID]
	# print(f"Game ID: {game.id}")
	# p1 = game.player1 #player that initially sent the invite
	# p2 = game.player2 #player that accepted the invite
	# p1.sock.send(f"NEWGAME,{p2.name}, {str(ID)},white".encode(FORMAT)) #FORMAT: INVITEACCEPTED, OtherPlayer, ID, color
	# p2.sock.send(f"NEWGAME,{p1.name}, {str(ID)},black".encode(FORMAT))
	# send(f"NEWGAME,{p2.name}, {str(ID)},white,{p2.connected}",p1.sock)
	# send(f"NEWGAME,{p1.name}, {str(ID)},black,{p1.connected}",p2.sock)

def rejectInvite(spec):
	player = spec[0]
	ID = int(spec[2])
	updateRejectInvite(ID,cursor,connection)
	# removeInvite(ID, player) #INVITE WAS TO "player"

def abortGame(spec):
	# p1 = playerDic[spec[0]] #player that resigned
	resigningPlayerName = spec[0]
	ID = int(spec[2])
	winningPlayerName = spec[3]

	updateGameCompletionStatus(ID,1,cursor,connection)
	updateGameWinner(ID,winningPlayerName,cursor,connection)
	updateGameLoser(ID,resigningPlayerName,cursor,connection)
	updateUserLosses(resigningPlayerName,1,cursor,connection)
	updateUserWins(winningPlayerName,1,cursor,connection)

	# p2 = getOtherPlayer(p1,ID) #player that won #CHANGE THIS\
	# gameToRemove = p1.games[ID]
	# p1 = gameToRemove.player1
	# p2 = gameToRemove.player2
	#Remove game from both players' game dicts
	# del p1.games[gameToRemove.id]
	# del p2.games[gameToRemove.id]
	#send game removal to both players
	# p1.sock.send(f"DELGAME,{str(gameToRemove.id)}".encode(FORMAT)) #FORMAT: DELGAME, GameID
	# p2.sock.send(f"DELGAME,{str(gameToRemove.id)}".encode(FORMAT))
	if resigningPlayerName in playerDic:
		if playerDic[resigningPlayerName].connected:
			send(f"RESIGNLOSS,{str(ID)}",playerDic[resigningPlayerName].sock)
	if winningPlayerName in playerDic:
		if playerDic[winningPlayerName].connected:
			send(f"RESIGNWIN,{str(ID)}",playerDic[winningPlayerName].sock)

def movePiece(spec, msgStr):
	#spec: [movingPlayerName, MOVE, jsonString (but split up every comma, so not really)]
	#TODO: Update game state on server
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


	#Store game state in server
	# recievingPlayer.games[ID].pieces = gameObj['pieces'] #only need to update for one player, since both game dict values point to the same game object
	# recievingPlayer.games[ID].turn = gameObj['turn']
	# recievingPlayer.games[ID].jsonState = jsonStr
	#send to other player
	# recievingPlayer.sock.send(f"NEWMOVE,{ID},{jsonStr}".encode(FORMAT)) #FORMAT: NEWMOVE, ID, jsonString
	# send(f"NEWMOVE,{ID},{jsonStr}",recievingPlayer.sock)

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
		#""" update games
		# for game in player.games:
		# 	ID = player.games[game].id #Get game ID
		# 	#Get other player
		# 	if player.games[game].player1 is player: #player is player1
		# 		otherPlayer = player.games[game].player2
		# 		color = "white"
		# 	else: #player is player2
		# 		otherPlayer = player.games[game].player1
		# 		color = "black"
		# 	#Send game to player
		# 	# player.sock.send(f"NEWGAME,{otherPlayer.name}, {str(ID)},{color}".encode(FORMAT)) #FORMAT: INVITEACCEPTED, OtherPlayer, ID, color
		# 	send(f"NEWGAME,{otherPlayer.name}, {str(ID)},{color},{otherPlayer.connected}",player.sock)
		# 	# player.sock.send(f"SETGAME, {player.games[ID].jsonState}".encode(FORMAT))
		# 	send(f"SETGAME, {player.games[ID].jsonState}",player.sock)
		# 	time.sleep(.1)
		#update invites
		# for inv in player.invitesRecieved:
		# 	print(f"sent player invite {inv} on reconnect")
		# 	# player.sock.send(f"NEWINVITE,{player.invitesRecieved[inv].fromPlayer.name},{str(inv)}".encode(FORMAT)) #send player the invite. FORMAT: NEWINVITE, FromPlayer, InviteID
		# 	send(f"NEWINVITE,{player.invitesRecieved[inv].fromPlayer.name},{str(inv)}", player.sock)
		# 	time.sleep(.1) """

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
	# print(username)
	# print(password)
	#verify login
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

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #choose socket family and type
server.bind(ADDR) #bind server to address

#handles individual connection between client and server
def handle_client(conn, addr):
	print(f"[NEW CONNECTION] {addr} connected.")
	connected = True
	while connected:
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