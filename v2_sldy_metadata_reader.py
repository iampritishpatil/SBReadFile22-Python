import os
import sys
import pandas as pd
from pathlib import Path
from SBReadFile import SBReadFile
import gc
from tqdm import tqdm
from collections import deque

def scan_files(path):
    """
    Generator that iterates over all files in a directory tree using a queue.
    
    Args:
        network_drive_path (str): Root path to start scanning.
    
    Yields:
        str: Full path of each file.
    """
    queue = deque([path])  # BFS-like queue for directory traversal

    while queue:
        current_dir = queue.popleft()  # Get the next directory to scan
        
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if entry.is_file():
                        yield entry  # Yield file immediately
                    elif entry.is_dir():
                        if "export" in entry.path:
                            continue
                        queue.append(entry.path)  # Add subdirectory to queue
        except PermissionError:
            print(f"Permission Error here. Skipping directory: {current_dir}")
            pass  # Skip directories without permission
        except Exception as e:
            print(f"Error: {e}. Skipping directory: {current_dir}")
            pass

# this was used to generate the list of sldy files
# def list_sldy_files(root_dir):
#     """ Recursively list all .sldy files in the given directory. """
#     sldy_files = []
#     sld_files = []
#     for file in tqdm(scan_files(root_dir), desc="Scanning files"):
#         tqdm.write(f"Found file: {file.path}")
#         if file.name.endswith(".sldy"):
#             sldy_files.append(str(file.path))
#         if file.name.endswith(".sld"):
#             sld_files.append(str(file.path))
#     with open("sldy_files.txt", "w") as f:
#         for item in sldy_files:
#             f.write("%s\n" % item)
#     with open("sld_files.txt", "w") as f:
#         for item in sld_files:
#             f.write("%s\n" % item)
#     return sldy_files

#loads from saved files
def list_sldy_files(root_dir):
    with open("sldy_files.txt", "r") as f:
        sldy_files = f.readlines()
    sldy_files = [x.strip() for x in sldy_files]
    return sldy_files


def get_metadata(sldy_path):
    """ Extract metadata from a given .sldy file. """
    sb_reader = SBReadFile()
    
    if not os.path.exists(sldy_path):
        print(f"Error: File not found - {sldy_path}")
        return None

    if not sb_reader.Open(sldy_path, All=False):
        print(f"Error: Unable to open file - {sldy_path}")
        return None

    metadata_list = []
    num_captures = sb_reader.GetNumCaptures()

    for capture_id in range(num_captures):
        capture_info = {
            "file_path": sldy_path,
            "capture_id": capture_id,
            "name": sb_reader.GetImageName(capture_id),
            "comments": sb_reader.GetImageComments(capture_id).replace('\n', ' ').replace('\r', ' '),
            "num_positions": sb_reader.GetNumPositions(capture_id),
            "num_timepoints": sb_reader.GetNumTimepoints(capture_id),
            "num_channels": sb_reader.GetNumChannels(capture_id),
            "num_z_planes": sb_reader.GetNumZPlanes(capture_id),
            "is_video": sb_reader.GetNumTimepoints(capture_id) > 1,
            "is_zstack": sb_reader.GetNumZPlanes(capture_id) > 1,
            "date": pd.Timestamp(*sb_reader.GetCaptureDate(capture_id)).strftime("%Y-%m-%d %H:%M:%S"),
        }
        for ch in range(capture_info["num_channels"]):
            try:
                capture_info[f"channel_{ch}_name"] = sb_reader.GetChannelName(capture_id, ch)
                #"exposure time" : sb_reader.GetExposureTime(capture_id),
                capture_info[f"channel_{ch}_exposure_time"] = sb_reader.GetExposureTime(capture_id, ch)
            except Exception as e:
                print(f"Error: {e}")
                capture_info[f"channel_{ch}_name"] = None
                capture_info[f"channel_{ch}_exposure_time"] = None            
        # tp = capture_info["num_timepoints"]
        # print(tp)
        # if tp >= 1:
            # capture_info["last_timepoint"] = sb_reader.GetElapsedTime(capture_id,1)

        if capture_info["is_video"]:
            try:
                capture_info["fps"] = sb_reader.GetSampleRate(capture_id)
                #"exposure time" : sb_reader.GetExposureTime(capture_id),
                # capture_info["exposure time"] = sb_reader.GetElapsedTime(capture_id,0)
                # print(capture_info["exposure time"])
            except Exception as e:
                # print(f"Error: {e}")
                capture_info["fps"] = None
                # capture_info["exposure time"] = None

        capture_info["shape_z"] = capture_info["num_z_planes"],
        capture_info["shape_x"] = sb_reader.GetNumXColumns(capture_id)
        capture_info["shape_y"] = sb_reader.GetNumYRows(capture_id)
        try:
            voxel_x, voxel_y, voxel_z = sb_reader.GetVoxelSize(capture_id)
            # capture_info["voxel_size"] = (voxel_x, voxel_y, voxel_z)
            capture_info["voxel_size_x"] = voxel_x
            capture_info["voxel_size_y"] = voxel_y
            capture_info["voxel_size_z"] = voxel_z
        except Exception as e:
            print(f"while getting voxel size Error: {e} ")
            # capture_info["voxel_size"] = (None, None, None)
            capture_info["voxel_size_x"] = None
            capture_info["voxel_size_y"] = None
            capture_info["voxel_size_z"] = None
        

        # Approximate dataset size (assuming uint16 data type)
        capture_info["size_mb"] = round(
            (capture_info["num_z_planes"] *
             capture_info["shape_x"] *
             capture_info["shape_y"] *
             capture_info["num_timepoints"] * 2) / (1024 * 1024), 2
        )

        metadata_list.append(capture_info)

    return metadata_list

def save_metadata_to_csv(metadata_list, output_csv="sldy_metadata.csv"):
    """ Save metadata to a CSV file. """
    if not metadata_list:
        print("No metadata extracted. No CSV file will be generated.")
        return

    df = pd.DataFrame(metadata_list)
    df.sort_values(by=["date"], inplace=True, ascending=False)
    df.to_csv(output_csv, index=False)
    df.to_parquet(output_csv.replace(".csv", ".parquet"), index=False)
    print(f"\nMetadata saved to: {output_csv}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    print(f"Scanning directory: {root_dir}\n")

    # Get all .sldy files in the directory
    sldy_files = list_sldy_files(root_dir)
    if not sldy_files:
        print("No .sldy files found.")
        sys.exit(1)

    print(f"Found {len(sldy_files)} .sldy files. Extracting metadata...\n")

    all_metadata = []
    for sldy_file in tqdm(sldy_files, desc="Processing .sldy files"):
        sldy_dir = Path(sldy_file).with_suffix(".dir")
        if not os.path.exists(sldy_dir):
            print(f"Error: Directory not found - {sldy_dir}")
            continue
        name_path = os.path.relpath(sldy_file, root_dir)
        tqdm.write(f"Processing file: {name_path}")
        metadata = get_metadata(sldy_file)
        if metadata:
            all_metadata.extend(metadata)
        gc.collect()
    # Save metadata to CSV
    save_metadata_to_csv(all_metadata, output_csv="sldy_metadata_new.csv")

if __name__ == "__main__":
    main()
    exit(0)