# Tic-Tac-Toe Game

This is a simple Tic-Tac-Toe game implemented using Python and sockets. This is our final project for CS457 at Colorado State University
Teammates: Ethan Fantl, Nathan Bennick
Team Name: Cubeland

**How to play:**
1. **Start the server:** Run the `server.py` script. An example call is as follows: `python3 server.py -p 65432`
2. **Connect clients:** Run the `client.py` script on two different machines or terminals. To connect to the server, run `python3 client.py -i 0.0.0.0 -p 65432`
3. **Play the game:** Players take turns entering their moves. The first player to get three in a row wins!

**Technologies used:**
* Python
* Sockets
* Selectors
* Loggers
* json
* Event masks
* structs
* threads
* tkinter

**using the server and client:**
* As specified earlier, to start the server, you must run the server.py script and specify the port number where the server should listen for incoming client connections.
  * python3 server.py -p <port numbers>
  * Once started, the server will bind to the IP address 0.0.0.0, which means it will listen for incoming connections on all network interfaces available on the host machine. This makes it accessible from other devices on the same network using the host's IP address.
  * The port number is used to establish connections. **ENSURE that the port is not blocked by a firewall or used by another application.** 
* Now we can set the client to send specific requests to the server matching the specified actions that our game will accept. Below are working requests that clients can make to the server. *Please note that most of these requests are made automatically by our UI, clientController, and clientLogic scripts, so the end user doesn't have to worry about these. We included this for your information, not for you to worry about manually using.*
  * One working request test:
    * `python3 app-client.py 'localhost' 65432 test <null>`
    * This simply pings the server and you should get a response back stating the server got your message
  * The next working request is connect. An example call from the client would be:
    * `python3 client.py '' 65432 connect null`
    * This call will register a player with the server. If you are the first player, then you will be placed in a queue waiting for another player. If you are the second player, once you connect, the game will begin!
    * Since this is a connect request with no action value, pass null in as the second option.
  * Our next working request is disconnection. When a client wants to disconnect from the server, they send:
    * `python3 client.py '' 65432 disconnect null`
    * This will gracefully remove the player from the game state recorder's list of players and kill any active game session
    * The server will remain active to accept more incoming requests (our max right now is 2, honeslty I have no idea what will happen if more than 2 join the server)
  * Move
    * The value sent here will indicate where you are going to place a piece on the board. It only accepts values 0-8, each one of those values representing an index on the board to place your value.
    * Our clientUI will handle this for the user, they simply have to click on the board indicating where they would like to place their next move.
    * If a user tries to play out of turn, a message will appear in the chat logs telling them that it is not their turn.
  * Chat
    * The value sent along side this request will be sent to the other play that is currently in the active game.
    * The UI will again handle this request for the user. All you need to do is type in the chat box and click send.
  * Rename
    * We wanted users to have their own style and freedom when playing the game, so they are allowed to rename themselves to any name they see fit.
    * When a player connects, they are stored into the game state recorder with their IP and port numbers as thier offical player index.
      * *We included the port number so players playing locally on the same machine can play together without conflicting IPs*
    * A player must simply enter their new name into the rename box, and they will now be able to chat and play with their new name. 
    
**Message Protocol:**
* All messages are formed using JSON format, messages to the server are formatted as JSON as well.
* ACTIONTYPE : ACTION_VALUE, where ACTIONTYPE is defined in a list of acceptable values, checked both at the client and server side.
* and messages from the server to the client are currently regulated to response : response value, where the response value is a message to the client
  
**Currently available actions:**
* Connect: Any value sent using this will be ignored, only the fact that connect is sent matters
* Disconnect: Same with connect
* Chat: The value sent with this will be what is sent to all other players
* Rename: The value sent with this will be what your player is renamed as for chat purposes
* Move: The value sent here will indicate where you are going to place a piece on the board, it accepts any value 0-8
