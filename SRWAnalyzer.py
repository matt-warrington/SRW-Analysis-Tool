import json
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD 
import tkinter.font as tkfont
import os
from datetime import datetime as dt
import webbrowser
from ExpandedLogView import ExpandedLogDialog
import GOGlobal
import pandas as pd
from ToolTip import ToolTip

# Import functions from other files
import myUtils
from ApsLogs import log_info, check_licenses, get_basic_info, logger
#from ErrorCodes import error_code_lookup

# Define constants
CONFIG_FILE_PATH = "config.json"
#########################################################################

class SRWAnalyzerApp(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root

        # Load configuration
        self.config = self.load_config()
        self.root.title("SRW Analyzer") 
        
        # Base font
        #self.base_font = tkfont.Font(family="Segoe UI", size=11)
        #self.root.option_add("*Font", self.base_font)

        # Bind to window resize event
        #self._resize_after_id = -1
        #self._last_font_size = 11
        #self.root.bind("<Configure>", self.on_resize)

        # Create a style for the hyperlink button
        self.link_style = ttk.Style()
        self.link_style.configure("Link.TButton", foreground="blue", borderwidth=0)
        self.link_style.map("Link.TButton",
                           foreground=[("hover", "purple")],
                           relief=[("pressed", "flat"), ("!pressed", "flat")])

        
        '''
        # Set the window to full screen
        try:
            # Get DPI scaling from Windows
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()  # Tell Windows we are DPI aware
            
            # Try Windows-specific maximize
            self.root.state('zoomed')
        except:
            # Fallback for other operating systems
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            window_width = screen_width - 20
            window_height = screen_height - 40
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        '''
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = screen_width - 20
        window_height = screen_height - 40
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Create container frame for scrollbars
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        
        # Create main scrollable frame
        self.main_canvas = tk.Canvas(self.container)
        self.scrollbar_y = ttk.Scrollbar(self.container, orient="vertical", command=self.main_canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self.container, orient="horizontal", command=self.main_canvas.xview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )

        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set
        )

        # Pack the scrollbars and canvas
        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        # Bind mousewheel to root for global scrolling
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)
        
        # Initialize scrolling widget tracker
        self.scrolling_widget = None

        # Variables
        self.set_variables_to_defaults()

        # Create UI elements
        self.create_widgets()

        self.set_widgets_to_defaults()

        # Bind the '<Destroy>' event to the cleanup method
        self.root.bind("<Destroy>", self.cleanup)

        # Add this to your existing initialization
        self._search_after_id = None
        self._last_search = None

        # Replace log_data with DataFrame
        self.log_df = pd.DataFrame()


    def on_resize(self, event):
        # Debounce: only run after resizing has stopped for 100ms
        if self._resize_after_id != -1:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(100, lambda: self._do_resize(event))

    def _do_resize(self, event):
        min_size = 10
        max_size = 24
        new_size = int(max(min_size, min(max_size, event.height // 75)))
        if self._last_font_size != new_size:
            self.base_font.configure(size=new_size)
            self._last_font_size = new_size

    
    def _bind_treeview_scrolling(self, treeview, scrollbar_y=None, scrollbar_x=None):
        """Helper method to bind scrolling events to any treeview"""
        widgets = [treeview]
        if scrollbar_y:
            widgets.append(scrollbar_y)
        if scrollbar_x:
            widgets.append(scrollbar_x)
            
        for widget in widgets:
            widget.bind("<MouseWheel>", lambda e: self._on_treeview_mousewheel(e, treeview))
            widget.bind("<Shift-MouseWheel>", lambda e: self._on_treeview_shift_mousewheel(e, treeview))
            widget.bind("<Enter>", lambda e, tv=treeview: self._set_scrolling_widget(tv))
            widget.bind("<Leave>", lambda e: self._set_scrolling_widget(None))

    def _set_scrolling_widget(self, widget):
        """Track which widget should receive scroll events"""
        self.scrolling_widget = widget

    def _on_mousewheel(self, event):
        # Check if the event originated from a treeview
        widget = event.widget
        while widget is not None:
            if isinstance(widget, ttk.Treeview):
                return
            widget = widget.master
            
        # If not in a treeview, scroll the main canvas
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_shift_mousewheel(self, event):
        # Check if the event originated from a treeview
        widget = event.widget
        while widget is not None:
            if isinstance(widget, ttk.Treeview):
                return
            widget = widget.master
            
        # If not in a treeview, scroll the main canvas
        self.main_canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def cleanup(self, event):
        # Delete the temporary directory if it exists
        myUtils.remove_directory(self.unzipped_file_path)

    def drop(self, event):
        files = event.data.strip().split()  # Handle multiple files if dropped

        for file in files:
            file = file.strip("{}")  # Remove curly braces around paths (if any)

            if not file.lower().endswith(".html"):
                messagebox.showwarning("Invalid File", f"Skipped: {file} (Not an HTML file)")
                continue

            destination = os.path.join(self.unzipped_file_path, os.path.basename(file))

            try:
                shutil.copy(file, destination)
                self.call_log_info() #update the log_df
            except Exception as e:
                messagebox.showerror("Error", f"Could not copy {file}: {e}")


    def create_widgets(self):
        #region File entry section
        self.file_frame = ttk.Frame(self.scrollable_frame)
        self.file_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.file_label = ttk.Label(self.file_frame, text="SRW .zip file Path:")
        self.file_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.file_entry = ttk.Entry(self.file_frame)
        self.file_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        self.browse_button = ttk.Button(self.file_frame, text="Browse...", command=self.find_srw)
        self.browse_button.grid(row=0, column=2, padx=5, pady=2)
        ToolTip(self.browse_button, "Find the SRW .zip you would like to run analysis on.")


        self.analyze_button = ttk.Button(self.file_frame, text="Analyze", command=self.analyze_file)
        self.analyze_button.grid(row=0, column=3, padx=5, pady=2)
        ToolTip(self.analyze_button, "Type a file path for a specific .zip file, then click Analyze. \n\nOr, click Browse to find the file.")

        self.file_frame.columnconfigure(1, weight=1)
        #endregion File entry section

        #region Current File Section
        self.current_file_frame = ttk.Frame(self.scrollable_frame)
        self.current_file_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.current_file_label = ttk.Label(self.current_file_frame, text="Current SRW:")
        self.current_file_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.clear_button = ttk.Button(self.current_file_frame, text="Clear", command=self.clear_file)
        self.clear_button.grid(row=0, column=1, padx=5, pady=2, sticky="e")

        self.current_file_frame.columnconfigure(0, weight=1)
        #endregion Current File Section

        # Create a frame for the system info and licenses section
        self.info_licenses_frame = ttk.Frame(self.scrollable_frame)
        self.info_licenses_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        # Set a maximum height for info_licenses_frame
        self.info_licenses_frame.grid_propagate(False)  # Prevent frame from auto-resizing
        self.info_licenses_frame.configure(height=200)  # Set fixed height in pixels

        #region System info section
        self.info_frame = ttk.Frame(self.info_licenses_frame)
        self.info_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.host_os_label = ttk.Label(self.info_frame, text="Host Operating System:")
        self.host_os_label.grid(row=0, column=0, padx=5, pady=2, sticky="e")
        
        # Create a frame to hold both the entry and button
        host_os_container = ttk.Frame(self.info_frame)
        host_os_container.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.host_os_entry = ttk.Entry(host_os_container, width=60, state='readonly')  
        self.host_os_entry.pack(side='left', padx=(0, 5))  # Add padding between entry and button

        self.build_button = ttk.Button(host_os_container, text="Build #", state="disabled", 
                                     command=lambda: webbrowser.open(f"https://www.google.com/search?q={self.build_button['text']}"))
        self.build_button.pack(side='left')

        self.host_version_label = ttk.Label(self.info_frame, text="GO-Global Host Version:")
        self.host_version_label.grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.host_version_entry = ttk.Entry(self.info_frame, width=30, state='readonly')
        self.host_version_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        self.server_role_label = ttk.Label(self.info_frame, text="Server Role:")
        self.server_role_label.grid(row=2, column=0, padx=5, pady=2, sticky="e")
        self.server_role_entry = ttk.Entry(self.info_frame, width=30, state='readonly')
        self.server_role_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self.server_ip_label = ttk.Label(self.info_frame, text="Server IP:")
        self.server_ip_label.grid(row=3, column=0, padx=5, pady=2, sticky="e")
        self.server_ip_entry = ttk.Entry(self.info_frame, width=30, state='readonly')
        self.server_ip_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        self.info_frame.columnconfigure(1, weight=1)
        #endregion System info section

        #region Client information
        # Create a frame to hold client information
        self.client_frame = ttk.Frame(self.info_licenses_frame)
        self.client_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.client_label = ttk.Label(self.client_frame, text="Client Versions and OS:")
        self.client_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.client_tree = ttk.Treeview(self.client_frame, columns=("version", "os", "ip"), show='headings', height=5)
        self.client_tree.heading("version", text="Client Version")
        self.client_tree.heading("os", text="Client OS")
        self.client_tree.heading("ip", text="IP Address")
        self.client_tree.grid(row=1, column=0, padx=5, pady=2, sticky="nsew")
        
        # Set column widths
        self.client_tree.column("version", width=100)
        self.client_tree.column("os", width=100)
        self.client_tree.column("ip", width=100)
        
        self.client_scrollbar = ttk.Scrollbar(self.client_frame, orient="vertical", command=self.client_tree.yview)
        self.client_scrollbar.grid(row=1, column=1, sticky='ns')
        self.client_tree.configure(yscrollcommand=self.client_scrollbar.set)

        # Bind double-click to toggle key
        self.client_tree.bind("<Double-1>", self.jump_to_context_client)
        #endregion Client information

        #region License Table
        self.licenses_frame = ttk.Frame(self.info_licenses_frame)
        self.licenses_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        self.licenses_label = ttk.Label(self.licenses_frame, text="Licenses:")
        self.licenses_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.licenses_tree = ttk.Treeview(self.licenses_frame, columns=("ID", "Status", "# Seats", "File"), show='headings')
        self.licenses_tree.grid(row=1, column=0, padx=5, pady=2, sticky="nsew")
        self.licenses_scrollbar = ttk.Scrollbar(self.licenses_frame, orient="vertical", command=self.licenses_tree.yview)
        self.licenses_scrollbar.grid(row=1, column=1, sticky='ns')
        self.licenses_tree.configure(yscrollcommand=self.licenses_scrollbar.set)

        self.licenses_frame.columnconfigure(0, weight=1)
        self.licenses_frame.rowconfigure(1, weight=1)

        self.licenses_tree.heading("ID", text="ID")
        self.licenses_tree.heading("Status", text="Status")
        self.licenses_tree.heading("# Seats", text="# Seats")
        self.licenses_tree.heading("File", text="File")

        self.licenses_tree.column("ID", width=100)
        self.licenses_tree.column("Status", width=100)
        self.licenses_tree.column("# Seats", width=100)
        self.licenses_tree.column("File", width=300)
        self.licenses_tree.bind("<Double-1>", self.open_license_file)
        #endregion License Table

        #region Log messages section
        self.logs_frame = ttk.LabelFrame(self.scrollable_frame, text="Log Messages")
        self.logs_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        #region Search frame
        self.search_frame = ttk.Frame(self.logs_frame)
        self.search_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Create labels for column headers
        for col in self.log_columns:
            lbl = ttk.Label(self.search_frame, text=col)
            lbl.grid(row=0, column=self.log_columns.index(col), padx=5, pady=2, sticky="w")

        # Configure search frame columns
        for col in self.log_columns:
            self.search_frame.columnconfigure(
                self.log_columns.index(col),
                minsize=self.column_widths[col],
                weight=1 if col == "Description" else 0
            )

        # Create entry widgets
        self.search_vars = {}
        self.search_entries = {}
        
        for col in self.log_columns:
            self.search_vars[col] = tk.StringVar()
            self.search_vars[col].trace_add('write', self.on_search_change)  # Add trace to each variable
            entry = ttk.Entry(
                self.search_frame,
                textvariable=self.search_vars[col]
            )
            self.search_entries[col] = entry
            entry.grid(row=1, column=self.log_columns.index(col), padx=5, pady=2, sticky="ew")

            # Width of the entry is based on the number of characters in the column, while column width is based on pixels.
            pixelsPerChar = 10
            entry.configure(width=int(self.column_widths[col] / pixelsPerChar))

        # Add buttons in a new row
        button_frame = ttk.Frame(self.search_frame)
        button_frame.grid(row=2, column=0, columnspan=len(self.log_columns), sticky="nsew", padx=5, pady=2)

        self.select_all_var = tk.BooleanVar()
        self.select_all_checkbox = ttk.Checkbutton(
            button_frame, 
            text="Select All", 
            variable=self.select_all_var, 
            command=self.toggle_all_selections
        )
        self.select_all_checkbox.pack(side=tk.LEFT, padx=5)

        # Remove the search button since we don't need it anymore
        self.save_logs_button = ttk.Button(button_frame, text="Save Selected Logs", command=self.save_selected_logs)
        self.save_logs_button.pack(side=tk.LEFT, padx=5)
        #endregion Search frame

        # Create a frame to hold the treeview and scrollbars
        self.tree_frame = ttk.Frame(self.logs_frame)
        self.tree_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Configure the tree_frame to expand
        self.logs_frame.grid_rowconfigure(1, weight=1)  # Make row 1 (tree_frame) expandable
        self.logs_frame.grid_columnconfigure(0, weight=1)  # Make column 0 expandable
        ToolTip(self.logs_frame, "Double-click on a log to select or unselect it.\nA log is selected if there is a ✓ in the Key column for that log.")

        
        # Create the treeview
        self.log_info_tree = ttk.Treeview(self.tree_frame, columns=self.log_columns, show='headings')
        
        # Create vertical scrollbar
        self.log_scrollbar_y = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.log_info_tree.yview)
        self.log_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create horizontal scrollbar
        self.log_scrollbar_x = ttk.Scrollbar(self.tree_frame, orient=tk.HORIZONTAL, command=self.log_info_tree.xview)
        self.log_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Configure the treeview to use both scrollbars and fill space
        self.log_info_tree.configure(
            yscrollcommand=self.log_scrollbar_y.set,
            xscrollcommand=self.log_scrollbar_x.set
        )
        
        # Pack the treeview to fill all available space
        self.log_info_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        #self.log_info_tree.bind("<Double-1>", self.open_log_in_browser)
        self.log_info_tree.bind("<Double-1>", self.toggle_key)

        # Make Treeview a drop target
        # need to download TkDND for this to work. https://sourceforge.net/projects/tkdnd/
        #self.log_info_tree.drop_target_register(DND_FILES) 
        #self.log_info_tree.dnd_bind("<<Drop>>", self.drop)

        for col in self.log_columns:
            self.log_info_tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col, False))

        # Set fixed widths for all columns except Description
        for col in self.log_columns:
            self.log_info_tree.column(col, 
                                    width=self.column_widths[col], 
                                    minwidth=10, 
                                    stretch=True if col == "Description" else False)

        self.logs_frame.columnconfigure(0, weight=3)
        self.logs_frame.rowconfigure(1, weight=3)
        #endregion Log messages section

        # Add expand button below log_info_tree
        self.expand_button = ttk.Button(self.logs_frame, text="Expand Log View", command=self.show_expanded_logs)
        self.expand_button.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ToolTip(self.expand_button, "Opens a larger window for viewing the log tree.\nWill open to the log currently in focus.\nSingle-click on a log to set the focus.\nLog in focus will be highlighted blue.")


        # Bind scrolling for log_info_tree
        self._bind_treeview_scrolling(
            self.log_info_tree,
            self.log_scrollbar_y,
            self.log_scrollbar_x
        )

        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(4, weight=1)

    def set_variables_to_defaults(self):
        """Initialize default values for class variables"""
        self.default_srw_path = self.get_srw_base_path()
        self.zip_file_path = None
        self.unzipped_file_path = None
        self.gg_version = None
        self.issue_type = None 
        self.case_number = None
        self.log_df = pd.DataFrame()  # Empty DataFrame instead of log_data list

        # Define column widths in pixels
        self.column_widths = {
            "Key": 30,
            "File": 200,
            "Line": 40,
            "Date": 100,
            "Time": 100,
            "User": 100,
            "Server": 100,
            "Process": 100,
            "PID": 60,
            "Session": 80,
            "Keys": 150,
            "Description": 700
        }
        
        # Update log columns to include new fields
        self.log_columns = list(self.column_widths.keys())
        self.search_vars = {}
        self.search_entries = {}  # Store references to entry widgets
        for col in self.log_columns:
            self.search_vars[col] = tk.StringVar()

        # Remove the temporary directory
        myUtils.remove_directory(self.unzipped_file_path)
        self.unzipped_file_path = ""


    def set_widgets_to_defaults(self):
        self.select_all_var.set(False)

    def get_srw_base_path(self):
        if not os.path.exists(CONFIG_FILE_PATH):
            # First run, set the default dump path
            new_base_path = myUtils.select_dir("Select a base path for finding SRWs...")
            config = {"srw_base_path": new_base_path}
            with open(CONFIG_FILE_PATH, 'w') as config_file:
                json.dump(config, config_file)
            return new_base_path
        else:
            # Read the dump path from the config file
            with open(CONFIG_FILE_PATH, 'r') as config_file:
                config = json.load(config_file)

            base_path = config.get("srw_base_path", "")
            if base_path == "" or not os.path.exists(base_path):
                base_path = myUtils.select_dir("Select a base path for finding SRWs...")
                config["srw_base_path"] = base_path
                with open(CONFIG_FILE_PATH, 'w') as config_file:
                    json.dump(config, config_file)
            
            return base_path

    def open_log_in_browser(self, event):
        # If the user double-clicks on the treeview without clicking a specific log, don't open the browser.
        if not self.log_info_tree.selection():
            return
        
        # Get the selected item
        selected_item = self.log_info_tree.selection()[0]
        values = self.log_info_tree.item(selected_item, "values")
        
        # Extract the file name and log number
        file_name = values[0]
        log_number = values[1]
        
        # Construct the file path
        file_path = os.path.join(self.unzipped_file_path, file_name)
        
        # Open the file in the default web browser
        file_url = f"file://{file_path}#line_{log_number}" # for some reason, this doesn't work, but you can manually add the line. Figure this out at some point.
        webbrowser.open(file_url)

    def jump_to_context_client(self, event):
        # If the user double-clicks on the treeview without clicking a specific log, don't do anything
        if not self.client_tree.selection():
            return
        
        # Get the selected item
        selected_item = self.client_tree.selection()[0]
        values = self.client_tree.item(selected_item, "values")

        # Jump to the location of the client's connection in the log_info_tree  
        col_index = self.log_info_tree["columns"].index('Description')
        for rowID in self.log_info_tree.get_children():
            desc = self.log_info_tree.item(rowID, 'values')[col_index]
            if desc == f"The version of the {values[1]} client is {values[0]}.":
                self.jump_to_context(rowID)
                break

    def jump_to_context(self, rowID: int):
        if not rowID:
            return

        self.log_info_tree.see(rowID)

        # Only set selection if the row we are jumping to is not already in the selection
        if rowID not in self.log_info_tree.selection():  
            self.log_info_tree.selection_set(rowID)  

    def open_license_file(self, event):
        # Get the selected item
        selected_item = self.licenses_tree.selection()[0]
        values = self.licenses_tree.item(selected_item, "values")
        
        # Extract the license ID
        license_file = values[3]
        
        # Check if the file exists and open it in Notepad, if there is a file value.
        if license_file != "-":
            if os.path.exists(license_file):
                subprocess.Popen(['C:\\Windows\\notepad.exe', license_file])
            else:
                messagebox.showerror("Error", f"License file {license_file} not found.")

    def clear_file(self):
        # Reset the current file label
        self.current_file_label.config(text="Current SRW:")

        self.set_variables_to_defaults()
        self.set_widgets_to_defaults()

        # Clear all Treeviews recursively
        self.clear_all_treeviews(self.scrollable_frame)

        # Clear all Entry widgets recursively
        self.clear_all_entries(self.scrollable_frame)

        # Reset build button to original state
        self.build_button.configure(
            state="disabled",
            text="Build #",
            style="TButton",  # Reset to default button style
            cursor=""  # Reset cursor to default
        )


    def clear_all_treeviews(self, parent_widget):
        """Recursively find and clear all Treeviews"""
        # Check if the current widget is a Treeview
        if isinstance(parent_widget, ttk.Treeview):
            for item in parent_widget.get_children():
                parent_widget.delete(item)
        
        # Recursively check all child widgets
        for child in parent_widget.winfo_children():
            self.clear_all_treeviews(child)

    def clear_all_entries(self, parent_widget):
        """Recursively find and clear all Entry widgets"""
        # Check if the current widget is an Entry
        if isinstance(parent_widget, ttk.Entry):
            current_state = parent_widget.cget('state')
            parent_widget.config(state='normal')
            parent_widget.delete(0, tk.END)
            parent_widget.config(state=current_state)
        
        # Recursively check all child widgets
        for child in parent_widget.winfo_children():
            self.clear_all_entries(child)

    def find_srw(self):
        file_path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")], initialdir=self.default_srw_path)
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)
            self.analyze_file()

    def analyze_file(self):
        file_path = self.file_entry.get()
        if file_path.endswith(".zip"):
            # Set new file path
            self.zip_file_path = file_path
            self.current_file_label.config(text=f"Current SRW: {file_path.split('/')[-1]}")

            # Get case number from parent directory name
            parent_dir = os.path.basename(os.path.dirname(file_path))
            self.case_number = parent_dir

            # Create temporary directory of extracted files
            myUtils.remove_directory(self.unzipped_file_path) # remove the unzipped folder before replacing it
            self.unzipped_file_path = myUtils.extract_zip(self.zip_file_path)

            # Get all the info you need
            self.call_basic_info()
            self.call_log_info()
            self.call_check_licenses()
        else:
            messagebox.showerror("Error", "Please select a valid .zip file.")

    def update_button_state(self):
        state = tk.NORMAL if self.zip_file_path else tk.DISABLED
        self.browse_button.config(state=state)
        self.clear_button.config(state=state if self.zip_file_path else tk.DISABLED)

    def call_basic_info(self):
        # Enable writing to the entries
        self.host_version_entry.config(state='normal')
        self.host_os_entry.config(state='normal')
        self.server_role_entry.config(state='normal')
        self.server_ip_entry.config(state='normal')

        # Update the values
        basics = get_basic_info(self.unzipped_file_path)
        self.gg_version = basics['hostVersion']
        
        # Update the entries
        self.host_version_entry.delete(0, tk.END)
        self.host_version_entry.insert(0, self.gg_version)
        self.host_os_entry.delete(0, tk.END)
        self.host_os_entry.insert(0, basics['hostOS'])
        self.server_role_entry.delete(0, tk.END)
        self.server_role_entry.insert(0, str(basics['serverRole']) if basics['serverRole'] is not None else "")
        self.server_ip_entry.delete(0, tk.END)
        self.server_ip_entry.insert(0, basics['serverIp'])

        # Enable build button, update its text, and apply link style
        if basics['platformBuild'] != "Not found":
            self.build_button.configure(
                state="normal", 
                text=basics['platformBuild'],
                style="Link.TButton",
                cursor="hand2"  # Changes cursor to hand pointer on hover
            )

        # Disable writing to the entries
        self.host_version_entry.config(state='readonly')
        self.host_os_entry.config(state='readonly')
        self.server_role_entry.config(state='readonly')
        self.server_ip_entry.config(state='readonly')

    def call_log_info(self):
        log_info_result = log_info(self.unzipped_file_path)
        
        if log_info_result:
            # Convert to DataFrame
            self.log_df = pd.DataFrame(log_info_result)
            
            # Convert date and time columns to datetime
            self.log_df['DateTime'] = pd.to_datetime(
                self.log_df['Date'] + ' ' + self.log_df['Time'],
                format='%Y-%m-%d %H:%M:%S.%f',
                errors='coerce'  # Handle cases without microseconds
            )
            
            # Ensure 'Key' column exists
            if 'Key' not in self.log_df.columns:
                self.log_df['Key'] = ''

            self.update_log_treeview(self.log_df)

            # Create a dictionary to track IP addresses and their pending entries
            ip_pending = {}
            
            for log in log_info_result:
                # Check for IP address entries
                ip_match = re.search(r'A client at IP address (\d+\.\d+\.\d+\.\d+)', log['Description'])
                if ip_match:
                    client_ip = ip_match.group(1)
                    ip_pending[client_ip] = {'ip': client_ip}
                    continue
                    
                # Check for version entries
                version_match = re.search(r'The version of the (.*?) client is (\d+\.\d+\.\d+\.\d+)', log['Description'])
                if version_match:
                    client_os = version_match.group(1).strip()
                    client_version = version_match.group(2).strip()
                    
                    # If we have a pending IP for this entry (assuming logs are in chronological order)
                    pending_ip = next((ip for ip, data in ip_pending.items() 
                                    if 'version' not in data), None)
                    
                    if pending_ip:
                        # Create complete entry with IP
                        entry = (client_version, client_os, pending_ip)
                        ip_pending[pending_ip]['version'] = client_version
                    else:
                        # Create entry without IP for backward compatibility
                        entry = (client_version, client_os, '')
                    
                    # Check if entry already exists
                    existing_items = [(self.client_tree.item(item)['values'][0],
                                    self.client_tree.item(item)['values'][1],
                                    self.client_tree.item(item)['values'][2] if len(self.client_tree.item(item)['values']) > 2 else '')
                                    for item in self.client_tree.get_children()]
                    
                    if entry not in existing_items:
                        self.client_tree.insert('', 'end', values=entry)
        else:
            logger.error(f"log_info({self.unzipped_file_path}) returned None.")
            for item in self.log_info_tree.get_children():
                self.log_info_tree.delete(item)
            

    def insert_tree(self, tree, parent, item):
        if isinstance(item, dict):
            for key, value in item.items():
                # Insert the key as a parent item
                child_item = tree.insert(parent, "end", text=key)
                # Recursively insert the child items
                self.insert_tree(tree, child_item, value)

        else:
            # Insert non-dictionary value as child item
            tree.insert(parent, "end", text=item)

    def call_check_licenses(self):
        result = check_licenses(self.unzipped_file_path)
        
        # Clear existing data in licenses_tree
        for item in self.licenses_tree.get_children():
            self.licenses_tree.delete(item)
        
        # Insert new data into licenses_tree
        for license_id in result.keys():
            self.licenses_tree.insert('', 'end', values=(license_id, result[license_id]['status'], result[license_id]['seats'], result[license_id]['file']))


    def sort_column(self, col, reverse):
        # Gather all data upfront with required fields
        data_list = []
        for item in self.log_info_tree.get_children(''):
            row_data = {
                'item': item,
                'value': self.log_info_tree.set(item, col),
                'time': self.log_info_tree.set(item, "Time"),
                'date': self.log_info_tree.set(item, "Date"),
                'line': self.log_info_tree.set(item, "Line")
            }
            # Pre-process datetime
            try:
                row_data['datetime'] = dt.strptime(
                    f"{row_data['date']} {row_data['time']}", 
                    "%Y-%m-%d %H:%M:%S.%f" if '.' in row_data['time'] else "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                row_data['datetime'] = dt.min  # fallback for invalid dates

            data_list.append(row_data)

        # Define sort keys based on column type
        if col in ('Line', 'PID', 'Session'):
            def sort_key(x):
                try:
                    # Empty values always go last regardless of sort direction
                    if not x['value']:
                        return (1, float('inf'), x['datetime'])
                    return (0, int(x['value']), x['datetime'])
                except ValueError:
                    return (1, float('inf'), x['datetime'])
        elif col in ('Date', 'Time'):
            def sort_key(x):
                # Empty dates/times always go last
                if not x['value']:
                    return (1, dt.max, float('inf'))
                return (0, x['datetime'], int(x['line']) if x['line'].isdigit() else float('inf'))
        else:
            def sort_key(x):
                # Empty values always go last
                if not x['value']:
                    return (1, '', x['datetime'])
                return (0, x['value'], x['datetime'])

        # Sort the data
        data_list.sort(key=sort_key, reverse=reverse)

        # Rearrange items
        for index, data in enumerate(data_list):
            self.log_info_tree.move(data['item'], '', index)

        # Reverse sort next time
        self.log_info_tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def search(self):
        search_values = {col: var.get() for col, var in self.search_vars.items()}
        
        if any(search_values.values()):
            filtered_data = [log for log in self.log_df.itertuples() if self.row_matches(log, search_values)]
        else:
            filtered_data = self.log_df.to_dict(orient='records')

        self.update_log_treeview(filtered_data)

    def row_matches(self, row, search_values):
        for col, search_value in search_values.items():
            if not search_value:  # Skip empty search terms
                continue
            
            search_value = search_value.lower()
            
            if search_value not in str(row.get(col, '')).lower():
                return False
        return True
    
    def toggle_all_selections(self):
        select_all = self.select_all_var.get()
        
        # Get all visible items in the treeview
        visible_items = self.log_info_tree.get_children()
        
        # If there are no visible items, return early
        if not visible_items:
            return
            
        # Determine the new key value based on the first visible item's current state
        #first_item_values = self.log_info_tree.item(visible_items[0])['values']
        new_key_value = '✓' if select_all else ''
        
        # Keep track of updated line numbers and filenames
        updated_entries = set()
        
        # Update all visible items and their corresponding log_data entries
        for item in visible_items:
            values = list(self.log_info_tree.item(item)['values'])
            line_number = values[2]      # Line column
            filename = values[1]         # Filename column
            updated_entries.add((str(line_number), filename))
            
            # Update the treeview
            values[0] = new_key_value
            self.log_info_tree.item(item, values=values)
            
            # Toggle selection based on checkbox
            if select_all:
                self.log_info_tree.selection_add(item)
            else:
                self.log_info_tree.selection_remove(item)
        
        # Update log_data for all affected entries
        for log in self.log_df.itertuples(index=False):
            if (str(log.Line), log.File) in updated_entries:
                new_values = list(log)
                new_values[0] = new_key_value
                self.log_df.loc[log.Index] = new_values
        
        # If expanded dialog exists, update its view
        if hasattr(self, 'expanded_dialog') and self.expanded_dialog:
            for item in self.expanded_dialog.log_info_tree.get_children():
                values = list(self.expanded_dialog.log_info_tree.item(item)['values'])
                if (str(values[2]), values[1]) in updated_entries:  # Check if this line/file was updated
                    values[0] = new_key_value
                    self.expanded_dialog.log_info_tree.item(item, values=values)

    def update_log_treeview(self, df):
        """Updated to handle DataFrame input while preserving selection"""
        # Store currently selected row indices before clearing the treeview
        selected_indices = {self.log_info_tree.item(iid, "text") for iid in self.log_info_tree.selection()}  # Get stored indices
        
        # Clear existing data
        for item in self.log_info_tree.get_children():
            self.log_info_tree.delete(item)

        # Add data from DataFrame to the treeview
        for index, row in df.iterrows():  # Keep index for tracking
            values = []
            for col in self.log_columns:
                if col == 'Keys':
                    # Handle Keys column which might be a list
                    keys = row.get(col, [])
                    if isinstance(keys, list):
                        values.append(' | '.join(keys))
                    else:
                        values.append(str(keys))
                else:
                    values.append(str(row.get(col, '')))

            # Insert row into Treeview, using the original DataFrame index as the iid
            self.log_info_tree.insert('', 'end', iid=str(index), text=str(index), values=values)

        # Restore selection using stored indices
        new_selected_rows = [iid for iid in self.log_info_tree.get_children() if self.log_info_tree.item(iid, "text") in selected_indices]

        if new_selected_rows:
            self.log_info_tree.selection_set(new_selected_rows)
            
            self.jump_to_context(new_selected_rows[0])


    def save_selected_logs(self):
        """Modified to work with DataFrame"""
        if self.log_df.empty:
            return
        
        selected_logs = self.log_df[self.log_df['Key'] == '✓']
        
        if selected_logs.empty:
            messagebox.showwarning("Warning", "No logs selected to save!")
            return

        # Get issue details from dialog
        result = self.create_save_logs_dialog()
        if not any(result.values()): #result['summary'] and not result['explanation'] and not result['resolution']:  # User cancelled
            return

        # Create Key Logs directory if it doesn't exist
        default_key_logs_dir = "C:\\Key Logs"
        key_logs_dir = self.config.get('key_logs_path', default_key_logs_dir)
        if key_logs_dir == "":
            key_logs_dir = default_key_logs_dir
        os.makedirs(key_logs_dir, exist_ok=True)
        
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"key_logs_{self.case_number}.txt",
            initialdir=key_logs_dir
        )
        
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write issue summary and resolution
                f.write("ISSUE SUMMARY:\n")
                f.write(f"\tIssue Type: {self.issue_type}\n")
                f.write(f"\t{result['summary']}\n\n")
                f.write("-" * 40 + "\n\n")  # Separator
                f.write("EXPLANATION:\n")
                f.write(f"\t{result['explanation']}\n\n")
                f.write("-" * 40 + "\n\n")  # Separator
                f.write("RESOLUTION:\n")
                f.write(f"\t{result['resolution']}\n\n")
                f.write("-" * 40 + "\n\n")  # Separator
                f.write("SERVER INFORMATION:\n")
                f.write(f"\tHost Version: {self.gg_version}\n")
                f.write(f"\tHost OS: {self.host_os_entry.get()}\n")
                f.write(f"\tServer Role: {self.server_role_entry.get()}\n\n")
                f.write(f"\tServer IP: {self.server_ip_entry.get()}\n\n")
                f.write("-" * 80 + "\n\n")  # Separator
                
                # Write header
                headers = [self.log_info_tree.heading(col)['text'] for col in self.log_columns]
                f.write('\t'.join(headers[1:]) + '\n')
                
                # Write data for selected items only
                for _, row in selected_logs.iterrows():
                    values = []
                    for col in self.log_columns:
                        if col == 'Keys':
                            values.append(' | '.join(row[col]))
                        else:
                            values.append(str(row[col]))
                    f.write('\t'.join(values[1:]) + '\n')
                
            messagebox.showinfo("Success", f"Selected logs saved successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs: {str(e)}")

    def create_save_logs_dialog(self):
        """Create a custom dialog for Issue Summary and Resolution"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Issue Details")
        dialog.geometry("500x550")  # Made taller to accommodate new fields
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + self.root.winfo_width()/2 - 250,
            self.root.winfo_rooty() + self.root.winfo_height()/2 - 250))

        # Issue Type frame
        issue_frame = ttk.Frame(dialog, padding="10")
        issue_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(issue_frame, text="Issue Type:").pack(side='left')
        
        issue_var = tk.StringVar()
        issue_dropdown = ttk.Combobox(
            issue_frame,
            textvariable=issue_var,
            values=GOGlobal.support_issue_types,
            state='readonly',
            width=30
        )
        issue_dropdown.pack(side='left', padx=5)
        issue_dropdown.set("Select Issue Type")

        
        # Issue Resolved checkbox
        resolved_var = tk.BooleanVar()
        resolved_frame = ttk.Frame(dialog, padding="10")
        resolved_frame.pack(fill=tk.X, padx=5)
        resolved_check = ttk.Checkbutton(
            resolved_frame, 
            text="Issue Resolved?", 
            variable=resolved_var,
            command=lambda: toggle_resolution_state(resolved_var.get())
        )
        resolved_check.pack(side='left')
        

        # Summary frame
        summary_frame = ttk.Frame(dialog, padding="10")
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(summary_frame, text="Issue Summary:").pack(anchor='w')
        summary_entry = ttk.Entry(summary_frame, width=50)
        summary_entry.pack(fill=tk.X, pady=5)

        # Explanation frame
        explanation_frame = ttk.Frame(dialog, padding="10")
        explanation_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        ttk.Label(explanation_frame, text="Explanation:").pack(anchor='w')
        explanation_text = tk.Text(explanation_frame, width=50, height=6)
        explanation_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Resolution frame
        resolution_frame = ttk.Frame(dialog, padding="10")
        resolution_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        ttk.Label(resolution_frame, text="Resolution:").pack(anchor='w')
        resolution_text = tk.Text(resolution_frame, width=50, height=6)
        resolution_text.pack(fill=tk.BOTH, expand=True, pady=5)

        def toggle_resolution_state(is_resolved):
            if is_resolved:
                resolution_text.configure(state='normal')
                resolution_text.delete('1.0', tk.END)
                resolution_text.configure(background='white')  # Visual feedback that it's editable
            else:
                resolution_text.configure(state='normal')  # Temporarily enable to modify content
                resolution_text.delete('1.0', tk.END)
                resolution_text.insert('1.0', "N/A")
                resolution_text.configure(state='disabled', background='#F0F0F0')  # Disable and gray out

        # Initialize resolution state
        toggle_resolution_state(False)  # Set initial state to disabled with N/A

        # Store the results
        result = {'summary': None, 'explanation': None, 'resolution': None}

        def on_ok():
            if issue_var.get() == "Select Issue Type":
                messagebox.showerror("Required Field", "Please select an issue type.")
                return
            
            
            if resolved_var.get() and not resolution_text.get('1.0', tk.END).strip():
                messagebox.showerror("Required Field", "You have marked the issue as resolved, but you have not provided a resolution. \nPlease provide a resolution for the issue.")
                return

            self.issue_type = issue_var.get()
            result['summary'] = summary_entry.get().strip()
            result['explanation'] = explanation_text.get('1.0', tk.END).strip()
            result['resolution'] = resolution_text.get('1.0', tk.END).strip()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        # Button frame
        button_frame = ttk.Frame(dialog, padding="15")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

        # Wait for the dialog to close
        dialog.wait_window()
        return result

    def on_treeview_resize(self, event=None):
        """Update entry widths when treeview columns are resized"""
        for col in self.log_columns:
            # Get the new column width from the main treeview
            new_width = self.log_info_tree.column(col, 'width')
            
            # Update the stored width
            self.column_widths[col] = new_width
            
            # Update the search frame column configuration
            self.search_frame.columnconfigure(
                self.log_columns.index(col),
                minsize=new_width,
                weight=1 if col == "Description" else 0
            )

    def on_search_change(self, *args):
        """Called whenever any search entry is modified. Implements debouncing to prevent
        excessive searches during rapid typing."""
        # Cancel any pending search
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        
        try:
            # Schedule a new search after 300ms
            self._search_after_id = self.after(300, self._perform_search)
        except Exception as e:
            logger.exception(f"Error scheduling search: {e}")
            # Fallback to immediate search if scheduling fails
            self._perform_search()
    
    def _perform_search(self):
        """Modified search using DataFrame operations"""
        try:
            self._search_after_id = None
            search_values = {col: var.get().lower() for col, var in self.search_vars.items() if var.get()}
            
            if not search_values:
                filtered_df = self.log_df
            else:
                # Start with full DataFrame
                mask = pd.Series(True, index=self.log_df.index)
                
                for col, search_value in search_values.items():
                    if col == 'Keys':
                        # Handle Keys column search
                        search_terms = [term.strip() for term in search_value.split(',')]
                        keys_str = self.log_df['Keys'].apply(lambda x: ' | '.join(x) if isinstance(x, list) else str(x)).str.lower()
                        terms_mask = pd.Series(True, index=self.log_df.index)
                        for term in search_terms:
                            terms_mask &= keys_str.str.contains(term, na=False)
                        mask &= terms_mask
                    else:
                        # Handle other columns
                        col_mask = self.log_df[col].astype(str).str.lower().str.contains(
                            search_value, 
                            na=False
                        )
                        mask &= col_mask
                
                filtered_df = self.log_df[mask]
            
            self._last_search = search_values
            self.update_log_treeview(filtered_df)
            
        except Exception as e:
            logger.exception(f"Error performing search: {e}")
            messagebox.showerror("Search Error", 
                               "An error occurred while searching. Please try again.")

    def toggle_key(self, event):
        """Modified to work with DataFrame"""
        item = self.log_info_tree.identify('item', event.x, event.y)
        if not item:
            return
            
        # Get current values
        values = list(self.log_info_tree.item(item)['values'])
        
        # Get the line number and filename to identify the log entry in log_data
        line_number = values[2]  # Line column
        filename = values[1]     # Filename column
        
        # Update the DataFrame
        mask = (self.log_df['Line'].astype(str) == str(line_number)) & (self.log_df['File'] == filename)
        if not mask.any():
            return
            
        # Toggle the Key value
        current_key = self.log_df.loc[mask, 'Key'].iloc[0]
        new_key = '' if current_key == '✓' else '✓'
        self.log_df.loc[mask, 'Key'] = new_key
        
        # Update the treeview
        values[0] = new_key
        self.log_info_tree.item(item, values=values)

    def _on_treeview_mousewheel(self, event, treeview):
        treeview.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def _on_treeview_shift_mousewheel(self, event, treeview):
        treeview.xview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def show_expanded_logs(self):
        dialog = ExpandedLogDialog(self)

    def load_config(self, config_path = CONFIG_FILE_PATH):
        """Load values from config file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {
                "srw_base_path": "",
                "key_logs_path": "" 
            }
        
            
        # Check and update other paths as needed
        if not config["srw_base_path"] or not os.path.exists(config["srw_base_path"]):
            logger.info("SRW base path not found. User selecting directory...")
            config["srw_base_path"] = myUtils.select_dir("Select a base directory for finding SRW .zips")

        # Check and update key_logs_path
        if not config["key_logs_path"] or not os.path.exists(config["key_logs_path"]):
            logger.info("Key logs path not found. User selecting directory...")
            config["key_logs_path"] = myUtils.select_dir("Select a directory in which to save key logs")

        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
        return config
        

# Main program
if __name__ == "__main__":
    root = tk.Tk()
    app = SRWAnalyzerApp(root)
    root.mainloop()
