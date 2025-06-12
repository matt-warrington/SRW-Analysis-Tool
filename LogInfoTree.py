from tkinter import ttk
import tkinter as tk

class LogInfoTree(ttk.Treeview):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Configure columns
        self.columns = ("selected", "file", "#", "date", "time", "keys", "description")
        self.configure(columns=self.columns, show='headings')
        
        # Set up column headings and widths
        self.heading("selected", text="Select")
        self.column("selected", width=50, anchor="center")
        
        self.heading("file", text="file")
        self.column("file", width=100)
        
        self.heading("#", text="#") 
        self.column("#", width=20)
        
        self.heading("date", text="date")
        self.column("date", width=50)
        
        self.heading("time", text="time")
        self.column("time", width=50)
        
        self.heading("keys", text="keys")
        self.column("keys", width=50)
        
        self.heading("description", text="description")
        self.column("description", width=500)
        
        # Add scrollbar
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.configure(yscrollcommand=self.scrollbar.set)


