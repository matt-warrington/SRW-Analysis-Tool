import datetime
from bs4 import BeautifulSoup
import myUtils
import os
import GOGlobal
import requests
from datetime import datetime as dt

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
def extract_log_entries(soup):
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
                'description': cells[3].text.strip()
            }
            log_entries.append(entry)
    
    return log_entries

def extract_log_entries_2(fileName: str, soup):
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
                #flagged_entries[keyword].append(entry)
                entry['keys'].append(keyword)

    #return flagged_entries


# Step 5: Identify Errors or Failures
def analyze_log_entries(log_entries):
    error_dict = {}
    error_keywords = ['error', 'failed', 'exception', 'critical']
    for keyword in error_keywords:
        if not keyword in error_dict.keys():
            error_dict[keyword] = {}

    for entry in log_entries:
        for keyword in error_keywords:
            if keyword in entry['description'].lower():
                error_dict[keyword].append(entry)
                break
    
    return error_dict

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
def log_info(file_path):
    summary = []
    log_entries = []
    error_dict = {}

    for file in os.listdir(file_path):
        if file.endswith(".html"):
            soup = load_log_file(os.path.join(file_path, file))
            log_entries += extract_log_entries(soup)
            info = extract_basic_info(soup, log_entries)
            error_dict[file] = analyze_log_entries(log_entries)
            summary.append(generate_summary(info, error_dict[file]))
    
    print("\n\n".join(summary))

    return generate_output(info, error_dict) #platform_version, platform_build_number, error_dict)

def log_info_2(file_path, keywords):
    #summary = []
    log_entries = []
    flagged_entries = None

    for file in os.listdir(file_path):
        if file.endswith(".html"):
            soup = load_log_file(os.path.join(file_path, file))
            log_entries += extract_log_entries_2(file, soup)
    
    #flagged_entries = flag_log_entries(log_entries, keywords)
    flag_log_entries(log_entries, keywords)
    
    return log_entries#, flagged_entries

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
            'seats': 0
        }
    }

    licenses = process_license_files(directory)
    for license in licenses:
        try:
            if license['response_body'].status_code == 200:
                response_dict = myUtils.convert_response_to_dict(license['response_body'].text)
                licenses_found[response_dict['name']] = {
                    'status': 'Valid' if response_dict['expired'] == 'false' else 'Expired',
                    'seats': int(license['num_seats'])
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
            'seats': 0
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
                            'seats': seats
                        }
                        licenses_found['Total'] = {
                            'status': 'Valid' if expiration_date > dt.today() else 'Expired',
                            'seats': seats
                        }
                else:
                    print('Relevant license information not found in the HTML.')
    except Exception as e:
        #print(f"Error processing cloud license: {e}")
        licenses_found['Total'] = {
            'status': e,
            'seats': 0
        }
    finally:
        return licenses_found
### Cloud Section ##################################################



# Main Function to Run the Analysis
def main(file_path):
    temp_path = "C:\\test\\check_log_files_temp"
    directory_unzipped = myUtils.extract_zip(file_path, temp_path)
    summary = []
    log_entries = []
    error_dict = {}

    for file in os.listdir(directory_unzipped):
        if file.endswith(".html"):
            soup = load_log_file(os.path.join(directory_unzipped, file))
            log_entries += extract_log_entries(soup)
            info = extract_basic_info(soup, log_entries)
            error_dict[file] = analyze_log_entries(log_entries)
            summary.append(generate_summary(info, error_dict[file]))
    
    print("\n\n".join(summary))
    
    if os.path.exists(temp_path):
        try:
            myUtils.remove_directory(temp_path)
        except Exception as e:
            print(f"Error removing directory {temp_path}: {e}")

# Example Usage
if __name__ == "__main__":
    log_file_path = myUtils.select_file("SRW", ".zip")
    main(log_file_path)
