__copyright__  = "Copyright (c) 2022, Intelligent Imaging Innovations, Inc. All rights reserved.  All rights reserved."
__license__  = "This source code is licensed under the BSD-style license found in the LICENSE file in the root directory of this source tree."

from SBReadFile import *
from matplotlib import pyplot as plt
import numpy as np
import sys, getopt
import time
from numpy.lib.format import open_memmap
import matplotlib.pyplot as plt

import zarr

def print_usage():
    print ('usage:\npython ',os.path.basename(__file__),' -s sldy_file [-i image_number] [-c channel_number] [-p plot_interval] [-r sample_rate]')
    print ('or (long form)\npython ',os.path.basename(__file__),' --sldy_file=file_path [--image_number=value] [--channel_number=value] [--plot_interval=value] [--sample_rate=value]')


def parse_arguments(argv):
    if len(argv) < 3:
        print_usage()
        sys.exit(2)

    theFileName = ''
    theCapture = 0
    theChannel = 0
    thePlotFrequency = 10
    sampleRate = 1  # Default sample rate

    try:
        opts, args = getopt.getopt(argv,"hi:c:p:s:r:",["help","sldy_file=","image_number=","channel_number=","plot_interval=","sample_rate="])
    except getopt.GetoptError as err:
        print(err)
        print_usage()
        sys.exit()
    print (opts)
    for opt, arg in opts:
        if opt in ("-h","--help"):
            print_usage()
            sys.exit()
        elif opt in ("-s", "--sldy_file"):
            theFileName = arg
        elif opt in ("-i", "--image_number"):
            theCapture = int(arg)
        elif opt in ("-c", "--channel_number"):
            theChannel = int(arg)
        elif opt in ("-p", "--plot_interval"):
            thePlotFrequency = int(arg)
        elif opt in ("-r", "--sample_rate"):
            sampleRate = float(arg)

    if theFileName == "":
        print_usage()
        sys.exit()

    print ('Input file: ', theFileName,' image number: ',theCapture, ' channel number: ',theChannel, ' sample rate: ', sampleRate)

    return theFileName, theCapture, theChannel, thePlotFrequency, sampleRate


def main(argv):
    theSBFileReader = SBReadFile()

    #work on the first capture
    theCapture = 0
    #work on the first channel
    theChannel = 0
    #plot frequency in timepoints
    thePlotFrequency = 10
    #sample rate in Hz
    sampleRate = 1



    # Call the function in main to parse the arguments
    theFileName, theCapture, theChannel, thePlotFrequency, sampleRate = parse_arguments(sys.argv[1:])

    theSecToWait = 500
    #this secion tries to open the file and see if there is data
    #otherwise it retries every second up to "theSecToWait" seconds
    for theTry in range(1,theSecToWait):
        if os.path.isfile(theFileName) == True:
            try:
                theRes = theSBFileReader.Open(theFileName,All=False) # do not load all the metadata, just essential
                theImageName = theSBFileReader.GetImageName(theCapture)
                break
            except Exception as err:
                print ('Error: ',err)
                raise(err)
                time.sleep(1) # sleep 1 sec
                print (theTry,"...")
                continue
        elif theTry==1:
            print ('Input file does not exist, retrying for up to ' , theSecToWait, " seconds\nOr hit Ctrl+c to exit")
        if theTry == theSecToWait-1:
            print ('Giving up')
            sys.exit()
        time.sleep(1) # sleep 1 sec
        print (theTry,"...")
        

    theRes = theSBFileReader.Open(theFileName,All=False) # do not load all the metadata, just essential
    if not theRes:
        #print ('Cannot open the file: ', theFileName)
        sys.exit()


    
    theImageName = theSBFileReader.GetImageName(theCapture)
    print ("*** the image name: ",theImageName)

    theImageComments = theSBFileReader.GetImageComments(theCapture)
    print ("*** the image comments: ",theImageComments)

    theNumPositions = theSBFileReader.GetNumPositions(theCapture)
    print ("*** the image num positions: ",theNumPositions)

    theNumTimepoints = theSBFileReader.GetNumTimepoints(theCapture)
    print ("*** the image num timepoints: ",theNumTimepoints)

    theNumChannels = theSBFileReader.GetNumChannels(theCapture)
    print ("*** the image num channels: ",theNumChannels)

    theX,theY,theZ = theSBFileReader.GetVoxelSize(theCapture)
    print ("*** the voxel x,y,z size is: ",theX,theY,theZ)

    theY,theM,theD,theH,theMn,theS = theSBFileReader.GetCaptureDate(theCapture)
    print ("*** the date yr/mn/day/hr/min/sec is: ",theY,theM,theD,theH,theMn,theS)


    theNumRows = theSBFileReader.GetNumYRows(theCapture)
    theNumColumns = theSBFileReader.GetNumXColumns(theCapture)
    theNumPlanes = theSBFileReader.GetNumZPlanes(theCapture)

    theZplane = int(theNumPlanes/2)
    theFirstTP = 0
    theNoProgress = 0;
    theTimePaused = 0;
    theMaxWaitS = 5 # wait at most 5 seconds. If over this, quit
    theSleepS = 0.01 # sleep between refreshes
    latency_const = 10 

    st = time.time()

    # Time per frame based on sample rate (in seconds)
    time_per_frame = 1.0 / sampleRate


    
    # for theRetry in range(0,10000):
        # print ("*** theRetry: ",theRetry)
    s=theSBFileReader.mDL
    #theImageGroup = s.GetImageGroup(inCaptureId)
    theImageGroup = s.GetImageGroup(1)
    theNumRows = theImageGroup.GetNumRows()
    theNumColumns = theImageGroup.GetNumColumns()
    theNumPlanes = theImageGroup.GetNumPlanes()
    # thePath = theImageGroup.mFile.GetImageDataFile(theImageGroup.mImageTitle, inChannelIndex, theSbTimepointIndex)
    # img_artist = plt.imshow(np.zeros((theNumRows,theNumColumns)))
    theImageGroup.mNpyHeader = CNpyHeader()
    
    # thePath = theImageGroup.mFile.GetImageDataFile(theImageGroup.mImageTitle, 0, 10)
    from pathlib import Path
    p=Path(theImageGroup.mFile.GetImageDataFile(theImageGroup.mImageTitle, 0, 0))
    with open(p, "rb") as theStream:
        theRes = theImageGroup.mNpyHeader.ParseNpyHeader(theStream)
        thePlaneSize = theNumColumns * theNumRows * theImageGroup.mNpyHeader.mBytesPerPixel
        theSeekOffset = theImageGroup.mNpyHeader.mHeaderSize


    chunk_len = 32 #take as parameter
    z = zarr.open(Path(r"Y:\FIOLA_DATA\data_crap\example.zarr"), 
                mode='w', 
                shape=theImageGroup.mNpyHeader.mShape, 
                dtype='u2', 
                chunks=(chunk_len,theNumRows,theNumColumns),
                write_empty_chunks=False,
                overwrite=True,
                fill_value=0
        )

    
    chunk_buf = np.zeros((chunk_len,theNumRows,theNumColumns),dtype=np.uint16)
    frame = 0
    print(f"the image shape should be {theImageGroup.mNpyHeader.mShape}")
    print(f"the number of timepoints is {theNumTimepoints}")
    time.sleep(latency_const)
    with open(p, "rb") as theStream:
        theStream.seek(theSeekOffset,0)
        while frame < theImageGroup.mNpyHeader.mShape[0]:  # Loop over all the frames
            print(f"Processing frame {frame}")

            ouBuf = theStream.read(thePlaneSize)  # Read data from the file
            # if not ouBuf:  # If no more data is available, wait
            #     time.sleep(0.01)
            #     print("Refreshing file reader")
            #     theSBFileReader.Refresh(theCapture)  # Refresh the capture to check for new data
            #     theNumTimepoints = theSBFileReader.GetNumTimepoints(theCapture) - 1
            #     z.resize((theNumTimepoints, theNumRows, theNumColumns))
            #     continue

            theNpBuf = np.frombuffer(ouBuf, dtype=np.uint16)
            theNpBuf = theNpBuf.reshape(theNumRows, theNumColumns)

            chunk_buf[frame % chunk_len, :, :] = theNpBuf  # Store in the buffer
            if (frame + 1) % chunk_len == 1 and frame > 0:  # Write chunk to Zarr file
                print(f"Flushing data chunk {frame}")
                z[(frame - chunk_len):frame, :, :] = chunk_buf

            frame += 1

            # Sleep to match the sample rate, considering latency
            time.sleep(time_per_frame)

    # Write the remaining data if there are any unflushed frames
    num_frames = frame % chunk_len
    if num_frames > 0:
        print(f"Flushing last chunk from frame {frame - num_frames}")
        z[(frame - num_frames):frame, :, :] = chunk_buf[:num_frames, :, :]
        frame += num_frames

    assert(frame == theImageGroup.mNpyHeader.mShape[0])

    et = time.time()
    elapsed_time = et - st - theTimePaused
    print('Execution time per loop iteration:', elapsed_time / frame, "s")

    input("Press Enter to exit.\n")
    print("Done")
    
        


if __name__ == "__main__":
    main(sys.argv[1:])
    


quit()

