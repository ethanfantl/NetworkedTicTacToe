import sys
import socket
import selectors
import struct
import traceback
import clientlogic
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sel = selectors.DefaultSelector()

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

if len(sys.argv) != 5:
    print("usage:", sys.argv[0], "<host> <port> <action> <value>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
action, value = sys.argv[3], sys.argv[4]
request = create_request(action, value)
start_connection(host, port, request)

try:
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception as e:
                logging.error(f"Main: error: exception for {message.addr}:\n{traceback.format_exc()}")
                message.close()
                logging.info(f"Disconnected from {message.addr}")

        if not sel.get_map():
            break
except KeyboardInterrupt:
    logging.info("Caught keyboard interrupt, exiting")
finally:
    sel.close()
    logging.info("Selector closed, exiting program")