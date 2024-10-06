import sys
import selectors
import json
import io
import struct


'''
This object manages communication between the server and client. 
'''
class Message:
    def __init__(self, selector, client_sock, client_address):
        self.selector = selector
        self.client_sock = client_sock 
        self.client_address = client_address 
        self._recieved_buffer = b""
        self._send_buffer = b""
        self._json_header_length = None
        self.json_header = None
        self.request = None
        self.response_created = False 
        
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
            print("Sending", repr(self._send_buffer), 'to', self.client_address)
            try:
                sent = self.client_sock.send(self._send_buffer) # sending as much data as the socket can handle at once
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:] # remove all data that was sent through socket
                # if we have sent it all, close the connection
                if sent and not self._send_buffer:
                    self.close()
    
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

    '''
    Create a response for a json request (this will be our only request)
    '''
    def _create_response_json_content(self):
        action = self.request.get("action")
        
        # here will be our actions. May want a switch statement later but right now all we have is test
        if action == "test":
            answer = f"Hello client, you have successfully pinged the server and got a response back :)"
            content = {"result": answer}
        else:
            content = {"result": f'Error: invalid action "{action}".'}
        content_encoding = "utf-8" # we only are using utf-8 as our encoding
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
        
        
    