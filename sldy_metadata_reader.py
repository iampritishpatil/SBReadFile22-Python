import os
import json
import numpy as np
import sys
from SBReadFile import SBReadFile
from pathlib import Path
import pandas as pd

def list_sldy_files(sldy_path):
    """ List all files in the SLDY directory """
    file_list = []
    for root, _, files in os.walk(sldy_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)
    return file_list

def get_metadata(sldy_path):
    """ Extract metadata from the SLDY file """
    sb_reader = SBReadFile()
    
    if not os.path.exists(sldy_path):
        print(f"Error: SLDY file '{sldy_path}' not found.")
        return None

    # Try to open the SLDY file
    res = sb_reader.Open(sldy_path, All=False)
    if not res:
        print(f"Error: Unable to open SLDY file '{sldy_path}'")
        return None

    metadata = {}
    
    num_captures = sb_reader.GetNumCaptures()
    metadata["num_captures"] = num_captures
    metadata["captures"] = []

    for capture_id in range(num_captures):
        capture_info = {}

        capture_info["name"] = sb_reader.GetImageName(capture_id)
        capture_info["comments"] = sb_reader.GetImageComments(capture_id)
        capture_info["num_positions"] = sb_reader.GetNumPositions(capture_id)
        capture_info["num_timepoints"] = sb_reader.GetNumTimepoints(capture_id)
        capture_info["num_channels"] = sb_reader.GetNumChannels(capture_id)

        # Determine if it's a time-lapse (video) or a Z-stack
        is_video = capture_info["num_timepoints"] > 1
        is_zstack = sb_reader.GetNumZPlanes(capture_id) > 1

        capture_info["is_video"] = is_video
        capture_info["is_zstack"] = is_zstack

        # Frame rate (FPS)
        if is_video:
            try:
                fps = sb_reader.GetSampleRate(capture_id)  # Try to get FPS if available
            except:
                fps = None
            capture_info["fps"] = fps

        # Get image dimensions
        num_rows = sb_reader.GetNumYRows(capture_id)
        num_cols = sb_reader.GetNumXColumns(capture_id)
        num_planes = sb_reader.GetNumZPlanes(capture_id)

        capture_info["shape"] = (num_planes, num_rows, num_cols)
        
        # Get voxel size
        voxel_x, voxel_y, voxel_z = sb_reader.GetVoxelSize(capture_id)
        capture_info["voxel_size"] = (voxel_x, voxel_y, voxel_z)

        # Get dataset size (approximate)
        capture_info["size_mb"] = round((num_planes * num_rows * num_cols * capture_info["num_timepoints"] * 2) / (1024 * 1024), 2)  # Assuming uint16

        metadata["captures"].append(capture_info)

    return metadata

def print_metadata(metadata):
    """ Pretty-print the extracted metadata """
    if metadata is None:
        return

    print("\n### SLDY File Metadata ###")
    print(f"Total Captures: {metadata['num_captures']}\n")

    for idx, capture in enumerate(metadata["captures"]):
        print(f"Capture {idx+1}: {capture['name']}")
        print(f"  - Comments: {capture['comments']}")
        print(f"  - Positions: {capture['num_positions']}")
        print(f"  - Timepoints: {capture['num_timepoints']}")
        print(f"  - Channels: {capture['num_channels']}")
        print(f"  - Shape: {capture['shape']}")
        print(f"  - Voxel Size (X, Y, Z): {capture['voxel_size']}")
        print(f"  - Approximate Size: {capture['size_mb']} MB")
        if capture["is_video"]:
            print(f"  - FPS: {capture['fps']}")
        print(f"  - Z-Stack: {'Yes' if capture['is_zstack'] else 'No'}")
        print(f"  - Video: {'Yes' if capture['is_video'] else 'No'}")
        print("-" * 50)
        def metadata_to_dataframe(metadata):
            """ Convert metadata to a pandas DataFrame """
            if metadata is None:
                return pd.DataFrame()

            captures = metadata["captures"]
            df = pd.DataFrame(captures)
            return df

        # Convert metadata to DataFrame and print
        df = metadata_to_dataframe(metadata)
        print("\n### Metadata DataFrame ###")
        print(df.T)
def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_sldy>")
        sys.exit(1)

    sldy_path = sys.argv[1]

    # List all files inside the SLDY directory
    files = list_sldy_files(sldy_path)
    print(f"\n### Files in SLDY Directory ({sldy_path}) ###")
    for file in files:
        print(f"  - {file}")

    # Extract metadata
    metadata = get_metadata(sldy_path)

    # Print metadata
    print_metadata(metadata)

if __name__ == "__main__":
    main()
