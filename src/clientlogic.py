import sys
import selectors
import json
import io
import struct
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class Message:
    def __init__(self, selector, sock, addr, request):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._json_header_length = None
        self.json_header = None
        self.response = None
        self._request_queued = False

    def _select_selector_events_mask(self, event):
        if event == "r":
            new_event = selectors.EVENT_READ
        elif event == "w":
            new_event = selectors.EVENT_WRITE
        elif event == "rw":
            new_event = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid event mask mode received.")
        self.selector.modify(self.sock, new_event, data=self)

    def _read(self):
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def _write(self):
        if self._send_buffer:
            try:
                sent = self.sock.send(self._send_buffer) # send data to the server registerd in the socket conneciton
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                if not self._send_buffer:
                    self._select_selector_events_mask("r")

    def _json_encode(self, obj):
        return json.dumps(obj, ensure_ascii=False).encode('utf-8')

    def _json_decode(self, json_bytes):
        tiow = io.TextIOWrapper(io.BytesIO(json_bytes), encoding='utf-8', newline="")
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(self):
        content_bytes = self._json_encode(self.request["content"])
        json_header = {
            "byteorder": sys.byteorder,
            "content-type": self.request["type"],
            "content-encoding": self.request["encoding"],
            "content-length": len(content_bytes),
        }
        json_header_bytes = self._json_encode(json_header)
        message_hdr = struct.pack(">H", len(json_header_bytes))
        return message_hdr + json_header_bytes + content_bytes

    def send_new_request(self, new_action, new_value):
        self.request = {
            "type" : "text/json",
            "encoding": "utf-8",
            "content": {"action": new_action, "value": new_value}
        }
        
        logging.info("Sending a new request to the server:)")
        
        # reset buffers and queue next request
        self._send_buffer = self._create_message()
        self._request_queued = True
        self._select_selector_events_mask("rw")

    def process_fixed_protocol_header(self):
        header_length = 2
        if len(self._recv_buffer) >= header_length:
            self._json_header_length = struct.unpack(">H", self._recv_buffer[:header_length])[0]
            self._recv_buffer = self._recv_buffer[header_length:]
        else:
            logging.info(f"not enough data in the protocol header. Here is the buffer length {len(self._recv_buffer)}")

    def process_json_header(self):
        if len(self._recv_buffer) >= self._json_header_length:
            self.json_header = self._json_decode(self._recv_buffer[:self._json_header_length])
            self._recv_buffer = self._recv_buffer[self._json_header_length:]

    def process_response(self):
        content_length = self.json_header["content-length"]
        if len(self._recv_buffer) >= content_length:
            data = self._recv_buffer[:content_length]
            self.response = self._json_decode(data)
            logging.info(f"Got a response {self.response} from the server")
            print(f"Received response: {self.response}")
            # self.close() -> we don't want to close the socket, we want persistant player connection
            self._json_header_length = None
            self.json_header = None
            self.request = None
            self._request_queued = False
            self._recv_buffer = b""
            self._select_selector_events_mask("w")

    def read(self):
        self._read()
        if self._json_header_length is None:
            self.process_fixed_protocol_header()

        if self._json_header_length is not None and self.json_header is None:
            self.process_json_header()

        if self.json_header and self.response is None:
            self.process_response()
        
        # self._select_selector_events_mask("w")

    def write(self):
        if not self._request_queued:
            self._send_buffer = self._create_message()
            self._request_queued = True
        self._write()

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
            
        # if we send all the data, set back to write mode
        if not self._send_buffer:
            self._select_selector_events_mask("r")

    def close(self):
        print("Closing connection to", self.addr)
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f"Error: selector.unregister() exception for {self.addr}: {repr(e)}")
        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {repr(e)}")
        finally:
            self.sock = None