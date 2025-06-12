import tkinter as tk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return

        # Get the root window (master)
        root = self.widget.winfo_toplevel()
        root_x = root.winfo_rootx()
        root_y = root.winfo_rooty()
        root_width = root.winfo_width()
        root_height = root.winfo_height()

        # Default tooltip position (relative to widget)
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 20

        # Create the tooltip window off-screen first to measure its size
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+0+0")
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("tahoma", "9", "normal"))
        label.pack(ipadx=1)
        tw.update_idletasks()  # Ensure geometry is calculated

        tip_width = tw.winfo_width()
        tip_height = tw.winfo_height()

        # Adjust x, y if tooltip would go outside the root window
        if x + tip_width > root_x + root_width:
            x = root_x + root_width - tip_width - 5
        if y + tip_height > root_y + root_height:
            y = root_y + root_height - tip_height - 5
        if x < root_x:
            x = root_x + 5
        if y < root_y:
            y = root_y + 5

        tw.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()