import tkinter as tk
from tkinter import messagebox, filedialog
import os

# Import functions from other files
import myUtils
from ApsLogs import log_info
from ErrorCodes import error_code_lookup
from Licenses import check_licenses

class FunctionCallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Function Caller")

        self.zip_file_path = None
        self.unzipped_file_path = None
        self.gg_version = None

        # Create UI elements
        self.create_widgets()
        self.update_button_state()

        # Bind the '<Destroy>' event to the cleanup method
        self.root.bind("<Destroy>", self.cleanup)

    def cleanup(self, event):
        # Delete the temporary directory if it exists
        myUtils.remove_directory(self.unzipped_file_path)

    def create_widgets(self):
        self.upload_label = tk.Label(self.root, text="Upload a .zip file:")
        self.upload_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 2))

        # Create a frame to hold the file entry, browse button, and upload button in one line
        self.file_frame = tk.Frame(self.root)
        self.file_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5)

        self.file_entry = tk.Entry(self.file_frame, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5)

        self.browse_button = tk.Button(self.file_frame, text="Browse...", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        self.upload_button = tk.Button(self.file_frame, text="Upload", command=self.upload_file)
        self.upload_button.pack(side=tk.LEFT, padx=5)

        self.file_name_label = tk.Label(self.root, text="")
        self.file_name_label.grid(row=2, column=0, columnspan=3, pady=5, padx=10)

        self.remove_button = tk.Button(self.root, text="Remove", command=self.remove_file, state=tk.DISABLED)
        self.remove_button.grid(row=3, column=0, columnspan=3, pady=5, padx=10)

        # Create a frame to hold the function buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.grid(row=4, column=0, columnspan=3, pady=10, padx=10)

        # Create buttons with the same width
        button_width = 20

        self.btn_log_info = tk.Button(self.button_frame, text="Call log_info", command=self.call_log_info, state=tk.DISABLED, width=button_width)
        self.btn_log_info.pack(pady=5)

        self.btn_error_code_lookup = tk.Button(self.button_frame, text="Call error_code_lookup", command=self.call_error_code_lookup, state=tk.DISABLED, width=button_width)
        self.btn_error_code_lookup.pack(pady=5)

        self.btn_check_licenses = tk.Button(self.button_frame, text="Call check_licenses", command=self.call_check_licenses, state=tk.DISABLED, width=button_width)
        self.btn_check_licenses.pack(pady=5)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)

    def upload_file(self):
        file_path = self.file_entry.get()
        if file_path.endswith(".zip"):
            self.zip_file_path = file_path
            self.file_name_label.config(text=f"Uploaded file: {file_path.split('/')[-1]}")
            
            # Create temporary directory of extracted filed from  
            self.unzipped_file_path = myUtils.extract_zip(self.zip_file_path)

            self.update_button_state()
        else:
            messagebox.showerror("Error", "Please select a valid .zip file.")

    def remove_file(self):
        self.zip_file_path = None
        self.gg_version = None
        self.file_entry.delete(0, tk.END)
        self.file_name_label.config(text="")

        # Delete the temporary directory
        if self.unzipped_file_path and os.path.exists(self.unzipped_file_path):
            try:
                myUtils.remove_directory(self.unzipped_file_path)
            except Exception as e:
                print(f"Error removing directory {self.unzipped_file_path}: {e}")

        self.update_button_state()

    def update_button_state(self):
        state = tk.NORMAL if self.zip_file_path else tk.DISABLED
        self.btn_log_info.config(state=state)
        self.btn_error_code_lookup.config(state=tk.DISABLED if self.gg_version is None else state)
        self.btn_check_licenses.config(state=state)
        self.remove_button.config(state=state if self.zip_file_path else tk.DISABLED)

    def call_log_info(self):
        log_info_result = log_info(self.unzipped_file_path)
        self.gg_version = log_info_result.get("gg_version")
        messagebox.showinfo("ApsLogs Output", f"gg_version: {self.gg_version}\nos_version: {log_info_result['os_version']}\nbuild_number: {log_info_result['build_number']}\npotential_issues: {log_info_result['potential_issues']}")
        self.update_button_state()

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
            messagebox.showinfo("ErrorCodes Output", result)
        else:
            messagebox.showerror("Error", "Please select a valid .zip file.")

    def call_check_licenses(self):
        result = check_licenses(self.unzipped_file_path)
        messagebox.showinfo("Licenses Output", result)

# Main program
if __name__ == "__main__":
    root = tk.Tk()
    app = FunctionCallerApp(root)
    root.mainloop()
