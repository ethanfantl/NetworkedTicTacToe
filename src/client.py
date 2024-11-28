import tkinter as tk
from tkinter import messagebox
import threading
import selectors
import clientController
import clientlogic
import logging
import sys
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TicTacToeUI:
    def __init__(self, root, host, port):
        self.root = root
        self.root.title("Networked Tic Tac Toe")
        self.root.geometry("350x550")
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        self.host = host
        self.port = port
        self.message = None
        self.selector = selectors.DefaultSelector()
        self.running = True

        self.create_board()
        self.create_chat()
        self.create_rename()
        self.connect_to_server()

    def create_board(self):
        for i in range(3):
            for j in range(3):
                button = tk.Button(self.root, text="", font="Arial 20", width=5, height=2,
                                   command=lambda i=i, j=j: self.place_piece(i, j))
                button.grid(row=i, column=j)
                self.buttons[i][j] = button

        reset_button = tk.Button(self.root, text="Reset", font="Arial 15", command=self.reset_game)
        reset_button.grid(row=3, column=0, columnspan=3)

    def place_piece(self, i, j):
        if self.buttons[i][j]["text"] == "":
            self.send_action("move", str(i * 3 + j))

    def create_chat(self):
        self.chat_display = tk.Text(self.root, height=10, width=30, state="disabled", wrap="word")
        self.chat_display.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        self.chat_input = tk.Entry(self.root, width=25)
        self.chat_input.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        send_button = tk.Button(self.root, text="Send", command=self.send_message)
        send_button.grid(row=5, column=2, padx=5, pady=5)
    
    def create_rename(self):
        self.rename_input = tk.Entry(self.root, width=25)
        self.rename_input.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        rename_button = tk.Button(self.root, text="Rename", command=self.rename_player)
        rename_button.grid(row=6, column=2, padx=5, pady=5)

    def rename_player(self):
        new_name = self.rename_input.get().strip()
        if len(new_name) > 1:
            self.send_action("rename", new_name)
            self.rename_input.delete(0, tk.END)
        else:
            messagebox.showwarning("Invalid Input", "Enter a valid name more than 1 character long")

    def send_message(self):
        message = self.chat_input.get().strip()
        if message:
            self.send_action("chat", message)
            self.chat_input.delete(0, tk.END)

    def reset_game(self):
        self.send_action("reset", "")
        #Placeholder for now
        #TO DO: Make server handle resets or make server do the reset on a win

    def connect_to_server(self):
        try:
            initial_request = clientController.create_request("connect", "")
            self.message = clientController.start_connection(self.host, self.port, initial_request)
            if self.message:
                #Idk if wee want to use threads, it was the only way I could get this to work
                threading.Thread(target=self.listen_to_server, daemon=True).start()
        except Exception as e:
            logging.error(f"Failed to connect to server: {e}")
            messagebox.showerror("Error", "Could not connect to server")
            self.running = False

    def send_action(self, action, value):
        if self.message:

            try:
                self.message.send_new_request(action, value)
            except Exception as e:
                logging.error(f"Failed to send action: {e}")

                messagebox.showerror("Error", "Failed to send action to server")

    def listen_to_server(self):
        try:
            while self.running:
                events = self.message.selector.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    if message:
                        message.process_events(mask)
                        if message.response:
                            self.handle_server_response(message.response)
                            message.response = None
        except Exception as e:
            logging.error(f"Error in server communication: {e}")
            self.running = False

    def handle_server_response(self, response):
        ##Only problem here is handling chats, we do that big little thing which is hard to parse
        ## Either add a action thing to the messages when server sends, or extract result in this code section
        action = response.get("action")
        if action == "update":
            self.update_board(response.get("board"))
        elif action == "game_over":
            self.update_board(response.get("board"))
            winner = response.get("winner", "No one")
            messagebox.showinfo("Game Over", f"The winner is: {winner}")
        elif action == "chat":
            self.append_chat(response.get("message"))
        elif action == "reset":
            self.update_board([["" for _ in range(3)] for _ in range(3)])
        elif (isinstance(response, dict) and "result" in response and len(response) == 1):
            self.append_chat(response.get("result"))

    def update_board(self, board):
        for i in range(3):
            for j in range(3):
                self.buttons[i][j]["text"] = board[i][j]

    def append_chat(self, message):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", message + "\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")


# Run the game
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("usage:", sys.argv[0], "client -i SERVER_IP/DNS -p PORT")
        sys.exit(1)

    host, port = sys.argv[2], int(sys.argv[4])       
    root = tk.Tk()
    game = TicTacToeUI(root, host, port)
    root.mainloop()