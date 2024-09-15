import argparse
import sys
from pathlib import Path
from SBReadFile import *
import time
import zarr
import numpy as np

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Process some sldy files with optional image number, channel number, and plot interval."
    )
    
    parser.add_argument('-s', '--sldy_file', required=True, 
                        help='Path to the sldy file')
    parser.add_argument('-i', '--image_number', type=int, default=0, 
                        help='Image number (default: 0)')
    parser.add_argument('-c', '--channel_number', type=int, default=0, 
                        help='Channel number (default: 0)')
    # parser.add_argument('-p', '--plot_interval', type=int, default=10, 
    #                     help='Plot interval (default: 10)')
    parser.add_argument('-fps', '--frames_per_second', type=int, default=20, 
                        help='Frames per second (default: 30)')    
    parser.add_argument('-l', '--latency', type=float, default=10, 
                        help='Latency in seconds (default: 10)')
    parser.add_argument('-ch', '--chunks', type=float, default=128, 
                        help='Latency in seconds (default: 128)')
    parser.add_argument('-wp', '--write_path', type=str, default='example.zarr')
    args = parser.parse_args()

    
    #print the arguments with a dictionary
    print("Arguments:")
    for arg in vars(args):
        print(f'{arg}: {getattr(args, arg)}')

    
    return args

def main():
    SBFileReader = SBReadFile()

    # Call the function in main to parse the arguments
    params = parse_arguments()

    file_path = Path(params.sldy_file)
    if not file_path.exists():
        print(f'File not found: {file_path}')
        sys.exit()
    sldy_file = SBFileReader.Open(str(file_path),All=False)
    image_name = SBFileReader.GetImageName(params.image_number)



    num_positions = SBFileReader.GetNumPositions(params.image_number)
    num_timepoints = SBFileReader.GetNumTimepoints(params.image_number)
    num_channels = SBFileReader.GetNumChannels(params.image_number)
    voxel_size = SBFileReader.GetVoxelSize(params.image_number)
    capture_date = SBFileReader.GetCaptureDate(params.image_number)

    comments = SBFileReader.GetImageComments(params.image_number)

    print(f"Image name: {image_name}")
    print(f"Number of positions: {num_positions}")
    print(f"Number of timepoints: {num_timepoints}")
    print(f"Number of channels: {num_channels}")
    print(f"Voxel size: {voxel_size}")
    print(f"Capture date: {capture_date}")
    print(f"Comments: {comments}")


    # num_rows = SBFileReader.GetNumYRows(params.image_number)
    # num_columns = SBFileReader.GetNumXColumns(params.image_number)
    # num_planes = SBFileReader.GetNumZPlanes(params.image_number)
    # # Your processing logic goes here
    # print(f"Number of rows: {num_rows}")
    # print(f"Number of columns: {num_columns}")
    # print(f"Number of planes: {num_planes}")


    slide=SBFileReader.mDL
    image_group = slide.GetImageGroup(params.image_number)
    num_rows = image_group.GetNumRows()
    num_columns = image_group.GetNumColumns()
    num_planes = image_group.GetNumPlanes()
    image_group.mNpyHeader = CNpyHeader()
    print(f"Number of rows: {num_rows}")
    print(f"Number of columns: {num_columns}")
    print(f"Number of planes: {num_planes}")
    

    npy_file=Path(image_group.mFile.GetImageDataFile(image_group.mImageTitle, 0, 0))
    with open(npy_file, "rb") as file_stream:
        theRes = image_group.mNpyHeader.ParseNpyHeader(file_stream)
        thePlaneSize = num_rows * num_columns * image_group.mNpyHeader.mBytesPerPixel
        theSeekOffset = image_group.mNpyHeader.mHeaderSize
        print(f"Plane size: {thePlaneSize}")
        print(f"Seek offset: {theSeekOffset}")
        print(f"Image group: {image_group}")
        print("theRes: ",theRes)

    num_frames = image_group.mNpyHeader.mShape[0]
    print(f"Number of frames: {num_frames}")
    print(image_group.mNpyHeader.mShape)

    def frames_generator():
        frames = 0
        print(f"Sleeping for latency of {params.latency} seconds")
        
        time.sleep(params.latency)
        print(f"Generating frames")
        sleep_time = params.chunks/params.frames_per_second
        print(f"will sleep for {sleep_time} seconds for each chunk")
        chunk_num = 0
        first_time = time.time()
        curr_time = time.time()
        print(f"last time: {curr_time}")
        while frames < num_frames-params.chunks:
            while time.time() - curr_time < sleep_time:
                time.sleep(0.01)
            curr_time = time.time()
            yield slice(frames, frames + params.chunks)
            frames += params.chunks
        #last slice

        yield slice(frames, num_frames)
        print(f"Finished generating frames")
        print(f"Total time taken: {time.time()-first_time}")

    
    
    frame = 0
    chunk_len = params.chunks
    chunk_buf = np.zeros((chunk_len,num_rows,num_columns),dtype=np.uint16)



    zarr_file = zarr.open(Path(params.write_path), 
                mode='w', 
                shape=image_group.mNpyHeader.mShape, 
                dtype='u2', 
                # chunks=(chunk_len,num_rows,num_columns),
                chunks=(chunk_len,chunk_len,chunk_len),                
                write_empty_chunks=False,
                overwrite=True,
                fill_value=0
        )    
    with open(npy_file, "rb") as file_stream:
        file_stream.seek(theSeekOffset,0)
        # frames_array = np.arange(num_frames)
        for frame_slice in frames_generator():
            # print(frame_slice)
            # iterator = range(frame_slice.start, frame_slice.stop, frame_slice.step)
            # for i,mod in zip(frames_array[frame_slice],range(chunk_len)):
            #     frame_bytes = file_stream.read(thePlaneSize)
            #     np_buffer = np.frombuffer(frame_bytes, dtype=np.uint16)
            #     np_buffer = np_buffer.reshape(num_rows, num_columns)
            #     chunk_buf[mod, :, :] = np_buffer
            #     # print(i,frame)
            #     assert(i == frame, "frame number mismatch")
            read_len = frame_slice.stop-frame_slice.start
            frame_bytes = file_stream.read(thePlaneSize * read_len)
            np_buffer = np.frombuffer(frame_bytes, dtype=np.uint16).reshape(read_len, num_rows, num_columns)
            chunk_buf[:read_len, :, :] = np_buffer[:, :, :]

            # print(chunk_buf.shape)
            # print(chunk_buf.flatten())
            zarr_file[frame_slice] = chunk_buf[:read_len,:,:]
            print(f"Processed frames {frame_slice}")

if __name__ == "__main__":
    main()