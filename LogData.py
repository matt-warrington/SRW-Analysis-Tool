import os
from tkinter import filedialog
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
import GOGlobal

class LogData:
    def __init__(self, log_file=None):
        self.log_file = log_file
        self.log_columns = [
            "Key",
            "File",
            "Line",
            "Date",
            "Time",
            "User",
            "Server",
            "Process",
            "PID",
            "Session",
            "Description"
        ]
        # Initialize an empty DataFrame with the correct columns
        self.log_df = pd.DataFrame(columns=self.log_columns)

    def load_from_records(self, records):
        """Load log data from a list of dicts (records)."""
        self.log_df = pd.DataFrame(records, columns=self.log_columns)
        # Ensure all columns exist
        for col in self.log_columns:
            if col not in self.log_df.columns:
                self.log_df[col] = ""
        return self.log_df

    def add_log(self, log_entry):
        """Add a single log entry (dict) to the DataFrame."""
        self.log_df = pd.concat([self.log_df, pd.DataFrame([log_entry], columns=self.log_columns)], ignore_index=True)

    def clear(self):
        """Clear all log data."""
        self.log_df = pd.DataFrame(columns=self.log_columns)

    def get_selected_logs(self):
        """Return DataFrame of logs where Key == '✓'."""
        if 'Key' not in self.log_df.columns:
            self.log_df['Key'] = ''
        return self.log_df[self.log_df['Key'] == '✓']

    def set_key(self, index, value='✓'):
        """Set the Key column for a given index."""
        if 'Key' not in self.log_df.columns:
            self.log_df['Key'] = ''
        self.log_df.at[index, 'Key'] = value

    def unset_key(self, index):
        """Unset the Key column for a given index."""
        if 'Key' not in self.log_df.columns:
            self.log_df['Key'] = ''
        self.log_df.at[index, 'Key'] = ''

    def to_dicts(self):
        """Return the log data as a list of dicts."""
        return self.log_df.to_dict(orient='records')

    def save_to_csv(self, path):
        """Save the DataFrame to a CSV file."""
        self.log_df.to_csv(path, index=False)

    def load_from_csv(self, path):
        """Load the DataFrame from a CSV file."""
        self.log_df = pd.read_csv(path)
        # Ensure all columns exist
        for col in self.log_columns:
            if col not in self.log_df.columns:
                self.log_df[col] = ""
        return self.log_df

    def setDateTime(self):
        """Create a DateTime column from Date and Time columns."""
        if 'Date' in self.log_df.columns and 'Time' in self.log_df.columns:
            self.log_df['DateTime'] = pd.to_datetime(
                self.log_df['Date'].astype(str) + ' ' + self.log_df['Time'].astype(str),
                format='%Y-%m-%d %H:%M:%S.%f',
                errors='coerce'
            )
        else:
            self.log_df['DateTime'] = pd.NaT

    def save_selected_logs(self, parent):
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
            initialfile=f"key_logs_{parent.case_number}.txt",
            initialdir=key_logs_dir
        )
        
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write issue summary and resolution
                f.write("ISSUE SUMMARY:\n")
                f.write(f"\tIssue Type: {result['issue_type']}\n")
                f.write(f"\t{result['summary']}\n\n")
                f.write("-" * 40 + "\n\n")  # Separator
                f.write("EXPLANATION:\n")
                f.write(f"\t{result['explanation']}\n\n")
                f.write("-" * 40 + "\n\n")  # Separator
                f.write("RESOLUTION:\n")
                f.write(f"\t{result['resolution']}\n\n")
                f.write("-" * 40 + "\n\n")  # Separator
                f.write("SERVER INFORMATION:\n")
                f.write(f"\tHost Version: {parent.gg_version}\n")
                f.write(f"\tHost OS: {parent.host_os_entry.get()}\n")
                f.write(f"\tServer Role: {parent.server_role_entry.get()}\n\n")
                f.write(f"\tServer IP: {parent.server_ip_entry.get()}\n\n")
                f.write("-" * 80 + "\n\n")  # Separator
                
                # Write header
                headers = list(self.log_columns)
                f.write('\t'.join(headers[1:]) + '\n')
                
                # Write data for selected items only
                for _, row in selected_logs.iterrows():
                    values = []
                    for col in self.log_columns:
                        values.append(str(row[col]))
                    f.write('\t'.join(values[1:]) + '\n')
                
            messagebox.showinfo("Success", f"Selected logs saved successfully to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs: {str(e)}")


    def create_save_logs_dialog(self, parent):
        """Create a custom dialog for Issue Summary and Resolution. Returns a dict."""
        dialog = tk.Toplevel(parent)
        dialog.title("Issue Details")
        dialog.geometry("500x550")
        dialog.resizable(True, True)
        dialog.transient(parent)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()//2 - 250,
            parent.winfo_rooty() + parent.winfo_height()//2 - 250))

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
                resolution_text.configure(background='white')
            else:
                resolution_text.configure(state='normal')
                resolution_text.delete('1.0', tk.END)
                resolution_text.insert('1.0', "N/A")
                resolution_text.configure(state='disabled', background='#F0F0F0')

        toggle_resolution_state(False)

        result = {'issue_type': None, 'summary': None, 'explanation': None, 'resolution': None}

        def on_ok():
            if issue_var.get() == "Select Issue Type":
                messagebox.showerror("Required Field", "Please select an issue type.")
                return
            if resolved_var.get() and not resolution_text.get('1.0', tk.END).strip():
                messagebox.showerror("Required Field", "You have marked the issue as resolved, but you have not provided a resolution. \nPlease provide a resolution for the issue.")
                return
            result['issue_type'] = issue_var.get()
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

        dialog.wait_window()
        return result