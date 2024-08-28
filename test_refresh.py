__copyright__  = "Copyright (c) 2022, Intelligent Imaging Innovations, Inc. All rights reserved.  All rights reserved."
__license__  = "This source code is licensed under the BSD-style license found in the LICENSE file in the root directory of this source tree."

from SBReadFile import *
from matplotlib import pyplot as plt
import numpy as np
import sys, getopt
import time
from numpy.lib.format import open_memmap

def print_usage():
    print ('usage:\npython ',os.path.basename(__file__),' -s sldy_file [-i image_number] [-c channel_number] [-p plot_interval]')
    print ('or (long form)\npython ',os.path.basename(__file__),' --sldy_file=file_path [--image_number=value] [--channel_number=value] [--plot_interval=value]')

def parse_arguments(argv):
    if len(argv) < 3:
        print_usage()
        sys.exit(2)

    theFileName = ''
    theCapture = 0
    theChannel = 0
    thePlotFrequency = 10

    try:
        opts, args = getopt.getopt(argv,"hi:c:p:s:",["help","sldy_file=","image_number=","channel_number=","plot_interval="])
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

    if theFileName == "":
        print_usage()
        sys.exit()

    print ('Input file: ', theFileName,' image number: ',theCapture, ' channel number: ',theChannel)

    return theFileName, theCapture, theChannel, thePlotFrequency


def main(argv):
    theSBFileReader = SBReadFile()

    #work on the first capture
    theCapture = 0
    #work on the first channel
    theChannel = 0
    #plot frequency in timepoints
    thePlotFrequency = 10

    # Call the function in main to parse the arguments
    theFileName, theCapture, theChannel, thePlotFrequency = parse_arguments(sys.argv[1:])

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

    #theXmlDescriptor = theSBFileReader.GetAuxDataXMLDescriptor(theCapture,theChannel)
    #print ("*** theXmlDescriptor is " ,theXmlDescriptor)

    #theLen,theType = theSBFileReader.GetAuxDataNumElements(theCapture,theChannel)
    #print ("*** theLen,theType ",theLen,theType)

    #theXmlData =   theSBFileReader.GetAuxSerializedData(theCapture,theChannel,0)
    #print ("*** theXmlData is " ,theXmlData)


    theNumRows = theSBFileReader.GetNumYRows(theCapture)
    theNumColumns = theSBFileReader.GetNumXColumns(theCapture)
    theNumPlanes = theSBFileReader.GetNumZPlanes(theCapture)
    theZplane = int(theNumPlanes/2)
    #create a figure for animation
    fig = plt.figure(0)
    title = "Timepoint: {tp:6d}, Mean: {mn:.1f}"
    theFirstTP = 0
    theNoProgress = 0;
    theTimePaused = 0;
    theMaxWaitS = 5 # wait at most 5 seconds. If over this, quit
    theSleepS = 0.01 # sleep between refreshes
    st = time.time()

    # fp = np.memmap(r"D:\testing_slidebook_python\New folder\test2.memmap", dtype='int16', mode='w+', shape=(theNumTimepoints,theNumRows,theNumColumns))

    fp = np.memmap(r"Y:\FIOLA_DATA\test3.memmap", dtype='int16', mode='w+', shape=(theNumTimepoints,theNumRows,theNumColumns))
    # fp = open_memmap(r"Y:\FIOLA_DATA\test2.npy", dtype='int16', mode='w+', shape=(theNumTimepoints,theNumRows,theNumColumns))    
    for theRetry in range(0,10000):
        print ("*** theRetry: ",theRetry)
        for theTimepoint in range(theFirstTP,theNumTimepoints):
            image = theSBFileReader.ReadImagePlaneBuf(theCapture,0,theTimepoint,theZplane,0,True) #captureid,position,timepoint,zplane,channel,as 2d
            #print ("*** The read buffer len is: " , len(image))
            #calculate mean intensity using numpy
            theMean = np.mean(image)
            print ("*** theTimepoint: " , theTimepoint, "The mean: ",theMean)
            # if theMean==0:
                #streaming has missed a timepoint
                #insert a break here
            # save the image to a memmap
            fp[theTimepoint,:,:] = np.array(image.copy(),dtype='int16')
            if theTimepoint%10==0:
                fp.flush()

            #plot the slice every n timepoints

            # if theTimepoint%thePlotFrequency==0:
            if False:                
                if theTimepoint == 0:
                    img_artist = plt.imshow(image[:10,:10])
                    
                    # img_artist=plt.stairs(*np.histogram(image.flatten(),bins=np.arange(150,250,1)))
                else:
                    img_artist.set_data(image[:10,:10])
                    # img_artist.set_data(*np.histogram(image.flatten(),bins=np.arange(150,250,1)))
                img_artist.norm.autoscale([170, 250])
                plt.draw()
                fig.canvas.flush_events()
                plt.title(title.format(tp=theTimepoint,mn=theMean),loc='left')
                try:
                    plt.pause(0.001)
                except KeyboardInterrupt:
                    print("Keyboard Interrupt")
                    sys.exit()

        # see if there are any new timepoints
        theSBFileReader.Refresh(theCapture)
        
        if theFirstTP == theNumTimepoints:
            theNoProgress += 1
            time.sleep(theSleepS) # sleep 10 ms
            theTimePaused += theSleepS
        else:
            theNoProgress = 0
            time.sleep(theSleepS)

        # if we have waited too long, quit
        if theNoProgress * theSleepS  > theMaxWaitS:
            break

        #loop again
        theFirstTP = theNumTimepoints;
        theNumTimepoints = theSBFileReader.GetNumTimepoints(theCapture)-1
    

    et = time.time()
    elapsed_time = et - st - theTimePaused
    print('Execution time per loop iteration:', elapsed_time/theNumTimepoints, " s", ", waited for: ",theTimePaused," s")

    data = input("Please hit Enter to exit:\n")
    print("Done")


if __name__ == "__main__":
    main(sys.argv[1:])
    


