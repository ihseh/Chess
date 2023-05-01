from passlib.hash import bcrypt
from datetime import datetime

def alter(cursor, connection):
    # query = "DELETE FROM tblGameInvites WHERE pmkGameInviteId > 0"
    # query = "DELETE FROM tblGames WHERE pmkGameId > 0"
    # query = "SELECT * FROM tblGames"
    query = "SELECT * FROM tblUsers"

    cursor.execute(query)
    connection.commit()
    return cursor.fetchall()

def verifyPassword(username, inputPassword, cursor):
    """
    Checks if an input password/string hash matches hash stored in database.
    """

    # Get password hash from database.
    userData = selectUser(username, cursor)
    # Return False is no user exists.
    if len(userData) == 0:
        return False

    # Verify input password.
    encrypted = userData[0][1]
    if not bcrypt.verify(inputPassword, encrypted):
        return False
    
    return True

def selectTableFields(table, cursor):
    query = f"DESCRIBE {table}"

    cursor.execute(query)

    return cursor.fetchall()

def verifyUser(username, cursor):
    query = "SELECT * FROM tblUsers "
    query += f"WHERE pmkUsername = \"{username}\""

    cursor.execute(query)
    result = list(cursor.fetchall())

    if len(result) == 0:
        return False
    return True

##### Functions to SELECT/FETCH Data #####
def selectUser(username, cursor):
    query = "SELECT * FROM tblUsers "
    query += f"WHERE pmkUsername = \"{username}\""
    
    cursor.execute(query)
    result = cursor.fetchall()
    
    return list(result)

def selectSearchUsers(searchString, queryLimit, cursor):
    """
    Returns users from the database starting with the input string.
    """
    # Do not apply a query limit if supplied limit < 0.
    if queryLimit < 0:
        query = "SELECT * FROM tblUsers "
        query += f"WHERE pmkUsername LIKE \"{searchString}%\""
    else:
        query = "SELECT * FROM tblUsers "
        query += f"WHERE pmkUsername LIKE \"{searchString}%\" LIMIT {queryLimit}"

    cursor.execute(query)
    result = cursor.fetchall()

    return list(result)

# Invite Select Functions
def selectAllIncomingGameInvites(toPlayer, cursor):
    """
    Returns all game invites going to a specific player, regardless if already accepted or rejected.
    """
        
    query = "SELECT * FROM tblGameInvites "
    query += f"WHERE pfkAddressee = \"{toPlayer}\""
    
    cursor.execute(query)
    results = cursor.fetchall()

    return list(results)
    
    
def selectIncomingGameInvites(toPlayer, cursor):
    """
    Returns game invites going to a specific player, NOT including ones already accepted or rejected.
    """
    query = "SELECT * FROM tblGameInvites "
    query += f"WHERE pfkAddressee = \"{toPlayer}\" AND fldIsAccepted = 0 AND fldIsRejected = 0"
    
    cursor.execute(query)
    results = cursor.fetchall()

    return list(results)

def selectAllOutgoingGameInvites(fromPlayer, cursor):
    query = "SELECT * FROM tblGameInvites "
    query += f"WHERE pfkRequester = \"{fromPlayer}\""
    
    cursor.execute(query)
    results = cursor.fetchall()

    return list(results)

def selectOutgoingGameInvites(fromPlayer, cursor):
    query = "SELECT * FROM tblGameInvites "
    query += f"WHERE pfkRequester = \"{fromPlayer}\" AND fldIsAccepted = 0 AND fldIsRejected = 0"
    
    cursor.execute(query)
    results = cursor.fetchall()

    return list(results)

def selectAllGameInvites(fromPlayer, toPlayer, cursor):
    query = "SELECT * FROM tblGameInvites "
    query += f"WHERE pfkRequester = \"{fromPlayer}\" AND pfkAddressee = \"{toPlayer}\""
    
    cursor.execute(query)
    results = cursor.fetchall()

    return list(results)

def selectGameInviteByID(gameID, cursor):
    query = "SELECT * FROM tblGameInvites "
    query += f"WHERE viteIdpmkGameIn = {int(gameID)}"

    cursor.execute(query)
    result = cursor.fetchone()

    return result

def selectGameByID(gameID, cursor):
    query = "SELECT * FROM tblGames "
    query += f"WHERE pmkGameId = {int(gameID)}"

    cursor.execute(query)
    result = cursor.fetchone()
    print(result)
    return result

def selectCurrentGames(player, cursor):
    query = "SELECT * FROM tblGames "
    query += f"WHERE (pfkPlayer1 = \"{player}\" OR pfkPlayer2 = \"{player}\") AND fldIsComplete = 0"
    
    cursor.execute(query)
    results = cursor.fetchall()

    return list(results) 

##### Functions to UPDATE/MODIFY Existing Data #####
def updateAcceptInvite(gameInviteID, cursor, connection):
    time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    query = "UPDATE tblGameInvites "
    query += f"SET fldIsAccepted = 1 "
    query += f"WHERE pmkGameInviteId = {str(gameInviteID)}"
    
    cursor.execute(query)    
    connection.commit()

def updateRejectInvite(gameInviteID, cursor, connection):
    time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    query = "UPDATE tblGameInvites "
    query += f"SET fldIsRejected = 1 "
    query += f"WHERE pmkGameInviteId = {str(gameInviteID)}"
    
    cursor.execute(query)    
    connection.commit()

# Update User Statistics
def updateUserWins(username, delta, cursor, connection):
    query = "UPDATE tblUsers "
    query += f"SET fldWins = fldWins + {str(delta)} "
    query += f"WHERE pmkUsername = \"{username}\""

    cursor.execute(query)
    connection.commit()

def updateUserLosses(username, delta, cursor, connection):
    query = "UPDATE tblUsers "
    query += f"SET fldLosses = fldLosses + {str(delta)} "
    query += f"WHERE pmkUsername = \"{username}\""

    cursor.execute(query)
    connection.commit()

def updateUserStalemates(username, delta, cursor, connection):
    query = "UPDATE tblUsers "
    query += f"SET fldStalemates = fldStalemates + {str(delta)} "
    query += f"WHERE pmkUsername = \"{username}\""

    cursor.execute(query)
    connection.commit()

def updateGameState(gameID, jsonStr, cursor, connection):
    query = "UPDATE tblGames "
    query += f"SET fldGameState = '{jsonStr}' "
    query += f"WHERE pmkGameId = {int(gameID)}"

    cursor.execute(query)
    connection.commit()

def updateGameWinner(gameID, winnerUsername, cursor, connection):
    query = "UPDATE tblGames "
    query += f"SET fnkWinner = \"{winnerUsername}\" "
    query += f"WHERE pmkGameId = {int(gameID)}"

    cursor.execute(query)
    connection.commit()

def updateGameLoser(gameID, loserUsername, cursor, connection):
    query = "UPDATE tblGames "
    query += f"SET fnkLoser = \"{loserUsername}\" "
    query += f"WHERE pmkGameId = {int(gameID)}"

    cursor.execute(query)
    connection.commit()

def updateGameCompletionStatus(gameID, status, cursor, connection):
    query = "UPDATE tblGames "
    query += f"SET fldIsComplete = {status} "
    query += f"WHERE pmkGameId = {int(gameID)}"

    cursor.execute(query)
    connection.commit()

##### Functions to INSERT/CREATE New Data #####
def insertNewGameInvite(fromPlayer, toPlayer, color, cursor, connection):

    time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    query = "INSERT INTO tblGameInvites (pfkRequester, pfkAddressee, fldRequesterColor) "
    query += f"VALUES (\"{fromPlayer}\", \"{toPlayer}\", \"{color}\")"

    cursor.execute(query)
    connection.commit() 

    query = "SELECT pmkGameInviteId FROM tblGameInvites "
    query += f"WHERE pfkRequester = \"{fromPlayer}\" AND pfkAddressee = \"{toPlayer}\" AND fldRequesterColor = \"{color}\" ORDER BY pmkGameInviteId DESC"

    cursor.execute(query)
    newID = cursor.fetchone()[0]

    return newID


def insertNewGame(player1, player2, cursor, connection):
    print("STARTINGGG!!!!!")
    time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    query = "INSERT INTO tblGames (pfkPlayer1, pfkPlayer2, fldGameState) "
    query += f"VALUES (\"{player1}\", \"{player2}\", \"\")"

    cursor.execute(query)
    connection.commit() 

    query = "SELECT pmkGameId FROM tblGames "
    query += f"WHERE pfkPlayer1 = \"{player1}\" AND pfkPlayer2 = \"{player2}\" ORDER BY pmkGameId DESC"

    cursor.execute(query)
    newID = cursor.fetchone()[0]

    return newID

