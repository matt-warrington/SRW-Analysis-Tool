import GOGlobal
import os
from ApsLogs import load_log_file


def get_basic_info(path: str):
    """Gather host and client information from log files in ``path``.

    Searches the given directory for HTML logs and extracts host OS, host
    version, and client versions to build a summary dictionary.
    """
    info = {
        'hostOS': None,
        'hostVersion': None,
        'clientVersions': []
    }
    
    if os.path.exists(path) and os.path.isdir(path):
        for file in os.listdir(path):
            if file.endswith(".html"):
                soup = load_log_file(os.path.join(path, file))
                info['hostOS'] = get_host_version(soup)
                info['hostVersion'] = get_platform_version(soup)
                info['clientVersions'] = get_client_versions(soup)
    else:
        raise Exception(ValueError)

    return info


def get_host_version(soup):
    """Extract the product version string from a BeautifulSoup object."""
    # Extract Product Version
    product_info_table = soup.find_all('table')[1]
    rows = product_info_table.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        if 'Product Version' in cells[0].text:
            return cells[1].text.strip()
    
    return ''


def get_client_versions(log_entries):
    """Parse client version entries from raw log dictionaries."""
    client_versions = []

    for entry in log_entries:
        descr = entry['description']
        if "The version of the" in descr:
            parts = descr.split('The version of the ')
            for part in parts[1:]:
                if ' client is ' in part:
                    client_info = part.split(' client is ')
                    client_versions.append((client_info[1].strip(), client_info[0].strip()))

    return client_versions


def get_client_versions(soup):
    """Extract client version tuples from an HTML log file."""
    client_versions = []

    log_section = soup.find('a', {'name': 'LogEntries'})
    log_table = log_section.find_next('table')
    rows = log_table.find_all('tr')[1:]
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 0:
            descr = cells[3].text.strip()
            if "The version of the" in descr:
                parts = descr.split('The version of the ')
                for part in parts[1:]:
                    if ' client is ' in part:
                        client_info = part.split(' client is ')
                        client_versions.append((client_info[1].strip()[:-1], client_info[0].strip()))

    return client_versions


def get_platform_version(log_entries):
    """Read platform version from textual log entries."""
    platform_version = None
    platform_build_number = None
    
    for entry in log_entries:
        if "The current operating system is" in entry['Description']:
            return entry['Description'].split("is")[1].strip()
    
    return "Not found"


def get_platform_version(soup):
    """Convert platform build numbers from HTML logs to friendly names."""
    operating_env_section = soup.find('a', {'name': 'EnvOp'})
    if operating_env_section:
        env_table = operating_env_section.find_next('table')
        env_rows = env_table.find_all('tr')
        
        for row in env_rows:
            cells = row.find_all('td')
            if len(cells) > 0 and 'Platform Build Number' in cells[0].text:
                build_num = cells[1].text.split('.')[0]
                return GOGlobal.supported_platforms[build_num] if GOGlobal.supported_platforms[build_num] else build_num
    