import tkinter as tk
from datetime import datetime as dt
from tkinter import messagebox, ttk
from venv import logger

import pandas as pd


class ExpandedLogDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent.root)
        self.dialog.title("Expanded Log View")
        self.parent = parent
        
        # Set the window to full screen
        try:
            # Get DPI scaling from Windows
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()  # Tell Windows we are DPI aware
            
            # Try Windows-specific maximize
            self.dialog.state('zoomed')
        except:
            # Fallback for other operating systems
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            window_width = screen_width - 20
            window_height = screen_height - 40
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Create main container frame
        self.container = ttk.Frame(self.dialog)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create search frame
        self.search_frame = ttk.Frame(self.container)
        self.search_frame.pack(fill="x", padx=5, pady=5)
        
        # Create labels for column headers
        for col in parent.log_columns:
            lbl = ttk.Label(self.search_frame, text=col)
            lbl.grid(row=0, column=parent.log_columns.index(col), padx=5, pady=2, sticky="w")
            
        # Configure search frame columns
        for col in parent.log_columns:
            self.search_frame.columnconfigure(
                parent.log_columns.index(col),
                minsize=parent.column_widths[col],
                weight=1 if col == "Description" else 0
            )
            
        # Create search entries
        self.search_vars = {}
        self.search_entries = {}
        for col in parent.log_columns:
            self.search_vars[col] = tk.StringVar()
            self.search_vars[col].trace_add('write', self.on_search_change)
            entry = ttk.Entry(
                self.search_frame,
                textvariable=self.search_vars[col]
            )
            self.search_entries[col] = entry
            entry.grid(row=1, column=parent.log_columns.index(col), padx=5, pady=2, sticky="ew")
            
            # Set entry width
            pixelsPerChar = 10
            entry.configure(width=int(parent.column_widths[col] / pixelsPerChar))
            
        # Add frame for controls right after search frame
        self.control_frame = ttk.Frame(self.container)
        self.control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add select all checkbox
        self.select_all_var = tk.BooleanVar()
        self.select_all_checkbox = ttk.Checkbutton(
            self.control_frame,
            text="Select All",
            variable=self.select_all_var,
            command=self.toggle_all_selections
        )
        self.select_all_checkbox.pack(side=tk.LEFT, padx=5)
        
        # Add save selected logs button
        self.save_button = ttk.Button(
            self.control_frame,
            text="Save Selected Logs",
            command=self.save_selected_logs
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Create tree frame
        self.tree_frame = ttk.Frame(self.container)
        self.tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create treeview
        self.log_info_tree = ttk.Treeview(self.tree_frame, columns=parent.log_columns, show='headings')
        
        # Create scrollbars
        self.scrollbar_y = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.log_info_tree.yview)
        self.scrollbar_y.pack(side="right", fill="y")
        
        self.scrollbar_x = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.log_info_tree.xview)
        self.scrollbar_x.pack(side="bottom", fill="x")
        
        # Configure treeview
        self.log_info_tree.configure(
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set
        )
        self.log_info_tree.pack(side="left", fill="both", expand=True)
        
        # Configure columns
        for col in parent.log_columns:
            self.log_info_tree.heading(
                col, 
                text=col,
                command=lambda _col=col: self.sort_column(_col, False)
            )
            self.log_info_tree.column(
                col,
                width=parent.column_widths[col],
                minwidth=10,
                stretch=True if col == "Description" else False
            )
            
        # Copy data from parent treeview
        self.copy_treeview_data(parent.log_df)
        
        # Bind double-click to toggle key
        self.log_info_tree.bind("<Double-1>", self.toggle_key)
        
        # Store parent's log data
        self.log_df = parent.log_df

        # Add this to your existing initialization
        self._search_after_id = None
        self._last_search = None
        
    def copy_treeview_data(self, source_df):
        # Clear existing items
        for item in self.log_info_tree.get_children():
            self.log_info_tree.delete(item)

        # Add new data to the treeview
        for _, row in source_df.iterrows():
            values = []
            for col in self.log_info_tree['columns']:
                if col == 'Keys':
                    values.append(' | '.join(row.get(col, [])))
                else:
                    values.append(str(row.get(col, '')))
            
            item = self.log_info_tree.insert('', 'end', values=values)

        # Get selected item from parent treeview and jump to corresponding item
        selected = self.parent.log_info_tree.selection()
        if selected:
            parent_values = self.parent.log_info_tree.item(selected[0])['values']
            # Find matching item in dialog's treeview
            for item in self.log_info_tree.get_children():
                if self.log_info_tree.item(item)['values'] == parent_values:
                    self.jump_to_context(item)
                    break

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
     
    def on_search_change(self, *args):
        """Called whenever any search entry is modified. Implements debouncing to prevent
        excessive searches during rapid typing."""
        # Cancel any pending search
        if self._search_after_id:
            self.dialog.after_cancel(self._search_after_id)
        
        try:
            # Schedule a new search after 300ms
            self._search_after_id = self.dialog.after(300, self._perform_search)
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

    def row_matches(self, row, search_values):
        if not self.log_info_tree.get_children():
            return False
        
        for col, search_value in search_values.items():
            if not search_value:  # Skip empty search terms
                continue
            
            search_value = search_value.lower()
            
            if search_value not in str(row.get(col, '')).lower():
                return False
        return True

    def jump_to_context(self, rowID: int):
        if not rowID:
            return

        self.log_info_tree.see(rowID)

        # Only set selection if the row we are jumping to is not already in the selection
        if rowID not in self.log_info_tree.selection():  
            self.log_info_tree.selection_set(rowID)  

    def toggle_key(self, event):
        """Modified to work with DataFrame"""
        item = self.log_info_tree.identify('item', event.x, event.y)
        if not item:
            return
            
        # Get current values
        values = list(self.log_info_tree.item(item)['values'])
        
        # Get the line number and filename to identify the log entry in parent's log_data
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

    def toggle_all_selections(self):
        """Modified to work with DataFrame"""
        select_all = self.select_all_var.get()
        
        # Get all visible items in the treeview
        visible_items = self.log_info_tree.get_children()
        
        # If there are no visible items, return early
        if not visible_items:
            return
            
        new_key_value = '✓' if select_all else ''
        
        # Update all visible items
        visible_lines = []
        visible_files = []
        for item in visible_items:
            values = list(self.log_info_tree.item(item)['values'])
            visible_lines.append(str(values[2]))  # Line column
            visible_files.append(values[1])       # File column
            
            # Update treeview
            values[0] = new_key_value
            self.log_info_tree.item(item, values=values)
        
        # Update DataFrame for visible entries
        mask = (self.log_df['Line'].astype(str).isin(visible_lines)) & (self.log_df['File'].isin(visible_files))
        self.log_df.loc[mask, 'Key'] = new_key_value

    def save_selected_logs(self):
        """Modified to work with DataFrame"""
        selected_logs = self.log_df[self.log_df['Key'] == '✓']
        
        if selected_logs.empty:
            messagebox.showwarning("Warning", "No logs selected to save!")
            return

        # Call parent's save_selected_logs method to maintain consistent behavior
        self.parent.save_selected_logs()

    '''    
    def update_log_treeview(self, df):
        # Clear existing items
        for item in self.log_info_tree.get_children():
            self.log_info_tree.delete(item)

        # Add data from DataFrame to the treeview
        for _, row in df.iterrows():
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
            
            self.log_info_tree.insert('', 'end', values=values)
    '''

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
            for col in self.parent.log_columns:
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
     