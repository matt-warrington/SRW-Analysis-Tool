import os
from ApsLog import ApsLog
import myUtils
import datetime

def user_active_at_time(sessions, username, dt_str):
    """
    Returns True if the user had an active session at the given datetime string (format: 'YYYY-MM-DD HH:MM:SS[.fff]').
    """
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    for sess in sessions:
        if sess[1]['user'].lower() != username.lower():
            continue
        # Parse start and end times
        try:
            # Try parsing with milliseconds, then without
            try:
                start = datetime.datetime.strptime(sess[1]['start'], "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                start = datetime.datetime.strptime(sess[1]['start'], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue  # skip if start is missing or invalid
        if sess[1]['end']:
            try:
                end = datetime.datetime.strptime(sess[1]['end'], "%Y-%m-%d %H:%M:%S.%f")
            except Exception:
                end = datetime.datetime.strptime(sess[1]['end'], "%Y-%m-%d %H:%M:%S")
        else:
            end = None
        # Check if dt is within session
        if start <= dt and (end is None or dt <= end):
            # we should change this to include if there is no start time, in case the session started in another APS log
            return True
    return False

# Example usage:
if __name__ == "__main__":
    path = myUtils.select_dir("APS Log", "*.html *.log")

    users = []
    sessions = []
    for file in os.listdir(path):
        if file.startswith("aps_") and (file.endswith(".html") or file.endswith(".log")):
            file_path = os.path.join(path, file)
            print(f"Found APS Log file: {file_path}")
            aps_log = ApsLog(file_path)

            print("Getting users...")
            users_this_log = aps_log.get_users()
            print(f"User count = {len(users_this_log)}")
            users.extend(u for u in users_this_log if u not in users)

            print("Getting sessions...")
            sessions_this_log = aps_log.get_sessions()
            print(f"Session count = {len(sessions_this_log)}")
            if len(sessions_this_log.items()) > 0:
                sessions.extend(sessions_this_log.items())  # don't care about unique session IDs

    username = input("Enter username to check: ").strip()
    dt_str = input("Enter datetime to check (YYYY-MM-DD HH:MM:SS): ").strip()
    active = user_active_at_time(sessions, username, dt_str)
    print(f"Was user '{username}' active at {dt_str}? {'Yes' if active else 'No'}")
'''
path = myUtils.select_dir("APS Log", "*.html *.log")

users = []
sessions = []
for file in os.listdir(path):
    if file.startswith("aps_") and (file.endswith(".html") or file.endswith(".log")):
        file_path = os.path.join(path, file)
        print(f"Found APS Log file: {file_path}")
        aps_log = ApsLog(file_path)

        print("Getting users...")
        users_this_log = aps_log.get_users()
        print(f"User count = {len(users_this_log)}")
        users.extend(u for u in users_this_log if u not in users)

        print("Getting sessions...")
        sessions_this_log = aps_log.get_sessions()
        print(f"Session count = {len(sessions_this_log)}")
        if len(sessions_this_log.items()) > 0:
            sessions.extend(sessions_this_log.items())  # don't care about unique session IDs

if users:
    print(f'\nUsers found: {users}')
else:
    print("\nNo users found in APS Log.")

#sessions = aps_log.get_sessions()
if sessions:
    print("\nSessions found in APS Log:")
    myUtils.print_nested_dict(sessions)
else:
    print("\nNo sessions found in APS Log.")

if users:
    sessions = aps_log.get_sessions(users[0])
    if sessions:
        print(f"\nSessions found for user {users[0]}:")
        myUtils.print_nested_dict(sessions)
    else:
        print(f"\nNo sessions found in APS Log for user {users[0]}.")

'''