import GOGlobal
import os
from ApsLogs import load_log_file

def get_basic_info(path: str):
    if not path:
        raise ValueError("Path cannot be None")

    info = {
        'hostOS': None,
        'hostVersion': None,
        'clientVersions': []
    }

    if os.path.exists(path) and os.path.isdir(path):
        for file in os.listdir(path):
            if file.endswith(".html"):
                soup = load_log_file(os.path.join(path, file))
                if soup:
                    info['hostOS'] = get_host_version(soup)
                    info['hostVersion'] = get_platform_version(soup)
                    info['clientVersions'] = get_client_versions(soup)
    else:
        raise ValueError("Invalid path: {path}")

    return info

def get_host_version(soup):
    if not soup:
        return ''

    tables = soup.find_all('table')
    if len(tables) < 2:
        return ''

    product_info_table = tables[1]
    rows = product_info_table.find_all('tr')

    for row in rows:
        cells = row.find_all('td')
        if cells and 'Product Version' in cells[0].text:
            return cells[1].text.strip()

    return ''

def get_client_versions(log_entries):
    client_versions = []

    if not log_entries:
        return client_versions

    for entry in log_entries:
        descr = entry.get('description') if isinstance(entry, dict) else None
        if not descr:
            continue
        if "The version of the" in descr:
            parts = descr.split('The version of the ')
            for part in parts[1:]:
                if ' client is ' in part:
                    client_info = part.split(' client is ')
                    client_versions.append((client_info[1].strip(), client_info[0].strip()))

    return client_versions

def get_client_versions(soup):
    client_versions = []

    if not soup:
        return client_versions

    log_section = soup.find('a', {'name': 'LogEntries'})
    if not log_section:
        return client_versions

    log_table = log_section.find_next('table')
    if not log_table:
        return client_versions

    rows = log_table.find_all('tr')[1:]

    for row in rows:
        cells = row.find_all('td')
        if len(cells) > 3:
            descr = cells[3].text.strip()
            if "The version of the" in descr:
                parts = descr.split('The version of the ')
                for part in parts[1:]:
                    if ' client is ' in part:
                        client_info = part.split(' client is ')
                        client_versions.append((client_info[1].strip()[:-1], client_info[0].strip()))

    return client_versions

def get_platform_version(log_entries):
    platform_version = None
    platform_build_number = None

    if not log_entries:
        return "Not found"

    for entry in log_entries:
        description = entry.get('Description') if isinstance(entry, dict) else None
        if description and "The current operating system is" in description:
            return description.split("is")[1].strip()

    return "Not found"

def get_platform_version(soup):
    if not soup:
        return "Unknown"

    operating_env_section = soup.find('a', {'name': 'EnvOp'})
    if not operating_env_section:
        return "Unknown"

    env_table = operating_env_section.find_next('table')
    if not env_table:
        return "Unknown"

    env_rows = env_table.find_all('tr')

    for row in env_rows:
        cells = row.find_all('td')
        if len(cells) > 1 and 'Platform Build Number' in cells[0].text:
            build_num = cells[1].text.split('.')[0]
            platform = GOGlobal.supported_platforms.get(build_num)
            return platform if platform else build_num

    return "Unknown"

