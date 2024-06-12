import myUtils
from bs4 import BeautifulSoup
import tkinter as tk
#from tkinter import filedialog
import os
import requests


# Access point for Main.py
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
    license_statuses = {
        "valid": {},
        "expired": {},
        "req_failed": {}
    }

    licenses = process_license_files(directory)
    for license in licenses:
        try:
            if license['response_body'].status_code == 200:
                response_dict = myUtils.convert_response_to_dict(license['response_body'].text)
                if response_dict['expired'] == "true":
                    #license_statuses['expired'].append([response_dict['name'], license['num_seats']])
                    license_statuses['expired'][response_dict['name']] = license['num_seats']
                else:
                    #license_statuses['valid'].append([response_dict['name'], license['num_seats']])
                    license_statuses['valid'][response_dict['name']] = license['num_seats']
            else:
                #license_statuses['req_failed'].append([f"PC: {license['product_code']} - SN: {license['serial_number']}", license['response_body'].status_code])
                license_statuses['req_failed'][response_dict['name']] = f"Received status code {license['response_body'].status_code}. "
        except Exception as e:
            print(f"Error processing license {license['product_code']}: {e}")
            #license_statuses['req_failed'].append([f"PC: {license['product_code']} - SN: {license['serial_number']}", 'processing error'])
            license_statuses['req_failed'][response_dict['name']] = "Encountered processing error. "


    return license_statuses

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
def validate_cloud_license(file_path): #file_path is unneccesary if we can find this without getting the first APS log in a series and using it to find license info.
    # Read the HTML content from a file
    with open('license_info.html', 'r') as file:
        html_content = file.read()

    # To get HTML content, we need to know the license product code or master ID
    # To get this info, we probably need either 
    #       an API call to the cloud license server that uses some info about the host rather than the license itself, or 
    #       the license info from the first APS log in the series. # BLOCKED by GO-630 GRAPHON: Ensure Support Request Wizard gets first APS log in series

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')

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
                expiration_date = license_details.split('Expiration date:')[1].split('<br>')[0].strip()

            if 'Seats:' in license_details:
                seats = license_details.split('Seats:')[1].split('<')[0].strip()

            if 'License master:' in license_details:
                license_master_id = license_details.split('License master:')[1].split('<')[0].strip()

            if 'Product code:' in license_details:
                product_code = license_details.split('Product code:')[1].split('<')[0].strip()

            # Print the extracted details
            print(f'Expiration Date: {expiration_date}')
            print(f'Seats: {seats}')
            print(f'License Master ID: {license_master_id}')
            print(f'Product Code: {product_code}')
        else:
            print('Relevant parent <td> tag not found.')
    else:
        print('Relevant license information not found in the HTML.')
### Cloud Section ##################################################

def main():
    # Main execution
    try:
        directory_path = myUtils.select_zip_file()
        if not directory_path:
            print("No file selected.")
            exit(1)

        unzipped_path = myUtils.extract_zip(directory_path)
        
        license_data = check_licenses(unzipped_path)
        myUtils.print_nested_dict(license_data)

        # Delete the temporary directory if it exists
        myUtils.remove_directory(unzipped_path)

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()