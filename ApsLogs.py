import logging
from tkinter import messagebox
import zipfile
from bs4 import BeautifulSoup
#from ApsLog import ApsLog
import myUtils
import os
import GOGlobal
import requests
from datetime import datetime as dt
import json
import re
import chardet
CONFIG_FILE_PATH = "config.json"
DEFAULT_LOG_FILE = "app.log"

def setup_logger():
    try:
        # Load log file path from config.json
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r') as config_file:
                config = json.load(config_file)
                log_file = config.get("log_file", DEFAULT_LOG_FILE)
        else:
            log_file = DEFAULT_LOG_FILE

        # Configure the logger
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger("SRWAnalyzer")
    except Exception as e:
        logger.exception(f"Failed to set up logger: {e}")
        raise

# Initialize the logger
logger = setup_logger()


def load_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            content = file.read()
            return BeautifulSoup(content, 'html.parser')
    except Exception:
        logger.warning(f"Initial read of {file_path} failed. Trying to detect encoding.")
        try:
            # Detect the encoding
            with open(file_path, 'rb') as file:
                raw_data = file.read()
                detected_encoding = chardet.detect(raw_data)['encoding']
            
            logger.info(f"Detected encoding for {file_path}: {detected_encoding}")  # Debug statement
            
            # Try opening the file with the detected encoding
            try:
                with open(file_path, 'r', encoding=detected_encoding ) as file:
                    content = file.read()
            except (UnicodeDecodeError, TypeError):
                # Fallback to utf-8 if the detected encoding fails
                logger.warning(f"Failed to decode with detected encoding ({detected_encoding}). Falling back to utf-8.")
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read()

            return BeautifulSoup(content, 'html.parser')
        except FileNotFoundError:
            logger.exception(f"File not found: {file_path}")
            raise RuntimeError(f"File not found: {file_path}")
        except PermissionError:
            logger.exception(f"Permission denied: {file_path}")
            raise RuntimeError(f"Permission denied: {file_path}")
        except Exception as e:
            logger.exception(f"Error loading log file: {e}")
            raise RuntimeError(f"Error loading log file: {e}")

def load_log_file_text(file_path, log_entries):
    try:
        # Detect the encoding
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            detected_encoding = chardet.detect(raw_data)['encoding']
        
        logger.info(f"Detected encoding for {file_path}: {detected_encoding}")  # Debug statement
        
        # Try opening the file with the detected encoding
        try:
            with open(file_path, 'r', encoding=detected_encoding) as file:
                log_entries.extend(file.readlines())
        except (UnicodeDecodeError, TypeError):
            # Fallback to utf-8 if the detected encoding fails
            logger.warning(f"Failed to decode with detected encoding ({detected_encoding}). Falling back to utf-8.")
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                log_entries.extend(file.readlines())
        return log_entries
    except FileNotFoundError:
        logger.exception(f"File not found: {file_path}")
        raise RuntimeError(f"File not found: {file_path}")
    except PermissionError:
        logger.exception(f"Permission denied: {file_path}")
        raise RuntimeError(f"Permission denied: {file_path}")
    except Exception as e:
        logger.exception(f"Error loading log file: {e}")
        raise RuntimeError(f"Error loading log file: {e}")

def get_host_version(soup):
    try:
        product_info_table = soup.find_all('table')[1]
        rows = product_info_table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if 'Product Version' in cells[0].text:
                return cells[1].text.strip()
    except Exception as e:
        logger.exception(f"Error getting host version: {e}")
        return ""
    return ""

def get_platform_version_from_logs(soup: BeautifulSoup):
    try:
        operating_env_section = soup.find('a', {'name': 'EnvOp'})
        if operating_env_section:
            env_table = operating_env_section.find_next('table')
            env_rows = env_table.find_all('tr')
            
            for row in env_rows:
                cells = row.find_all('td')
                if len(cells) > 0 and 'Platform Build Number' in cells[0].text:
                    build_num = cells[1].text.split(".")[0].strip()
                    build_num_full = cells[1].text.strip()
                    return GOGlobal.supported_platforms[build_num] if GOGlobal.supported_platforms[build_num] else build_num, build_num_full
    except Exception as e:
        logger.exception(f"Error getting platform version from logs: {e}")
        return ""

def get_platform_version_from_sysInfo(sysInfo_dir):
    try:
        sysInfo_path = os.path.join(sysInfo_dir, "SystemInformation.txt")
        
        with open(sysInfo_path) as file:
            lines = file.readlines()
            if len(lines) > 2:
                return lines[2].split(":")[1].strip()
            else:
                logger.info(f"SystemInformation.txt is not of sufficient length to find a the Operating System.")
                return ""
    except Exception as e:
        logger.exception(f"Error getting platform version from sysInfo: {e}")
        return ""

# Step 4: Extract Log Entries
def extract_log_entries(fileName: str, soup):
    log_entries = []
    log_section = soup.find('a', {'name': 'LogEntries'})
    if log_section:
        log_table = log_section.find_next('table')
        
        if log_table:
            rows = log_table.find_all('tr')[1:]
    
            for row in rows:
                cells = row.find_all('td')
                if len(cells) != 0:
                    description = cells[3].text.strip()
                    user = server = process = pid = session = ''
                    
                    # Try to match full pattern first
                    pattern = r'^(\S+) on (\S+)(?: \(\d+\))?, (\S+) \((\d+)\)'
                    match = re.match(pattern, description)
                    
                    if match:
                        user, server, process, pid = match.groups()
                        description = description[match.end():].strip()
                    else:
                        # Fall back to just process and PID
                        process_pid_pattern = r'^(\S+) \((\d+)\)'
                        process_match = re.match(process_pid_pattern, description)
                        if process_match:
                            process, pid = process_match.groups()
                            description = description[process_match.end():].strip()
                    
                    # Look for Session ID in the remaining description
                    session_pattern = r'Session ID (\d+):'
                    session_match = re.search(session_pattern, description)
                    if session_match:
                        session = session_match.group(1)
                        # Remove the session info from description
                        description = description.replace(session_match.group(0), '').strip()
                    
                    entry = {
                        'Line': cells[0].text.strip(),
                        'Date': cells[1].text.strip(),
                        'Time': cells[2].text.strip(),
                        'User': user,
                        'Server': server,
                        'Process': process,
                        'PID': pid,
                        'Session': session,
                        'Description': description,
                        'File': fileName
                    }
                    log_entries.append(entry)
        else:
            logger.error(f"Warning: No log table found in {fileName}. This file may not contain log entries.")
            return []
    else: 
        logger.error(f"Warning: No log section found in {fileName}. This file may not contain log entries.")
        return []    
    
    return log_entries

# Step 6a: Generate Summary
def generate_summary(info, error_dict):
    summary = []
    summary.append(f"Host OS: {info['hostOS'] if info['hostOS'] else 'N/A'}")
    summary.append(f"Host Version: {info['hostVersion'] if info['hostVersion'] else 'N/A'}")
    summary.append(f"Client Versions: {info['clientVersions'] if info['clientVersions'] else 'N/A'}")
    summary.append("\nPotential Issues Detected:\n")
    
    if error_dict:
        for type, details in error_dict.items():
            summary.append(f"{type}  - Entry {details['Line']} on {details['Date']} at {details['Time']}: {details['Description']}")
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

def log_info(file_path):
    log_entries = []

    for file in os.listdir(file_path):
        #log = ApsLog(file_path) # I might want to switch to using an APSLog object but not ready yet...
        if file.endswith(".html"):
            soup = load_log_file(os.path.join(file_path, file))
            log_entries.extend(extract_log_entries(file, soup))

        if file.endswith(".log") and file.startswith("aps"):
            log_entries.extend(load_log_file_text(os.path.join(file_path, file), log_entries))

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
    logger.error("No .lic or .html files found in the zip archive.")

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
            logger.exception(f"Error processing license {license['product_code']}: {e}")
        
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
                    response_body = check_license_validity(product_code, serial_number)
                    license_data.append({
                        'product_code': product_code,
                        'serial_number': serial_number,
                        'num_seats': num_seats,
                        'file': file_path,
                        'response_body': response_body
                    })
                elif serial_number:
                    logger.error(f"Cannot check license validity because no product code was found in {file_path}.")
                    logger.error(f"Serial Number: {serial_number}")
                elif product_code:
                    logger.error(f"Cannot check license validity because no serial number was found in {file_path}.")
                    logger.error(f"Product code: {product_code}")
                else:
                    logger.error(f"Cannot check license validity because no product code or serial number was found in {file_path}.")
    except Exception as e:
        logger.exception(f"Error processing files in directory {directory}: {e}")
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
        logger.exception(f"Error copying {lic_file_path} to .txt: {e}")
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
        logger.exception(f"Error parsing license file {file_path}: {e}")

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
        logger.exception(f"Error checking license validity for product code {product_code} and serial number {serial_number}: {e}")
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
        logger.exception(f"Error processing cloud license: {e}")
        licenses_found['Total'] = {
            'status': e,
            'seats': 0,
            'file': '-'
        }
    finally:
        return licenses_found
### Cloud Section ##################################################


def get_basic_info(path: str):
    info = {
        'hostOS': "",
        'platformBuild': "",
        'hostVersion': "",
        'serverRole': "",
        'serverIp': ""
    }
    
    try:
        if os.path.exists(path) and os.path.isdir(path):
            # Check for server role in registry file - look for any registry file matching the pattern
            reg_files = [f for f in os.listdir(path) if f.startswith("HKLM.Software.") and f.endswith(".reg64.txt")]
            for reg_file in reg_files:
                reg_file_path = os.path.join(path, reg_file)
                try:
                    with open(reg_file_path, 'r', encoding='utf-16') as file:
                        for line in file:
                            if "ServerRole" in line:
                                try:
                                    info['serverRole'] = GOGlobal.server_roles[int(line.split(':')[1].strip())]
                                    break
                                except (ValueError, IndexError):
                                    logger.exception("Error parsing ServerRole value")
                    if info['serverRole']:  # If we found the server role, no need to check other files
                        break
                except Exception as e:
                    logger.exception(f"Error reading registry file {reg_file}: {e}")

            ipconfig_path = os.path.join(path, 'ipconfig.txt')
            if os.path.exists(ipconfig_path):
                try:
                    with open(ipconfig_path, 'r') as file:
                        for line in file:
                            match = re.search(r'IPv4.*?:\s*([\d\.]+)', line) #IPv4 will be the same across any language (hopefully)
                            if match:
                                info['serverIp'] = match.group(1)
                                break  # Stop reading after the first match
                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.exception(f"Failed to read {ipconfig_path}: {e}. Setting server IP to default value.")
                    info['serverIp'] = "0.0.0.0"  # Default IP value if reading fails


            # Get other info from HTML files
            for file in os.listdir(path):
                if file.endswith(".html"):
                    soup = load_log_file(os.path.join(path, file))
                    
                    info['hostOS'], info['platformBuild'] = get_platform_version_from_logs(soup)
                    if not info['hostOS']:
                        info['hostOS'] = get_platform_version_from_sysInfo(path)
                        info['platformBuild'] = "Not found"
                    info['hostVersion'] = get_host_version(soup)
                    break
    except Exception as e:
        logger.exception(f"Error getting basic info: {e}")
    
    return info


# Main Function to Run the Analysis
def main():
    zip_file_path = myUtils.select_file("SRW", ".zip")

    temp_path = os.path.join(os.path.dirname(zip_file_path), "temp")
    myUtils.extract_zip(zip_file_path, temp_path)
    log_entries = log_info(temp_path)

    myUtils.remove_directory(temp_path)

# Example Usage
if __name__ == "__main__":
    main()
