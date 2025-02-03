#%%
import os
from pathlib import Path
# %%
path = Path("/Users/pritish/Documents/2p_data")

file_extension = ".sldy"

# Step 1: Collect all file paths efficiently
all_files = []

def scan_directory(directory):
    """Recursively scans directory using os.scandir() and collects all file paths."""
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_file():
                    all_files.append(entry.path)  # Collect full file path
                elif entry.is_dir():  # Recurse into subdirectories
                    scan_directory(entry.path)
    except PermissionError:
        pass  # Skip directories without permission

scan_directory(path)

# Step 2: Filter files by extension
filtered_files = [file for file in all_files if file.endswith(file_extension)]

# Step 3: Process filtered files
for file in filtered_files:
    print(file)

# %%


import os
from collections import deque

def scan_files(path, file_extension=None):
    """
    Generator that iterates over all files in a directory tree using a queue.
    
    Args:
        network_drive_path (str): Root path to start scanning.
        file_extension (str, optional): If provided, yields only files with this extension.
    
    Yields:
        str: Full path of each matching file.
    """
    queue = deque([path])  # BFS-like queue for directory traversal

    while queue:
        current_dir = queue.popleft()  # Get the next directory to scan
        
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if entry.is_file():
                        if file_extension is None or entry.name.endswith(file_extension):
                            yield entry.path  # Yield file immediately
                    elif entry.is_dir():
                        queue.append(entry.path)  # Add subdirectory to queue
        except PermissionError:
            print(f"Permission Error here. Skipping directory: {current_dir}")
            pass  # Skip directories without permission
        except Exception as e:
            print(f"Error: {e}. Skipping directory: {current_dir}")
            pass

for file in scan_files(path, file_extension):
    print(file)  # Process file immediately without storing all in memory

# %%
