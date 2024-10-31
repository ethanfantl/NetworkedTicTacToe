import tkinter as tk
from tkinter import messagebox

class TicTacToeUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Networked Tic Tac Toe")
        self.root.geometry("350x500")
        self.current_player = "X"
        self.buttons = [[None for _ in range(3)] for _ in range(3)]
        
        # Initialize the game board and chat UI
        self.create_board()
        self.create_chat()
        #We should be able to instantiate this and then control it as an object 

    def create_board(self):
        # GGrid with clickable buttons
        for i in range(3):
            for j in range(3):
                button = tk.Button(self.root, text="", font="Arial 20", width=5, height=2,
                                   command=lambda i=i, j=j: self.place_piece(i, j)) ##FI think this is good, and the replacement code will have to go at place_piece
                button.grid(row=i, column=j)
                self.buttons[i][j] = button

       
        reset_button = tk.Button(self.root, text="Reset", font="Arial 15", command=self.reset_game)
        reset_button.grid(row=3, column=0, columnspan=3)

    def place_piece(self, i, j):
        if self.buttons[i][j]["text"] == "":
            self.buttons[i][j]["text"] = self.current_player
            self.current_player = "O" if self.current_player == "X" else "X"

    def create_chat(self):
        # Chat box
        self.chat_display = tk.Text(self.root, height=10, width=30, state="disabled", wrap="word")
        self.chat_display.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        # Chat create input place
        self.chat_input = tk.Entry(self.root, width=25)
        self.chat_input.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        #Send message button
        send_button = tk.Button(self.root, text="send", command=self.send_message)
        send_button.grid(row=5, column=2, padx=5, pady=5)

    def send_message(self):
        message = self.chat_input.get().strip()
        #Absolutely all of this stuff is going to have to eventually be replaced with our code
        if message:
            self.chat_display.config(state="normal")
            self.chat_display.insert("end", f"Player {self.current_player}: {message}\n")
            self.chat_display.config(state="disabled")
            self.chat_display.see("end")  
            self.chat_input.delete(0, tk.END)

    def reset_game(self):
        #This again is temporary, I think it should be replaced
        self.current_player = "X"
        for i in range(3):
            for j in range(3):
                self.buttons[i][j]["text"] = ""
        self.chat_display.config(state="normal")
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state="disabled")

# Run the game
root = tk.Tk()
game = TicTacToeUI(root)
root.mainloop()