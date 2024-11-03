# Tic-Tac-Toe Game

This is a simple Tic-Tac-Toe game implemented using Python and sockets.

**How to play:**
1. **Start the server:** Run the `server.py` script. An example call is as follows: `python3 server.py '' 65432`
2. **Connect clients:** Run the `client.py` script on two different machines or terminals. To connect to the server, run `python3 client.py '' 65432 connect null`
3. **Play the game:** Players take turns entering their moves. The first player to get three in a row wins!

**Technologies used:**
* Python
* Sockets
* Selectors
* Loggers
* json
* Event masks
* structs
* 

**Additional resources:**
* Temporarily  Empty, more will be added as additional resources are used.

**using the server:**
* How to start the server --> python3 server.py <listening clients (for now, set either as '' or quad 0's for all incoming clients)> <port numbers>
  * This will set the server to listen for certian clients on a specified ip range and port numbers
* Now we can set the client to send specific requests to the server matching the specified actions that our game will accept. For now
  * One working request test. Example call from a client:
    * `python3 app-client.py 'localhost' 65432 test <null value for now (tester)>`
    * This simply pings the server and you should get a response back stating the server got your message
  * The next working request is connect. An example call from the client would be:
    * `python3 client.py '' 65432 connect null`
    * This call will register a player with the server. If you are the first player, then you will be placed in a queue waiting for another player. If you are the second player, once you connect, the game will begin!
    * Since this is a connect request with no action value, pass null in as the second option.
    
**Message Protocol:**
* All messages are formed using JSON format, messages to the server are formatted as
* ACTIONTYPE : ACTION_VALUE, where ACTIONTYPE is defined in a list of acceptable values, checked both at the client and server side.
* and messages from the server to the client are currently regulated to response : response value, where the response value is a message to the client
