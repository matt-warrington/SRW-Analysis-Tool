import os
import re
from venv import logger

from bs4 import BeautifulSoup
import chardet


class ApsLog:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.logs = []
        self.start_time = None
        self.end_time = None
        self.users = []
        self.sessions = {}

    def get_logs (self):
        if not self.logs:
            try:
                logger.info(f"Loading logs from {self.file_name}")
                self.logs = self.load_log_file()
            except Exception as e:
                logger.error(f"Error loading logs from {self.file_name}: {e}")
                self.logs = []
            
        return self.logs

    def load_log_file(self):
        log_entries_formatted = []
        if self.file_path.endswith('.log'):
            try:
                # Detect the encoding
                with open(self.file_path, 'rb') as file:
                    raw_data = file.read()
                    detected_encoding = chardet.detect(raw_data)['encoding']
                
                logger.info(f"Detected encoding for {self.file_path }: {detected_encoding}")  # Debug statement
                
                # Try opening the file with the detected encoding
                log_entries = []
                try:
                    with open(self.file_path , 'r', encoding=detected_encoding) as file:
                        log_entries.extend(file.readlines())
                except (UnicodeDecodeError, TypeError):
                    # Fallback to utf-8 if the detected encoding fails
                    logger.warning(f"Failed to decode with detected encoding ({detected_encoding}). Falling back to utf-8.")
                    with open(self.file_path , 'r', encoding='utf-8', errors='replace') as file:
                        log_entries.extend(file.readlines())

                basic_log_pattern = re.compile(
                    r'<!--\s*SituationID=(?P<SituationID>\d+)\s*-->\s*'
                    r'(?P<Date>\d{4}-\d{2}-\d{2})\s+'
                    r'(?P<Time>\d{2}:\d{2}:\d{2}\.\d{3})\s*'
                    r'(?P<Description>.+)'
                )
                
                for i, entry in enumerate(log_entries):
                    user = server = process = pid = session = ''

                    basic_log = basic_log_pattern.match(entry)
                    if not basic_log:
                        continue

                    description = basic_log.group('Description').strip()
                    date = basic_log.group('Date').strip()
                    time = basic_log.group('Time').strip()
                    
                    # Search the description for the patterns that match
                    # users, servers, processes, PIDs, and sessions
                    # Try to match full pattern first
                    full_pattern = r'^(\S+) on (\S+)(?: \(\d+\))?, (\S+) \((\d+)\)'
                    full_match = re.match(full_pattern, description)
                    
                    if full_match:
                        user, server, process, pid = full_match.groups()
                        description = description[full_match.end():].strip()
                    else:
                        # Fall back to just process and PID
                        process_pid_pattern = r'^(\S+) \((\d+)\)'
                        process_match = re.match(process_pid_pattern, description)
                        if process_match:
                            process, pid = process_match.groups()
                            description = description[process_match.end():].strip()
                    
                    # Look for Session ID in the remaining description
                    session_pattern = r'Session ID (\d+):'
                    session_match = re.search(session_pattern, description)
                    if session_match:
                        session = session_match.group(1)
                        # Remove the session info from description
                        description = description.replace(session_match.group(0), '').strip()

                    entry_formatted =  {
                        'Line': i,
                        'Date': date,
                        'Time': time,
                        'User': user,
                        'Server': server,
                        'Process': process,
                        'PID': pid,
                        'Session': session,
                        'Description':description,
                        'Keys': [],
                        'File': self.file_name
                    }
                    log_entries_formatted.append(entry_formatted)
            except FileNotFoundError:
                logger.exception(f"File not found: {self.file_path }")
                raise RuntimeError(f"File not found: {self.file_path }")
            except PermissionError:
                logger.exception(f"Permission denied: {self.file_path }")
                raise RuntimeError(f"Permission denied: {self.file_path }")
            except Exception as e:
                logger.exception(f"Error loading log file: {e}")
                raise RuntimeError(f"Error loading log file: {e}")
        else:
            logs_bs = None

            try:
                with open(self.file_path, 'r', encoding='utf-16') as file:
                    content = file.read()
                    logs_bs = BeautifulSoup(content, 'html.parser')
            except FileNotFoundError:
                        logger.exception(f"File not found: {self.file_path}")
                        raise RuntimeError(f"File not found: {self.file_path}")
            except PermissionError:
                logger.exception(f"Permission denied: {self.file_path}")
                raise RuntimeError(f"Permission denied: {self.file_path}")
            except Exception as e:
                logger.exception(f"Error loading log file: {e}")
                try:
                    with open(self.file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        logs_bs = BeautifulSoup(content, 'html.parser')
                except Exception as e2:
                    logger.exception(f"Error loading log file: {e}")
                    logger.warning(f"Initial read of {self.file_path} failed. Trying to detect encoding.")
                    try:
                        # Detect the encoding
                        with open(self.file_path, 'rb') as file:
                            raw_data = file.read()
                            detected_encoding = chardet.detect(raw_data)['encoding']
                        
                        logger.info(f"Detected encoding for {self.file_path}: {detected_encoding}")  # Debug statement
                        
                        # Try opening the file with the detected encoding
                        try:
                            with open(self.file_path, 'r', encoding=detected_encoding ) as file:
                                content = file.read()
                                logs_bs = BeautifulSoup(content, 'html.parser')
                        except (UnicodeDecodeError, TypeError):
                            # Fallback to utf-8 if the detected encoding fails
                            logger.warning(f"Failed to decode with detected encoding ({detected_encoding}). Falling back to utf-8.")
                            with open(self.file_path, 'r', encoding='utf-8', errors='replace') as file:
                                content = file.read()
                    except Exception as e:
                        logger.exception(f"Error loading log file: {e}")
                        raise RuntimeError(f"Error loading log file: {e}")
                    
            if logs_bs:
                log_entries_formatted = self.extract_log_entries(logs_bs)
        
        return log_entries_formatted

    def extract_log_entries(self, soup):
        log_entries = []
        
        log_section = soup.find('a', {'name': 'LogEntries'})
        if log_section:
            log_table = log_section.find_next('table')
            
            if log_table:
                rows = log_table.find_all('tr')[1:]
        
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) != 0:
                        description = cells[3].text.strip()
                        user = server = process = pid = session = ''
                        
                        # Try to match full pattern first
                        pattern = r'^(\S+) on (\S+)(?: \(\d+\))?, (\S+) \((\d+)\)'
                        match = re.match(pattern, description)
                        
                        if match:
                            user, server, process, pid = match.groups()
                            description = description[match.end():].strip()
                        else:
                            # Fall back to just process and PID
                            process_pid_pattern = r'^(\S+) \((\d+)\)'
                            process_match = re.match(process_pid_pattern, description)
                            if process_match:
                                process, pid = process_match.groups()
                                description = description[process_match.end():].strip()
                        
                        # Look for Session ID in the remaining description
                        session_pattern = r'Session ID (\d+):'
                        session_match = re.search(session_pattern, description)
                        if session_match:
                            session = session_match.group(1)
                            # Remove the session info from description
                            description = description.replace(session_match.group(0), '').strip()
                        
                        entry = {
                            'Line': cells[0].text.strip(),
                            'Date': cells[1].text.strip(),
                            'Time': cells[2].text.strip(),
                            'User': user,
                            'Server': server,
                            'Process': process,
                            'PID': pid,
                            'Session': session,
                            'Description': description,
                            'Keys': [],
                            'File': self.file_name
                        }
                        log_entries.append(entry)
            else:
                logger.error(f"Warning: No log table found in {self.file_name}. This file may not contain log entries.")
                return []
        else: 
            logger.error(f"Warning: No log section found in {self.file_name}. This file may not contain log entries.")
            return []    
        
        return log_entries

    def get_users(self):
        if not self.users:
            if self.get_logs():
                for log in self.logs:
                    if log['User'] and not re.match(r'^Logon\d+$', log['User']) and log['User'] not in self.users:
                        self.users.append(log['User'])
        return self.users
    
    def get_sessions(self, user=None):
        """
        Tracks all sessions in the APS log.
        For each session, tracks:
            - user (from 'logged on to session' entry)
            - start time (from 'logged on to session' entry)
            - end time (from 'Session ___ stopped.' entry)
        Returns a dict: {session_id: {'user': ..., 'start': ..., 'end': ...}}
        If a user is specified, only sessions for that user are returned.
        """
        if not self.sessions:
            if self.get_logs():
                for log in self.logs:
                    if not log['User'] or not log['Session']:
                        continue

                    description = log.get('Description', '')

                    # Session start
                    if 'logged on to session' in description.lower():
                        session_id = log.get('Session', '')
                        log_user = log.get('User', '')
                        dt_str = f"{log.get('Date', '')} {log.get('Time', '')}"
                        
                        self.sessions[session_id] = {
                            'user': log_user,
                            'start': dt_str,
                            'end': None
                        }
                    # Session end: look for "Session ___ stopped."
                    else:
                        match = re.search(r'Session\s+["\']?.+?["\']?\s+stopped\.', description, re.IGNORECASE)
                        if match:
                            session_id = log.get('Session', '')
                            log_user = log.get('User', '')
                            dt_str = f"{log.get('Date', '')} {log.get('Time', '')}"

                            if session_id in self.sessions:
                                self.sessions[session_id]['end'] = dt_str
                            else:
                                self.sessions[session_id] = {
                                    'user': log_user,
                                    'start': None,
                                    'end': dt_str
                            }
        if user is None:
            return self.sessions
        else:
            # Filter sessions for the specified user
            return {sid: sess for sid, sess in self.sessions.items() if sess['user'] == user}