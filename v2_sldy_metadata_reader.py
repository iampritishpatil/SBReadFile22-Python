import os
import sys
import pandas as pd
from pathlib import Path
from SBReadFile import SBReadFile

def list_sldy_files(root_dir):
    """ Recursively list all .sldy files in the given directory. """
    return [str(file) for file in Path(root_dir).rglob("*.sldy")]

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
            "comments": sb_reader.GetImageComments(capture_id),
            "num_positions": sb_reader.GetNumPositions(capture_id),
            "num_timepoints": sb_reader.GetNumTimepoints(capture_id),
            "num_channels": sb_reader.GetNumChannels(capture_id),
            "num_z_planes": sb_reader.GetNumZPlanes(capture_id),
            "is_video": sb_reader.GetNumTimepoints(capture_id) > 1,
            "is_zstack": sb_reader.GetNumZPlanes(capture_id) > 1,
            "date" : sb_reader.GetCaptureDate(capture_id),
            # "elapsed time" : sb_reader.GetElapsedTime(capture_id),
            
        }
        for ch in range(capture_info["num_channels"]):
            capture_info[f"channel_{ch}_name"] = sb_reader.GetChannelName(capture_id, ch)
            #"exposure time" : sb_reader.GetExposureTime(capture_id),
            capture_info[f"channel_{ch}_exposure_time"] = sb_reader.GetExposureTime(capture_id, ch)
            
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

        capture_info["shape"] = (
            capture_info["num_z_planes"],
            sb_reader.GetNumYRows(capture_id),
            sb_reader.GetNumXColumns(capture_id),
        )

        voxel_x, voxel_y, voxel_z = sb_reader.GetVoxelSize(capture_id)
        capture_info["voxel_size"] = (voxel_x, voxel_y, voxel_z)

        # Approximate dataset size (assuming uint16 data type)
        capture_info["size_mb"] = round(
            (capture_info["num_z_planes"] *
             capture_info["shape"][1] *
             capture_info["shape"][2] *
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
    df.to_csv(output_csv, index=False)
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
    for sldy_file in sldy_files:
        sldy_dir = Path(sldy_file).with_suffix(".dir")
        if not os.path.exists(sldy_dir):
            print(f"Error: Directory not found - {sldy_dir}")
            continue
        metadata = get_metadata(sldy_file)
        if metadata:
            all_metadata.extend(metadata)

    # Save metadata to CSV
    save_metadata_to_csv(all_metadata)

if __name__ == "__main__":
    main()
