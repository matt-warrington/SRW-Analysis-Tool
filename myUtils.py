from functools import wraps
import tkinter as tk
from tkinter import filedialog
import zipfile
import re
import json
import os
import requests



def https_get(url: str):
    """Perform a HTTP GET request and return the JSON payload.

    The original implementation simply returned ``requests``' response object
    and expected callers to decode the JSON themselves.  By doing the error
    checking and decoding here we provide a much safer and easier to use
    helper.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()  # make HTTP errors obvious to the caller
        try:
            return response.json()
        except ValueError as e:
            # Response wasn't valid JSON; log the issue and return an empty dict
            print(f"Failed to decode JSON from {url}: {e}")
            return {}
    except requests.RequestException as e:
        print(f"There was an exception in GET request to {url}:")
        print(f"\tException: {e}")
        return {}


def https_get_txt(url: str):
    """Perform a HTTP GET request and return the plain text payload.

    Returning only the ``Response`` object left the caller responsible for
    checking status codes and extracting text.  Handling those concerns here
    keeps network access in one place and avoids duplicated error handling.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
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
    # Ensure the hidden root window is properly destroyed to avoid
    # orphaned Tk instances which can cause resource leaks in larger
    # applications.
    root.destroy()
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
    """Recursively delete a directory and all its contents with safeguards.

    The previous implementation relied on a broad ``except`` block that masked
    the original error and could happily attempt to remove sensitive locations
    such as the working directory if called with an empty string.  This version
    exits early for empty or missing paths, refuses to delete a small set of
    critical directories, and raises exceptions that preserve the original
    error context for easier debugging.
    """

    if not dir_path:
        return

    dir_path = os.path.abspath(dir_path)

    # Prevent accidental deletion of critical locations
    protected_paths = {
        os.path.abspath(os.sep),              # root
        os.path.expanduser("~"),             # user home
        os.path.abspath(os.getcwd()),         # current working directory
    }
    if dir_path in protected_paths:
        raise ValueError(f"Refusing to remove protected directory: {dir_path}")

    if not os.path.exists(dir_path):
        return

    try:
        with os.scandir(dir_path) as entries:
            for entry in entries:
                entry_path = entry.path
                try:
                    if entry.is_dir(follow_symlinks=False):
                        remove_directory(entry_path)
                    else:
                        os.remove(entry_path)
                except OSError as exc:
                    raise RuntimeError(f"Failed to remove {entry_path}: {exc}") from exc
        os.rmdir(dir_path)
    except OSError as exc:
        raise RuntimeError(f"Failed to remove directory {dir_path}: {exc}") from exc

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
    """Convert HTTP response content into a dictionary.

    ``https_get`` may already return a parsed dictionary, while other callers
    might pass a raw string payload.  The previous implementation assumed a
    string and attempted to ``json.loads`` it directly which would fail if a
    dictionary was supplied.  This helper now gracefully handles both cases.

    Args:
        response_txt (Union[str, dict]): The response body from an HTTP
            request.  It can be either a JSON string or an already parsed
            dictionary.

    Returns:
        dict: The parsed response or an empty dictionary if parsing fails.
    """

    # If the response is already a dictionary, make a shallow copy so callers
    # can safely mutate the result without affecting the original object.
    if isinstance(response_txt, dict):
        return dict(response_txt)

    try:
        response_txt = re.sub(
            r'(\w+):', r'"\1":', response_txt
        )  # Replace single quotes with double quotes to ensure valid JSON
        license_dict = json.loads(response_txt)  # Convert the string to a dictionary
        return license_dict
    except (json.JSONDecodeError, TypeError) as e:
        # ``TypeError`` is caught in case a non-string, non-dict object is
        # passed.  Logging the issue helps diagnose malformed responses.
        print(f"Error converting response to dict: {e}")
        return {}

def protect_network_path(func):
        '''
        The point of this is to prevent certain functions (e.g. unzip_files()) from running on network folders.
        '''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Network paths on Windows typically start with ``\\`` while on
            # Unix-like systems remote paths may be expressed as ``//``.  The
            # previous implementation only checked for ``//`` and therefore
            # failed to protect Windows UNC paths.  By normalising the string
            # and checking for both prefixes we reduce the chance of
            # accidentally modifying remote locations.
            for arg in args:
                if isinstance(arg, str):
                    normalised = arg.replace("\\", "/")
                    if normalised.startswith("//"):
                        raise PermissionError(
                            f"Operation not allowed on protected path: {arg}"
                        )

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
