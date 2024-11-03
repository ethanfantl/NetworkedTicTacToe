import sys
import socket
import selectors
import struct
import traceback
import clientlogic
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sel = selectors.DefaultSelector()

# basic movement definitions, we can add or change these later
valid_actions = [
    "test",
    "connect",
    "disconnect",
    "move",
    "chat"
]

def create_request(action, value):
    return dict(
        type="text/json",
        encoding="utf-8",
        content=dict(action=action, value=value),
    )

def start_connection(host, port, request):
    addr = (host, port)
    logging.info(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    try:
        sock.connect_ex(addr)
    except socket.error as e:
        logging.error(f"Connection failed to {addr}: {e}")
        return

    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = clientlogic.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)
    return message

def handle_input(message):
    sys.stdout.flush() # helps with order of appearance in terminal, for readability
    new_action = input("Enter new action: ").strip()
    if (new_action not in valid_actions):
        print("You entered an invalid action, please use one of the following actions")
        print(valid_actions)
        return
    new_value = input("Enter new value: ").strip()
    logging.info(f"sending new action {new_action} and new value {new_value} to server")
    message.send_new_request(new_action, new_value)

if len(sys.argv) != 5:
    print("usage:", sys.argv[0], "<host> <port> <action> <value>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
action, value = sys.argv[3], sys.argv[4]
if(action not in valid_actions):
    print("Defined action %s is not a valid action" % action)
    sys.exit(1)
    
request = create_request(action, value)
start_connection(host, port, request) # opens non blocking with socket.connect_ex

# this is kinda ugly but it fixed the logs and requests being out of order in the terminal, come back to this
# because this handles only the first request, then we have the other while loop to handle the rest
try:
    response_received = False
    while not response_received:
        events = sel.select(timeout=None)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
                if message.response is not None:
                    response_received = True
                    message.response = None  # Reset the response
            except Exception as e:
                logging.error(f"Main: error: exception for {message.addr}:\n{traceback.format_exc()}")
                message.close()
                logging.info(f"Disconnected from {message.addr}")
                sys.exit(1)
except KeyboardInterrupt:
    logging.info("Caught keyboard interrupt, closing the program now")
    sys.exit(1)

sel.register(sys.stdin, selectors.EVENT_READ, data="input")
print("Entering new actions")
try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data == "input":
                # message = next(iter(sel.get_map().values())).data  # Get the message from the socket (I got to clean this up for sure)
                handle_input(message)
            elif key.data is message:
                try:
                    message.process_events(mask)
                    if message.response is not None:
                        # You can handle the response here if needed
                        message.response = None
                except Exception as e:
                    logging.error(f"Main: error: exception for {message.addr}:\n{traceback.format_exc()}")
                    message.close()
                    logging.info(f"Disconnected from {message.addr}")
                    sys.exit(1)
except KeyboardInterrupt:
    logging.info("Caught keyboard interrupt, closing the program now")
finally:
    sel.close()
    logging.info("Selector closed, exiting program/client")