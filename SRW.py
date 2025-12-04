import os
from venv import logger
from bs4 import BeautifulSoup
import chardet

import ApsLog
import HostInfo
import myUtils


class SRW:
    def __init__(self, file_path):
        """Lightweight wrapper that unpacks a SRW support bundle.

        Instantiation does the minimum work needed to make the rest of the
        helper methods usable: store the provided bundle path, extract the
        archive to a working directory, and preload commonly requested
        metadata.  The intent is that other modules can simply create ``SRW``
        and immediately call ``get_*`` helpers without worrying about the
        extraction lifecycle.
        """
        self.file_path = file_path
        self.extracted_path = os.path.join(os.path.expanduser("~"), "Documents", "temp_zip_reader")
        # Host information will be populated after the bundle is unpacked.
        self.host_info = None
        self.license_info = None
        self.log_info = None
        # Hold parsed APS logs.  Using a list keeps ordering predictable for
        # downstream analysis and avoids duplicate parsing of the same bundle.
        self.aps_logs = []

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
        # Lazily populate APS logs so the class can be created even when the
        # caller only needs host or license information.
        if not self.aps_logs:
            self.get_file_path()

            if self.file_path is None:
                self.set_file_path()

            tempPath = "C:\\temp_zip_reader"
            myUtils.extract_zip(self.file_path, tempPath)

            # Iterate over extracted files and collect any APS HTML/log files.
            # The individual ``ApsLog`` instances stay short lived; we keep the
            # parsed results on ``self.aps_logs`` for future access.
            for file in os.listdir(tempPath):
                if file.startswith("aps_") and (file.endswith(".html") or file.endswith(".log")):
                    aps_log = ApsLog(file)
                    if aps_log.get_logs():
                        self.aps_logs.extend(aps_log.logs)
                    else:
                        logger.warning(f"No APS logs found in {file}.")

        return self.aps_logs

    def get_host_info(self):
        # Host information is created lazily because it depends on the
        # extracted bundle being available on disk.  ``HostInfo`` encapsulates
        # the parsing of OS, platform, and network details from the extracted
        # directory.
        if not self.host_info:
            self.host_info = HostInfo(os.path.dirname(self.file_path))
        return self.host_info

    def get_license_info(self):
        # Placeholder hook for when license parsing is implemented.  Returning
        # an empty dict keeps consumers defensive while making the current
        # contract explicit.
        if not self.license_info:
            self.license_info = {}
        return self.license_info