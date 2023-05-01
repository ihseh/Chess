import arcade
import arcade.gui
import socket
import time
import threading
import sys
import random
import json
import math

#arcade variables
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Chess"
SQUARE_SIZE = 100
BOARD_SIZE = 8
MARGIN = 50

#socket variables
HEADER = 64
PORT = 8080
# PORT = 22
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"
# SERVER = socket.gethostbyname(socket.gethostname())
# SERVER = '172.31.24.105'
# SERVER = '3.15.33.221'
# SERVER = '18.117.82.36'
# SERVER = '3.142.120.7'
# SERVER = '3.145.148.56'
SERVER = '3.20.76.52'
ADDR = (SERVER,PORT)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #setup socket
event = threading.Event() #event for killing thread

#PLAYER DATA
clientName = ""
# clientName = sys.argv[1] #store first command line argument as client name
# clientName = "default"
connectedToServer = True
# try:
#     if sys.argv[2] == "login":
#         showLogin = True
# except:
#     showLogin = False
#Game List
game_dic = {} #stores instances of game class
#Invites lists
inv_dic = {} #stores instances of invite class

#method to send message to server
def send(msg, client):
    message = msg.encode(FORMAT) #encode message
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    try:
        client.send(send_length)
        client.send(message)
        print(f"sent: {message}")
    except:
        print("COULDN'T REACH SERVER")

#waits for input from server and processes input accordingly. Method will be called in new thread as to not stop program executing with infinite while loop
def wait_for_server_input(client, window):
    while True:
        msg_length = client.recv(HEADER).decode(FORMAT)
        print(f"message length = {msg_length}")
        if msg_length:
            msg_length  = int(msg_length)
            message = client.recv(msg_length).decode(FORMAT)
            while len(message) < msg_length:
                extra = client.recv(1).decode(FORMAT)
                message += extra

            print(f"recieved {message}")

        if event.is_set(): #break if user closes client
            break
        # message = client.recv(4086).decode(FORMAT)
        msg = message.split(',') #split message into list
        if msg[0] == DISCONNECT_MESSAGE:
            print("Disconnect Recieved!!!!!")
        if msg[0] == "NEWINVITE": #New invite recieved
            addInviteToInviteDic(msg[1], msg[2]) #arguments: fromPlayer, InviteID 
        elif msg[0] == "NEWGAME": #A player accepted your game invitation
            #add game to game list
            # print(f"NEW GAME WITH {msg[1]}")
            # print("NewGame")
            addGameToGameDic(msg[1], int(msg[2]), msg[3], msg[4])
        elif msg[0] == "RESIGNWIN":
            # delGame(int(msg[1]))
            resignWin(int(msg[1]))
        elif msg[0] == "RESIGNLOSS":
            resignLoss(int(msg[1]))
        elif msg[0] == "NEWMOVE":
            from_json(message, False)
        elif msg[0] == "SETGAME":
            from_json(message, True)
        elif msg[0] == "WIN":
            winGame(int(msg[1]))
        elif msg[0] == "LOSE":
            loseGame(int(msg[1]))
        elif msg[0] == "DISC":
            updateStatus(int(msg[1]),"red")
        elif msg[0] == "VALIDLOGIN":
            print("VALID")
            valid(msg[1])
        elif msg[0] == "INVALIDLOGIN":
            print("INVALID")
            invalid()
        elif msg[0] == "VALIDINVITE":
            inviteConfirmation("valid")
        elif msg[0] == "INVALIDINVITE":
            inviteConfirmation("invalid")
        elif msg[0] == "INVALIDINVITESELF":
            inviteConfirmation("invalidself")
        elif msg[0] == "YELLOWDOT":
            updateStatus(int(msg[1]),"yellow")
        elif msg[0] == "GREENDOT":
            updateStatus(int(msg[1]),"green")

def updateStatus(ID,color):
    try:
        game_dic[ID].board.opConnected = color
    except:
        print("Game not found")

def valid(username): #take user to home screen
    loginView.showLoginError = False
    global clientName
    clientName= username
    window.show_view(homeView)

def invalid(): #notify of invalid username/password
    loginView.showLoginError = True

#Game class
class Game():
    def __init__(self, ID, player1, player2, color, cont, abort):
        self.id = ID #same id as invite ID
        self.player1 = player1
        self.player2 = player2
        self.cont = cont #continue button
        self.abort = abort #abort button
        self.board = Board()
        self.board.turn = "white"
        self.board.color = color 
        self.board.make_grid()
        self.board.id = ID

    def __str__(self): #toString
        return f"Game: {self.player1} vs {self.player2}"
    
    #helper method for to_json
    def getPiecesForJson(self) -> list:
        piecesDicJson = {}
        for piece in self.board.pieces_dic:
            piecesDicJson[piece] = self.board.pieces_dic[piece].getPieceForJson()
        return piecesDicJson

    #convert game class to JSON string
    def to_json(self): 
        pieces = self.getPiecesForJson()
        gameAsDic = {
            'id' : self.id,
            'player1' : self.player1,
            'player2' : self.player2,
            'pieces' : pieces,
            'turn' : self.board.turn
        }
        return json.dumps(gameAsDic)
    
    def update_state(self, gameAsDic):
        #update turn ---- SHOULDNT NEED TO DO, SINCE MOVEPIECE DOES THIS
        # self.board.turn = gameAsDic["turn"]
        #update piece dic
        pieceDic = gameAsDic["pieces"]
        self.board.draw = False #Pause drawing.
        while not self.board.drawDone:
            time.sleep(.005)
        for p in pieceDic:
            if not self.board.pieces_dic[p].isSameLocation(pieceDic[p]["location"]['x'],pieceDic[p]["location"]['y']):
                print("Moving Piece")
                self.board.movePiece(self.board.pieces_dic[p], self.board.grid[pieceDic[p]["location"]['y']][pieceDic[p]["location"]['x']],False, False)  #pieceToMove, squareToMove, send, castle = False
        self.board.draw = True

    def set_state_on_reconnect(self, gameAsDict):
        print("Updating State on Reconnect")
        pieceDict = gameAsDict["pieces"]
        #set turn
        self.board.turn = gameAsDict['turn']
        #Remove taken pieces
        piecesToRemove = []
        for p in self.board.pieces_dic:
            if p not in pieceDict:
                piecesToRemove.append(p)
        for p in piecesToRemove:
            # print(f"deleting {self.board.pieces_dic[p]}")
            del self.board.pieces_dic[p]
        #set locations and hasMoved
        for p in self.board.pieces_dic:
            self.board.pieces_dic[p].hasMoved = pieceDict[p]['hasMoved']
            self.board.pieces_dic[p].location = self.board.grid[pieceDict[p]['location']['y']][pieceDict[p]['location']['x']]
            #move sprite
            self.board.pieces_dic[p].sprite.center_x = self.board.pieces_dic[p].location.xCoord
            self.board.pieces_dic[p].sprite.center_y = self.board.pieces_dic[p].location.yCoord
        #set pieceOn for each square
        for row in self.board.grid:
            for square in row:
                square.pieceOn = None
        for p in self.board.pieces_dic:
            self.board.pieces_dic[p].location.pieceOn = self.board.pieces_dic[p]

#Square class: Holds information about each square in board.grid[][]
class Square():
    def __init__(self, xCoord, yCoord, x, y):
        self.xCoord = xCoord
        self.yCoord = yCoord
        self.x = x
        self.y = y
        self.pieceOn = None

    def __str__(self):
        return "Square: x = " + str(self.x) + ", y = " + str(self.y)
    
    #helper method for Game.to_json
    def getSquareForJSON(self) -> dict:
        squareDic = {
            'x' : self.x,
            'y' : self.y
        }
        return squareDic

#Piece class: Holds information about each piece, including sprite
class Piece():
    def __init__(self, sprite, color, type, square):
        self.sprite = sprite
        self.color = color
        self.type = type
        self.hasMoved = False
        self.location = square

    def __str__(self):
        return f"{self.color} {self.type} on {self.location.x},{self.location.y}"
    
    def isSameLocation(self, x, y):
        if self.location.x == x and self.location.y == y:
            return True
        else:
            return False
    
    def getPieceForJson(self) -> dict:
        square = self.location.getSquareForJSON()
        pieceDic = {
            # 'color' : self.color,
            # 'type' : self.type,
            'hasMoved' : self.hasMoved,
            'location' : square
        }
        return pieceDic

#invite class: holds invite id, player invite was from, and acc/rej buttons
class Invite(): 
    def __init__(self, ID, fromPlayer, acc, rej): #fromPlayer, acceptButton, rejectButton. Doesn't need toPlayer, because that's always the client
        self.id = ID
        self.fromPlayer = fromPlayer
        self.acc = acc #accept button
        self.rej = rej #reject button
   
#read in json string, and update appropriate game
def from_json(msgStr, reconnect):
    # print(msgStr)
    try:
        ind = str(msgStr).index("{")
        jsonStr = msgStr[int(ind):]
        gameAsDict = json.loads(jsonStr) #convert to dictionary
        ID = gameAsDict['id']
        gameObject = game_dic[ID]
        if reconnect:
            gameObject.set_state_on_reconnect(gameAsDict)
        else:
            gameObject.board.opConnected = "green"
            gameObject.update_state(gameAsDict)
    except:
        print("Error")

#Create new instance of Game class, and add to game dic
def addGameToGameDic(otherPlayer, ID, color, opConnected):
    # print("addGameToGameDic")
    gameToAdd = Game(ID, "You", otherPlayer, color, ContinueGameButton(text = "Continue", width = 100, height = 20) , RemoveGameButton(text = "Resign", width = 100, height = 20))
    game_dic[gameToAdd.id] = gameToAdd
    if opConnected == "True":
        game_dic[gameToAdd.id].board.opConnected = "yellow"
    else:
        game_dic[gameToAdd.id].board.opConnected = "red"
    # print(f"Game id: {gameToAdd.id}")

#Create new invite object, add to player's dic of invites
def addInviteToInviteDic(fromPlayer, inviteID):
    inviteToAdd = Invite(inviteID, fromPlayer, AcceptButton(text = "Accept", width = 100, height = 20), RejectButton(text = "Reject", width = 100, height = 20))
    inv_dic[inviteToAdd.id] = inviteToAdd
    print(f"invite id: {inviteToAdd.id}")

#Delete game from game dic. NO LONGER USED
def delGame(ID):
    try:
        if window.current_view is game_dic[ID].board:
            pass #show resign message
        del game_dic[ID]
        currentGamesView.update_list()
    except:
        print("Error")
    
def resignWin(ID):
    try:
        if window.current_view is game_dic[ID].board:
            game_dic[ID].board.winbyres = True
            game_dic[ID].board.over = True
        else:
            # print("DELETING!!!!!")
            del game_dic[ID]
            currentGamesView.update_list()
    except:
        print("Error")

def resignLoss(ID):
    try:
        del game_dic[ID]
        currentGamesView.update_list()
    except:
        print("Error")

def winGame(ID):
    try:
        # print("WINGAME")
        # game_dic[ID].board.result = "WON"
        # game_dic[ID].board.showResult()
        # window.current_view.showResult()
        game_dic[ID].board.winbymate = True
        game_dic[ID].board.over = True
    except:
        print("Error")

def loseGame(ID):
    try:
        # print("LOSEGAME")
        # game_dic[ID].board.result = "LOST"
        # game_dic[ID].board.showResult()
        # window.current_view.showResult()
        game_dic[ID].board.losebymate = True
        game_dic[ID].board.over = True
    except:
        print("Error")

#Determine which piece center is closest to piece location when piece dropped
def snapPiece(piece, x, y, grid):
        min = 1000
        for row in grid:
            for square in row:
                xdist = pow((square.xCoord - x),2)
                ydist = pow((square.yCoord - y),2)
                dist = math.sqrt(xdist + ydist)
                if(dist < min):
                    min = dist
                    squareToMove = square
        return squareToMove

#Check that the movement of the piece is valid
#Return true if the move is valid, false if not.
def checkValidMove(piece, fromSquare, toSquare, grid, boardClassObject):

    #local methods to check squares in between piece to and from locations, to ensure that they're empty
    def checkBishopLane():
        y = smallerXSquare.y + increment
        for x in range(smallerXSquare.x + 1, biggerXSquare.x):
            #print(grid[y][x])
            if grid[y][x].pieceOn:
                #print("Piece on square")
                return False
            y += increment
        return True
    def checkRookLaneX():
        for y in range(smallerYSquare.y + 1, biggerYSquare.y):
                if grid[y][fromSquare.x].pieceOn:
                    return False
        return True
    def checkRookLaneY():
        for x in range(smallerXSquare.x + 1, biggerXSquare.x):
                if grid[fromSquare.y][x].pieceOn:
                    return False
        return True
    def checkDoublePawnLane():
        if abs(fromSquare.y - toSquare.y) == 1:
            return True
        else:
            if piece.color == "white":
                if grid[fromSquare.y - 1][fromSquare.x].pieceOn:
                    return False
                else:
                    return True
            elif piece.color == "black":
                if grid[fromSquare.y + 1][fromSquare.x].pieceOn:
                    return False
                else:
                    return True
    #check that the move is to a new square
    if fromSquare is toSquare:
        return False
    #set variables to be used in calculations
    #get square with larger x-coordinate
    if fromSquare.x > toSquare.x:
        biggerXSquare = fromSquare
        smallerXSquare = toSquare
    else:
        biggerXSquare = toSquare
        smallerXSquare = fromSquare
    #get square with larger y-coordinate
    if fromSquare.y > toSquare.y:
        biggerYSquare = fromSquare
        smallerYSquare = toSquare
    else:
        biggerYSquare = toSquare
        smallerYSquare = fromSquare
    #check if variables refer to same square, set increment accordingly
    if smallerXSquare is smallerYSquare:
        increment = 1
    else:
        increment = -1
    #check that piece is not occupied by another piece of same color
    if toSquare.pieceOn: #if pieceOn is not None
        if toSquare.pieceOn.color == piece.color:
            return False
    #set yy-variables, used in catstle-ing
    if piece.color == "black":
        colorY = 0 #y-coord of black pieces' back row
    elif piece.color == "white":
        colorY = 7 #y-coord of white pieces' back row
    #check that movement pattern is appropriate for each piece 
    if piece.type == "pawn": #PAWN
        #check if pawn is taking diagonal
        if piece.color == "white":
            if toSquare.y + 1 == fromSquare.y and abs(toSquare.x - fromSquare.x) == 1 and toSquare.pieceOn: #if pawn is moving to a diagonal forward square, with a piece of other color on it
                return True
        elif piece.color == "black":
            if toSquare.y - 1 == fromSquare.y and abs(toSquare.x - fromSquare.x) == 1 and toSquare.pieceOn:
                return True
        if toSquare.pieceOn: #cannot take otherwise
            return False
        if piece.hasMoved: #allow 1 step forward if pawn has already moved
            if piece.color == "white":
                if toSquare.y + 1 == fromSquare.y and toSquare.x == fromSquare.x:
                    return True
                else:
                    return False
            elif piece.color == "black":
                if toSquare.y - 1 == fromSquare.y and toSquare.x == fromSquare.x:
                    return True
                else:
                    return False
        else: #allow up to 2 steps forward if piece has not moved
            if piece.color == "white":
                if fromSquare.y - toSquare.y <= 2 and fromSquare.y - toSquare.y > 0 and toSquare.x == fromSquare.x:
                    return checkDoublePawnLane()
                else:
                    return False
            elif piece.color == "black":
                if toSquare.y - fromSquare.y <= 2 and toSquare.y - fromSquare.y > 0 and toSquare.x == fromSquare.x:
                    return checkDoublePawnLane()
                else:
                    return False
    if piece.type == "bishop": #BISHOP
        if abs(toSquare.x - fromSquare.x) == abs(toSquare.y - fromSquare.y): #If movement is diagonal
            return checkBishopLane()
        else:
            return False
    if piece.type == "rook": #ROOK
        if toSquare.x == fromSquare.x:
            return checkRookLaneX() 
        elif toSquare.y == fromSquare.y:
            return checkRookLaneY()
        else:
            return False
    if piece.type == "knight": #KNIGHT
        xChange = abs(toSquare.x - fromSquare.x)
        yChange = abs(toSquare.y - fromSquare.y)
        if (xChange == 2 and yChange == 1) or (xChange == 1 and yChange == 2):
            return True
        else:
            return False
    if piece.type == "king": #KING
        if abs(toSquare.x - fromSquare.x) <= 1 and abs(toSquare.y - fromSquare.y) <= 1: #Check if movement is within 1 square radius
            return True
        else: #check if castle is ok, if attempted. DOES NOT ACCOUNT FOR NOT CASTLE-ING THROUGH CHECK
            if toSquare.y == fromSquare.y and abs(toSquare.x - fromSquare.x) == 2 and piece.hasMoved == False: 
                if toSquare.x == 1: #left rook castle
                    if grid[colorY][0].pieceOn:
                        if (not grid[colorY][0].pieceOn.hasMoved) and (not grid[colorY][1].pieceOn) and (not grid[colorY][2].pieceOn):
                            return True
                elif toSquare.x == 5: #right rook castle
                    if grid[colorY][7].pieceOn:
                        if (not grid[colorY][7].pieceOn.hasMoved) and (not grid[colorY][4].pieceOn) and (not grid[colorY][5].pieceOn) and (not grid[colorY][6].pieceOn):
                            return True
        return False
        
    if piece.type == "queen": #QUEEN
        if abs(toSquare.x - fromSquare.x) == abs(toSquare.y - fromSquare.y):
            return checkBishopLane()
        if toSquare.x == fromSquare.x:
            return checkRookLaneX()
        if toSquare.y == fromSquare.y:
            return checkRookLaneY()
        else:
            return False
        
def checkTurnAndColor(piece, turn, color): #check that piece being moved is a piece of the turn's color.
    if (piece.color == turn) and (str(color) == str(turn)): 
        return True
    else:
        return False

#Check if a certain king is in check. 
#Return True if king is in check, false otherwise
def kingInCheck(king, grid, boardClassObject):
    #check if any piece in pieces_dic puts king in check
    for p in boardClassObject.pieces_dic:
        if checkValidMove(boardClassObject.pieces_dic[p], boardClassObject.pieces_dic[p].location, king.location, grid, boardClassObject): #piece, fromSquare, toSquare, grid, boardClassObject
            return True
    return False

#Board class that holds sprites, grid of squares, pieces_dic, audio, most of the game methods, etc
class Board(arcade.View):

    def __init__(self):
        """ Initializer """
        # Call the parent class initializer / initialize constants
        super().__init__()
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT
        self.title = SCREEN_TITLE
        # arcade.set_background_color(arcade.color.LIGHT_GRAY)
        self.dragging = False
        self.movingPiece = None
        self.draw = True
        self.drawDone = True
        #explosions 
        self.explode = 18
        self.explosions = True
        #Audio
        self.audio_move_piece = arcade.load_sound('audio/place_piece.wav', False)
        #self.audio_capture_piece = arcade.sound.load_sound("audio_file_name")
        self.audio_explosion = arcade.load_sound('audio/explosion.wav', False)
        self.audio_check = arcade.load_sound('audio/check.wav', False)
        self.audio_checkmate = arcade.load_sound('audio/checkmate.wav', False)
        self.audio_promotePawn = arcade.load_sound('audio/promote.wav', False)

        # #Home button
        # self.manager = arcade.gui.UIManager()
        # self.backButton = BackHomeButton(text="Home", width=50, height = 20, x = 20, y = 770)
        # self.manager.add(self.backButton)

        #Cursor
        # self.window.set_mouse_visible(False)
        self.cursor = arcade.Sprite("cursor/cursor.png", scale=1.5)
        self.cursor_grab = arcade.Sprite("cursor/cursor-grab.png", scale=1.5)

        self.turn = None
        self.color = None
        self.whiteInCheck = False
        self.blackInCheck = False
        self.result = None
        self.winbyres = False
        self.winbymate = False
        self.losebymate = False
        self.over = False
        self.winbyresMessage = arcade.Sprite("sprites/winbyres.png", scale=.7, center_x = 450, center_y = 400)
        self.winmateMessage = arcade.Sprite("sprites/win.png", scale=.8, center_x = 450, center_y = 400)
        self.losemateMessage = arcade.Sprite("sprites/loss.png", scale=.8, center_x = 450, center_y = 400)
        self.id = 0


        self.grid = [] #2D array of squares. Indexed [y][x]
        #generate grid of squares
        # self.make_grid() #called from game constructor instead, so that color is set first

        #dic of pieces
        self.pieces_dic = {}

        self.started = False
        
        # #load black piece sprites
        # self.king_b = arcade.Sprite("sprites/kingb.png", center_x= 350, center_y= 50, scale = 2)
        # self.queen_b = arcade.Sprite("sprites/queenb.png", center_x= 450, center_y= 50, scale = 2)
        # self.rook_b = arcade.Sprite("sprites/rookb.png", center_x= 50, center_y= 50, scale = 2)
        # self.rook_b2 = arcade.Sprite("sprites/rookb.png", center_x= 750, center_y= 50, scale = 2)
        # self.bishop_b = arcade.Sprite("sprites/bishopb.png", center_x= 250, center_y= 50, scale = 2)
        # self.bishop_b2 = arcade.Sprite("sprites/bishopb.png", center_x= 550, center_y= 50, scale = 2)
        # self.knight_b = arcade.Sprite("sprites/knightb.png", center_x= 150, center_y= 50, scale = 2)
        # self.knight_b2 = arcade.Sprite("sprites/knightb.png", center_x= 650, center_y= 50, scale = 2)
        # self.pawn_b1 = arcade.Sprite("sprites/pawnb.png", center_x = 50, center_y = 150, scale = 2)
        # self.pawn_b2 = arcade.Sprite("sprites/pawnb.png", center_x = 150, center_y = 150, scale = 2)
        # self.pawn_b3 = arcade.Sprite("sprites/pawnb.png", center_x = 250, center_y = 150, scale = 2)
        # self.pawn_b4 = arcade.Sprite("sprites/pawnb.png", center_x = 350, center_y = 150, scale = 2)
        # self.pawn_b5 = arcade.Sprite("sprites/pawnb.png", center_x = 450, center_y = 150, scale = 2)
        # self.pawn_b6 = arcade.Sprite("sprites/pawnb.png", center_x = 550, center_y = 150, scale = 2)
        # self.pawn_b7 = arcade.Sprite("sprites/pawnb.png", center_x = 650, center_y = 150, scale = 2)
        # self.pawn_b8 = arcade.Sprite("sprites/pawnb.png", center_x = 750, center_y = 150, scale = 2)

        # #load white piece sprites
        # self.king_w = arcade.Sprite("sprites/kingw.png", center_x= 350, center_y= 750, scale = 2)
        # self.queen_w = arcade.Sprite("sprites/queenw.png", center_x= 450, center_y= 750, scale = 2)
        # self.rook_w = arcade.Sprite("sprites/rookw.png", center_x= 50, center_y= 750, scale = 2)
        # self.rook_w2 = arcade.Sprite("sprites/rookw.png", center_x= 750, center_y= 750, scale = 2)
        # self.bishop_w = arcade.Sprite("sprites/bishopw.png", center_x= 250, center_y= 750, scale = 2)
        # self.bishop_w2 = arcade.Sprite("sprites/bishopw.png", center_x= 550, center_y= 750, scale = 2)
        # self.knight_w = arcade.Sprite("sprites/knightw.png", center_x= 150, center_y= 750, scale = 2)
        # self.knight_w2 = arcade.Sprite("sprites/knightw.png", center_x= 650, center_y= 750, scale = 2)
        # self.pawn_w1 = arcade.Sprite("sprites/pawnw.png", center_x = 50, center_y = 650, scale = 2)
        # self.pawn_w2 = arcade.Sprite("sprites/pawnw.png", center_x = 150, center_y = 650, scale = 2)
        # self.pawn_w3 = arcade.Sprite("sprites/pawnw.png", center_x = 250, center_y = 650, scale = 2)
        # self.pawn_w4 = arcade.Sprite("sprites/pawnw.png", center_x = 350, center_y = 650, scale = 2)
        # self.pawn_w5 = arcade.Sprite("sprites/pawnw.png", center_x = 450, center_y = 650, scale = 2)
        # self.pawn_w6 = arcade.Sprite("sprites/pawnw.png", center_x = 550, center_y = 650, scale = 2)
        # self.pawn_w7 = arcade.Sprite("sprites/pawnw.png", center_x = 650, center_y = 650, scale = 2)
        # self.pawn_w8 = arcade.Sprite("sprites/pawnw.png", center_x = 750, center_y = 650, scale = 2)
        
        #set up explosion animation
        if self.explosions:
            self.explosion = arcade.AnimatedTimeBasedSprite()
            for i in range(1,18):
                frame = arcade.load_texture(f"sprites/explode/f{i}.png")
                anim = arcade.AnimationKeyframe(i-1,30,frame)
                self.explosion.frames.append(anim)
            self.explosion.scale = 1.5
        
        #Status 
        #dots
        self.greenDot = arcade.Sprite("sprites/greendot.png", scale=.1, center_x = 790, center_y = 790)
        self.redDot = arcade.Sprite("sprites/reddot.png", scale=.1, center_x = 790, center_y = 790)
        self.yellowDot = arcade.Sprite("sprites/yellowdot.png", scale=.1, center_x = 790, center_y = 790)
        self.opConnected = "red"

        self.yourturn = arcade.Sprite("sprites/yourturn.png",scale = .07, center_x = 760, center_y = 15)

       
    #generate grid: 2D array of squares. Indexed self.grid[y][x] to access piece at x,y
    def make_grid(self):
        for j in range(8):
            if self.color == "black":
                yCoord = j * 100 + 50
            elif self.color == "white":
                yCoord = (7-j) * 100 + 50
            y = j
            singleRow = []
            for i in range(8):
                if self.color == "black":
                    xCoord = i * 100 + 50
                elif self.color == "white":
                    xCoord = (7-i) * 100 + 50
                x = i
                singleRow.append(Square(xCoord,yCoord, x, y))
            self.grid.append(singleRow)
        
        #load black piece sprites
        self.king_b = arcade.Sprite("sprites/kingb.png", center_x= self.grid[0][3].xCoord, center_y= self.grid[0][3].yCoord, scale = 2)
        self.queen_b = arcade.Sprite("sprites/queenb.png", center_x= self.grid[0][4].xCoord, center_y= self.grid[0][4].yCoord, scale = 2)
        self.rook_b = arcade.Sprite("sprites/rookb.png", center_x= self.grid[0][0].xCoord, center_y= self.grid[0][0].yCoord, scale = 2)
        self.rook_b2 = arcade.Sprite("sprites/rookb.png", center_x= self.grid[0][7].xCoord, center_y= self.grid[0][7].yCoord, scale = 2)
        self.bishop_b = arcade.Sprite("sprites/bishopb.png", center_x= self.grid[0][2].xCoord, center_y= self.grid[0][2].yCoord, scale = 2)
        self.bishop_b2 = arcade.Sprite("sprites/bishopb.png", center_x= self.grid[0][5].xCoord, center_y= self.grid[0][5].yCoord, scale = 2)
        self.knight_b = arcade.Sprite("sprites/knightb.png", center_x= self.grid[0][1].xCoord, center_y= self.grid[0][1].yCoord, scale = 2)
        self.knight_b2 = arcade.Sprite("sprites/knightb.png", center_x= self.grid[0][6].xCoord, center_y= self.grid[0][6].yCoord, scale = 2)
        self.pawn_b1 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][0].xCoord, center_y = self.grid[1][0].yCoord, scale = 2)
        self.pawn_b2 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][1].xCoord, center_y = self.grid[1][1].yCoord, scale = 2)
        self.pawn_b3 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][2].xCoord, center_y = self.grid[1][2].yCoord, scale = 2)
        self.pawn_b4 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][3].xCoord, center_y = self.grid[1][3].yCoord, scale = 2)
        self.pawn_b5 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][4].xCoord, center_y = self.grid[1][4].yCoord, scale = 2)
        self.pawn_b6 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][5].xCoord, center_y = self.grid[1][5].yCoord, scale = 2)
        self.pawn_b7 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][6].xCoord, center_y = self.grid[1][6].yCoord, scale = 2)
        self.pawn_b8 = arcade.Sprite("sprites/pawnb.png", center_x = self.grid[1][7].xCoord, center_y = self.grid[1][7].yCoord, scale = 2)
        #load white piece sprites
        self.king_w = arcade.Sprite("sprites/kingw.png", center_x= self.grid[7][3].xCoord, center_y= self.grid[7][3].yCoord, scale = 2)
        self.queen_w = arcade.Sprite("sprites/queenw.png", center_x= self.grid[7][4].xCoord, center_y= self.grid[7][4].yCoord, scale = 2)
        self.rook_w = arcade.Sprite("sprites/rookw.png", center_x= self.grid[7][0].xCoord, center_y= self.grid[7][0].yCoord, scale = 2)
        self.rook_w2 = arcade.Sprite("sprites/rookw.png", center_x= self.grid[7][7].xCoord, center_y= self.grid[7][7].yCoord, scale = 2)
        self.bishop_w = arcade.Sprite("sprites/bishopw.png", center_x= self.grid[7][2].xCoord, center_y= self.grid[7][2].yCoord, scale = 2)
        self.bishop_w2 = arcade.Sprite("sprites/bishopw.png", center_x= self.grid[7][5].xCoord, center_y= self.grid[7][5].yCoord, scale = 2)
        self.knight_w = arcade.Sprite("sprites/knightw.png", center_x= self.grid[7][1].xCoord, center_y= self.grid[7][1].yCoord, scale = 2)
        self.knight_w2 = arcade.Sprite("sprites/knightw.png", center_x= self.grid[7][6].xCoord, center_y= self.grid[7][6].yCoord, scale = 2)
        self.pawn_w1 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][0].xCoord, center_y = self.grid[6][0].yCoord, scale = 2)
        self.pawn_w2 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][1].xCoord, center_y = self.grid[6][1].yCoord, scale = 2)
        self.pawn_w3 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][2].xCoord, center_y = self.grid[6][2].yCoord, scale = 2)
        self.pawn_w4 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][3].xCoord, center_y = self.grid[6][3].yCoord, scale = 2)
        self.pawn_w5 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][4].xCoord, center_y = self.grid[6][4].yCoord, scale = 2)
        self.pawn_w6 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][5].xCoord, center_y = self.grid[6][5].yCoord, scale = 2)
        self.pawn_w7 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][6].xCoord, center_y = self.grid[6][6].yCoord, scale = 2)
        self.pawn_w8 = arcade.Sprite("sprites/pawnw.png", center_x = self.grid[6][7].xCoord, center_y = self.grid[6][7].yCoord, scale = 2)
        
        #Add pieces to list of pieces
        #black pieces
        self.pieces_dic["king_b"] = Piece(self.king_b, "black", "king", self.grid[0][3])
        self.pieces_dic["queen_b"] = Piece(self.queen_b, "black", "queen", self.grid[0][4])
        self.pieces_dic["rook_b"] = Piece(self.rook_b, "black", "rook", self.grid[0][0])
        self.pieces_dic["rook_b2"] = Piece(self.rook_b2, "black", "rook", self.grid[0][7])
        self.pieces_dic["bishop_b"] = Piece(self.bishop_b, "black", "bishop", self.grid[0][2])
        self.pieces_dic["bishop_b2"] = Piece(self.bishop_b2, "black", "bishop", self.grid[0][5])
        self.pieces_dic["knight_b"] = Piece(self.knight_b, "black", "knight", self.grid[0][1])
        self.pieces_dic["knight_b2"] = Piece(self.knight_b2, "black", "knight", self.grid[0][6])
        self.pieces_dic["pawn_b1"] = Piece(self.pawn_b1, "black", "pawn", self.grid[1][0])
        self.pieces_dic["pawn_b2"] = Piece(self.pawn_b2, "black", "pawn", self.grid[1][1])
        self.pieces_dic["pawn_b3"] = Piece(self.pawn_b3, "black", "pawn", self.grid[1][2])
        self.pieces_dic["pawn_b4"] = Piece(self.pawn_b4, "black", "pawn", self.grid[1][3])
        self.pieces_dic["pawn_b5"] = Piece(self.pawn_b5, "black", "pawn", self.grid[1][4])
        self.pieces_dic["pawn_b6"] = Piece(self.pawn_b6, "black", "pawn", self.grid[1][5])
        self.pieces_dic["pawn_b7"] = Piece(self.pawn_b7, "black", "pawn", self.grid[1][6])
        self.pieces_dic["pawn_b8"] = Piece(self.pawn_b8, "black", "pawn", self.grid[1][7])
        #white pieces
        self.pieces_dic["king_w"] = Piece(self.king_w, "white", "king", self.grid[7][3])
        self.pieces_dic["queen_w"] = Piece(self.queen_w, "white", "queen", self.grid[7][4])
        self.pieces_dic["rook_w"] = Piece(self.rook_w, "white", "rook", self.grid[7][0])
        self.pieces_dic["rook_w2"] = Piece(self.rook_w2, "white", "rook", self.grid[7][7])
        self.pieces_dic["bishop_w"] = Piece(self.bishop_w, "white", "bishop", self.grid[7][2])
        self.pieces_dic["bishop_w2"] = Piece(self.bishop_w2, "white", "bishop", self.grid[7][5])
        self.pieces_dic["knight_w"] = Piece(self.knight_w, "white", "knight", self.grid[7][1])
        self.pieces_dic["knight_w2"] = Piece(self.knight_w2, "white", "knight", self.grid[7][6])
        self.pieces_dic["pawn_w1"] = Piece(self.pawn_w1, "white", "pawn", self.grid[6][0])
        self.pieces_dic["pawn_w2"] = Piece(self.pawn_w2, "white", "pawn", self.grid[6][1])
        self.pieces_dic["pawn_w3"] = Piece(self.pawn_w3, "white", "pawn", self.grid[6][2])
        self.pieces_dic["pawn_w4"] = Piece(self.pawn_w4, "white", "pawn", self.grid[6][3])
        self.pieces_dic["pawn_w5"] = Piece(self.pawn_w5, "white", "pawn", self.grid[6][4])
        self.pieces_dic["pawn_w6"] = Piece(self.pawn_w6, "white", "pawn", self.grid[6][5])
        self.pieces_dic["pawn_w7"] = Piece(self.pawn_w7, "white", "pawn", self.grid[6][6])
        self.pieces_dic["pawn_w8"] = Piece(self.pawn_w8, "white", "pawn", self.grid[6][7])

        #Update piece for each square
        for piece in self.pieces_dic:
            self.pieces_dic[piece].location.pieceOn = self.pieces_dic[piece]

        # #set variables to refer to each king piece later. MOVED TO MAKE_GRID
        self.blackKing = self.grid[0][3].pieceOn
        self.whiteKing = self.grid[7][3].pieceOn

    def on_update(self, delta_time):
        if self.explosions: #update explosion animation frame each update interval
            if self.explode < 18:
                self.explosion.update_animation()
                self.explode += 1

    def on_draw(self):
        """
        Render the board.
        """
        self.clear()

        arcade.start_render()

        # Iterate over each row and column
        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                # Formula to calculate the x, y position of the square
                x = column * SQUARE_SIZE + MARGIN
                y = row * SQUARE_SIZE + MARGIN
                # if square is even, draw a black rectangle
                if (row + column) % 2 == 0:
                    arcade.draw_rectangle_filled(x, y, SQUARE_SIZE, SQUARE_SIZE, arcade.color.ONYX)
                else:
                    arcade.draw_rectangle_filled(x, y, SQUARE_SIZE, SQUARE_SIZE, arcade.color.EGGSHELL)
        
        #draw pieces

        self.drawDone = False

        if self.draw:
            for piece in self.pieces_dic:
                self.pieces_dic[piece].sprite.draw()
        
        self.drawDone = True

        #draw explosion
        if self.explosions:
            if self.explode < 18:
                self.explosion.draw()

        #draw online status dot and turn label
        if self.opConnected == "green":
            self.greenDot.draw()
        elif self.opConnected == "red":
            self.redDot.draw()
        elif self.opConnected == "yellow":
            self.yellowDot.draw()
        
        # Draw cursor
        if not self.dragging:
            # Default cursor when not dragging a piece.
            self.cursor.draw()
        else:
            # Change cursor to grab on drag.
            self.cursor_grab.draw()
        
        if self.turn == self.color:
            self.yourturn.draw()

        if self.winbyres:
            self.winbyresMessage.draw()   
        if self.winbymate:
            self.winmateMessage.draw()
        if self.losebymate:
            self.losemateMessage.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called when the user presses a mouse button. """
        if not self.over:
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.movingPiece = None
                for piece in self.pieces_dic:
                    if self.pieces_dic[piece].sprite.collides_with_point((x, y)):
                        #check that it is your turn, and that piece is your color
                        if checkTurnAndColor(self.pieces_dic[piece], self.turn, self.color): #Only pick up the piece if the piece is that player's color and it is their turn
                            self.dragging = True #set to True when mouse is clicked
                            self.movingPiece = self.pieces_dic[piece]
                            self.offset_x = self.pieces_dic[piece].sprite.center_x - x
                            self.offset_y = self.pieces_dic[piece].sprite.center_y - y
                self.cursor.stop()

    def on_mouse_release(self, x, y, button, modifiers):
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.dragging = False #set to False when mouse is released
                if self.movingPiece:
                    squareToMove = snapPiece(self.movingPiece, x, y, self.grid) #Determine which square is closest to location piece was dropped
                    #check valid move
                    if self.fullCheck(self.movingPiece, squareToMove): #check that move is valid, including verification of king-into or still-in check
                        self.movePiece(self.movingPiece, squareToMove, True, False) #Move piece if move is entirely valid
                    else:
                        # if not valid, snap piece back to previous square
                        self.movingPiece.sprite.center_x = self.movingPiece.location.xCoord
                        self.movingPiece.sprite.center_y = self.movingPiece.location.yCoord
            self.movingPiece = None

    def showResult(self):
        arcade.gui.UIMessageBox(width = 200,
                                height = 100,
                                message_text = f"You {self.result}",
                                buttons = ("Exit"))

    #if move is valid, check that king is not or no longer in check. Return True if so.
    def fullCheck(self, piece, squareToMove):
        if checkValidMove(piece, piece.location, squareToMove, self.grid, self): #check that movement pattern is ok for appropriate piece
            if self.testMove(piece,squareToMove): #evaluates true if king is not in check after move
                return True
            else:
                return False

    #Return True if king is in check-mate
    def checkMate(self, turn):
        piecesOfColor = []
        if turn == "white":
            for p in self.pieces_dic:
                if self.pieces_dic[p].color == "black":
                    piecesOfColor.append(self.pieces_dic[p])
        elif turn == "black":
            for p in self.pieces_dic:
                if self.pieces_dic[p].color == "white":
                    piecesOfColor.append(self.pieces_dic[p])
        for piece in piecesOfColor:
            for row in self.grid:
                for square in row:
                    if self.fullCheck(piece, square):
                        #print(f"safe: {piece} to {square}")
                        return False
        return True

    #MOVE PIECE function: pieceToMove to squareToMove.
    def movePiece(self, pieceToMove, squareToMove, sendBool = True, castle = False):
        # print("TOP OF MOVE PIECE METHOD")
        #check if piece is taking an opponents piece
        if squareToMove.pieceOn: #there is a piece on that square. Must be a piece of opposite color
            # self.pieces_list.remove(squareToMove.pieceOn) #remove piece that is taken from that square
            #Remove piece from dictionary

            for key in self.pieces_dic:
                if squareToMove.pieceOn == self.pieces_dic[key]:
                    keyToDel = key
            print(f"deleting: {self.pieces_dic[keyToDel]}")
            del self.pieces_dic[keyToDel]

            if self.explosions: #show and play explosions if toggled
                self.explode = 0
                self.explosion.center_x = squareToMove.xCoord
                self.explosion.center_y = squareToMove.yCoord
                if window.current_view is self:
                    arcade.play_sound(self.audio_explosion)
        #store previous location for caste-ing
        prevLocation = pieceToMove.location
        #set previous square to empty
        pieceToMove.location.pieceOn = None
        #move piece, snap to new square
        pieceToMove.location = squareToMove
        #update new square.pieceOn
        squareToMove.pieceOn = pieceToMove
        #move sprite
        pieceToMove.sprite.center_x = squareToMove.xCoord
        pieceToMove.sprite.center_y = squareToMove.yCoord
        pieceToMove.hasMoved = True
        #Move rook if castle
        if pieceToMove.color == "black":
            colorY = 0
        elif pieceToMove.color == "white":
            colorY = 7
        if pieceToMove.type == "king" and abs(squareToMove.x - prevLocation.x) == 2:
            if squareToMove.x == 1: #left rook castle
                self.movePiece(self.grid[colorY][0].pieceOn,self.grid[colorY][2], True, True) #MOVE ROOK with castle=True 
            elif squareToMove.x == 5: #right rook castle
                self.movePiece(self.grid[colorY][7].pieceOn,self.grid[colorY][4], True, True) #MOVE ROOK with castle=True
        #If pawn on last row, promote to queen
        if pieceToMove.type == "pawn":
            if pieceToMove.color == "white" and squareToMove.y == 0:
                pieceToMove.type = "queen"
                pieceToMove.sprite = arcade.Sprite("sprites/queenw.png", center_x= squareToMove.xCoord, center_y= squareToMove.yCoord, scale = 2)
                if window.current_view is self:
                    arcade.play_sound(self.audio_promotePawn)
            elif pieceToMove.color == "black" and squareToMove.y == 7:
                pieceToMove.type = "queen"
                pieceToMove.sprite = arcade.Sprite("sprites/queenb.png", center_x= squareToMove.xCoord, center_y= squareToMove.yCoord, scale = 2)
                if window.current_view is self:
                    arcade.play_sound(self.audio_promotePawn)

        #check for king in check
        if pieceToMove.color == "white":
            king = self.blackKing
        elif pieceToMove.color == "black":
            king = self.whiteKing
        if kingInCheck(king, self.grid, self):
            if window.current_view is self:
                arcade.play_sound(self.audio_check) #play check sound
            if pieceToMove.color == "white":
                self.blackInCheck = True
            elif pieceToMove.color == "black":
                self.whiteInCheck = True
        else:
            if window.current_view is self:
                arcade.play_sound(self.audio_move_piece) #play regular move sound
            if pieceToMove.color == "white":
                self.blackInCheck = False
            elif pieceToMove.color == "black":
                self.whiteInCheck = False
        #check if check-mate
        if self.checkMate(self.turn):
            if window.current_view is self:
                time.sleep(.5)
                arcade.play_sound(self.audio_checkmate) #play checkmate sound
            mate = True
        else:
            mate = False
        #update turn if not a castle-rook movement
        if not castle:
            # if self.turn == "white":
            if pieceToMove.color == "white":
                self.turn = "black"
            # elif self.turn == "black":
            if pieceToMove.color == "black":
                self.turn = "white"
        #send move to server
        ID = 0
        if sendBool:
            for game in game_dic:
                if game_dic[game].board is self:
                    ID = game
                    stateStr = game_dic[game].to_json()
            send(f"{clientName},MOVE,{stateStr}",client) #FORMAT: ClientName, MOVE, gameStateDict
            if mate:
                send(f"{clientName},MATE,{ID},{self.turn}", client) #FORMAT: ClientName, MATE, ID, winning color
    
    #Move a pieceToMove to squareToMove, check if own king is in check, move piece back to original square, return whether or not king would be in check if move executed
    def testMove(self, pieceToMove, squareToMove):
        #MOVE PIECE TO SQUARE
        takenPiece = None
        if squareToMove.pieceOn: #there is a piece of opposite color on that square
            takenPiece = squareToMove.pieceOn #store taken piece
            print(f"Taken piece: {takenPiece}")
            # self.pieces_list.remove(squareToMove.pieceOn) #remove piece
            for key in self.pieces_dic:
                if takenPiece == self.pieces_dic[key]:
                    print(f"TRUE: {self.pieces_dic[key]}")
                    keyToDel = key
            del self.pieces_dic[keyToDel]

        #store previous square
        prevSquare = pieceToMove.location
        #set previous square to empty
        pieceToMove.location.pieceOn = None
        #move piece, snap to new square
        pieceToMove.location = squareToMove
        #update new square.pieceOn
        squareToMove.pieceOn = pieceToMove
        #CHECK IF KING IN CHECK
        valid = True
        if pieceToMove.color == "white":
            king = self.whiteKing
        elif pieceToMove.color == "black":
            king = self.blackKing
        if kingInCheck(king, self.grid, self):
            valid = False
        
        #MOVE PIECE BACK TO ORIGINAL SQUARE

        #add taken piece back to list, if needed
        if takenPiece:
            self.pieces_dic[keyToDel] = takenPiece

        #set previous square pieceOn back to pieceToMove
        prevSquare.pieceOn = pieceToMove
        #move piece back to previous Square
        pieceToMove.location = prevSquare
        #set squareToMove to empty
        if takenPiece:
            squareToMove.pieceOn = takenPiece
        else:
            squareToMove.pieceOn = None
        #return
        
        return valid #RETURN RESULT

    def ownKingSafe(self): #NOT CURRENTLY IN USE
        if self.movingPiece.color == "white" and self.whiteInCheck:
            if kingInCheck(self.whiteKing, self.grid, self):
                return False
        elif self.movingPiece.color == "black" and self.blackInCheck:
            if kingInCheck(self.blackKing, self.grid, self):
                return False
        return True
    
    def on_mouse_motion(self, x, y, dx, dy): #Keeps piece and cursor at mouse location
        if self.dragging:
            self.movingPiece.sprite.center_x = x
            self.movingPiece.sprite.center_y = y
        self.cursor.center_x = x + 3
        self.cursor.center_y = y - 14
        self.cursor_grab.center_x = x + 3
        self.cursor_grab.center_y = y - 14

    def on_key_press(self, key, key_modifiers):
        """ Called whenever a key on the keyboard is pressed. """
        if key == arcade.key.BACKSPACE:
            window.show_view(homeView)
            homeView.manager.enable()
            window.set_mouse_visible(True)
            if self.over:
                for game in game_dic:
                    if game_dic[game].board is self:
                        idToDel = game
                del game_dic[idToDel]
            else:
                send(f"{clientName},LEFTGAMEVIEW,{game_dic[self.id].player2},{self.id}",client)

#Buttons
class CurrGamesButton(arcade.gui.UIFlatButton): #takes you to current games screen
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        homeView.manager.disable()
        window.show_view(currentGamesView)
        currentGamesView.manager.enable()
        currentGamesView.update_list()

class InvitesButton(arcade.gui.UIFlatButton): #takes you to invites screen
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        homeView.manager.disable()
        window.show_view(invitesView)
        invitesView.manager.enable()
        invitesView.update_list()
        
class NewGameButton(arcade.gui.UIFlatButton): #takes you to send new game invite screen
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        homeView.manager.disable()
        window.show_view(newGameView)
        newGameView.manager.enable()
        newGameView.inviteSendMsg = "None"


class BackHomeButton(arcade.gui.UIFlatButton): #back to home screen
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        window.show_view(homeView)
        homeView.manager.enable()
        invitesView.manager.disable()
        newGameView.manager.disable()
        currentGamesView.manager.disable()
        window.set_mouse_visible(True)

class ContinueGameButton(arcade.gui.UIFlatButton): #continue game. Should take you to board screen
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        for game in game_dic:
            if game_dic[game].cont is self:
                currentGamesView.manager.disable()
                window.set_mouse_visible(False)
                window.show_view(game_dic[game].board)
                send(f"{clientName},ENTEREDGAMEVIEW,{game_dic[game].player2},{game}",client)

class RemoveGameButton(arcade.gui.UIFlatButton): #remove game from game list
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        for game in game_dic:
            if game_dic[game].abort is self:
                send(f"{clientName},ABORT,{game_dic[game].id},{game_dic[game].player2}", client) #FORMAT: ClientName, ABORT, GameID

class AcceptButton(arcade.gui.UIFlatButton): #accept invite
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        for inv in inv_dic:
            if inv_dic[inv].acc is self:
                invToDel = inv #store invite to delete
                #send accepted message to server
                send(f"{clientName},ACCEPT,{inv_dic[inv].id}", client) #FORMAT: ClientName, ACCEPT, InviteID
        del inv_dic[invToDel] #remove key from dic
        #update invite list
        invitesView.update_list()

class RejectButton(arcade.gui.UIFlatButton): #reject invite
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        for inv in inv_dic:
            if inv_dic[inv].rej is self:
                invToDel = inv #store invite to delete
                #update invite list
        send(f"{clientName},REJECT,{inv_dic[inv].id}", client) #FORMAT: ClientName, ACCEPT, InviteID
        del inv_dic[inv]  #remove invite from invite dic
        invitesView.update_list()

class SubmitButton(arcade.gui.UIFlatButton): #Sends new invite to server
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        newGameView.inviteSendMsg = "None"
        send(f"{clientName},INVITE,{newGameView.inputInviteText.text},{newGameView.colorChoice}", client)
        newGameView.inputInviteText.text = ""

class playAsWhite(arcade.gui.UIFlatButton):
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        newGameView.showColorChoice = True
        newGameView.colorChoice = "white"

class playAsBlack(arcade.gui.UIFlatButton):
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        newGameView.showColorChoice = True
        newGameView.colorChoice = "black"

class playAsRandom(arcade.gui.UIFlatButton):
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        newGameView.showColorChoice = True
        newGameView.colorChoice = "random"

class LoginButton(arcade.gui.UIFlatButton): #Sends username/password to server
    def on_click(self, event: arcade.gui.UIOnClickEvent):
        login(loginView.usernameInput.text, loginView.passwordInput.text)
        

#login screen
class Login(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.csscolor.LEMON_CHIFFON)
        self.background = arcade.load_texture("images/loginbackground.png")
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.usernameInput = arcade.gui.UIInputText(x = 300, y = 600, text = "username", width = 150, height = 30)
        self.manager.add(arcade.gui.UIPadding(child = self.usernameInput, padding = (3,3,3,3), bg_color = (255,255,255)))
        self.passwordInput = arcade.gui.UIInputText(x = 300, y = 530, text = "password", width = 150, height = 30)
        self.manager.add(arcade.gui.UIPadding(child = self.passwordInput, padding = (3,3,3,3), bg_color = (255,255,255)))
        self.manager.add(LoginButton(text="Login", width=155, height = 30, x = 300, y = 450))
        self.showLoginError = False
        self.loginErrorText = arcade.gui.UIPadding(child = arcade.gui.UILabel(text = "Invalid username/password", x = 280, y = 400,text_color = (255,0,0)),padding = (3,3,3,3), bg_color = (255,255,255))
        self.loginErrorManager = arcade.gui.UIManager()
        self.loginErrorManager.add(self.loginErrorText)
        self.notConnectedText = arcade.gui.UIPadding(child = arcade.gui.UILabel(text = "Failed to connect to server. Please restart application.", x = 220, y = 400,text_color = (255,0,0)), padding = (3,3,3,3), bg_color = (255,255,255))
        self.connectedManager = arcade.gui.UIManager()
        self.connectedManager.add(self.notConnectedText)
    
    def on_draw(self):
        arcade.start_render()
        self.clear()
        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background)
        arcade.draw_rectangle_filled(center_x = 378, center_y = 542, width = 180, height = 205, color = (255,158,69))
        self.manager.draw()
        if self.showLoginError:
            self.loginErrorManager.draw()
        if not connectedToServer:
            self.connectedManager.draw()

    
    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and (self.usernameInput.rect.center_x - self.usernameInput.rect.width/2 < x < self.usernameInput.rect.center_x + self.usernameInput.rect.width/2) and (self.usernameInput.rect.center_y - self.usernameInput.rect.height/2 < y < self.usernameInput.rect.center_y + self.usernameInput.rect.height/2):
            self.usernameInput.text = ""
        if button == arcade.MOUSE_BUTTON_LEFT and (self.passwordInput.rect.center_x - self.passwordInput.rect.width/2 < x < self.passwordInput.rect.center_x + self.passwordInput.rect.width/2) and (self.passwordInput.rect.center_y - self.passwordInput.rect.height/2 < y < self.passwordInput.rect.center_y + self.passwordInput.rect.height/2):
            self.passwordInput.text = ""

    def on_key_press(self, key, key_modifiers):
        if key == arcade.key.ENTER:
            login(self.usernameInput.text, self.passwordInput.text)

def login(username, password):
    send(f"LOGIN,{username},{password}",client)
    # print(f"{username}, {password}")

#Home screen class
class Home(arcade.View):
    def __init__(self):
        # init the UI managers
        super().__init__()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        # Set background color
        arcade.set_background_color(arcade.csscolor.POWDER_BLUE)
        # Load and scale image 
        self.background = arcade.load_texture("images/chess_home.png")
        
        # vertical box layout to hold the buttons
        self.v_box = arcade.gui.UIBoxLayout(vertical = True, space_between = 10, align = 'left')
        # Buttons 
        self.curr_games_button = CurrGamesButton(text="View Current Games", width=200)
        self.invites_button = InvitesButton(text="View Game Invites", width=200)
        self.new_game_button = NewGameButton(text="New Game Invite", width=200)
        # self.nameLabel = arcade.gui.UILabel(x = 50, y = 750, text = clientName)
        
        #add each button to vertical stack
        self.v_box.add(self.curr_games_button)
        self.v_box.add(self.invites_button)
        self.v_box.add(self.new_game_button)
        # self.v_box.add(self.nameLabel)
        
        #add vertical stack to manager
        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center_x",
                anchor_y="center_y",
                child=self.v_box)
        )
    
    def on_show(self):
        arcade.set_background_color(arcade.csscolor.LIGHT_GRAY)
        loginView.manager.disable()

    def on_draw(self):
        arcade.start_render()
        self.clear()
        # Draw the background image
        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background)
        self.manager.draw()

#current games screen class
class CurrentGames(arcade.View):
    def __init__(self):
        super().__init__()
        #Set up manager and add back button
        self.manager = arcade.gui.UIManager()
        self.backButton = BackHomeButton(text="Home", width=100, height = 50, x = 50, y = 700)
        self.background = arcade.load_texture("images/backdrop.png")
        self.manager.add(self.backButton)
        #vertical stack to hold each game
        self.vertStack= arcade.gui.UIBoxLayout(vertical = True, space_between = 10, align = 'left')
        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center_x",
                anchor_y="center_y",
                child=self.vertStack)
        )

    #update the list of current games
    def update_list(self):
        self.vertStack.clear() #clear vertical stack
        for game in game_dic:
            gameInfo = arcade.gui.UIBoxLayout(vertical = False, space_between = 10, align = 'right')
            gameInfo.add(arcade.gui.UILabel(text = str(game_dic[game]), font_name = ('Times'), font_size = 20, text_color = (0, 0, 255, 255), bold = True))
            gameInfo.add(game_dic[game].cont)
            gameInfo.add(game_dic[game].abort)
            self.vertStack.add(gameInfo)

    def on_draw(self):
        arcade.start_render()
        self.clear()
        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background)
        self.manager.draw()

#invitations screen class
class Invites(arcade.View):
    def __init__(self):
        super().__init__()
        #Set up manager and add back button
        self.manager = arcade.gui.UIManager()
        self.background = arcade.load_texture("images/backdrop.png")

        # self.manager.enable()
        self.backButton = BackHomeButton(text="Home", width=100, height = 50, x = 50, y = 700)
        self.manager.add(self.backButton)
        #vertival stack to hold each invite
        self.vertStack = arcade.gui.UIBoxLayout(vertical = True, space_between = 10, align = 'left')
        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center_x",
                anchor_y="center_y",
                child=self.vertStack)
        )
    
    #update list of invitations
    def update_list(self):
        self.vertStack.clear() #clear vertical stack
        for inv in inv_dic:
            invInfo = arcade.gui.UIBoxLayout(vertical = False, space_between = 10, align = 'right') #create horizontal stack to hold each part of the invite (label, buttons)
            invInfo.add(arcade.gui.UILabel(text = f"Invite from {inv_dic[inv].fromPlayer}", font_name = ('Times'), font_size = 20, text_color = (0, 0, 255, 255), bold = True)) #add invite label
            invInfo.add(inv_dic[inv].acc)
            invInfo.add(inv_dic[inv].rej)
            self.vertStack.add(invInfo) #add invite to vertical stack of all invites

    def on_draw(self):
        arcade.start_render()
        self.clear()
        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background)
        self.manager.draw()

def inviteConfirmation(val):
    # global newGameView
    newGameView.inviteSendMsg = val

#send new game invite screen class
class NewGame(arcade.View):
    def __init__(self):
        #Set up manager and add back button
        super().__init__()
        self.background = arcade.load_texture("images/backdrop.png")
        self.manager = arcade.gui.UIManager()
        # self.manager.enable()
        self.backButton = BackHomeButton(text="Home", width=100, height = 50, x = 50, y = 700)
        self.manager.add(self.backButton)        
        #variables for text input location. Referenced in on_mouse_press. UPDATE: Widgets have a .rect object, which has .x, .y, .height, and .width. This format
        self.inputX = 200
        self.inputY = 500
        self.inputWidth = 250
        self.inputHeight = 20
        #create text input
        self.inputInviteText = arcade.gui.UIInputText(x = self.inputX, y = self.inputY, text = "Input player name here", width = self.inputWidth, height = self.inputHeight)
        #add widgets to manager
        self.manager.add(arcade.gui.UIPadding(child = self.inputInviteText, padding = (3,3,3,3), bg_color = (255,255,255)))
        self.manager.add(SubmitButton(text = "Send Invite", x = 196, y = 390, width = 200, height = 30))
        
        self.showColorChoice = False
        self.colorChoice = "random"
        #make horizontal stack
        self.colorPickStack = arcade.gui.UIBoxLayout(vertical = False, space_between = 10, align = 'left', x = 92, y = 470)
        self.colorPickStack.add(arcade.gui.UILabel(text = "Play as:", font_size = 20, text_color = (255,255,255)))
        self.pw = playAsWhite(text = "White", height = 25)
        self.pb = playAsBlack(text = "Black", height = 25)
        self.pr = playAsRandom(text = "Random", height = 25)
        self.colorPickStack.add(self.pw)
        self.colorPickStack.add(self.pb)
        self.colorPickStack.add(self.pr)
        #add to manager
        self.manager.add(self.colorPickStack)
        
        #valid/invalid invite messages
        self.inviteSendMsg = "None"
        self.validInviteManager = arcade.gui.UIManager()
        self.validInviteManager.add(arcade.gui.UIPadding(child = arcade.gui.UILabel(text = "Invite sent!", font_size = 15, text_color = (50,255,100), x = 250, y = 300),bg_color = (255,255,255),padding = (2,2,2,2)))
        self.invalidInviteManager = arcade.gui.UIManager()
        self.invalidInviteManager.add(arcade.gui.UIPadding(arcade.gui.UILabel(text = "Invalid invite - player not found :(", font_size = 15, text_color = (255,0,0), x = 250, y = 300),bg_color = (255,255,255),padding = (2,2,2,2)))
        self.invalidSelfInviteManager = arcade.gui.UIManager()
        self.invalidSelfInviteManager.add(arcade.gui.UIPadding(arcade.gui.UILabel(text = "Invalid invite - cannot invite yourself", font_size = 15, text_color = (255,0,0), x = 250, y = 300),bg_color = (255,255,255),padding = (2,2,2,2)))

    def on_draw(self):
        arcade.start_render()
        self.clear()
        arcade.draw_lrwh_rectangle_textured(0, 0,
                                            SCREEN_WIDTH, SCREEN_HEIGHT,
                                            self.background)
        if self.showColorChoice:
            if self.colorChoice == "white":
                cx = self.pw.rect.center_x
                cy = self.pw.rect.center_y
            elif self.colorChoice == "black":
                cx = self.pb.rect.center_x
                cy = self.pb.rect.center_y
            elif self.colorChoice == "random":
                cx = self.pr.rect.center_x
                cy = self.pr.rect.center_y
            arcade.draw_rectangle_filled(center_x = cx, center_y = cy, width = 95, height = 24, color = (255,0,0))
        self.manager.draw()

        if self.inviteSendMsg == "valid":
            self.validInviteManager.draw()
        if self.inviteSendMsg == "invalid":
            self.invalidInviteManager.draw()
        if self.inviteSendMsg == "invalidself":
            self.invalidSelfInviteManager.draw()
        

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and (self.inputX < x < self.inputX + self.inputWidth) and (self.inputY < y < self.inputY + self.inputHeight):
            self.inputInviteText.text = ""
            
    def on_key_press(self, key, key_modifiers):
        if key == arcade.key.ENTER:
            self.inviteSendMsg = "None"
            send(f"{clientName},INVITE,{self.inputInviteText.text.rstrip()},{self.colorChoice}", client)
            self.inputInviteText.text = ""

class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__()
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT
        self.screen_title = SCREEN_TITLE

    def on_key_press(self, key, key_modifiers):
        if key == arcade.key.ESCAPE:
            print("ESC")
            event.set()  #stop thread
            print(f"CLIENTNAME = {clientName}")
            send(f"{DISCONNECT_MESSAGE},{clientName}", client) #send disconnect message to server
            arcade.close_window()

#GLOBAL DEFINITIONS
window = GameWindow()
homeView = Home()
currentGamesView = CurrentGames()
invitesView = Invites()
newGameView = NewGame()
loginView = Login()

def main():
    global connectedToServer
    # socket functionality
    try:
        client.connect(ADDR) #connect to server
        # send(clientName, client) #send client name to server
        thread = threading.Thread(target = wait_for_server_input, args = [client, window])
        thread.start()
        connectedToServer = True
    except:
        print("COULDN'T CONNECT TO SERVER")
        connectedToServer = False

    #Arcade functionality
    # if showLogin:
    #     window.show_view(loginView)
    # else:
    #     window.show_view(homeView)
    window.show_view(loginView)
    arcade.run()

main()
