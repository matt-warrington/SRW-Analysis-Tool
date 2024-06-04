import myUtils
import zipfile
from tkinter import simpledialog, messagebox

def extract_error_codes(zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # Extract only the ErrorCodes.txt file
        for file_info in zip_ref.infolist():
            if file_info.filename.endswith("ErrorCodes.txt"):
                with zip_ref.open(file_info.filename) as file:
                    return file.read().decode('utf-8')
    return None

def parse_error_codes(content):
    error_dict = {}
    lines = content.splitlines()
    for line in lines:
        if '=' in line:
            code, description = map(str.strip, line.split('=', 1))
            try:
                code = int(code)
            except ValueError:
                # Skip if the code cannot be converted to an integer
                continue
            error_dict[code] = description
    return error_dict

def get_error_code_range(error_dict):
    codes = list(error_dict.keys())
    if codes:
        return min(codes), max(codes)
    return None, None

def error_code_lookup(zip_file_path):
    content = extract_error_codes(zip_file_path)
    if not content:
        messagebox.showerror("Error", "ErrorCodes.txt not found in the selected zip file.")
        return
    
    error_dict = parse_error_codes(content)
    
    if not error_dict:
        messagebox.showerror("Error", "No error codes found in ErrorCodes.txt.")
        return
    
    min_code, max_code = get_error_code_range(error_dict)
    
    while True:
        try:
            error_code = simpledialog.askstring("Input", f"Enter an error code (range: {min_code} to {max_code}):")
            if not error_code:
                messagebox.showinfo("Information", "Thanks for using the error code lookup tool!")
                break
            error_code = int(error_code)
            description = error_dict.get(error_code)
            if description:
                messagebox.showinfo("Error Description", f"Error code {error_code}: {description}")
            else:
                messagebox.showerror("Error", f"Error code {error_code} not found.")
        except ValueError:
            messagebox.showerror("Error", "Invalid input! Please enter a valid integer error code.")

# Main function to be called from another script
def main():
    zip_file_path = myUtils.select_file("ErrorCodeKit", ".zip")
    if zip_file_path:
        error_code_lookup(zip_file_path)

if __name__ == "__main__":
    main()
