from bs4 import BeautifulSoup
import myUtils
import os

# Step 1: Load and Parse the HTML Log File
def load_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-16') as file:
            content = file.read()
        return BeautifulSoup(content, 'html.parser')
    except:
        raise RuntimeError("Error loading log file.")

# Step 2: Extract Basic Information
def extract_basic_info(soup):
    info = {}
    
    # Extract Product Version
    product_info_table = soup.find_all('table')[1]
    rows = product_info_table.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if 'Product Version' in cells[0].text:
            info['Product Version'] = cells[1].text.strip()
    
    return info

# Step 3: Extract Platform Version
def extract_platform_version(log_entries, soup):
    platform_version = None
    platform_build_number = None
    
    # Method 1: Check log entries for platform version
    for entry in log_entries:
        if "The current operating system is" in entry['Description']:
            platform_version = entry['Description'].split("is")[1].strip()
            break
    
    # Method 2: Extract platform build number from operating environment
    operating_env_section = soup.find('a', {'name': 'EnvOp'})
    if operating_env_section:
        env_table = operating_env_section.find_next('table')
        env_rows = env_table.find_all('tr')
        
        for row in env_rows:
            cells = row.find_all('td')
            if len(cells) > 0 and 'Platform Build Number' in cells[0].text:
                platform_build_number = cells[1].text.strip()
                
                # We may remove method 1 (above) for checking the platform_version if this works well, 
                # but for now we will leave this check here...
                '''
                if platform_version == None:
                    # Maybe.... just maybe....
                    # Call the endoflife.date API for a list of 
                    build = platform_build_number.split(".")[0]
                    response_txt = myUtils.https_get_txt(f"https://endoflife.date/api/windows-server.json")
                    
                    if response_txt:
                        response_json = response_txt.json() # might need to check if this is possible - what if the response is not able to be made JSON?
                        for data in response_json:
                            if data['latest'].contains(platform_build_number):
                                platform_version = f"Windows Server {data['cycle']}"
                '''
                # add a URL to the output in the form of https://www.google.com/search?q={platform_build_number}
    
    #platform can also be gotten from the SystemInformation.txt

    return platform_version, platform_build_number

# Step 4: Extract Log Entries
def extract_log_entries(soup):
    log_entries = []
    log_section = soup.find('a', {'name': 'LogEntries'})
    log_table = log_section.find_next('table')
    rows = log_table.find_all('tr')[1:]  # Skip header row
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 0:
            entry = {
                'Entry Number': cells[0].text.strip(),
                'Date': cells[1].text.strip(),
                'Time': cells[2].text.strip(),
                'Description': cells[3].text.strip()
            }
            log_entries.append(entry)
    
    return log_entries

# Step 5: Identify Errors or Failures
def analyze_log_entries(log_entries):
    error_dict = {}
    error_keywords = ['error', 'failed', 'exception', 'critical']
    
    for entry in log_entries:
        for keyword in error_keywords:
            if keyword in entry['Description'].lower():
                if keyword not in error_dict:
                    error_dict[keyword] = []
                error_dict[keyword].append(entry)
                break  # Assumes each entry will only match one keyword
    
    return error_dict


# Step 6a: Generate Summary
def generate_summary(info, platform_version, platform_build_number, error_dict):
    summary = []
    
    summary.append(f"Product Version: {info.get('Product Version', 'N/A')}")
    summary.append(f"Platform Version: {platform_version if platform_version else 'N/A'}")
    summary.append(f"Platform Build Number: {platform_build_number if platform_build_number else 'N/A'}")
    summary.append("\nPotential Issues Detected:\n")
    
    issues_found = False
    for keyword, entries in error_dict.items():
        if entries:
            issues_found = True
            summary.append(f"Entries with '{keyword}':")
            for entry in entries:
                summary.append(f"  - Entry {entry['Entry Number']} on {entry['Date']} at {entry['Time']}: {entry['Description']}")
    
    if not issues_found:
        summary.append("No errors or failures detected.")
    
    return "\n".join(summary)

# Step 6b: Generate an output
def generate_output(info, platform_version, platform_build_number, error_dict):
    return {
        "gg_version" : info.get('Product Version', 'N/A'),
        "os_version" : platform_version if platform_version else 'N/A',
        "build_number" : platform_build_number if platform_build_number else 'N/A',
        "potential_issues" : error_dict if error_dict else {}
    }


# Main Function to Run the Analysis
def log_info(file_path):
    temp_path = "C:\\test\\check_log_files_temp"
    directory_unzipped = myUtils.extract_zip(file_path, temp_path)
    summary = []
    log_entries = []
    error_dict = {}

    for file in os.listdir(directory_unzipped):
        if file.endswith(".html"):
            soup = load_log_file(os.path.join(directory_unzipped, file))
            info = extract_basic_info(soup) # info can be just from the last file. That's fine
            log_entries += extract_log_entries(soup)
            platform_version, platform_build_number = extract_platform_version(log_entries, soup) # extract_platform_version() should honestly just be a part of get_basic_info
            error_dict[file] = analyze_log_entries(log_entries)
            summary.append(generate_summary(info, platform_version, platform_build_number, error_dict[file]))

    
    print("\n\n".join(summary))
    
    if os.path.exists(temp_path):
        try:
            myUtils.remove_directory(temp_path)
        except Exception as e:
            print(f"Error removing directory {temp_path}: {e}")


    return generate_output((info, platform_version, platform_build_number, error_dict))

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
            info = extract_basic_info(soup) # info can be just from the last file. That's fine
            log_entries += extract_log_entries(soup)
            platform_version, platform_build_number = extract_platform_version(log_entries, soup) # extract_platform_version() should honestly just be a part of get_basic_info
            error_dict[file] = analyze_log_entries(log_entries)
            summary.append(generate_summary(info, platform_version, platform_build_number, error_dict[file]))

    
    print("\n\n".join(summary))
    
    if os.path.exists(temp_path):
        try:
            myUtils.remove_directory(temp_path)
        except Exception as e:
            print(f"Error removing directory {temp_path}: {e}")

# Example Usage
if __name__ == "__main__":
    log_file_path = myUtils.select_file("SRW", ".zip") # figure out how to open this to a default folder
    main(log_file_path)
