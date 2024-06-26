from ultralytics import YOLO
from skimage.color import gray2rgb
import cv2 as cv2
import os
import PySpin
import matplotlib.pyplot as plt
import sys
import keyboard
import time

from split import split
from geometries import geometries
from measurements import measurements
import cv2 
import numpy as np
import math


from numba import jit, cuda 

import exTrue

global continue_recording
continue_recording = True

model = YOLO('C:/Users/Praveen/Documents/yolov8/runs/segment/train9_hyper/newbest.pt')  # pretrained YOLOv8n model


def handle_close(evt):
    """
    This function will close the GUI when close event happens.

    :param evt: Event that occurs when the figure closes.
    :type evt: Event
    """

    global continue_recording
    continue_recording = False


def acquire_and_display_images(cam, nodemap, nodemap_tldevice):
    """
    This function continuously acquires images from a device and display them in a GUI.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :param nodemap_tldevice: Transport layer device nodemap.
    :type cam: CameraPtr
    :type nodemap: INodeMap
    :type nodemap_tldevice: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    global continue_recording

    sNodemap = cam.GetTLStreamNodeMap()

    # Change bufferhandling mode to NewestOnly
    node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
    if not PySpin.IsReadable(node_bufferhandling_mode) or not PySpin.IsWritable(node_bufferhandling_mode):
        print('Unable to set stream buffer handling mode.. Aborting...')
        return False

    # Retrieve entry node from enumeration node
    node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
    if not PySpin.IsReadable(node_newestonly):
        print('Unable to set stream buffer handling mode.. Aborting...')
        return False

    # Retrieve integer value from entry node
    node_newestonly_mode = node_newestonly.GetValue()

    # Set integer value from entry node as new value of enumeration node
    node_bufferhandling_mode.SetIntValue(node_newestonly_mode)

    print('*** IMAGE ACQUISITION ***\n')
    try:
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsReadable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        print('Acquisition mode set to continuous...')

        #  Begin acquiring images
        #
        #  *** NOTES ***
        #  What happens when the camera begins acquiring images depends on the
        #  acquisition mode. Single frame captures only a single image, multi
        #  frame catures a set number of images, and continuous captures a
        #  continuous stream of images.
        #
        #  *** LATER ***
        #  Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        print('Acquiring images...')

        #  Retrieve device serial number for filename
        #
        #  *** NOTES ***
        #  The device serial number is retrieved in order to keep cameras from
        #  overwriting one another. Grabbing image IDs could also accomplish
        #  this.
        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)

        # Close program
        print('Press enter to close the program..')

        # Figure(1) is default so you can omit this line. Figure(0) will create a new window every time program hits this line
        fig = plt.figure(1)

        # Close the GUI when close event happens
        fig.canvas.mpl_connect('close_event', handle_close)
        frame=0

        # Retrieve and display images
        while(continue_recording):
            frame+=1
            print("\nFrame Number ",frame)
            try:

                #  Retrieve next received image
                #
                #  *** NOTES ***
                #  Capturing an image houses images on the camera buffer. Trying
                #  to capture an image that does not exist will hang the camera.
                #
                #  *** LATER ***
                #  Once an image from the buffer is saved and/or no longer
                #  needed, the image must be released in order to keep the
                #  buffer from filling up.
                
                image_result = cam.GetNextImage(1000)

                #  Ensure image completion
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

                else:                    

                    # Getting the image data as a numpy array
                    image_data = image_result.GetNDArray()
                    image_data = gray2rgb(image_data)
                    image_dup = np.zeros_like(image_data)

                    #Running model on the frame and creating result class
                    rslt=model(image_data,save_conf=True)
                    names = rslt[0].names
                    
                    #print(names)
                    conf_tnsr=rslt[0].boxes.conf

                    #print(conf_tnsr)
                    classes_names = ["gelbreak", "gel", "needle"]
                    mess=""

                    gelbreak_probs=[]
                    gel_probs=[]
                    needle_probs=[]

                    for each in rslt[0]:
                        probabilities = rslt[0].boxes.conf
                        classes = rslt[0].boxes.cls
                        
                        #measure_frame = rslt[0].plot(img=image_dup)
                        #print("frame input type "+str(type(measure_frame)))
                        for i in range(0,(classes.size(dim=0))):
                            if int(classes[i].item())==0:
                                gelbreak_probs.append(probabilities[i].item())
                            elif int(classes[i].item())==1:
                                gel_probs.append(probabilities[i].item())
                            elif int(classes[i].item())==2:
                                needle_probs.append(probabilities[i].item())
                        #print(type(needle_probs))
                        
                    if len(needle_probs)==0:
                        mess="Needle Not Detected"
                        annotated_frame=rslt[0].plot()
                        #plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                        #plt.imshow(annotated_frame, cmap='gray')  
                        #plt.savefig(rf"C:/Users/Praveen/Documents/AI_ML_Testing/Segmentation/No_Needle/{frame}.png")
                        #plt.pause(0.001)
                        #plt.clf()
                        pass
                    else:
                        mess="Needle Detected"
                        annotated_frame=rslt[0].plot()
                        plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                        pass
                        

                    if len(gelbreak_probs)>0:
                        mess="Break in print Detected"
                        annotated_frame=rslt[0].plot()
                        plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                        #plt.imshow(annotated_frame, cmap='gray')  
                        #plt.savefig(rf"C:/Users/Praveen/Documents/AI_ML_Testing/Segmentation/Gel_Break/{frame}.png")
                        #plt.pause(0.001)
                        #plt.clf()
                        pass
                    else:
                        pass

                    if (len(gel_probs)>0 & len(gelbreak_probs)>0):
                        mess="Both Gel and GelBreak in same Frame"
                        annotated_frame=rslt[0].plot()
                        plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                        #plt.imshow(annotated_frame, cmap='gray')  
                        #plt.savefig(rf"C:/Users/Praveen/Documents/AI_ML_Testing/Segmentation/Gel_and_Break/{frame}.png")
                        #plt.pause(0.001)
                        #plt.clf()
                        pass

                    if gel_probs:
                            
                        if len(gel_probs) != 1:
                            mess=">1 Gel Detected"
                            annotated_frame=rslt[0].plot()
                            plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                            #plt.imshow(annotated_frame, cmap='gray')  
                            #plt.savefig(rf"C:/Users/Praveen/Documents/AI_ML_Testing/Segmentation/Mutli_Gel/{frame}.png")
                            #plt.pause(0.001)
                            #plt.clf()
                            pass
                        else:
                            print("Crybaby is Awake")
                            try:
                                measure_frame = rslt[0].plot(conf=False, img=image_dup, kpt_radius=0, kpt_line=False, labels=False, boxes=False, masks=True, probs=False)
                                ob=exTrue.exTrue(measure_frame)
                                mess="Difference in percentage is " + str(ob) + " percentage"
                                annotated_frame=rslt[0].plot()
                                plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                                #plt.imshow(annotated_frame, cmap='gray')
                                #plt.pause(0.001)
                                #plt.clf()
                            except Exception as e:
                                mess="The error is: "+e
                                annotated_frame=rslt[0].plot()
                                plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})
                                #plt.imshow(annotated_frame, cmap='gray')  
                                #plt.savefig(rf"C:/Users/Praveen/Documents/AI_ML_Testing/Measure/{frame}.png")
                                #plt.pause(0.001)
                                #plt.clf()

                            pass
                    else:
                        pass

                    # Visualize the results on the frame
                    #annotated_frame = rslt[0].plot()
                    #plt.text(30, 30, mess, style='italic',bbox={'facecolor': 'green', 'alpha': 0.5, 'pad': 10})

                    


                    # Draws an image on the current figure
                    plt.imshow(annotated_frame, cmap='gray')
                    

                    # Interval in plt.pause(interval) determines how fast the images are displayed in a GUI
                    # Interval is in seconds.
                    plt.pause(0.001)

                    # Clear current reference of a figure. This will improve display speed significantly
                    plt.clf()
                    
                    # If user presses enter, close the program
                    if keyboard.is_pressed('ENTER'):
                        print('Program is closing...')
                        
                        # Close figure
                        plt.close('all')             
                        input('Done! Press Enter to exit...')
                        continue_recording=False                        

                #  Release image
                #
                #  *** NOTES ***
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                return False

        #  End acquisition
        #
        #  *** NOTES ***
        #  Ending acquisition appropriately helps ensure that devices clean up
        #  properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return True


def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Acquire images
        result &= acquire_and_display_images(cam, nodemap, nodemap_tldevice)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def main():
    """
    Example entry point; notice the volume of data that the logging event handler
    prints out on debug despite the fact that very little really happens in this
    example. Because of this, it may be better to have the logger set to lower
    level in order to provide a more concise, focused log.

    :return: True if successful, False otherwise.
    :rtype: bool
    """
    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Run example on each camera
    for i, cam in enumerate(cam_list):

        print('Running example for camera %d...' % i)

        result &= run_single_camera(cam)
        print('Camera %d example complete... \n' % i)

    # Release reference to camera
    # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
    # cleaned up when going out of scope.
    # The usage of del is preferred to assigning the variable to None.
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input('Done! Press Enter to exit...')
    return result


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
