# Tic-Tac-Toe Game

This is a simple Tic-Tac-Toe game implemented using Python and sockets.

**How to play:**
1. **Start the server:** Run the `server.py` script.
2. **Connect clients:** Run the `client.py` script on two different machines or terminals.
3. **Play the game:** Players take turns entering their moves. The first player to get three in a row wins!

**Technologies used:**
* Python
* Sockets

**Additional resources:**
* Temporarily  Empty, more will be added as additional resources are used.

**using the server:**
* How to start the server --> python3 server.py <listening clients (for now, set either as '' or quad 0's for all incoming clients)> <port numbers>
  * This will set the server to listen for certian clients on a specified ip range and port numbers
* Now we can set the client to send specific requests to the server matching the specified actions that our game will accept. For now
  * The only working request is test. Example call from a client:
    * python3 app-client.py 'localhost' 65432 test <null value for now (tester)>
    
