import io
import json
import os
import subprocess
import tempfile
import zipfile
import pandas as pd
import requests
import ApsLogs as aps
from bs4 import BeautifulSoup
import myUtils
import logging
from collections import defaultdict
              
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
        logging.info(f"License Validity Check: {url}")
        return requests.get(url)
    except requests.RequestException as e:
        print(f"Error checking license validity for product code {product_code} and serial number {serial_number}: {e}")
        return None
### On-Prem Section ##################################################

def analyze_license_data(license_data):
    os_summary = defaultdict(lambda: {
        'valid_seats': 0,
        'expired_seats': 0,
        'total_seats': 0,
        'unique_hosts': set()
    })

    for data in license_data:
        os_version = data['platform_version']
        os_summary[os_version]['unique_hosts'].add(data['file'])

        if data['status'] == "Valid": 
            os_summary[os_version]['valid_seats'] += int(data['num_seats'])
        else:
            os_summary[os_version]['expired_seats'] += int(data['num_seats'])
        
        os_summary[os_version]['total_seats'] += int(data['num_seats'])

    # Convert the set of hosts to counts
    for os_version in os_summary:
        os_summary[os_version]['unique_hosts'] = len(os_summary[os_version]['unique_hosts'])

    return os_summary


def process_license_files(directory, zip_file_path = ""):
    """
    Processes all .lic files in the given directory and its subdirectories.
    Also handles .lic files inside .zip files and retrieves platform version
    information from .html files.

    Args:
        directory (str): The path to the directory containing license files.

    Returns:
        list: A list of dictionaries with license data, their validation responses, and platform version.
    """
    license_data = []
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        for root, dirs, files in os.walk(directory):
            path = root if zip_file_path == "" else zip_file_path
            platform_version = None
            # Check for .html files to determine the platform version
            
            for filename in files:
                if filename.endswith("SystemInformation.txt"):
                    platform_version = aps.get_platform_version_from_sysInfo(root)
                    break

            if platform_version:
                logging.info(f"Host OS found in {path}: {platform_version}")
            
            logging.info(f"\tChecking for .lic or .zip files in {path}.")
            for filename in files:
                try:
                    if filename.endswith(".lic"):
                        logging.info(f"\t\tFound {filename}.")
                        file_path = os.path.join(root, filename)
                        txt_path = copy_lic_to_txt(file_path)
                        
                        product_code, serial_number, num_seats = parse_license_file(txt_path)
                        if product_code and serial_number:
                            if LOG_LEVEL != 0:
                                response_body = check_license_validity(product_code, serial_number)

                                # Validate the license
                                status = "-"
                                if response_body.status_code == 200:
                                    response_dict = myUtils.convert_response_to_dict(response_body.text)
                                    status = 'Valid' if response_dict['expired'] == 'false' else 'Expired'
                            else:
                                status = 'Log Level = Silent'

                            license_data.append({
                                'product_code': product_code,
                                'serial_number': serial_number,
                                'num_seats': num_seats,
                                'file': path,
                                'status': status,
                                'platform_version': platform_version
                            })
                        else:
                            missing_info = []
                            if not product_code:
                                missing_info.append("product code")
                            if not serial_number:
                                missing_info.append("serial number")
                            logging.warning(f"Cannot check license validity because no {', '.join(missing_info)} found in {file_path}.")
                    
                    elif filename.endswith(".zip"):
                        check_zip_for_lic(root, filename, license_data)
                        
                except Exception as e:
                    logging.critical(f"Error while searching for license in {filename}: {e}")

    except Exception as e:
        logging.error(f"Error processing files in directory {directory}: {e}")
    
    return license_data

def check_zip_for_lic(zip_base_path, zip_file_name, license_data):
    logging.info(f"Checking {zip_file_name} for a license. ")
    temp_dir = None

    # Extract the directory name from the .zip file path
    top_level_dir = zip_base_path #os.path.splitext(os.path.basename(zip_file_path))[0]

    def search_directory(current_dir, top_level_dir):
        try:
            for root, dirs, files in os.walk(current_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.endswith('.lic'):
                        logging.info(f"Found {file} in {root}.")
                        extract_and_save_license(file_path, top_level_dir)
                    elif file.endswith('.zip'):
                        search_zip_file(file_path, top_level_dir)
        except Exception as e:
            print(f"Exception in search_directory: {e}")

    def search_zip_file(zip_file_path, parent_dir):
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
                for file_name in zip_file.namelist():
                    if file_name.endswith('/'):
                        continue
                    full_path = os.path.join(zip_file_path, file_name)
                    if file_name.endswith('.lic'):
                        lic_content = zip_file.read(file_name)
                        save_license_file(lic_content, file_name, top_level_dir)
                    elif file_name.endswith('.zip'):
                        nested_zip_data = zip_file.read(file_name)
                        nested_zip_file = io.BytesIO(nested_zip_data)
                        search_nested_zip_file(nested_zip_file, full_path, top_level_dir)
        except Exception as e:
            print(f"Exception in search_zip_file({zip_file_path}): {e}")

    def search_nested_zip_file(nested_zip_file, parent_path, top_level_dir):
        logging.info(f"Found {nested_zip_file} in {parent_path}.")
        try:
            with zipfile.ZipFile(nested_zip_file, 'r') as zip_file:
                for file_name in zip_file.namelist():
                    if file_name.endswith('/'):
                        continue
                    full_path = os.path.join(parent_path, file_name)
                    if file_name.endswith('.lic'):
                        lic_content = zip_file.read(file_name)
                        save_license_file(lic_content, file_name, top_level_dir)
                    elif file_name.endswith('.zip'):
                        nested_zip_data = zip_file.read(file_name)
                        deeper_nested_zip_file = io.BytesIO(nested_zip_data)
                        search_nested_zip_file(deeper_nested_zip_file, full_path, top_level_dir)
        except Exception as e:
            print(f"Exception in search_nested_zip_file: {e}")

    def extract_and_save_license(lic_file_path, top_level_dir):
        logging.info(f"Saving info for {lic_file_path}. ")
        try:
            with open(lic_file_path, 'r') as lic_file:
                lic_content = lic_file.read()
            save_license_file(lic_content, os.path.basename(lic_file_path), top_level_dir)
        except Exception as e:
            print(f"Exception in extract_and_save_license: {e}")

    def save_license_file(lic_content, lic_file_name, top_level_dir):
        nonlocal temp_dir
        try:
            if temp_dir is None:
                temp_dir = tempfile.mkdtemp(dir=top_level_dir)
            txt_file_path = os.path.join(temp_dir, lic_file_name + '.txt')
            
            if isinstance(lic_content, bytes):
                lic_content = lic_content.decode('utf-8')
            
            with open(txt_file_path, 'w') as txt_file:
                txt_file.write(lic_content)
        except Exception as e:
            print(f"Exception in save_license_file: {e}")


    # Start the search
    z = os.path.join(zip_base_path, zip_file_name)
    with zipfile.ZipFile(z, 'r') as zip_ref:
        temp_dir = tempfile.mkdtemp(dir=zip_base_path)
        myUtils.extract_zip(z, temp_dir)
        search_directory(temp_dir, temp_dir)

    # Process the extracted license files if any were found
    if temp_dir:
        result = process_license_files(temp_dir)

        if len(result) != 0:
            logging.critical(f"Successfully processed licenses in {z}:")
            license_data.extend(result)

        # Cleanup: Remove the extracted files and temporary directory
        if os.path.exists(temp_dir):
            myUtils.remove_directory(temp_dir)
        else:
            logging.warning(f"Failed to remove temp_dir ({temp_dir}) because it did not exist. ")

@myUtils.protect_network_path
def copy_directory_with_xcopy(src_path, dst_path):
        logging.info(f"Copying from {src_path} to {dst_path}.")

        CREATE_NO_WINDOW = 0x08000000  # Suppress the command prompt window

        # Ensure paths use backslashes
        src_path = src_path.replace('/', '\\')
        dst_path = dst_path.replace('/', '\\')
        
        # Ensure the destination directory exists
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        
        # Construct the xcopy command
        command = f'xcopy "{src_path}" "{dst_path}" /E /I /Y'

        # Execute the command using subprocess
        try:
            result = subprocess.run(command, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)

            # Check if the command was successful
            if result.returncode == 0:
                return True
            else:
                logging.info(f"Copy failed: {result.stderr}")
                #messagebox.showwarning("Copy Failed", f"Copy failed with error:\n\n{result.stderr}")
                return False
        except Exception as e:
            logging.info(f"Exception thrown: {str(e)}")
            #messagebox.showwarning(
            #    "Exception thrown",
            #    f"{type(e).__name__} when copying from {src_path} to {dst_path}:\n\n{str(e)}"
            #)
            return False

def get_log_level_from_config(default_path = "config.json"):
    log_level = 1
    
    if not os.path.exists(default_path):
        config = {"log_level": log_level}
        with open(default_path, 'w') as config_file:
            json.dump(config, config_file)
        return log_level
    else:
        # Read the dump path from the config file
        with open(default_path, 'r') as config_file:
            config = json.load(config_file)

        log_level = config.get("log_level", -1)
        if log_level == -1:
            config = {"log_level": 1}
            with open(default_path, 'w') as config_file:
                json.dump(config, config_file)
        
    return log_level


def get_temp_dir_from_config(default_path = "config.json"):
    # Get the path to the user's desktop
    temp_dir_location = os.path.join(os.path.expanduser("~"), "Desktop\Temp")
    default_temp_dir_location = temp_dir_location

    
    if not os.path.exists(default_path):
        config = {"temp_dir_location": default_temp_dir_location}
        with open(default_path, 'w') as config_file:
            json.dump(config, config_file)
        return default_temp_dir_location
    else:
        # Read the dump path from the config file
        with open(default_path, 'r') as config_file:
            config = json.load(config_file)

        temp_dir_location = config.get("temp_dir_location", "")
        if temp_dir_location == "":
            config = {"temp_dir_location": default_temp_dir_location}
            with open(default_path, 'w') as config_file:
                json.dump(config, config_file)

            temp_dir_location = default_temp_dir_location
        
    return temp_dir_location


if __name__ == "__main__":
    # Replace with the actual root directory you want to process
    LOG_LEVEL = get_log_level_from_config()

    if LOG_LEVEL < 2:
        logging.disable(logging.CRITICAL)


    root_directory = myUtils.select_dir()
    
    # Make a temporary directory so we can delete it at the end.
    temp_dir = get_temp_dir_from_config()
    os.makedirs(temp_dir, exist_ok=True)

    '''
    if "\\\\" in root_directory or "supportnas.graphon.com" in root_directory: 
        os.makedirs(temp_dir, exist_ok=True)
        copy_directory_with_xcopy(root_directory, temp_dir)
        root_directory = temp_dir
    '''
    
    try:
        result = process_license_files(root_directory)
    except Exception as e:
        print(f"Exception while processing license files in {root_directory}:\n\t{str(e)}")
    finally:
        myUtils.remove_directory(temp_dir)

    if len(result) == 0:
        print(f"No licenses found in {root_directory}")
    else:
        os_summary = analyze_license_data(result)

        #if LOG_LEVEL > 1:
        for os_version, summary in os_summary.items():
            print(f"OS Version: {os_version}")
            print(f"\tValid Seats: {summary['valid_seats']}")
            print(f"\tExpired Seats: {summary['expired_seats']}")
            print(f"\tTotal Seats: {summary['total_seats']}")
            print(f"Unique Hosts: {summary['unique_hosts']}")
            print("----------")

        # Prepare data for the DataFrame
        data = {
            "OS Version": [],
            "Valid Seats": [],
            "Expired Seats": [],
            "Total Seats": [],
            "Unique Hosts": []
        }

        # Label the rows
        data["OS Version"].append("OS Version")
        data["Valid Seats"].append("Valid Seats")
        data["Expired Seats"].append("Expired Seats")
        data["Total Seats"].append("Total Seats")
        data["Unique Hosts"].append("Unique Hosts")

        for os_version, summary in os_summary.items():
            data["OS Version"].append(os_version)
            data["Valid Seats"].append(summary["valid_seats"])
            data["Expired Seats"].append(summary["expired_seats"])
            data["Total Seats"].append(summary["total_seats"])
            data["Unique Hosts"].append(summary["unique_hosts"])
        
        # Create the DataFrame

        df = pd.DataFrame(data)

        # Save the DataFrame to an Excel file
        output_file = "C:\\host_os\\os_summary.xlsx"
        df.to_excel(output_file, index=False)