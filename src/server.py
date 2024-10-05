import sys
import socket
import traceback
import libserver
import selectors
import serverlogic

# used to register the server socket and each client socket, monitoring them for events
sel = selectors.DefaultSelector()


'''
This function is called whenever the listening socket finds a new connection. It will accept that
connection, create a new client socket, and register that new socket with the selector for monitoring
'''
def accept_connection(sock):
    conn, addr = sock.accept()
    print("The server has accepeted a connection from", addr)
    
    # set our new client connection to non-blcoking mode
    conn.setblocking(False)
    
    # create a message object (in serverlogic.py) to handle communication with this specific client
    message = serverlogic.Message(sel, conn, addr) 
    
    # register new client socket with the selector for monitoring read events
    sel.register(conn, selectors.EVENT_READ, data=message)

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
    listenSocket.setblocking(false)     
    
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
                    # if data is None, we known that this is a new connection, so accept and register
                    accept_connection(key.fileobj)
                else:
                    # else its a message object with an already associated socket, so we process it
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        print(
                            "Error: exception for connection", f"{message.addr}\n {traceback.format_exc()}"
                        )
                        message.close() # close the specific connection if there is an error in processing
    except KeyboardInterrupt:
        print("Keyboard interrupt, killing server")
    finally:
        sel.close()
        
        
if __name__ == "__main__":
    main()