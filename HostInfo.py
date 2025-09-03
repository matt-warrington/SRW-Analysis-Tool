import os
import re
from venv import logger

import GOGlobal


class HostInfo:
    def __init__(self, path):
        self.os = None
        self.platform_build = None
        self.gg_version = None
        self.role = None
        self.ip = None

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
                                        self.role = GOGlobal.server_roles[int(line.split(':')[1].strip())]
                                        break
                                    except (ValueError, IndexError):
                                        logger.exception("Error parsing ServerRole value")
                        if self.role:  # If we found the server role, no need to check other files
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
                                    self.ip = match.group(1)
                                    break  # Stop reading after the first match
                    except (FileNotFoundError, PermissionError, OSError) as e:
                        logger.exception(f"Failed to read {ipconfig_path}: {e}. Setting server IP to default value.")
                        self.ip = "0.0.0.0"  # Default IP value if reading fails

                try:
                    sysInfo_path = os.path.join(path, "SystemInformation.txt")
                    
                    with open(sysInfo_path) as file:
                        lines = file.readlines()
                        if len(lines) > 3:
                            self.name = lines[1].split(":")[1].strip()
                            self.os = lines[2].split(":")[1].strip()
                            self.platform_build = lines[3].split(":")[1].strip()
                        else:
                            logger.info(f"SystemInformation.txt is not of sufficient length to find the needed info.")
                            return ""
                except Exception as e:
                    logger.exception(f"Error getting platform version from sysInfo: {e}")
                    return ""
        except Exception as e:
            logger.exception(f"Error getting host info: {e}")

    def get_os(self):
        if not self.os:
            # get from file
            self.os = "" 
        return self.os
    
    def get_platform_build(self):
        if not self.platform_build:
            # get from file
            self.platform_build = ""
        return self.platform_build
    
    def get_gg_version(self):
        if not self.gg_version:
            # get from file
            self.gg_version = ""
        return self.gg_version
    
    def get_role(self):
        if not self.role:
            # get from file
            self.role = ""
        return self.role
    
    def get_ip(self):
        if not self.ip:
            # get from file
            self.ip = ""
        return self.ip