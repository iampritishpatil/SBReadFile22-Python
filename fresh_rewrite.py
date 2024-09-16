import argparse
import sys
from pathlib import Path
from SBReadFile import SBReadFile, CNpyHeader
import time
import zarr
import numpy as np

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process some SLDY files with optional image number, channel number, and plot interval."
    )
    
    parser.add_argument('-s', '--sldy_file', required=True, help='Path to the SLDY file')
    parser.add_argument('-f', '--frames', type=int,required=True , default=10000, help="Total number of frames to copy")
    parser.add_argument('-i', '--image_number', type=int, default=0, help='Image number (default: 0)')
    parser.add_argument('-c', '--channel_number', type=int, default=0, help='Channel number (default: 0)')
    parser.add_argument('-fps', '--frames_per_second', type=int, default=20, help='Frames per second (default: 20)')
    parser.add_argument('-l', '--latency', type=float, default=10, help='Latency in seconds (default: 10)')
    parser.add_argument('-ch', '--chunks', type=int, default=128, help='Number of frames per chunk (default: 128)')
    parser.add_argument('-wp', '--write_path', type=str, default='example.zarr', help='Output path for the Zarr file')
    
    args = parser.parse_args()

    print("Arguments:")
    for arg, value in vars(args).items():
        print(f'{arg}: {value}')
    
    return args

def check_file_exists(file_path):
    """Check if the specified file exists."""
    if not file_path.exists():
        print(f'File not found: {file_path}')
        sys.exit(1)

def print_image_metadata(sb_reader, image_number):
    """Print metadata for the selected image."""
    image_name = sb_reader.GetImageName(image_number)
    num_positions = sb_reader.GetNumPositions(image_number)
    num_timepoints = sb_reader.GetNumTimepoints(image_number)
    num_channels = sb_reader.GetNumChannels(image_number)
    voxel_size = sb_reader.GetVoxelSize(image_number)
    capture_date = sb_reader.GetCaptureDate(image_number)
    comments = sb_reader.GetImageComments(image_number)

    print(f"Image name: {image_name}")
    print(f"Number of positions: {num_positions}")
    print(f"Number of timepoints: {num_timepoints}")
    print(f"Number of channels: {num_channels}")
    print(f"Voxel size: {voxel_size}")
    print(f"Capture date: {capture_date}")
    print(f"Comments: {comments}")

def frames_generator(latency, num_frames, chunks, fps):
    """Generate frame slices with specified latency and chunk size."""
    frames = 0
    print(f"Sleeping for latency of {latency} seconds...")
    time.sleep(latency)
    
    fps *=0.98 # reduce the fps by 2% prevent leading the frames

    sleep_time = chunks / fps
    print(f"Generating frames with {sleep_time:.2f} seconds sleep for each chunk.")
    start_time = time.time()
    
    while frames < num_frames - chunks:
        while (time.time() - start_time) < frames / fps:
                # print(f"Sleeping  {time.time():.2f} , { start_time:.2f} , {frames / fps:.2f}")
                time.sleep(sleep_time/4)
                
        yield slice(frames, frames + chunks)
        frames += chunks
    
    # Last slice
    time.sleep(sleep_time)
    yield slice(frames, num_frames)
    print(f"Finished generating frames in {time.time() - start_time:.2f} seconds.")

def process_sldy_file(params):
    """Process the SLDY file and write to a Zarr file."""
    sb_reader = SBReadFile()
    file_path = Path(params.sldy_file)
    
    check_file_exists(file_path)
    
    sldy_file = sb_reader.Open(str(file_path), All=False)
    print_image_metadata(sb_reader, params.image_number)

    slide = sb_reader.mDL
    image_group = slide.GetImageGroup(params.image_number)
    image_group.mNpyHeader = CNpyHeader()
    
    npy_file = Path(image_group.mFile.GetImageDataFile(image_group.mImageTitle, 0, 0))
    with open(npy_file, "rb") as file_stream:
        image_group.mNpyHeader.ParseNpyHeader(file_stream)

    # num_frames = image_group.mNpyHeader.mShape[0]
    num_frames = params.frames
    num_rows, num_columns = image_group.GetNumRows(), image_group.GetNumColumns()
    plane_size = num_rows * num_columns * image_group.mNpyHeader.mBytesPerPixel
    seek_offset = image_group.mNpyHeader.mHeaderSize

    print(f"Number of frames: {num_frames}")
    print(f"Image dimensions: {num_rows}x{num_columns}")
    
    chunk_len = params.chunks
    zarr_file = zarr.open(
        Path(params.write_path),
        mode='w',
        # shape=image_group.mNpyHeader.mShape,
        shape=(num_frames, num_rows, num_columns),
        dtype='u2',
        # chunks=(chunk_len, num_rows, num_columns),
        chunks=(chunk_len, 256, 256),
        write_empty_chunks=False,
        overwrite=True,
        fill_value=0
    )

    with open(npy_file, "rb") as file_stream:
        file_stream.seek(seek_offset, 0)
        for frame_slice in frames_generator(params.latency, num_frames, params.chunks, params.frames_per_second):
            read_len = frame_slice.stop - frame_slice.start
            frame_bytes = file_stream.read(plane_size * read_len)
            np_buffer = np.frombuffer(frame_bytes, dtype=np.uint16).reshape(read_len, num_rows, num_columns).copy()
            zarr_file[frame_slice] = np_buffer
            print(f"Processed frames {frame_slice}")

def main():
    """Main function to run the script."""
    params = parse_arguments()
    process_sldy_file(params)

if __name__ == "__main__":
    main()
