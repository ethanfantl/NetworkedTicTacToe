import sys
import selectors
import json
import io
import struct
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


'''
This object manages communication between the server and client. 
'''
class Message:
    def __init__(self, selector, client_sock, client_address, game_state_recorder):
        self.selector = selector
        self.client_sock = client_sock 
        self.client_address = client_address 
        self._recieved_buffer = b""
        self._send_buffer = b""
        self._json_header_length = None
        self.json_header = None
        self.request = None
        self.response_created = False 
        self.game_state_recorder = game_state_recorder
        
    '''
    This method is intended to update the selector that is monitoring the client socket to the appropriate event 
    '''    
    def _select_selector_events_mask(self, event):
        if event == "r":
            new_event = selectors.EVENT_READ
        elif event == "w":
            new_event = selectors.EVENT_WRITE
        elif event == "rw":
            new_event = selectors.EVENT_READ | selectors.EVENT_WRITE 
        else:
            raise ValueError(f"Invalid event mask mode recieved. Options are r, w, and rw. Received f{repr(event)}")
        self.selector.modify(self.client_sock, new_event, data=self)
       
    '''
    Read all incoming data from the client socket and store it in the receievd buffer
    '''  
    def _read(self):
        try:
            data = self.client_sock.recv(4096) # right now read up to 4096 bytes (may need to change later)
        except BlockingIOError:
            pass # since we have a non blocking socket, hitting this means no data is available so pass
        else:
            if data:
                self._recieved_buffer += data
            else:
                raise RuntimeError("No data indicating the client has closed connection. Peer closed :(")
    
    '''
    Send data from our send buffer (staged in later methods) to the client socket
    ''' 
    def _write(self):
        if self._send_buffer:
            logging.info(f"Sending {repr(self._send_buffer)} to, {self.client_address}")
            try:
                sent = self.client_sock.send(self._send_buffer) # sending as much data as the socket can handle at once
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:] # remove all data that was sent through socket
                if not self._send_buffer:
                    self._select_selector_events_mask("rw")
                # if sent and not self._send_buffer:
                    # self.close()
    
    '''
    This method encodes a python object to a JSON readable format. Return the bytes for the specific encoding
    '''                
    def _json_encode(self, obj, encoding):
       return json.dumps(obj, ensure_ascii=False).encode(encoding)
   
   
    '''
    Decode the recieved json bytes into an object using whatever encoding is set
    '''
    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
        obj = json.load(tiow)
        tiow.close()
        return obj
   
    '''
    create a message to send back to the client. Includes header and payload
    ''' 
    def _create_message(self, *, content_bytes, content_type, content_encoding):
        """
        Create a message to send to the client. The message consists of:
        1. A header (with the content's metadata).
        2. The actual content.
        """
        new_json_header = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        json_header_bytes = self._json_encode(new_json_header, "utf-8")
        message_hdr = struct.pack(">H", len(json_header_bytes))  # 2-byte header length
        message = message_hdr + json_header_bytes + content_bytes  # Full message
        return message

    def process_ready_request(self, value):
        return self.game_state_recorder.update_ready_status(self.client_address, value)
    
    def broadcast_message(self, content):
        content_bytes = self._json_encode(content, "utf-8")
        message = self._create_message(
            content_bytes=content_bytes, content_type="text/json", content_encoding="utf-8"
        )

        for addr, details in self.game_state_recorder.players.items():
            try:
                details["connection"].send(message)
                logging.info(f"Broadcasted message to {addr}: {content}")
            except Exception as e:
                   logging.error(f"Failed to send broadcast to {addr}: {e}")
    '''
    Create a response for a json request 
    '''
    def _create_response_json_content(self):
        action = self.request.get("action")
        value = self.request.get("value")
        
        if action == "test":
            answer = f"Hello client, you have successfully pinged the server and got a response back"
            content = {"result": answer}

        elif (action == "ready"):
            answer = f"{self.client_address} has updated their ready status"
            if(self.process_ready_request(value)):
                dictionary_status = "Request has been recorded in game state recorder"
                content = {"result": answer + ". " + dictionary_status}
            else:
                dictionary_status = "Request FAILED to process in server game state recorder"
                content = {"result": answer + ". " + dictionary_status}

        elif (action == "chat"):
            answer = f"{self.client_address} says: {value}"
            content = {"result": f"Message broadcasted: {value}"}
            self.broadcast_message({"result": answer})

        else:
            content = {"result": f'Error: invalid action "{action}".'}
        content_encoding = "utf-8"
        
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response
    
    '''
    Called by read method. This method processes the fixed header definined in our protocol and sets the appropriate values
    '''
    def process_fixed_protocol_header(self):
        header_length = 2
        if len(self._recieved_buffer) >= header_length:
            self._json_header_length = struct.unpack(">H", self._recieved_buffer[:header_length])[0]
            self._recieved_buffer = self._recieved_buffer[header_length:]
    
    '''
    This is called by our read method. We process the json header after we have processed the protocol
    '''
    def process_json_header(self):
        header_length = self._json_header_length
        if len(self._recieved_buffer) >= header_length:
            self.json_header = self._json_decode(self._recieved_buffer[:header_length], 'utf-8')
            self._recieved_buffer = self._recieved_buffer[header_length:]
            for reqhdr in ("byteorder", "content-length", "content-type", "content-encoding"):
                if reqhdr not in self.json_header:
                    raise ValueError(f'Missing required header '"{reqhdr}")
                
    '''
    Called by Read. Process whatever request has been sent to server
    '''
    def process_request(self):
        content_length = self.json_header["content-length"]
        # wait until all data has come through
        if not len(self._recieved_buffer) >= content_length:
            return
        data = self._recieved_buffer[:content_length]
        self._recieved_buffer = self._recieved_buffer[content_length:]
        
        if self.json_header["content-type"] == "text/json":
            encoding = self.json_header["content-encoding"]
            self.request = self._json_decode(data, encoding)
            print("Server has received request", repr(self.request), self.client_address)
        else:
            raise ValueError(f"server recieved a request from {self.client_address} that was not of type text/json. Please check packet types :(")
        self._select_selector_events_mask("w") # set to write now that we have read
    
    def create_response(self):
        if self.json_header["content-type"] == "text/json":
            response = self._create_response_json_content()
        else:
            raise ValueError("uh oh") 
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message
    
    '''
    This is called by process events. This method reads data from our client, processes the header and request data when all data is received
    '''
    def read(self):
        self._read() # internal read
        logging.info("The server has interally read a new message")
        
        if self._json_header_length is None:
            self.process_fixed_protocol_header()
        
        if self._json_header_length is not None:
            if self.json_header is None:
                self.process_json_header()
        
        if self.json_header:
            if self.request is None:
                self.process_request()
                
    '''
    This method is called by process events. This will write data to the client if a response has been created
    ''' 
    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()
        self._write()
        
        if not self._send_buffer and self.response_created:
            self.response_created = False
            self.request = None
            self._json_header_length = None
            self.json_header = None
            self._recieved_buffer = b""
            self._select_selector_events_mask("r")
    
    '''
    Close the connection with the client and unregister the socket from our selector
    '''    
    def close(self):
        print("closing connection to", self.client_address)
        try:
            self.selector.unregister(self.client_sock)
        except Exception as e:
            print(
                f"error: selector.unregister() failed and threw an exception for",
                f"{self.client_address}:{repr(e)}"
            )
            
        try:
            self.client_sock.close()
        except OSError as e:
            print(
                f"error: socket.close() exception for",
                f"{self.client_sock}:{repr(e)}"
            )
        finally:
            self.client_sock = None
    
    '''
    THIS METHOD IS CALLED by our server, this being the main driver method for processing all events
    that are detected on our socket
    '''
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
            
'''
We need to define game logic on the server side to handle updates to the game state recorder
'''

class GameSession:
    def __init(self, player1, player2):
        self.board = [['' for _ in range(3)] for _ in range(3)] # establish blank board on server side
        self.players = [player1, player2]
        self.current_turn = player1
        self.winner = None
        
    def make_move(self, player, row, col):
        if(self.current_turn != player):
            return{'status':'error', 'message':'not your turn buko'}
        if(self.board[row][col] != ''):
            return{'status':'error', 'message':'spot is already occupited'}
        self.board[row][col] = 'X' if player == self.players[0] else "O"
        self.check_winner()
        self.current_turn = self.players[0] if self.current_turn == self.players[1] else self.players[1]
        return{'status':'succuss', 'board':self.baord, 'winner':self.winner}
    
    def check_winner(self):
        # Check rows for a winner
        for row in self.board:
            if row[0] == row[1] == row[2] and row[0] != '':
                self.winner = row[0]
                return

        # Check columns for a winner
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] and self.board[0][col] != '':
                self.winner = self.board[0][col]
                return

        # Check diagonals for a winner
        if self.board[0][0] == self.board[1][1] == self.board[2][2] and self.board[0][0] != '':
            self.winner = self.board[0][0]
            return
        if self.board[0][2] == self.board[1][1] == self.board[2][0] and self.board[0][2] != '':
            self.winner = self.board[0][2]
            return

        # If no winner, check for a draw
        if all(cell != '' for row in self.board for cell in row):
            self.winner = 'Draw'
        

class PlayerNotFoundError(Exception):
    pass
            
class GameStateRecorder:
    def __init__(self):
        self.players = {}
        self.waiting_players = {}
        self.game_sessions = [] # a list for now if we want to have multiple games running later

    # for sending quick messages back to the client    
    def send_message(self, addr, content):
        conn = self.players[addr]
        message = Message(sel, conn, addr, None)
        message.send_response(content)
    
    def add_player(self, addr, connection, message):
        if(addr in self.players):
            print(f"player from connection {addr} has already been registered in the game state board.")
            return
        player_name = "player1" if not self.waiting_players else "player2"
        if not self.waiting_players:
            self.players[addr] = {'connection': connection, 'message_object': message, 'player_name': player_name}
            logging.info( f"Player from connection {addr} has been successfully added to the game state board with name {player_name}")
        else:
            player1 = self.waiting_player
            player2 = addr
            session = GameSession(player1, player2)
            self.game_sessions.append(session)
            self.waiting_players = None
            # notify both players of a starting game
            self.send_message(player1, {'action': 'start', 'symbol': 'X', 'message': 'Game started! You are X.'})
            self.send_message(player2, {'action': 'start', 'symbol': 'O', 'message': 'Game started! You are O.'})
        
    def remove_player(self, addr):
        session = self.find_session_by_player(addr)
        if session:
            opponent_addr = [p for p in session.players if p != addr][0]
            self.send_message(opponent_addr, {'action': 'opponent_left', 'message': 'Your opponent has disconnected.'})
            self.game_sessions.remove(session)
        if addr in self.players:
            del self.players[addr]
        logging.info(f"Player {addr} has been removed and any active game sessions have been removed")
    
    def find_session_by_player(self, player_addr):
        for active_session in self.game_sessions:
            if player_addr in active_session.players:
                return active_session
        return None
           
    # def update_ready_status(self, addr, is_ready):
        # if addr not in self.players:
            # raise PlayerNotFoundError("Server tried to update the ready status of a player that has not been registered in the GameStateRecorder")
        # if(is_ready != "yes" and is_ready != "no"):
            # print (f"You tried to update player ready status with invalid option {is_ready}. Your options are yes|no")
            # return False
        # if (is_ready == "yes"):
            # self.players[addr]["game_state"]["ready"] = "yes"
        # else:
            # logging.info(f"Setting player {addr} to not ready")
            # self.players[addr]["game_state"]["ready"] = "no"
       #  for address, details in self.players.items():
       #      logging.info(f"Player address is {address}, status is {details['game_state']['ready']}")
       #  return True
    
        
        
    