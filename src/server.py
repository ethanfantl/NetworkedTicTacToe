import sys
import socket
import traceback
import selectors
import serverlogic

# used to register the server socket and each client socket, monitoring them for events
sel = selectors.DefaultSelector()
game_state_recorder = serverlogic.GameStateRecorder()


'''
This function is called whenever the listening socket finds a new connection. It will accept that
connection, create a new server socket, and register that new socket with the selector for monitoring
'''
def accept_connection(sock):
    conn, addr = sock.accept()
    print("The server has accepeted a connection from", addr)
    
    # set our new client connection to non-blcoking mode
    conn.setblocking(False)
    
    # create a message object (in serverlogic.py) to handle communication with this specific client
    message = serverlogic.Message(sel, conn, addr, game_state_recorder) 
    
    # register new client socket with the selector for monitoring read events
    sel.register(conn, selectors.EVENT_READ, data=message)
    
    # register the client with the game state recorder, pass the message instance so we can keep an open communication over the socket
    game_state_recorder.add_player(addr, conn, message)

def main():
    if len(sys.argv) != 3:
        print("usage:", sys.argv[0], "<host> <port>")
        sys.exit(1)
        
    host, port = sys.argv[1], int(sys.argv[2])
    
    # create and bind the listen socket
    listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listenSocket.bind((host, port))
    listenSocket.listen()
    print("Server is now listening on", (host, port))
    
    # set blocking to false which is necessary for handeling multiple connections
    listenSocket.setblocking(False)     
    
    # register live socket with sel and wait for incoming connections
    sel.register(listenSocket, selectors.EVENT_READ, data=None)
    
    '''
    Server waits for new events on the registered sockets. If there are events, the selector will 
    return the sockets that are ready to be processed.  
    '''
    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_connection(key.fileobj)
                else:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        print(
                            "Error: exception for connection", f"{message.client_address}\n {traceback.format_exc()}"
                            f"Because of player disconnect, {message.client_address} will now be removed from game state table"
                        )
                        game_state_recorder.remove_player(message.client_address)
                        message.close() # close the specific connection if there is an error in processing
    except KeyboardInterrupt:
        print("Keyboard interrupt, killing server")
    finally:
        sel.close()
        
        
if __name__ == "__main__":
    main()