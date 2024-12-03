import sys
import socket
import selectors
import struct
import traceback
import clientlogic
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("tictactoeClient.log", mode='w')
    ]
)

sel = selectors.DefaultSelector()

# methods that can be called by clients
valid_actions = [
    "test",
    "connect",
    "disconnect",
    "move",
    "chat",
    "rename"
]

# create a request
def create_request(action, value):
    return dict(
        type="text/json",
        encoding="utf-8",
        content=dict(action=action, value=value),
    )

# start our connection to the server
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

# class for handling input from user
def handle_input(message):
    sys.stdout.flush()
    new_action = input("Enter new action: ").strip()
    if new_action not in valid_actions:
        print("You entered an invalid action, please use one of the following actions")
        print(valid_actions)
        return
    new_value = input("Enter new value: ").strip()
    logging.info(f"Sending {new_action} : {new_value} to server")
    message.send_new_request(new_action, new_value)