# I think I could replace this with a JSON file one day that could be way more useful for gathering all the relevant info I need. This is just a first attempt at storing some info centrally...
import requests

def get_supported_versions():
    url = "https://portal.graphon.com/register/index.php?op=getVersions"
    response = requests.get(url)
    response.raise_for_status()  # Raises an error for bad responses
    data = response.json()

    # Adjust the key below as needed based on the actual JSON structure
    if 'versions' in data:
        return data['versions']
    return data

versions = [
    "6.3.2.34154",
    "6.3.1.33754",
    "6.3.1.33709",
    "6.2.6.33307",
    "6.2.5.32895",
    "6.2.4.32657",
    "6.2.3.32551",
    "6.2.3.32518",
    "6.2.2.32366",
    "6.2.2.32205",
    "6.2.2.32151",
    "6.2.2.32074",
    "6.2.1.32140",
    "6.2.1.31562",
    "6.2.0.31099",
    "6.1.1.30272",
    "6.1.0.30001",
    "6.0.5.32115",
    "6.0.5.31674",
    "6.0.4.30702",
    "6.0.3.30239",
    "6.0.2.30092",
    "6.0.1.29306",
    "6.0.1.28446",
    "6.0.1.28103",
    "6.0.1.27682",
    "6.0.1.27172"
]

supported_platforms = {
    "20348": "Windows Server 2022",
    "17763": "Windows Server 2019",
    "14393": "Windows Server 2016",
    "19045": "Windows 10", # Not 100% sure about these... 
    "22631": "Windows 11", # ...
    "22621": "Windows 11"  # taken from Wassim's patch Tuesday email.
}

server_roles = {
    1: "Independent Host",
    2: "Dependent Host",
    3: "Relay Load Balancer",
    4: "Proxy Server",
    5: "Application Host",
    6: "Portal",
    7: "Farm Host",
    8: "Farm Manager"
}

support_issue_types = [
    "Admin Console",
    "AppController",
    "Crash / Hang - Application",
    "Crash / Hang - GO-Global",
    "Crash / Hang - Server",
    "Display",
    "Licensing",
    "Mobile Client",
    "OpenID Connect",
    "Performance",
    "Printing",
    "Published Application",
    "Session Disconnect",
    "Web Client",
    "Other"
]
