from functools import wraps
import tkinter as tk
from tkinter import filedialog
import zipfile
import re
import json
import os
import requests



def https_get(url: str):
    try:
        response_txt = requests.get(url)
        response_json = response_txt.json()
        response_dict = convert_response_to_dict(response_json)
        return response_dict
    except requests.RequestException as e:
        print(f"There was an exception in GET request to {url}:")
        print(f"\tException: {e}")
        return {}
    
def https_get_txt(url: str):
    try:
        return requests.get(url)
    except requests.RequestException as e:
        print(f"There was an exception in GET request to {url}:")
        print(f"\tException: {e}")
        return None
    
def print_nested_dict(dictionary, indent=0):
    if isinstance(dictionary, dict):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                print("  " * indent + f"{key}:")
                print_nested_dict(value, indent + 1)
            else:
                print("  " * indent + f"{key}: {value}")
    else:
        print("printed_nested_dict() was called on a non-dictionary object... just printing the object:")
        print(dictionary)

def select_file(fileType = "Any", fileTypeExt = "*.*", initialDir = "C:\\Test"):
    """
    Opens a file dialog for the user to select a file.
    
    Params:
        str: fileType - what type of file would you like to instruct users to enter?
        str: fileTypeExt - what is the extension of the file type you are looking for? 
        str: initialDir - the default directory for the dialog to open up to

    Returns:
        str: The path to the selected file.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(
        initialdir=initialDir,
        title=f"Select a file of type {fileType}",
        filetypes=[(f"{fileType} Files", fileTypeExt)]
    )

    root.destroy()

    return file_path

def select_dir(header="Select a directory", initialDir="C:\\Test"):
    """
    Opens a directory dialog for the user to select a directory.
    
    Params:
        str: initialDir - the default directory for the dialog to open up to

    Returns:
        str: The path to the selected directory.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    dir_path = filedialog.askdirectory(
        initialdir=initialDir,
        title=header
    )

    root.destroy()

    return dir_path.replace("/", "\\")

def select_zip_file():
    """
    Opens a file dialog for the user to select a .zip file.
    
    Returns:
        str: The path to the selected .zip file.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(
        title="Select a ZIP file",
        filetypes=[("ZIP files", "*.zip")]
    )
    return file_path

def extract_zip(path: str, toPath = "C:\\temp_zip_reader"):
    # Extract all files to a temp folder so we can directly see the license file
    if not os.path.exists(toPath):
        os.mkdir(toPath)
        if not os.path.exists(toPath):
            return ""

    with zipfile.ZipFile(path, 'r') as zip_ref:
        zip_ref.extractall(toPath)

    return toPath

# This one may be dangerous... it could be used on something it shouldn't... 
# can I limit this somehow to make sure it only works if the directory has been created during the execution of a project, or even just in the last X minutes?
def remove_directory(dir_path):
    """Recursively delete a directory and all its contents."""
    try:
        if dir_path and os.path.exists(dir_path):
            # Iterate over all the entries in the directory
            for entry in os.listdir(dir_path):
                entry_path = os.path.join(dir_path, entry)
                # Check if it is a directory and recurse
                if os.path.isdir(entry_path):
                    remove_directory(entry_path)
                else:
                    # Remove the file
                    os.remove(entry_path)
            # Remove the now-empty directory
            os.rmdir(dir_path)
    except:
        raise RuntimeError(f"Failed to remove directory {dir_path}")

def copy_file_contents(path, newPath):
    try:
        with open(path, 'r') as lic_file:
            contents = lic_file.read()
        with open(newPath, 'w') as txt_file:
            txt_file.write(contents)
    except Exception as e:
        with open(newPath, 'w') as txt_file:
            txt_file.write(f"Error copying license file {path} to {newPath}.")

def convert_response_to_dict(response_txt):
    """
    Converts a JSON response string to a dictionary.
    
    Args:
        response_txt (str): The response text from the HTTP request.
    
    Returns:
        dict: The response text converted to a dictionary.
    """
    try:
        response_txt = re.sub(r'(\w+):', r'"\1":', response_txt)  # Replace single quotes with double quotes to ensure the JSON format
        license_dict = json.loads(response_txt)  # Convert the string to a dictionary
        return license_dict
    except json.JSONDecodeError as e:
        print(f"Error converting response to dict: {e}")
        return {}

def protect_network_path(func):
        '''
        The point of this is to prevent certain functions (e.g. unzip_files()) from running on network folders.
        '''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Would the check for "//" be enough to ensure we can't run an operation on a network path?
            for arg in args:
                if isinstance(arg, str) and arg.startswith("//"):
                     raise PermissionError(f"Operation not allowed on protected path: {arg}")

            return func(self, *args, **kwargs)
        return wrapper

@protect_network_path
def unzip_path(path):
    """
    Ensure that all zip files in the given path are unzipped.

    Returns:
        True - Succeeded.
        False - Failed to find path.
    """
    path_parts = path.split(os.sep)
    current_path = path_parts[0] + os.sep
    path_parts = path_parts[1:]
    

    for part in path_parts:
        current_path = os.path.join(current_path, part)
        if not os.path.exists(current_path):
            zip_path = current_path + ".zip"
            if os.path.isfile(zip_path) :
                # Unzip the file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(os.path.dirname(current_path))
            else:
                return False

    return True

def main():
    #Testing
    path = select_file()
    print(path)
    path = select_file("HTML", ".html")

if __name__ == "__main__":
    main()