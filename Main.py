import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import os
from datetime import datetime as dt

# Import functions from other files
import myUtils
from ApsLogs import log_info, log_info_2
from ErrorCodes import error_code_lookup
from ApsLogs import check_licenses
from BasicInfo import get_basic_info

class FunctionCallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SRW Analysis Tool")
        self.root.geometry("1200x800")

        # Variables
        self.zip_file_path = None
        self.unzipped_file_path = None
        self.gg_version = None
        self.log_data = []
        self.log_keywords = [ # Update this default set of keywords and phrases...
            "error", 
            "failed", 
            "WERfault.exe"] 

        # Create UI elements
        self.create_widgets()
        #self.update_button_state()

        # Bind the '<Destroy>' event to the cleanup method
        self.root.bind("<Destroy>", self.cleanup)

    def cleanup(self, event):
        # Delete the temporary directory if it exists
        myUtils.remove_directory(self.unzipped_file_path)

    def create_widgets(self):
        # File upload section
        self.file_frame = ttk.Frame(root)
        self.file_frame.pack(padx=10, pady=10, fill="x")

        self.file_label = ttk.Label(self.file_frame, text="Upload File:")
        self.file_label.pack(side="left")

        self.file_entry = ttk.Entry(self.file_frame)
        self.file_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.browse_button = ttk.Button(self.file_frame, text="Browse...", command=self.browse_file)
        self.browse_button.pack(side="left", padx=5)

        self.upload_button = ttk.Button(self.file_frame, text="Upload", command=self.upload_file)
        self.upload_button.pack(side="left", padx=5)

        # Current File Section
        self.current_file_frame = ttk.Frame(root)
        self.current_file_frame.pack(padx=10, pady=10, fill="x")

        self.current_file_label = ttk.Label(self.current_file_frame, text="Current SRW:")
        self.current_file_label.pack(side="left")

        self.clear_button = ttk.Button(self.current_file_frame, text="Clear", command=self.clear_file)
        self.clear_button.pack(side="right", padx=5)

        # Create a frame for the system info and licenses section
        self.info_licenses_frame = ttk.Frame(root)
        self.info_licenses_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # System info section
        self.info_frame = ttk.Frame(self.info_licenses_frame)
        self.info_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.host_os_label = ttk.Label(self.info_frame, text="Host Operating System:")
        self.host_os_label.grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.host_os_entry = ttk.Entry(self.info_frame, width=30, state='readonly')
        self.host_os_entry.grid(row=0, column=1, padx=5, pady=2)

        self.host_version_label = ttk.Label(self.info_frame, text="GO-Global Host Version:")
        self.host_version_label.grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.host_version_entry = ttk.Entry(self.info_frame, width=30, state='readonly')
        self.host_version_entry.grid(row=1, column=1, padx=5, pady=2)

        self.client_label = ttk.Label(self.info_frame, text="Client Versions and OS:")
        self.client_label.grid(row=2, column=0, padx=5, pady=2, sticky="e")
        self.client_tree = ttk.Treeview(self.info_frame, columns=("version", "os"), show='headings', height=5)
        self.client_tree.heading("version", text="Client Version")
        self.client_tree.heading("os", text="Client OS")
        self.client_tree.grid(row=2, column=1, padx=5, pady=2)
        self.client_scrollbar = ttk.Scrollbar(self.info_frame, orient="vertical", command=self.client_tree.yview)
        self.client_scrollbar.grid(row=2, column=2, sticky='ns')
        self.client_tree.configure(yscrollcommand=self.client_scrollbar.set)

        # Licenses section as Treeview
        # Licenses section as Treeview
        self.licenses_frame = ttk.Frame(self.info_licenses_frame)
        self.licenses_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.licenses_label = ttk.Label(self.licenses_frame, text="Licenses:")
        self.licenses_label.pack(side="top", anchor="w")
        
        # Update Treeview to have 3 columns: ID, Status, # Seats
        self.licenses_tree = ttk.Treeview(self.licenses_frame, columns=("ID", "Status", "# Seats"), show='headings')
        self.licenses_tree.pack(side="left", fill="both", expand=True)
        self.licenses_scrollbar = ttk.Scrollbar(self.licenses_frame, orient="vertical", command=self.licenses_tree.yview)
        self.licenses_scrollbar.pack(side="right", fill="y")
        self.licenses_tree.configure(yscrollcommand=self.licenses_scrollbar.set)
        
        # Define headings
        self.licenses_tree.heading("ID", text="ID")
        self.licenses_tree.heading("Status", text="Status")
        self.licenses_tree.heading("# Seats", text="# Seats")

        # Define column widths
        self.licenses_tree.column("ID", width=100)
        self.licenses_tree.column("Status", width=100)
        self.licenses_tree.column("# Seats", width=100)

        # Log messages section
        self.logs_frame = ttk.LabelFrame(root, text="Log Messages")
        self.logs_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.search_frame = ttk.Frame(self.logs_frame)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)

        self.search_vars = {}
        columns = ["file", "#", "date", "time", "keys", "description"]
        for col in columns:
            self.lbl = ttk.Label(self.search_frame, text=col)
            self.lbl.pack(side=tk.LEFT, padx=5)
            self.search_vars[col] = tk.StringVar()
            self.ent = ttk.Entry(self.search_frame, textvariable=self.search_vars[col])
            self.ent.pack(side=tk.LEFT, padx=5)

        # Later change this self.search to be triggered upon update of any search bar...
        self.search_button = ttk.Button(self.search_frame, text="Search", command=self.search)
        self.search_button.pack(side=tk.LEFT, padx=5)

        # Create a Treeview widget within this frame
        self.log_info_tree = ttk.Treeview(self.logs_frame, columns=columns, show='headings')
        self.log_info_tree.pack(expand=True, fill=tk.BOTH)
        self.log_scrollbar_x = ttk.Scrollbar(self.log_info_tree, orient=tk.HORIZONTAL, command=self.log_info_tree.xview)
        self.log_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.log_info_tree.configure(xscrollcommand=self.log_scrollbar_x.set)

        # Define headings
        for col in columns:
            self.log_info_tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col, False))

        # Define column widths
        self.log_info_tree.column("file", width=100)
        self.log_info_tree.column("#", width=20)
        self.log_info_tree.column("date", width=50)
        self.log_info_tree.column("time", width=50)
        self.log_info_tree.column("keys", width=50)
        self.log_info_tree.column("description", width=500)

    def clear_file(self):
        self.zip_file_path = None
        self.unzipped_file_path = None

        # Clear the file entry
        self.file_entry.delete(0, tk.END)
        self.current_file_label.config(text="Current SRW:")

        # Clear the host version and OS entries
        self.host_version_entry.config(state='normal')
        self.host_version_entry.delete(0, tk.END)
        self.host_version_entry.config(state='readonly')
        self.host_os_entry.config(state='normal')
        self.host_os_entry.delete(0, tk.END)
        self.host_os_entry.config(state='readonly')

        # Clear the client Treeview
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        # Clear the licenses Treeview
        for item in self.licenses_tree.get_children():
            self.licenses_tree.delete(item)

        # Clear the log info Treeview
        for item in self.log_info_tree.get_children():
            self.log_info_tree.delete(item)

        # Clear the search entries
        for var in self.search_vars.values():
            var.set("")

        # Remove the temporary directory
        myUtils.remove_directory(self.unzipped_file_path)
        self.unzipped_file_path = ""
        
    
    def onSelectLogMessage(self, event):
        item_id = self.logs_tree.selection()[0]
        item_text = self.logs_tree.item(item_id, "text")

        popup = tk.Toplevel(self.root)
        popup.title("Log Message")
        tk.Label(popup, text=item_text, wraplength=400).pack(pady=10, padx=10)
        tk.Button(popup, text="Close", command=popup.destroy).pack(pady=5)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)
            self.upload_file()

    def upload_file(self):
        file_path = self.file_entry.get()
        if file_path.endswith(".zip"):
            '''
            # Clear existing data
            self.zip_file_path = None
            self.unzipped_file_path = None
            self.gg_version = None

            # Clear the host version and OS entries
            self.host_version_entry.config(state='normal')
            self.host_version_entry.delete(0, tk.END)
            self.host_version_entry.config(state='readonly')
            self.host_os_entry.config(state='normal')
            self.host_os_entry.delete(0, tk.END)
            self.host_os_entry.config(state='readonly')

            # Clear the client Treeview
            for item in self.client_tree.get_children():
                self.client_tree.delete(item)

            # Clear the licenses Treeview
            for item in self.licenses_tree.get_children():
                self.licenses_tree.delete(item)

            # Clear the log info Treeview
            for item in self.log_info_tree.get_children():
                self.log_info_tree.delete(item)

            # Clear the search entries
            for var in self.search_vars.values():
                var.set("")

            # Remove the temporary directory
            myUtils.remove_directory(self.unzipped_file_path)
            self.unzipped_file_path = ""
            '''
            
            # Set new file path
            self.zip_file_path = file_path
            self.current_file_label.config(text=f"Uploaded file: {file_path.split('/')[-1]}")

            # Create temporary directory of extracted files
            myUtils.remove_directory(self.unzipped_file_path) # remove the unzipped folder before replacing it
            self.unzipped_file_path = myUtils.extract_zip(self.zip_file_path)

            # Get all the info you need
            self.call_basic_info()
            self.call_log_info_2()
            self.call_check_licenses()
        else:
            messagebox.showerror("Error", "Please select a valid .zip file.")

    def update_button_state(self):
        state = tk.NORMAL if self.zip_file_path else tk.DISABLED
        #self.btn_log_info.config(state=state)
        #self.btn_error_code_lookup.config(state=tk.DISABLED if self.gg_version is None else state)
        #self.btn_check_licenses.config(state=state)
        #self.remove_button.config(state=state if self.zip_file_path else tk.DISABLED)
        self.browse_button.config(state=state)
        self.clear_button.config(state=state if self.zip_file_path else tk.DISABLED)

    def call_basic_info(self):
        # Enable writing to the entries
        self.host_version_entry.config(state='normal')
        self.host_os_entry.config(state='normal')

        # Update the values
        basics = get_basic_info(self.unzipped_file_path)
        self.gg_version = basics['hostVersion']
        
        # Update the entries
        self.host_version_entry.delete(0, tk.END)
        self.host_version_entry.insert(0, self.gg_version)
        self.host_os_entry.delete(0, tk.END)
        self.host_os_entry.insert(0, basics['hostOS'])

        # Clear existing data in client_tree
        for item in self.client_tree.get_children():
            self.client_tree.delete(item)

        # Insert new data into client_tree, ensuring uniqueness
        unique_entries = set()
        for client_version, client_os in basics['clientVersions']:
            entry = (client_version, client_os)
            if entry not in unique_entries:
                unique_entries.add(entry)
                self.client_tree.insert('', 'end', values=entry)

        # Disable writing to the entries
        self.host_version_entry.config(state='readonly')
        self.host_os_entry.config(state='readonly')
   
    def call_log_info(self):
        log_info_result = log_info(self.unzipped_file_path)

        # Insert the dictionary keys and values into the Treeview
        self.insert_tree(self.log_info_tree, "", log_info_result)
        #self.update_button_state()

    def call_log_info_2(self):
        log_info_result = log_info_2(self.unzipped_file_path, self.log_keywords)
        self.log_data = log_info_result
        self.update_log_treeview(log_info_result)
        #self.insert_tree(self.log_info_tree, "", log_info_result)#[0])
        #self.insert_tree(self.flagged_log_tree, "", log_info_result[1])

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
    
    def call_error_code_lookup(self):        
        default_error_code_file_path = "C:\\Users\\Matt\\Documents\\Tools\\Code Kits\\6.3.1.33505\\errorCodeKit.zip"
        error_code_file_path = "C:\\Users\\Matt\\Documents\\Tools\\Code Kits\\"
        for folder in os.listdir(error_code_file_path):
            if self.gg_version in folder:
                error_code_file_path = os.path.join(error_code_file_path, folder)
        
        files = os.listdir(error_code_file_path)
        if "errorCodeKit.zip" in files:
            error_code_file_path = os.path.join(error_code_file_path, "errorCodeKit.zip")
        else:
            error_code_file_path = default_error_code_file_path

        if error_code_file_path.endswith(".zip"):
            result = error_code_lookup(error_code_file_path)
            #messagebox.showinfo("ErrorCodes Output", result)
            # Insert the dictionary keys and values into the Treeview
            self.insert_tree(self.errorCodes_info_tree, "", result)
        else:
            messagebox.showerror("Error", "Please select a valid .zip file.")

    def call_check_licenses(self):
        result = check_licenses(self.unzipped_file_path)
        
        # Clear existing data in licenses_tree
        for item in self.licenses_tree.get_children():
            self.licenses_tree.delete(item)
        
        # Insert new data into licenses_tree
        for license_id in result.keys():
            self.licenses_tree.insert('', 'end', values=(license_id, result[license_id]['status'], result[license_id]['seats']))

    def update_treeview(self, data):
        # Clear existing data
        for item in self.log_info_tree.get_children():
            self.log_info_tree.delete(item)
        # Insert new data
        for log in data:
            self.log_info_tree.insert("", "end", values=log)

    def update_log_treeview(self, data):
        # Clear existing data
        for item in self.log_info_tree.get_children():
            self.log_info_tree.delete(item)

        # Add new data to the treeview
        for entry in data:
            values = []
            for col in self.log_info_tree['columns']:
                if col == 'keys':
                    values.append(' | '.join(entry.get(col, [])))  # Convert list to comma-delimited string
                else:
                    values.append(entry.get(col, ''))
            self.log_info_tree.insert('', 'end', text=entry.get('#', ''), values=values)
    

    def sort_column(self, col, reverse):
        # Get the list of data in the column
        data_list = [(self.log_info_tree.set(item, col), item) for item in self.log_info_tree.get_children('')]

        # If the column is "Date" or "Time", we need to convert the data to the appropriate type for sorting
        if col == "Date":
            data_list.sort(key=lambda x: dt.strptime(x[0], "%Y-%m-%d"), reverse=reverse)
        elif col == "Time":
            data_list.sort(key=lambda x: dt.strptime(x[0], "%H:%M:%S"), reverse=reverse)
        else:
            data_list.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, item) in enumerate(data_list):
            self.log_info_tree.move(item, '', index)

        # Reverse sort next time
        self.log_info_tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def search(self):
        search_values = {col: var.get() for col, var in self.search_vars.items()}
        filtered_data = [log for log in self.log_data if self.row_matches(log, search_values)]
        self.update_log_treeview(filtered_data)

    def row_matches(self, row, search_values):
        for col in self.log_info_tree["columns"]:
            if col == 'keys':
                if search_values[col] and search_values[col] not in (" | ").join(row['keys']):
                    return False
            else:
                if search_values[col] and search_values[col] not in str(row[col]):
                    return False
        return True

# Main program
if __name__ == "__main__":
    root = tk.Tk()
    app = FunctionCallerApp(root)
    root.mainloop()
