from tkinter import messagebox
import zipfile
from bs4 import BeautifulSoup
import myUtils
import os
import GOGlobal
import requests
from datetime import datetime as dt
import json

DEFAULT_KEYWORDS = [
    "error",
    "werfault.exe",
    "failed",
    "disconnected",
    "memory usage limit",
    "(WLE",
    "(WSE",
]
CONFIG_FILE_PATH = "aps_config.json"

# Note: Order should not matter since multiple keywords can be assigned to one message, but if we ever change that, the order will matter.
def load_keywords_from_config(config_path=CONFIG_FILE_PATH):
    """
    Load keywords from a configuration file.

    Args:
        config_path (str): The path to the configuration file.

    Returns:
        list: A list of keywords loaded from the configuration file. If an error occurs during loading, an empty list is returned.
    """
    try:
        if not os.path.exists(config_path):
            config = {'log_keywords': DEFAULT_KEYWORDS}
            with open(config_path, 'w') as config_file:
                json.dump(config, config_file, indent=4)  # indent for readability
            return DEFAULT_KEYWORDS
        
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            log_keywords = config.get("log_keywords", [])
            
            # Check if log_keywords is empty or not present
            if not log_keywords or len(log_keywords) == 0:
                print(f"Warning: 'log_keywords' is empty or not present in '{config_path}'. Using defaults.")
                return DEFAULT_KEYWORDS
            
            return log_keywords
    
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        return DEFAULT_KEYWORDS
    except PermissionError:
        print(f"Permission denied for file: {config_path}")
        return DEFAULT_KEYWORDS
    except Exception as e:
        print(f"Error loading config file '{config_path}': {e}")
        return DEFAULT_KEYWORDS

# Step 1: Load and Parse the HTML Log File
def load_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            content = file.read()
        return BeautifulSoup(content, 'html.parser')
    except:
        raise RuntimeError("Error loading log file.")

# Step 2: Extract Basic Information
def extract_basic_info(soup, log_entries):
    info = {
        "hostOS": None,
        "hostVersion": None,
        "clientVersions": []
    }
    
    # Extract Product Version
    info['hostOS'] = get_platform_version(soup)
    info['hostVersion'] = get_host_version(soup)
    info['clientVersions'].append(get_client_versions(log_entries))
    
    return info

def get_host_version(soup):
    # Extract Product Version
    product_info_table = soup.find_all('table')[1]
    rows = product_info_table.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if 'Product Version' in cells[0].text:
            return cells[1].text.strip()
    
    return None

def get_client_versions(log_entries):
    client_versions = []

    for entry in log_entries:
        descr = entry['description']
        if "The version of the" in descr:
            parts = descr.split('The version of the ')
            for part in parts[1:]:
                if ' client is ' in part:
                    client_info = part.split(' client is ')
                    client_type = client_info[0].strip()
                    version = client_info[1].strip()
                    client_versions.append((client_type, version))
    return client_versions


def get_platform_version(log_entries):
    platform_version = None
    platform_build_number = None
    
    for entry in log_entries:
        if "The current operating system is" in entry['description']:
            return entry['description'].split("is")[1].strip()
    
    return "Not found"

def get_platform_version(soup):
    operating_env_section = soup.find('a', {'name': 'EnvOp'})
    if operating_env_section:
        env_table = operating_env_section.find_next('table')
        env_rows = env_table.find_all('tr')
        
        for row in env_rows:
            cells = row.find_all('td')
            if len(cells) > 0 and 'Platform Build Number' in cells[0].text:
                build_num = cells[1].text.split(".")[0].strip()
                return GOGlobal.supported_platforms[build_num] if GOGlobal.supported_platforms[build_num] else build_num

# Step 3: Extract Platform Version
def extract_platform_version(log_entries, soup):
    platform_version = None
    platform_build_number = None
    
    for entry in log_entries:
        if "The current operating system is" in entry['Description']:
            platform_version = entry['Description'].split("is")[1].strip()
            break
    
    operating_env_section = soup.find('a', {'name': 'EnvOp'})
    if operating_env_section:
        env_table = operating_env_section.find_next('table')
        env_rows = env_table.find_all('tr')
        
        for row in env_rows:
            cells = row.find_all('td')
            if len(cells) > 0 and 'Platform Build Number' in cells[0].text:
                platform_build_number = cells[1].text.strip()
    
    return platform_version, platform_build_number

# Step 4: Extract Log Entries
def extract_log_entries(fileName: str, soup):
    log_entries = []
    log_section = soup.find('a', {'name': 'LogEntries'})
    log_table = log_section.find_next('table')
    rows = log_table.find_all('tr')[1:]
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 0:
            entry = {
                '#': cells[0].text.strip(),
                'date': cells[1].text.strip(),
                'time': cells[2].text.strip(),
                'description': cells[3].text.strip(),
                'keys': [],
                'file': fileName
            }
            log_entries.append(entry)
    
    return log_entries

def flag_log_entries(log_entries: list, keywords: list):
    flagged_entries = {}
    for keyword in keywords:
        flagged_entries[keyword] = []

    for entry in log_entries:
        for keyword in keywords:
            if keyword in entry['description']:
                entry['keys'].append(keyword)


# Step 6a: Generate Summary
def generate_summary(info, error_dict):
    summary = []
    summary.append(f"Host OS: {info['hostOS'] if info['hostOS'] else 'N/A'}")
    summary.append(f"Host Version: {info['hostVersion'] if info['hostVersion'] else 'N/A'}")
    summary.append(f"Client Versions: {info['clientVersions'] if info['clientVersions'] else 'N/A'}")
    summary.append("\nPotential Issues Detected:\n")
    
    if error_dict:
        for type, details in error_dict.items():
            summary.append(f"{type}  - Entry {details['#']} on {details['date']} at {details['time']}: {details['description']}")
    else:
        summary.append("No errors or failures detected.")
    
    return "\n".join(summary)

# Step 6b: Generate an output
def generate_output(info, error_dict):
    return {
        "hostOS": info["hostOS"] if info["hostOS"] else 'N/A',
        "hostVersion": info["hostVersion"] if info["hostVersion"] else 'N/A',
        "clientOS": info["clientVersions"][-1][0] if info["clientVersions"] else "N/A",
        "clientVersion": info["clientVersions"][-1][1] if info["clientVersions"] else "N/A",
        "potential_issues": error_dict
    }

# Main Function to Run the Analysis

def log_info(file_path, keywords=DEFAULT_KEYWORDS):
    log_entries = []

    keywords = load_keywords_from_config()

    for file in os.listdir(file_path):
        if file.endswith(".html"):
            soup = load_log_file(os.path.join(file_path, file))
            log_entries += extract_log_entries(file, soup)
    
    flag_log_entries(log_entries, keywords)
    
    return log_entries

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
    
    return parse_error_codes(content)

def get_error_code(code: str, codes: dict):
    if code in codes.keys():
        return codes[code]
    else:
        return f"Error code {code} not found."

def check_licenses(file_path):
    # Get a list of all files in the zip archive
    file_list = os.listdir(file_path)
    
    # Check if any files end with .lic
    lic_files = [file for file in file_list if file.endswith('.lic')]
    if lic_files:
        return validate_on_prem_licenses(file_path)
    
    # If no .lic files found, search for .html files
    html_files = [file for file in file_list if file.endswith('.html')]
    if html_files:
        return validate_cloud_license(file_path)
    
    # If no .lic or .html files found
    print("No .lic or .html files found in the zip archive.")

### On-Prem Section ##################################################
def validate_on_prem_licenses(directory):
    """
    Checks the validity of all licenses in the given directory.
    
    Args:
        directory (str): The path to the directory containing license files.
    
    Returns:
        dict: A dictionary with lists of valid, expired, and request-failed licenses.
    """
    licenses_found = {
        "Total": {
            'status': 'Valid',
            'seats': 0,
            'file': '-'
        }
    }

    licenses = process_license_files(directory)
    for license in licenses:
        try:
            if license['response_body'].status_code == 200:
                response_dict = myUtils.convert_response_to_dict(license['response_body'].text)
                licenses_found[response_dict['name']] = {
                    'status': 'Valid' if response_dict['expired'] == 'false' else 'Expired',
                    'seats': int(license['num_seats']),
                    'file': license['file']
                }

                # Update total seats / overall status
                if response_dict['expired'] == 'true':
                    licenses_found['Total']['status'] = 'Expired'
                licenses_found['Total']['seats'] += int(license['num_seats'])
            else:
                raise Exception(LookupError)
        except Exception as e:
            print(f"Error processing license {license['product_code']}: {e}")
        
    return licenses_found

## Helper - validate_on_prem_licenses
def process_license_files(directory):
    """
    Processes all .lic files in the given directory.
    
    Args:
        directory (str): The path to the directory containing license files.
    
    Returns:
        list: A list of dictionaries with license data and their validation responses.
    """
    license_data = []

    try:
        for filename in os.listdir(directory):
            if filename.endswith(".lic"):
                file_path = os.path.join(directory, filename)
                txt_path = copy_lic_to_txt(file_path)
                
                product_code, serial_number, num_seats = parse_license_file(txt_path)
                if product_code and serial_number:
                    # response_body = myUtils.https_get(f"http://license.graphon.com/license/GraphOn/api_validate_maintenance?serial={serial_number}_PRODUCTCODE={product_code}")
                    response_body = check_license_validity(product_code, serial_number)
                    license_data.append({
                        'product_code': product_code,
                        'serial_number': serial_number,
                        'num_seats': num_seats,
                        'file': file_path,
                        'response_body': response_body
                    })
                elif serial_number:
                    print(f"Cannot check license validity because no product code was found in {file_path}.")
                    print(f"Serial Number: {serial_number}")
                elif product_code:
                    print(f"Cannot check license validity because no serial number was found in {file_path}.")
                    print(f"Product code: {product_code}")
                else:
                    print(f"Cannot check license validity because no product code or serial number was found in {file_path}.")
    except Exception as e:
        print(f"Error processing files in directory {directory}: {e}")
    finally:
        return license_data

## Helper - validate_on_prem_licenses
def copy_lic_to_txt(lic_file_path):
    """
    Copies a .lic file to a .txt file for easier parsing.
    
    Args:
        lic_file_path (str): The path to the .lic file.
    
    Returns:
        str: The path to the created .txt file.
    """
    try:
        txt_file_path = lic_file_path.replace('.lic', '.txt')
        myUtils.copy_file_contents(lic_file_path, txt_file_path)
        return txt_file_path
    except Exception as e:
        print(f"Error copying {lic_file_path} to .txt: {e}")
        raise

## Helper - validate_on_prem_licenses
def parse_license_file(file_path):
    """
    Parses a .lic file to extract product code, serial number, and number of seats.
    
    Args:
        file_path (str): The path to the .lic file.
    
    Returns:
        tuple: A tuple containing product code, serial number, and number of seats.
    """
    product_code = None
    serial_number = None
    num_seats = None

    try:
        with open(file_path, 'r') as file:
            for line in file:
                if '# Product code' in line:
                    product_code = line.split(':')[1].strip()
                if '# License ID' in line:
                    serial_number = line.split(':')[1].strip()
                    if 'TL-' in serial_number:
                        serial_number = serial_number.split('-')[1]
                if '# Seats' in line:
                    num_seats = line.split(':')[1].strip()
    except Exception as e:
        print(f"Error parsing license file {file_path}: {e}")

    return product_code, serial_number, num_seats

## Helper - validate_on_prem_licenses
def check_license_validity(product_code, serial_number):
    """
    Makes an HTTP GET request to check the validity of a license.
    
    Args:
        product_code (str): The product code of the license.
        serial_number (str): The serial number of the license.
    
    Returns:
        Response: The HTTP response object.
    """
    try:
        url = f"http://license.graphon.com/license/GraphOn/api_validate_maintenance?serial={serial_number}_PRODUCTCODE={product_code}"
        return requests.get(url)
    except requests.RequestException as e:
        print(f"Error checking license validity for product code {product_code} and serial number {serial_number}: {e}")
        return None
### On-Prem Section ##################################################

### Cloud Section ##################################################
## Main
def validate_cloud_license(directory):
    '''
    UNFINISHED - NEED THIS TO RETURN A DICTIONARY OF LICENSES SO WE CAN DISPLAY IT IN THE SAME WAY AS ON-PREM LICENSES
    '''
    licenses_found = {
        "Total": {
            'status': '-',
            'seats': 0,
            'file': '-'
        }
    }

    try:
        for filename in os.listdir(directory):
            if filename.endswith(".html"):
                file_path = os.path.join(directory, filename)
                soup = load_log_file(file_path)

                # Find the relevant line containing the license information
                license_info = soup.find(text=lambda text: text and "GO-Global license information" in text)
                if license_info:
                    # Get the parent <td> tag, which contains all the relevant info
                    parent_td = license_info.find_parent('td')
                    if parent_td:
                        # Extract the required details using BeautifulSoup
                        license_details = str(parent_td)

                        # Parse the extracted details
                        expiration_date = None
                        seats = None
                        license_master_id = None
                        product_code = None

                        if 'Expiration date:' in license_details:
                            expiration_date_str = license_details.split('Expiration date:')[1].split('<br')[0].strip()
                            expiration_date = dt.strptime(expiration_date_str, '%Y-%m-%d')

                        if 'Seats:' in license_details:
                            seats = license_details.split('Seats:')[1].split('<')[0].strip()

                        if 'License master:' in license_details:
                            license_master_id = license_details.split('License master:')[1].split('<')[0].strip()

                        licenses_found[license_master_id] = {
                            'status': 'Valid' if expiration_date > dt.today() else 'Expired',
                            'seats': seats,
                            'file': '-'
                        }
                        licenses_found['Total'] = {
                            'status': 'Valid' if expiration_date > dt.today() else 'Expired',
                            'seats': seats,
                            'file': '-'
                        }
                        break
    except Exception as e:
        #print(f"Error processing cloud license: {e}")
        licenses_found['Total'] = {
            'status': e,
            'seats': 0,
            'file': '-'
        }
    finally:
        return licenses_found
### Cloud Section ##################################################



# Main Function to Run the Analysis
def main(file_path):
    log_info(file_path)

# Example Usage
if __name__ == "__main__":
    zip_file_path = myUtils.select_file("SRW", ".zip")

    temp_path = os.path.join(os.path.dirname(zip_file_path), "temp")
    myUtils.extract_zip(zip_file_path, temp_path)
    log_entries = log_info(temp_path)

    for entry in log_entries:
        if len(entry['keys']) > 0:
            print(entry['description'])

    myUtils.remove_directory(temp_path)
