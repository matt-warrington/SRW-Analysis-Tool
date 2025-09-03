import os
from venv import logger
from bs4 import BeautifulSoup
import chardet

import ApsLog
import HostInfo
import myUtils


class SRW:
    def __init__(self, file_path):
        self.file_path = file_path
        self.extracted_path = os.path.join(os.path.expanduser("~"), "Documents", "temp_zip_reader")
        self.host_info = {
            'OS': "",
            'platformBuild': "",
            'gg_version': "",
            'serverRole': "",
            'IP': ""
        }
        self.license_info = None
        self.log_info = None
        self.aps_logs = None

        self.extract_zip(self.file_path, self.extracted_path)
        self.get_aps_logs()
        self.get_host_info()
        self.get_license_info()
    
    def extract_zip(self, zip_path, extract_to):
        """
        Extracts the contents of a zip file to a specified directory.
        
        Args:
            zip_path (str): The path to the zip file.
            extract_to (str): The directory where the contents should be extracted.
        """
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)
        
        myUtils.extract_zip(zip_path, extract_to)

    def get_file_path(self):
        return self.file_path
    def set_file_path(self, path = None):
        # Placeholder: set self.file_path here
        if (path == None):
            myUtils.selectFile("SRW .zip", "*.zip")

        self.file_path = path  # Replace with actual logic

    def get_aps_logs(self):
        if not self.aps_logs:
            self.get_file_path()

            if self.file_path is None:
                self.set_file_path()
            
            tempPath = "C:\\temp_zip_reader"
            myUtils.extract_zip(self.file_path, tempPath)

            # Check all files in the folder tempPath and add each file of the format aps_*.html or aps_*log to self.aps_logs
            for file in os.listdir(tempPath):
                if file.startswith("aps_") and (file.endswith(".html") or file.endswith(".log")):
                    aps_log = ApsLog(file)
                    if aps_log.get_logs():
                        self.aps_logs.extend(aps_log.logs)
                    else:
                        logger.warning(f"No APS logs found in {file}.")

        return self.aps_logs
    
    def get_host_info(self):
        if not self.host_info:
            # Placeholder: set self.host_info here
            self.host_info = HostInfo(os.path.dirname(self.file_path))
        return self.host_info
    
    def get_license_info(self):
        if not self.license_info:
            # TODO: Implement logic to extract license info from the zip file or CLS
            self.license_info = {}
        return self.license_info