#!/usr/bin/env python3
#
## AI_mt.py 10MAR2019wbk
## 7JAN2019wbk derived from: AI_unified_mt.py
##
## This should be the last version derived from AI_unified_mt.py since I plan to move the code from NCS v1 SDK to OpenVINO or Coral TPU
## Changes: Completed 18MAR2019wbk
##  1) Send images as MQTT buffer instead of local file system path, allows notifications to be on different machine
##  2) Add option to save all analized images to local storage, primarily for testing/debugging
##  3) Add round-robin sampling for rtsp cameras, could be useful for Lorex DVR where all are on the same server (minimally tested)
##     so-far, round-robin sampling seems inferior in my testing, probably shouldn't be used.
##  4) Allow mix of input methods -- rtsp, onvif, images via MQTT
##  Completed 20MAR2019wbk:
##  5) Add MQTT message buffer "front-end" to get images to analyze, typically from node-red ftp server node.
##  topic: MQTTcam/N, payload: buffer containing jpeg image
##
##
## 24MAR2019wbk
## Note there is no NCS v1 API support on Windows.  (Intel indroduced this with OpenVINO, R5?)
## I don't run Windows, but I've done limited testing on a couple of friend's machines I set up for dual boot.
## i3 4025U:    Windows7    -- 5 onvif cameras gets ~6.2 fps, ~6.1 fps Windows10
##                          -- 5 rtsp streams gets ~5.2fps, ~5.3 fps Windows10
##              Ubuntu16.04 -- same hardware, CPU AI only, No NCS installed to compare with Windows (dual boot)
##                          -- 5 Onvif cameras gets ~8.4 fps
##                          -- 5 rtsp ~7.4 fps.
##
## Pi3B:        CPU AI is too slow to be useful ~0.6 fps,  start program with option:  - nt 0
##              Python 2.7  -- 5 onvif cameras 1 NCS gets ~6.5 fps, 2 NCS doesn't run reliably giving NCS timeout errors, might be power suppy issue.  
##              Python 3.5  -- 5 onvif cameras 1 NCS gets ~6.6 fps, same erratic results with two NCS sticks, but short runs do ~11.7 fps
##                          -- 5 rtsp streams gets ~4.5 fps, 2 NCS gets ~6.2 fps  I don't think the Pi is a good choice for rtsp streams.           
##
## i5 M540:     Ubuntu16.04 -- 5 onvif, CPU AI with old CPU without AVX, AVX2, does poorly ~3.9 fps, better than Pi3 but worse than i3 4025U
##                          -- 5 onvif, 1 NCS, no CPU AI gets ~8.8 fps, 2 NCS ~17.0 fps, 1 NCS + 1 CPU AI ~12.0 fps, lack of USB3 holds it back
##                          -- 5 rtsp, 1 NCS, no CPU AI ~8.8 fps.
##
## i7 4500U:    Ubuntu16.04 -- 5 rtsp, CPU AI gets ~10.6 fps
##                          -- 5 rtsp, 1 NCS, no CPU AI gets ~10.7 fps
##                          -- 5 rtsp, CPU AI + 1 NCS gets ~20.1 fps
##                          -- 5 rtsp, CPU AI + 2 NCS gets ~24.4 fps, this is camera limited since each is set for 5 fps
##              Ubuntu18.04 -- 5 rtsp, CPU AI + 1 NCS ~19.5 fps.
##
## i5 4200U     Ubuntu16.04 -- 5 rtsp, CPU AI ~9.7 fps
##                          -- 5 rtsp, CPU AI + 1 NCS ~18.1 fps.
##
##
##
## 21MAR2019wbk
## i7 4 GHz quad core 6700K Desktop -- 2 Onvif, 5 rtsp, 1 mqtt  gets ~29.4 fps wtih one NCS and one CPU AI thread.
##
## 11MAR2019wbk
## i7 1 NCS, no CPU AI threads gives 10.6 fps with 4 rtsp streams for both roundrobin and one thread per stream sampling.
##
##
###
# AI_unified_mt.py
# 16JAN2019wbk derived from: AI_multi_threaded.unified.py
# Add option to capture images vis RTSP streams instead of jpeg snapshots.
# Move thread functions back into this module, the split just made things uglier, not better.
#
#
# AI_multi_threaded.unified.py
# 12NOV2018wbk derived from: onvif_AI_multi.py
# 5DEC2018wbk
# Unifiy to run on Linux or Windows, threading model on Windows is only minimally tested, 25FEB19 seems pretty solid on Win7 & Win10.
# move thread functions to a library file:  AIutils.py
# add automatic switch to openCV 3.2+ dnn module for CPU only MobilenetSSD
# Still works with python2.7 and python3.5 if Python 2.7 also has correct openCV version, last tested on Raspberry Pi
#
# 8DEC2018wbk
# Minor fixes and optimizations, better error handling -->  continue to run with camera failures (requires one thread per camera)
# On an i7 quad core with hyperhreading CPU AI -- 6 cameras -- 13 total threads: ~36 fps -- Camera limited, CPU_AI threads waiting for data
#    with a single Movidius NCS -- 6 cameras -- 8 total threads: ~10.7 fps -- AI limited, Onvif threads waiting for AI
# On i3 dual core Windows 7 -- 6 cameras -- 13 threads: ~6.7 fps -- AI limited.
#    same 6 cameras and this i3 system booted to Ubuntu-Mate 18.04: ~7.9 fps
#
# 11JAN2019wbk
# Make seperate queue for each camera unless roundrobin camera sampling specified.
# Allow mix of CPU and AI threads, default to 1 CPU thread in addition to any NCS threads
# On i3 with 3 cameras and 1 CPU thread got ~6.8 fps, adding 1 NCS stick got ~15.7 fps
#     using 2 CPU threads instead gets ~7.1 fps, adding -d 0 options only improves to ~7.8 fps
# On my i7 Desktop using only a single CPU thread gets ~20.5 fps
#
#
##
# onvif_AI_multi.py
# 10NOV2018wbk
# Many threads, one to read each camera, one for each NCS, and the main thread
# Initial version that seems to work pretty well.
# On i7 Desktop (Python 3.5) with 3 Onvif cameras and 1 NCS getting ~10.7 fps (5 threads total)
# with 3 cameras and 2 NCS getting ~20.5 fps (6 threads total)
# and with  3 cameras and 3 NCS getting ~29.5 fps (7 threads total)
# Trying a 4th NCS (10 threads) ~29 fps, clearly Camera limited.
#### Might still be useful for analyizing multiple sub-regions in a frame
#### instead of shrinking the entire frame (pretty much needed for better than 720p cameras).
# With 4 cameras round-robin, 1 NCS stick  (3 threads) ~7.6 fps
#### round-robin sampling is NOT recommended as it basically stops working with a network connection error or camera failure.
#
# 11NOV2018wbk
# remove restriction that all cameras need the same frame resolution.
#
# 13NOV2018wbk
# No NCS --> CPU AI:
# With 4 cameras round-robin, and 1 AI thread (3 threads) get ~5.8 fps on my heavily loaded i7 Desktop
# With 4 cameras round-robin, AI thread per camera (6 threads) ~ 9.9 fps -- apears Camera limited (Camera output queue never full, AI queues often empty)
# With 4 cameras, and thread per camera sampling (9 threads) ~30 fps -- apears Camera limited (Camera output queues never full, AI queues often empty)
#
# On lightly loaded i3 with round-robin camera sampling and one AI thread per camera (6 threads) get ~6.3 fps -- apears Camera limited
# On i3, (9 threads) gets only ~8 fps  -- appears AI limited (Cameara output queues often full, AI input queues never empty)



# determine OS platform
# TODO: if I ever get a Mac, enhance this to work there too.
import platform
global __WIN__
if platform.system()[:3] != 'Lin':
    __WIN__ = True
else:
    __WIN__ = False


# Get python major version for
import sys
global usingP2
if sys.version_info.major < 3:
    usingP2=True    #TODO: maybe its time to give up on Python 2.7 support for this?? I only test 2.7 on Raspberry Pi
else:
    # subtle code changes have apparently minimized the difference
    #print("*** Info *** This code has better performance on Pi3B with Python version 2.7!")
    usingP2=False


# import the necessary packages
if __WIN__ == False:
    from mvnc import mvncapi as mvnc
    import signal
from imutils.video import FPS
import argparse
import numpy as np
import cv2
import paho.mqtt.client as mqtt
import os
import datetime
import time
import requests
from PIL import Image
from io import BytesIO
# threading stuff
if usingP2:         #TODO: maybe its time to give up on Python 2.7 support for this??
    import Queue
else:
    from queue import Queue

from threading import Lock, Thread



# mark start of this code in log file
print("")
currentDT = datetime.datetime.now()
print("*************************************************" + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
print("")


# *** System Globals
# these are write once in main() and read-only everywhere else, thus don't need syncronization
global QUIT
QUIT=False  # True exits main loop and all threads
global nextCamera
global waitThreadSync
waitThreadSync = True # threads wait outside their main loop until this goes false upon entering main program loop
global CameraURL    # needs to still be global for non threaded call to grab an initial Onvif snapshot
global CamError     # needs to still be global for non threaded call to grab an initial Onvif snapshot
global Nrtsp
global Nrr_rtsp
global Nonvif
global Ncameras
global AlarmMode    # would be Notify, Audio, or Idle, Idle mode doesn't save detections
global UImode
global CameraToView
global sendAll
global saveAll
global confidence
global subscribeTopic
subscribeTopic = "Alarm/#"  # topic controller publishes to to set AI operational modes
global Nmqtt
global mqttCamOffset
global inframe
global mqttFrameDrops
global mqttFrames


# these need syncronization
cameraLock = Lock()
global nextCamera
nextCamera = 0      # next camera queue for AI threads to use to grab a frame
rtspLock = Lock()   # make rtsp frame graps be atomic, seems openCV may not be completely thread safe.



# *** constants for MobileNet-SSD AI model
# frame dimensions should be sqaure for MobileNet-SSD
PREPROCESS_DIMS = (300, 300)
# initialize the list of class labels our network was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ("background", "aeroplane", "bicycle", "bird",
    "boat", "bottle", "bus", "car", "cat", "chair", "cow",
    "diningtable", "dog", "horse", "motorbike", "person",
    "pottedplant", "sheep", "sofa", "train", "tvmonitor")
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))  # from PyImageSearch example code
#COLORS[15] = (255,255,255)  # force person box to be white
#COLORS[15] = (0,0,255)  # force person box to be red
COLORS[15] = (0,255,0)  # force person box to be green



# *** Function definitions
#**********************************************************************************************************************
#**********************************************************************************************************************
#**********************************************************************************************************************

# Boilerplate code to setup signal handler for graceful shutdown on Linux
if __WIN__ is False:
    def sigint_handler(signal, frame):
        global QUIT
        currentDT = datetime.datetime.now()
        print('caught SIGINT, normal exit. -- ' + currentDT.strftime("%Y-%m-%d  %H:%M:%S"))
        #quitQ.put(True)
        QUIT=True

    def sighup_handler(signal, frame):
        global QUIT
        currentDT = datetime.datetime.now()
        print('caught SIGHUP! ** ' + currentDT.strftime("%Y-%m-%d  %H:%M:%S"))
        #quitQ.put(True)
        QUIT=True

    def sigquit_handler(signal, frame):
        global QUIT
        currentDT = datetime.datetime.now()
        print('caught SIGQUIT! *** ' + currentDT.strftime("%Y-%m-%d  %H:%M:%S"))
        #quitQ.put(True)
        QUIT=True

    def sigterm_handler(signal, frame):
        global QUIT
        currentDT = datetime.datetime.now()
        print('caught SIGTERM! **** ' + currentDT.strftime("%Y-%m-%d  %H:%M:%S"))
        #quitQ.put(True)
        QUIT=True

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGHUP, sighup_handler)
    signal.signal(signal.SIGQUIT, sigquit_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)



#**********************************************************************************************************************
## MQTT callback functions
##
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global subscribeTopic
    #print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.  -- straight from Paho-Mqtt docs!
    client.subscribe(subscribeTopic)


CameraToView=0
# The callback for when a PUBLISH message is received from the server, aka message from SUBSCRIBE topic.
AlarmMode="Audio"    # will be Email, Audio, or Idle  via MQTT from alarmboneServer
def on_message(client, userdata, msg):
    global AlarmMode    # would be Notify, Audio, or Idle, Idle mode doesn't save detections
    global UImode
    global CameraToView
    global sendAll
    global saveAll
    if str(msg.topic) == "Alarm/MODE":          # Idle will not save detections, Audio & Notify are the same here
        currentDT = datetime.datetime.now()     # logfile entry
        print(str(msg.topic)+":  " + str(msg.payload) + currentDT.strftime(" ... %Y-%m-%d %H:%M:%S"))
        AlarmMode = str(msg.payload)
        return
    if str(msg.topic) == "Alarm/UImode":    # dashboard control Disable, Detections, Live exposes apparent node-red websocket bugs
        currentDT = datetime.datetime.now() # especially if browser is not on localhost, use sparingly, useful for camera setup.
        print(str(msg.topic)+": " + str(int(msg.payload)) + currentDT.strftime("   ... %Y-%m-%d %H:%M:%S"))
        UImode = int(msg.payload)
        return
    if str(msg.topic) == "Alarm/ViewCamera":    # dashboard control to select image to view
        currentDT = datetime.datetime.now()
        print(str(msg.topic)+": " + str(int(msg.payload)) + currentDT.strftime("   ... %Y-%m-%d %H:%M:%S"))
        CameraToView = int(msg.payload)
        return
    if str(msg.topic) == "Alarm/sendAll":   # sends all images not just detections as DetectionImageBuffer/CamN messages 
        currentDT = datetime.datetime.now()
        print(str(msg.topic)+":  " + str(msg.payload) + currentDT.strftime(" ... %Y-%m-%d %H:%M:%S"))
        send = str(msg.payload)
        if send.count("True"):
            sendAll=True
        else:
            sendAll=False
        return
    if str(msg.topic) == "Alarm/saveAll":   # save all images, not just detections, will fill up drive fast!
        currentDT = datetime.datetime.now() # but helpful for troubleshooting
        print(str(msg.topic)+":  " + str(msg.payload) + currentDT.strftime(" ... %Y-%m-%d %H:%M:%S"))
        save = str(msg.payload)
        if save.count("True"):
            saveAll=True
        else:
            saveAll=False
        return


def on_publish(client, userdata, mid):
    #print("mid: " + str(mid))      # don't think I need to care about this for now, print for initial tests
    pass


def on_disconnect(client, userdata, rc):
    if rc != 0:
        currentDT = datetime.datetime.now()
        print("Unexpected MQTT disconnection!" + currentDT.strftime(" ... %Y-%m-%d %H:%M:%S"))
    pass


# callbacks for mqttCam that can't be shared
def on_mqttCam_connect(client, userdata, flags, rc):
    client.subscribe("MQTTcam/#")


def on_mqttCam(client, userdata, msg):
    global Nmqtt
    global mqttCamOffset
    global inframe
    global mqttFrameDrops
    global mqttFrames
    if msg.topic.startswith("MQTTcam/") and Nmqtt > 0:
        camNstr=msg.topic[len("MQTTcam/"):]    # get camera number as string
        if camNstr.isdecimal():
            camN = int(camNstr)
            if camN >= Nmqtt:
                currentDT = datetime.datetime.now()
                print("[Error! Invalid MQTTcam Camera number: " + str(camN) + currentDT.strftime(" ... %Y-%m-%d %H:%M:%S"))
                return
        else:
            currentDT = datetime.datetime.now()
            print("[Error! Invalid MQTTcam message sub-topic: " + camNstr + currentDT.strftime(" ... %Y-%m-%d %H:%M:%S"))
            return
        # put input image into the camera's inframe queue
        try:
            mqttFrames+=1
            # thanks to @krambriw on the node-red user forum for clarifying this for me
            npimg=np.fromstring(msg.payload, np.uint8)      # convert msg.payload to numpy array
            frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)   # decode image file into openCV image
            #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # correct color plane order, doesn't affect AI but images look funky without it.
            inframe[camN+mqttCamOffset].put((frame, camN+mqttCamOffset), True, 0.5) 
            return
        except:
            mqttFrameDrops+=1
        return



#**********************************************************************************************************************
## function to grab Onvif snapshot
# Some very slick, very high level code to grab a snapshot from an Onvif camera that supports snapshots.
# Finding the snapshot URL can be an issue.
# But I've some simple nodejs code to scan the local network for Onvif devices and print what it finds
def OnvifSnapshot(camera):
    global CamError
    global CameraURL
    try:
        r = requests.get(CameraURL[camera])
        i = Image.open(BytesIO(r.content))
        npimg = np.array(i)
        npimg=cv2.cvtColor(npimg, cv2.COLOR_BGR2RGB)
        CamError[camera]=False     # after geting a good frame, enable logging of next error
        return npimg
    except Exception as e:
        # this appears to fix the Besder camera problem where it drops out for minutes every 5-12 hours
        # likely issues here wtih round-robin sampling
        if not CamError[camera]:   # suppress the zillions of sequential error messages while it recovers
            currentDT = datetime.datetime.now()
            print('Onvif cam'+ str(camera) + ': ' + str(e) + CameraURL[camera] + ' --- ' + currentDT.strftime(" %Y-%m-%d_%H:%M:%S.%f"))
        frame = None
        CamError[camera]=True
        return None



# *** Thread functions
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# *** RTSP Sampling Thread
#******************************************************************************************************************
# rtsp stream sampling thread
def rtsp_thread(inframe, camn, Rcap, URLs, Error):    # negative camn means round-robin stream sampling in a single thread
    global waitThreadSync
    global QUIT
    global Nonvif
    global Nrtsp
    maxFPS = 30             # max rtsp frames/sec, what fast here to drop frames in attempt to minimize latency which can be 4-12 seconds!!!
    napTime=1/maxFPS
    if camn >= 0:           # round-robin breaks if a camera dies, one thread per camera is best!
        camrr=False         # but if all rtsp streams come from the same DVR device rr may be useful.
        camOffset=Nonvif    # so far my tests indicate that rr sampleing is inferior, probably will completely disable it eventually.
    else:
        camrr=True      # only minimally tested initially, mostly with my Lorex DVR
        camn=0
        camOffset=Nonvif+Nrtsp
        ncams=len(URLs)
    ocnt=0
    while waitThreadSync and not QUIT:
        if not camrr:   # one rtsp thread per camera
            rtspLock.acquire()
            (_, _) = Rcap[camn].read()  # try to keep rtsp buffers empty for reduced latency
            rtspLock.release()
        else:   # one thread samples array of rtsp streams, generall from a "DVR"
            for i in range(ncams):
                rtspLock.acquire()
                (_, _) = Rcap[i].read()
                rtspLock.release()
    if camrr:
        print("[INFO] RTSP round-robin stream sampling thread is running...")
    else:
        print("[INFO] RTSP stream sampling thread" + str(camn) + " is running...")
    while not QUIT:
         # grab the frame
        try:
            rtspLock.acquire()
            ret, frame = Rcap[camn].read()
            rtspLock.release()
            if ret:
                if Error[camn]:   # log when it recovers
                    currentDT = datetime.datetime.now()
                    print('[$$$$$$] RTSP Camera'+ str(camn+camOffset) + ' has recovered: ' + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
                    Error[camn]=False    # after geting a good frame, enable logging of next error
            else:
                frame = None
                if not Error[camn]:
                    Error[camn]=True
                    currentDT = datetime.datetime.now()
                    print('[Error!] RTSP Camera'+ str(camn+camOffset) + ': ' + URLs[camn][0:30] + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
                else:   # try closing the stream and reopeing it, I have one straight from China that does this error regularly
                    Rcap[camn].release()
                    time.sleep(1.0)
                    currentDT = datetime.datetime.now()
                    print('[******] RTSP stream'+ str(camn+camOffset) + ' closing and re-opening stream ' + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
                    Rcap[camn]=cv2.VideoCapture(URLs[camn])
                    if Rcap[camn].isOpened():
                        continue    # avoid the sleep if stream is re-opened.
                    else:
                        currentDT = datetime.datetime.now()
                        print('[Error!] RTSP stream'+ str(camn+camOffset) + ' re-open failed! $$$ ' + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))                   
        except Exception as e:
            # this appears to fix the Besder camera problem where it drops out for minutes every 5-12 hours, will it work for rtsp stream?
            frame = None
            if not Error[camn]:   # suppress the zillions of sequential error messages while it recovers
                Error[camn]=True
                # unlike the Besder camera snapshot errors, these never seem to recover on their own
                currentDT = datetime.datetime.now()
                print('[Error!] RTSP stream'+ str(camn+camOffset) + ': ' + str(e) + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
            else:   # try closing the stream and reopeing it, I have one straight from China that does this error regularly
                Rcap[camn].release()
                time.sleep(2.0)
                Rcap[camn]=cv2.VideoCapture(URLs[camn])
                if Rcap[camn].isOpened():
                    continue    # avoid the sleep if stream is re-opened.
                else:
                    print('[Error!] RTSP stream'+ str(camn+camOffset) + ' re-open failed! ### ' + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))                   
            if QUIT:
                break
            if camrr is False:
                time.sleep(10.0)     # let other threads have more time while this camera recovers
        try:
            if frame is not None and not QUIT:
                inframe.put((frame, camn+camOffset), False)   # no block if queue full, go grab fresher frame
                if camrr is True:
                    camn=(camn+1) % ncams
                else:
                    time.sleep(napTime)
        except: # most likely queue is full
            if QUIT:
                break
            ocnt=ocnt+1
            if camrr is True:
                pass # round-robbin is problematic, is locking on one camera until ready better, maybe.
                ##camn=(camn+1) % ncams
            else:
                time.sleep(0.001)   # force thread dispatch
                
    # a large drop count for rtsp streams is not a bad thing as we are trying to keep the input buffers nearly empty to reduce latency.
    if camrr is True:
        print("RTSP stream round-robin sampling thread is exiting, dropped frames " + str(ocnt) + " times.")
    else:
        print("RTSP stream sampling thread" + str(camn) + " is exiting, dropped frames " + str(ocnt) + " times.")



## *** ONVIF Sampling Thread ***
#******************************************************************************************************************
# Onvif camera sampling thread
def onvif_thread(inframe, camn, URLs, Error):     # negative camn means round-robin camera sampling in a single camera thread
    global waitThreadSync
    global QUIT
    maxOnvifRate = 30    # maximum "reasonable" framerate" for cameras
    sleepyTime=1/maxOnvifRate
    while waitThreadSync and not QUIT:
        time.sleep(sleepyTime)
    if camn >= 0:   # round-robin breaks if a camera dies, one thread per camera is best!
        camrr=False
        print("[INFO] ONVIF Camera" + str(camn) + " thread is running...")
    else:
        #rr# Unless I find a DVR that supplies jpeg snapshot URLs, rr sampling makes no sense for Onvif cameras
        #rr#camrr=True
        #rr#camn=-1
        #rr#print("[INFO] Onvif Camera round-robin sampling thread is running...")
        print("[INFO] Onvif Camera round-robin sampling is now disabled!")
        print("   Othersise a network/camera error will interfere with all cameras, killing performance.")
        return
    ocnt=0  # count of times inframe thread output queue was full (dropped frames)
    ncams=len(CameraURL)    # might want to pass CameraURL instead of uisng the global, not clear, but makes round-robin easier.
    ##while not QUIT:
    while not (QUIT or camrr):
        # grab the frame
        #rr#if camrr is True:
        #rr#    camn=(camn+1) % ncams
        try:
            r = requests.get(URLs[camn])
            i = Image.open(BytesIO(r.content))
            frame = np.array(i)
            frame=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if CamError[camn] and frame is not None:   # log when it recovers
                currentDT = datetime.datetime.now()
                print('[******] Onvif cam'+ str(camn) + ' error has recovered: ' + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
                Error[camn]=False    # after getting a good frame, enable logging of next error
        except Exception as e:
            # this appears to fix the Besder camera problem where it drops out for minutes every 5-12 hours
            if not Error[camn]:   # suppress the zillions of sequential error messages while it recovers
                currentDT = datetime.datetime.now()
                ##print('Onvif cam'+ str(camn) + ': ' + str(e) + URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
                ## printing the error string hasn't been particularly informative
                print('[Error!] Onvif cam'+ str(camn) + ': ' +  URLs[camn][0:30] + ' --- ' + currentDT.strftime(" %Y-%m-%d %H:%M:%S"))
            frame = None
            Error[camn]=True
            if QUIT:
                break
            if camrr is False:
                time.sleep(5.0)     # let other threads have more time while this camera recovers, which sometimes takes minutes
        try:
            if frame is not None and not QUIT:
                #rr#if camrr is True:   # this should never happen now, TODO_ remove this dead code once I'm sure rr makes no sense for snapshots
                #rr#    inframe.put((frame, camn), True, 1.0)   # wait for space in queue to smooth sampling
                #rr#else:
                    inframe.put((frame, camn), True, 0.200)
                    time.sleep(sleepyTime)   # force thread switch, hopefully smoother sampling, 10Hz seems upper limit for snapshots
        except: # most likely queue is full
            if QUIT:
                break
            ocnt=ocnt+1
            time.sleep(sleepyTime)
            continue
    if camrr is True:
        print("Onvif Camera round-robin thread is exiting, dropped frames " + str(ocnt) + " times.")
    else:
        print("ONVIF Camera" + str(camn) + " thread is exiting, dropped frames " + str(ocnt) + " times.")



## *** NCS AI Thread ***
#******************************************************************************************************************
#******************************************************************************************************************
if __WIN__ is False:
    # thread function for Movidius NCS AI
    def AI_thread(results, inframe, graph, tnum, cameraLock):
        global nextCamera
        global waitThreadSync
        global QUIT
        global Ncameras
        NCSerror=0
        w=PREPROCESS_DIMS[0]
        h=PREPROCESS_DIMS[1]
        while waitThreadSync and not QUIT:
            time.sleep(0.10)
        print("[INFO] NCS AI thread" + str(tnum) + " is running...")
        bcnt=0  # count of times thread input inframe queue was empty, no data for thread to process
        mcnt=0  # count of times frame dropped because main thread results queue was full
        while not QUIT:
            cameraLock.acquire()
            cq=nextCamera   # next camera queue to read
            nextCamera = (nextCamera+1)%Ncameras
            cameraLock.release()
            # get a frame
            if not inframe[cq].empty() and not QUIT:
                try:
                    (image, cam) = inframe[cq].get(False)   # don't block if no data from this camera, skip to next one
                except:
                    if QUIT:
                        break
                    bcnt=bcnt+1     # unfortunately queue.empty() is not reliable! keep track
                    continue
            else:
                if QUIT:
                    break
                continue   #just move to next camera if this one is not ready with data in its queue
            (hh,ww)=image.shape[:2]
            # preprocess the image
            img = cv2.resize(image, PREPROCESS_DIMS)
            img = img - 127.5
            img = img * 0.007843
            img = img.astype(np.float16)

            # send the image to the NCS and run a forward pass to grab the network predictions
            try:
                graph.LoadTensor(img, None)
                (output, _) = graph.GetResult()
            except Exception as e:
                ## So far I only see these errors on the Raspberry Pi and usually the Pi either needs to be rebooted,
                ## or the Movidius stick unplugged and plugged in again.  Hence the "Watchdog Timer" in the node-red "controller"
                ## I have some evidence that the "normal" 2.4A Pi power supply is not up to two NCS and marginal for one.
                currentDT = datetime.datetime.now()
                print("NCS Error: " + str(e)  + currentDT.strftime(" -- %Y-%m-%d %H:%M:%S.%f"))
                if NCSerror == 0:
                    NCSerror += 1
                    continue
                else:
                    print("*** NCS Errors:  Thread" + str(tnum) + " is exiting! ***")
                    return
            # grab the number of valid object predictions from the output, then initialize the list of predictions
            num_valid_boxes = output[0]
            predictions = []

            # loop over results, modifeid from PyImageSearch and other NCS sample code
            for box_index in range(int(num_valid_boxes)):
                # calculate the base index into our array so we can extract bounding box information
                base_index = 7 + box_index * 7

                # boxes with non-finite (inf, nan, etc) numbers must be ignored
                if (not np.isfinite(output[base_index]) or
                    not np.isfinite(output[base_index + 1]) or
                    not np.isfinite(output[base_index + 2]) or
                    not np.isfinite(output[base_index + 3]) or
                    not np.isfinite(output[base_index + 4]) or
                    not np.isfinite(output[base_index + 5]) or
                    not np.isfinite(output[base_index + 6])):
                    continue

                # extract the image width and height and clip the boxes to the image size in case network returns boxes outside the image
                x1 = max(0, int(output[base_index + 3] * w))
                y1 = max(0, int(output[base_index + 4] * h))
                x2 = min(w, int(output[base_index + 5] * w))
                y2 = min(h, int(output[base_index + 6] * h))

                # grab the prediction class label, confidence (i.e., probability), and bounding box (x, y)-coordinates
                pred_class = int(output[base_index + 1])
                pred_conf = output[base_index + 2]
                pred_boxpts = ((x1, y1), (x2, y2))

                # create prediciton tuple and append the prediction to the predictions list
                prediction = (pred_class, pred_conf, pred_boxpts)
                predictions.append(prediction)

            # loop over our predictions
            personDetected=False
            ndetected=0
            for (i, pred) in enumerate(predictions):
                # extract prediction data for readability
                (pred_class, pred_conf, pred_boxpts) = pred

                # filter out weak detections by ensuring the `confidence` is greater than the minimum confidence
                if pred_conf > confidence and pred_class == 15:
                    (ptA, ptB) = (pred_boxpts[0], pred_boxpts[1])
                    # Support per camera frame sizes
                    X_MULTIPLIER = float(ww) / PREPROCESS_DIMS[0]
                    Y_MULTIPLIER = float(hh) / PREPROCESS_DIMS[1]
                    startX = int(ptA[0] * X_MULTIPLIER)
                    startY = int(ptA[1] * Y_MULTIPLIER)
                    endX = int(ptB[0] * X_MULTIPLIER)
                    endY = int(ptB[1] * Y_MULTIPLIER)
                    # adhoc "fix" for out of focus blobs close to the camera
                    xlen=endX-startX
                    ylen=endY-startY
                    xcenter=int((startX+endX)/2)
                    ycenter=int((startY+endY)/2)
                    # out of focus blobs sometimes falsely detect -- insects walking on camera, etc.
                    # In my real world use I have some static false detections, mostly under IR or mixed lighting -- hanging plants etc.
                    # I put camera specific adhoc filters here based on (xlen,ylen,xcenter,ycenter)
                    # TODO: come up with better way to do it, probably return (xlen,ylen,xcenter,ycenter) and filter at saving or Notify step.
                    if float(xlen*ylen)/(ww*hh) > 0.7:     # detection filling more than 70% fo the frame is bogus
                        continue
                    if float(ylen)/hh > 0.9:    # more than 90% of the frame height is bogus
                        continue
                    personDetected=True
                    # print prediction to terminal
                    label = "{:.0f}%  C:{},{}  W:{} H:{}  UL:{},{}  LR:{},{}".format(pred_conf * 100, str(xcenter), str(ycenter), str(xlen), str(ylen), str(startX), str(startY), str(endX), str(endY))
                    cv2.rectangle(image, (startX,startY), (endX,endY), COLORS[pred_class], 2)
                    cv2.putText(image, label, (2, (hh-5)-(ndetected*28)), cv2.FONT_HERSHEY_SIMPLEX, 0.85, COLORS[pred_class], 1, cv2.LINE_AA)
                    ndetected=ndetected+1
            # Queue results
            try:
                if personDetected:
                    results.put((image, cam, personDetected), True, 1.0)    # try not to drop frames with detections
                else:
                    results.put((image, cam, personDetected), True, 0.033)
            except:
                # presumably outptut queue was full, main thread too slow.
                mcnt+=1
                continue
        # Thread exits
        print("NCS AI thread" + str(tnum) + " is exiting, waited for input frames " + str(bcnt) + " times, dropped " + str(mcnt) + " output frames.")



# *** CPU AI Thread ***
#******************************************************************************************************************
#******************************************************************************************************************
# function for CPU AI detection
def CPU_AI_thread(results, inframe, net, tnum, camearaLock):
    global nextCamera
    global waitThreadSync
    global QUIT
    global Ncameras
    while waitThreadSync and not QUIT:
        time.sleep(0.10)
    print("[INFO] CPU AI thread" + str(tnum) + " is running...")
    bcnt=0
    mcnt=0
    prevDetections=0    # This is the crude 3.3.0 work-around to drop duplicate detections, seems real detections always vary a bit
    while not QUIT:     # I'm not sure later versions fix it, or if its confined to the Raspberry Pi camera module, but I've left it in here.
        cameraLock.acquire()
        cq=nextCamera
        nextCamera = (nextCamera+1)%Ncameras
        cameraLock.release()
        # get a frame
        if not inframe[cq].empty() and not QUIT:
            try:
                (image, cam) = inframe[cq].get(False)
            except:
                if QUIT:
                    break
                bcnt=bcnt+1
                continue
        else:
            if QUIT:
                break
            continue
        personDetected = False
        (h, w) = image.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(image, PREPROCESS_DIMS), 0.007843, PREPROCESS_DIMS, 127.5)
        # pass the blob through the network and obtain the detections and predictions
        net.setInput(blob)
        detections = net.forward()
        # loop over the detections, pretty much straight from the PyImageSearch sample code.
        ndetected=0
        for i in np.arange(0, detections.shape[2]):
            # extract the confidence (i.e., probability) associated with the prediction
            conf = detections[0, 0, i, 2]
            # extract the index of the class label from the `detections`,
            idx = int(detections[0, 0, i, 1])
            # filter out weak detections by ensuring the `confidence` is greater than the minimum confidence
            if conf > confidence and not np.array_equal(prevDetections, detections) and idx == 15:
                # then compute the (x, y)-coordinates of the bounding box for the object
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                # adhoc "fix" for out of focus blobs close to the camera
                xlen=endX-startX
                ylen=endY-startY
                xcenter=int((startX+endX)/2)
                ycenter=int((startY+endY)/2)
                # out of focus blobs sometimes falsely detect -- insects walking on camera, etc.
                # In my real world use I have some static false detections, mostly under IR or mixed lighting -- hanging plants etc.
                # I put camera specific adhoc filters here based on (xlen,ylen,xcenter,ycenter)
                # TODO: come up with better way to do it, probably return (xlen,ylen,xcenter,ycenter) and filter at saving or Notify step.
                if float(xlen*ylen)/(w*h) > 0.7:     # detection filling more than 70% fo the frame is bogus
                    continue
                if float(ylen)/h > 0.9:    # more than 90% of the frame height is bogus
                    continue
                # display the prediction
                label = "{:.0f}%  C:{},{}  W:{} H:{}  UL:{},{}  LR:{},{}".format(conf * 100, str(xcenter), str(ycenter), str(xlen), str(ylen), str(startX), str(startY), str(endX), str(endY))
                cv2.rectangle(image, (startX, startY), (endX, endY), COLORS[idx], 2)
                cv2.putText(image, label, (2, (h-5)-(ndetected*28)), cv2.FONT_HERSHEY_SIMPLEX, 0.85, COLORS[idx], 1, cv2.LINE_AA)
                personDetected = True
                ndetected=ndetected+1
        prevDetections=detections
        # Queue results
        try:
            if personDetected:
                results.put((image, cam, personDetected), True, 1.0)    # try not to drop frames with detections
            else:
                results.put((image, cam, personDetected), True, 0.033)
        except:
            # presumably outptut queue was full, main thread too slow.
            mcnt+=1
            continue
    # Thread exits
    print("CPU AI thread" + str(tnum) + " is exiting, waited for input frames " + str(bcnt) + " times, dropped " + str(mcnt) + " output frames.")



# *** main()
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
def main():
    global QUIT
    global waitThreadSync
    global UImode
    UImode=0    # controls if MQTT buffers of processed images from selected camera are sent as topic: ImageBuffer
    global sendAll
    global saveAll
    global confidence
    global subscribeTopic
    global CamError
    global CameraURL
    global Nonvif
    global Nrtsp
    global Nrr_rtsp
    global Nmqtt
    global mqttCamOffset
    global mqttFrameDrops
    global inframe
    global Ncameras
    global mqttFrames    

    # *** get command line parameters
    # construct the argument parser and parse the arguments for this module
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--confidence", default=.75, help="detection confidence threshold")
    
    
    # number of software (CPU only) AI threads, always have one thread per installed NCS stick
    # os.cpu_count() will return the cores/hyperthreads, but appaentyl breaks Python 2.7 compatability
    ap.add_argument("-nt", "--nAIcpuThreads", type=int, default=1, help="0 --> no CPU AI thread, >0 --> N threads")

    # number of MQTT cameras published as Topic: MQTTcam/N, subscribed here as Topic: MQTTcam/#, Cams numbered 0 to N-1
    ap.add_argument("-Nmqtt", "--NmqttCams", type=int, default=0, help="number of MQTT cameras published as Topic: MQTTcam/N,  Cams numbered 0 to N-1")
    
    # enable/disable MQTT messages for UI dashboard images
    ap.add_argument("-send", "--sendAll", action="store_true", help="send all images, not just detections, via MQTT topic: DetectionImageBuffer/CamN")
    
    # disable using NCS, so I don't need to keep unplugging the NCS stick to test CPU only framerates.
    ap.add_argument("-noNCS", "--noNCS", action="store_true", help="don't probe for Movidius NCS")
    
    # specify text file with list of URLs for camera rtsp streams
    ap.add_argument("-rtsp", "--rtspURLs", default="MYcameraURL.rtsp", help="path to file containing rtsp camera stream URLs")
    
    # specify text file with list of URLs for round-robin sampling of security DVR rtsp streams
    ap.add_argument("-rr", "--rr_rtspURLs", default="MYcameraURL.rr", help="path to file containing DVR round-robin stream URLs")
    
    # specify text file with list of URLs cameras http "Onvif" snapshot jpg images
    ap.add_argument("-cam", "--cameraURLs", default="MYcameraURL.txt", help="path to file containing http camera jpeg image URLs")
    
    # display mode, mostly for test/debug and setup, general plan would be to run "headless"
    ap.add_argument("-d", "--display", type=int, default=2,
        help="display images on host screen, 0=no display, 1=detections only, 2=live & detections")

    # save all processed images 
    ap.add_argument("-save", "--saveAll", action="store_true", help="save all images not just detections on host filesystem, for test/debug")
    
    # specify MQTT broker
    ap.add_argument("-mqtt", "--mqttBroker", default="localhost", help="name or IP of MQTT Broker")

    # specify MQTT broker for camera images via MQTT, if not "localhost"
    ap.add_argument("-camMQTT", "--mqttCameraBroker", default="localhost", help="name or IP of MQTTcam/# message broker")
    
    # specify display width and height
    ap.add_argument("-dw", "--displayWidth", type=int, default=1920, help="host display Width in pixels, default=1920")
    ap.add_argument("-dh", "--displayHeight", type=int, default=1080, help="host display Height in pixels, default=1080")

    # specify host display width and height of camera image
    ap.add_argument("-iw", "--imwinWidth", type=int, default=640, help="camera image host display window Width in pixels, default=640")
    ap.add_argument("-ih", "--imwinHeight", type=int, default=360, help="camera image host display window Height in pixels, default=360")
    
    # specify file path of location to same detection images on the localhost
    ap.add_argument("-sp", "--savePath", default="", help="path to location for saving detection images, default ~/detect")
   
    args = vars(ap.parse_args())


    # set variables from command line auguments or defaults
    confidence = args["confidence"]
    nCPUthreads = args["nAIcpuThreads"]
    Nmqtt = args["NmqttCams"]
    dispMode = args["display"]
    if dispMode > 2:
        displayMode=2
    CAMERAS = args["cameraURLs"]
    RTSP = args["rtspURLs"]
    RR_RTSP = args["rr_rtspURLs"]
    saveAll = args["saveAll"]
    sendAll = args["sendAll"]
    noNCS = args["noNCS"]
    MQTTserver = args["mqttBroker"]
    MQTTcameraServer = args["mqttCameraBroker"]
    displayWidth = args["displayWidth"]
    displayHeight = args["displayHeight"]
    imwinWidth = args["imwinWidth"]
    imwinHeight = args["imwinHeight"]
    savePath = args["savePath"]
    

    # *** get Onvif camera URLs
    # cameraURL.txt file can be created by first running the nodejs program (requires node-onvif be installed):
    # nodejs onvif_discover.js
    #
    # This code does not really use any Onvif features, Onvif compatability is useful to "automate" getting  URLs used to grab snapshots.
    # Any camera that returns a jpeg image from a web request to a static URL should work.
    try:
        CameraURL=[line.rstrip() for line in open(CAMERAS)]    # force file not found
        Nonvif=len(CameraURL)
        CamError=list()
        for i in range(Nonvif):    # set up error flags for each camera
            CamError.append(False)
        print("[INFO] " + str(Nonvif) + " http Onvif snapshot threads will be created.")
    except:
        # fallback to trying cameras in my test setup
        print("[INFO] No " + str(CAMERAS) + " file.  No Onvif snapshot threads will be created.")
        Nonvif=0
    Ncameras=Nonvif


    # *** get rtsp URLs
    try:
        rtspURL=[line.rstrip() for line in open(RTSP)]
        Nrtsp=len(rtspURL)
        rtspError=list()
        for i in range(Nrtsp):    # set up error flags for each camera
            rtspError.append(False)
        print("[INFO] " + str(Nrtsp) + " rtsp stream threads will be created.")
    except:
        # fallback to trying cameras in my test setup
        print("[INFO] No " + str(RTSP) + " file.  No rtsp stream threads will be created.")
        Nrtsp=0
    Ncameras+=Nrtsp


    # *** get round-robin rtsp URLs
    try:
        rr_rtspURL=[line.rstrip() for line in open(RR_RTSP)]
        Nrr_rtsp=len(rr_rtspURL)
        rr_rtspError=list()
        for i in range(Nrr_rtsp):    # set up error flags for each camera
            rr_rtspError.append(False)
        print("[INFO] One round-robin rtsp thread with " + str(Nrr_rtsp) + " cameras will be created.")
    except:
        # fallback to trying cameras in my test setup
        print("[INFO] No " + str(RR_RTSP) + " file.  No round-robin rtsp thread will be created.")
        Nrr_rtsp=0
    Ncameras+=Nrr_rtsp


    # *** setup path to save AI detection images
    if savePath == "":
        detectPath= os.getcwd()
        if __WIN__ is True:
            detectPath=detectPath + "\\detect"
        else:
            detectPath=detectPath + "/detect"
        if os.path.exists(detectPath) == False:
            os.mkdir(detectPath)
    else:
        detectPath=savePath
        if os.path.exists(detectPath) == False:
            print(" Path to location to save detection images must exist!  Exiting ...")
            quit()


    # *** allocate queues
    # we simply make one queue for each camera, rtsp stream, and MQTTcamera
    QDEPTH = 2      # small values improve latency
    print("[INFO] allocating camera and stream image queues...")
    mqttCamOffset = Ncameras
    mqttFrameDrops = 0
    mqttFrames = 0
    Ncameras+=Nmqtt     # I generally expect Nmqtt to be zero if Ncameras is not zero at this point, but its not necessary
    if Ncameras == 0:
        print("[INFO] No Cameras, rtsp Streams, or MQTT image inputs specified!  Exiting...")
        quit()
    if Nmqtt > 0:
        print("[INFO] allocating " +str(Nmqtt) + " MQTT image queues...")
    inframe = list()
    if usingP2:
        results = Queue.Queue(2*Ncameras)        # AI output ( image, cam, detectedFlag )
        for i in range(Ncameras):
            if i < (Nonvif+Nrtsp+Nrr_rtsp):
                inframe.append(Queue.Queue(QDEPTH))
            else:
                inframe.append(Queue.Queue(QDEPTH+3))
    else:
        results = Queue(2*Ncameras)
        for i in range(Ncameras):
            if i < (Nonvif+Nrtsp+Nrr_rtsp):
                inframe.append(Queue(QDEPTH))
            else:
                inframe.append(Queue(QDEPTH+3))     # if latency really mattered, wouldn't use MQTT (ftp) cameras


    # *** detect NCS and setup one thread per NCS
    # No NCS support on Windows at present.
    Movidius = False
    if __WIN__ is False and noNCS is False:
        # grab a list of all NCS devices plugged in to USB
        print("[INFO] finding NCS devices...")
        devices = mvnc.EnumerateDevices()
        if len(devices) > 0:
            print("[INFO] found {} Movidius NCS devices.".format(len(devices)))
            Movidius=True
            # open the CNN graph file
            print("       loading the graph file into memory...")
            with open("./graphs/mobilenetgraph", mode="rb") as f:
                graph_in_memory = f.read()
            device = list()
            graph = list()
            for devnum in range(len(devices)):
                print("       opening device{} ...".format(devnum))
                device.append(mvnc.Device(devices[devnum]))
                device[devnum].OpenDevice()
                print("       allocating graph on NCS device{} ...".format(devnum))
                graph.append(device[devnum].AllocateGraph(graph_in_memory))


    # *** setup CPU AI threads, if any
    if __WIN__ is True or Movidius is False:
        Movidius = False
        # if no devices found, try and fall back to CPU only AI
        devices = 0
        if nCPUthreads > 0:
            print("[INFO] No NCS devices found. Falling back to CPU only AI")
        else:
            print("*** No NCS devices found and CPU threads turned off in startup option! --- Exiting...")
            quit()
    if nCPUthreads > 0:
        # load our serialized model from disk
        print("[INFO] loading Caffe model for CPU AI threads...")
        net=list()
        for i in range(nCPUthreads):
            net.append(cv2.dnn.readNetFromCaffe("cpuModel/MobileNetSSD_deploy.prototxt.txt", "cpuModel/MobileNetSSD_deploy.caffemodel"))


    # *** open rtsp streams
    if Nrtsp > 0:
        currentDT = datetime.datetime.now()
        print("[INFO] " + currentDT.strftime(" %H:%M:%S") + "  starting " + str(Nrtsp) + " RTSP capture streams, this takes some time ...")
        Rcap = list()
        for i in range(Nrtsp):
            Rcap.append(cv2.VideoCapture(rtspURL[i]))
            Rcap[i].set(cv2.CAP_PROP_BUFFERSIZE, 2)
            currentDT = datetime.datetime.now()
            print("       " + currentDT.strftime(" %H:%M:%S") + "  Camera" + str(i+Nonvif) + " rtsp stream is running...")


    # *** open rr-rtsp streams
    if Nrr_rtsp > 0:
        currentDT = datetime.datetime.now()
        print("[INFO] " + currentDT.strftime(" %H:%M:%S") + "  starting " + str(Nrr_rtsp) + " round-robin RTSP capture streams, this takes some time ...")
        rr_Rcap = list()
        for i in range(Nrr_rtsp):
            rr_Rcap.append(cv2.VideoCapture(rr_rtspURL[i]))
            rr_Rcap[i].set(cv2.CAP_PROP_BUFFERSIZE, 3)  # doesn't error but doesn't seem to reduce latency either
            currentDT = datetime.datetime.now()
            print("       " + currentDT.strftime(" %H:%M:%S") + "  Round-robin camera" + str(i+Nrtsp+Nonvif) + " rtsp stream is running...")

    # build grey image for mqtt windows
    img = np.zeros(( imwinHeight, imwinWidth, 3), np.uint8)
    img[:,:] = (127,127,127)
    retv, img_as_jpg = cv2.imencode('.jpg', img)


    # *** setup display windows if necessary
    # mostly for initial setup and testing, not worth a lot of effort at the moment
    if dispMode > 2:
        displayMode=2
    if dispMode > 0:
        if Nonvif > 0:
            print("[INFO] setting up Onvif camera image windows ...")
            for i in range(Nonvif):
                if dispMode == 1:
                    name=str("Detect_" + str(i))
                else:
                    name=str("Live_" + str(i))
                cv2.namedWindow(name, flags=cv2.WINDOW_GUI_NORMAL + cv2.WINDOW_AUTOSIZE)
                frame=OnvifSnapshot(i)
                if frame is None:
                    print("*** Bad Camera! *** URL: " + str(CameraURL[i]))
                    CamError[i]=True
                    continue
                cv2.imshow(name, cv2.resize(frame, (imwinWidth, imwinHeight)))
                cv2.waitKey(1)
        if Nrtsp > 0:
            print("[INFO] setting up rtsp camera image windows ...")
            for i in range(Nrtsp):
                if dispMode == 1:
                    name=str("Detect_" + str(i+Nonvif))
                else:
                    name=str("Live_" + str(i+Nonvif))
                cv2.namedWindow(name, flags=cv2.WINDOW_GUI_NORMAL + cv2.WINDOW_AUTOSIZE)
                ret, frame = Rcap[i].read()
                if not ret or frame is None:
                    print("*** Bad rtsp stream! *** URL: " + str(rtspURL[i]))
                    rtspError[i]=True
                    continue
                cv2.imshow(name, cv2.resize(frame, (imwinWidth, imwinHeight)))
                cv2.waitKey(1)
        if Nrr_rtsp > 0:
            print("[INFO] setting up round-robin rtsp camera image windows ...")
            for i in range(Nrr_rtsp):
                if dispMode == 1:
                    name=str("Detect_" + str(i+Nonvif+Nrtsp))
                else:
                    name=str("Live_" + str(i+Nonvif+Nrtsp))
                cv2.namedWindow(name, flags=cv2.WINDOW_GUI_NORMAL + cv2.WINDOW_AUTOSIZE)
                ret, frame = rr_Rcap[i].read()
                if not ret or frame is None:
                    print("*** Bad rtsp stream! *** URL: " + str(rr_rtspURL[i]))
                    rr_rtspError[i]=True
                    continue
                cv2.imshow(name, cv2.resize(frame, (imwinWidth, imwinHeight)))
                cv2.waitKey(1)
        if Nmqtt > 0:
            print("[INFO] setting up MQTT camera image windows ...")
            for i in range(Nmqtt):
                if dispMode == 1:
                    name=str("Detect_" + str(i+mqttCamOffset))
                else:
                    name=str("Live_" + str(i+mqttCamOffset))
                cv2.namedWindow(name, flags=cv2.WINDOW_GUI_NORMAL + cv2.WINDOW_AUTOSIZE)
                cv2.imshow(name, img)
                cv2.waitKey(1)
               


        # *** move windows into tiled grid
        top=38
        left=0
        Xshift=imwinWidth+3
        Yshift=imwinHeight+28
        Nrows=int(displayHeight/imwinHeight)    
        for i in range(Ncameras):
            if dispMode == 1:
                name=str("Detect_" + str(i))
            else:
                name=str("Live_" + str(i))
            col=int(i/Nrows)
            row=i%Nrows
            cv2.moveWindow(name, left+col*Xshift, top+row*Yshift)
                    

    # *** connect to MQTT broker
    print("[INFO] connecting to MQTT broker...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.will_set("AI/Status", "Python AI has died!", 2, True)  # let everyone know we have died, perhaps node-red can restart it
    client.connect(MQTTserver, 1883, 60)
    client.loop_start()

    # *** MQTT send a blank image to the dashboard UI
    print("[INFO] Clearing dashboard ...")
    client.publish("ImageName", "AI has started.", 2, False)
    client.publish("ImageBuffer", bytearray(img_as_jpg), 2, False)

    # *** Open second MQTT client thread for MQTTcam/# messages
    if Nmqtt > 0:
        print("[INFO] connecting to broker for MQTTcam...")
        mqttCam = mqtt.Client()
        mqttCam.on_connect = on_mqttCam_connect
        mqttCam.on_message = on_mqttCam
        mqttCam.on_publish = on_publish
        mqttCam.on_disconnect = on_disconnect
        mqttCam.connect(MQTTcameraServer, 1883, 60)
        mqttCam.loop_start()

    

    # *** start camera reading threads
    o = list()
    if Nonvif > 0:
        print("[INFO] starting " + str(Nonvif) + " Onvif Camera Threads ...")
        for i in range(Nonvif):
            o.append(Thread(target=onvif_thread, args=(inframe[i], i, CameraURL, CamError)))
            o[i].start()
    if Nrtsp > 0:
        print("[INFO] starting " + str(Nrtsp) + " RTSP Camera Sampling Threads ...")
        for i in range(Nrtsp):
            o.append(Thread(target=rtsp_thread, args=(inframe[i+Nonvif], i, Rcap, rtspURL, rtspError)))
            o[i+Nonvif].start()

    if Nrr_rtsp > 0:
        print("[INFO] starting 1 round-robin RTSP Camera Sampling Thread ...")
        o.append(Thread(target=rtsp_thread, args=(inframe[0], -1, rr_Rcap, rr_rtspURL, rr_rtspError)))
        o[Nrtsp+Nonvif].start()


    # *** start Movidius AI threads
    AIt = list()
    if Movidius is True:
        print("[INFO] starting " + str(len(devices)) + " Movidius NCS AI Threads ...")
        for i in range(len(devices)):
            AIt.append(Thread(target=AI_thread, args=(results, inframe, graph[i], i, cameraLock)))
            AIt[i].start()


    # *** start CPU AI threads
    CPUt = list()
    if nCPUthreads > 0:
        print("[INFO] starting " + str(nCPUthreads) + " CPU AI Threads ...")
        for i in range(nCPUthreads):
            CPUt.append(Thread(target=CPU_AI_thread, args=(results, inframe, net[i], i, cameraLock)))
            CPUt[i].start()


    # *** enter main program loop (main thread)
    # loop over frames from the camera and display results from AI_thread
    excount=0
    aliveCount=0
    currentDT = datetime.datetime.now()
    print("[INFO]" + currentDT.strftime(" %H:%M:%S") + "  syncronize thread start ...")
    waitThreadSync=False
    #start the FPS counter
    print("[INFO] starting the FPS counter ...")
    fps = FPS().start()
    print("[INFO] AI/Status: Python AI running." + currentDT.strftime("  %Y-%m-%d %H:%M:%S"))
    client.publish("AI/Status", "Python AI running." + currentDT.strftime("  %Y-%m-%d %H:%M:%S"), 2, True)
    while not QUIT:
        try:
            if not results.empty():
                (img, cami, personDetected) = results.get(False)
                fps.update()    # update the FPS counter
                #personDetected=True   # force every frame to be written for testing, use with -d 0 or -d 1 option
                # setup for file saving
                retv, img_as_jpg = cv2.imencode('.jpg', img)    # for sending image as mqtt buffer, 10X+ less data being sent.
                if not retv:
                    print("[INFO] conversion of np array to jpg in buffer failed!")
                    img_as_jpg = None
                currentDT = datetime.datetime.now()
                folder=currentDT.strftime("%Y-%m-%d")
                filename=currentDT.strftime("%H_%M_%S.%f")
                filename=filename[:-3]  #just keep milliseconds
                if __WIN__ is False:
                    folder=str(detectPath + "/" + folder)
                else:
                    folder=str(detectPath + "\\" + folder)
                if os.path.exists(folder) == False:
                    os.mkdir(folder)
                if __WIN__ is False:
                    if personDetected:
                        outName=str(folder + "/" + filename + "_" + "Cam" + str(cami) +"_AI.jpg")
                    else:
                        outName=str(detectPath + "/" + filename + "_" + "Cam" + str(cami) +".jpg")
                else:
                    if personDetected:
                        outName=str(folder + "\\" + filename + "_" + "Cam" + str(cami) +"_AI.jpg")
                    else:
                        outName=str(detectPath + "\\" + filename + "_" + "Cam" + str(cami) +".jpg")
                if personDetected and not AlarmMode.count("Idle"):  # save detected image
                    cv2.imwrite(outName, img)
                    client.publish("AI/Detection", outName, 2, False)
                    if img_as_jpg is not None:
                        client.publish(str("DetectionImageBuffer/Cam" + str(cami)), bytearray(img_as_jpg), 1, False)
                    print(outName)  # log detections
                elif saveAll is True:
                    cv2.imwrite(outName, img)
                if  sendAll is True and not personDetected:
                    if img_as_jpg is not None:
                        client.publish("ImageName", outName, 2, False)
                        client.publish(str("DetectionImageBuffer/Cam" + str(cami)), bytearray(img_as_jpg), 1, False)
                # save image for live display in dashboard
                if (CameraToView == cami) and (UImode == 1 or (UImode == 2 and personDetected)):
                    if img_as_jpg is not None:
                        client.publish("ImageName", outName, 2, False)
                        client.publish("ImageBuffer", bytearray(img_as_jpg), 1, False)
                # display the frame to the screen if enabled, in normal usage display is 0 (off)
                if dispMode > 0:
                    if personDetected and dispMode == 1:
                        name=str("Detect_" + str(cami))
                        cv2.imshow(name, cv2.resize(img, (imwinWidth, imwinHeight)))
                    else:
                        name=str("Live_" + str(cami))
                        cv2.imshow(name, cv2.resize(img, (imwinWidth, imwinHeight)))
            if dispMode > 0:
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"): # if the `q` key was pressed, break from the loop
                    QUIT=True   # exit main loop
                    continue
            aliveCount = (aliveCount+1) % 50
            if aliveCount == 0:
                client.publish("AmAlive", "true", 0, False)
        # if "ctrl+c" is pressed in the terminal, break from the loop
        except KeyboardInterrupt:
            QUIT=True   # exit main loop
            continue
        except Exception as e:
            currentDT = datetime.datetime.now()
            print(" **** Main Loop Error: " + str(e)  + currentDT.strftime(" -- %Y-%m-%d %H:%M:%S.%f"))
            excount=excount+1
            if excount <= 3:
                continue    # hope for the best!
            else:
                break       # give up! Hope watchdog gets us going again!
    #end of while not QUIT  loop


    # *** Clean up for program exit
    fps.stop()    # stop the FPS counter timer
    currentDT = datetime.datetime.now()
    print("Program Exit signal received:" + currentDT.strftime("  %Y-%m-%d %H:%M:%S"))
    
    # wait for threads to exit
    if Movidius is True:
        for i in range(len(devices)):
            if not results.empty():
               (_, _, _) = results.get(False)
            AIt[i].join()
        print("[INFO] All Movidius NCS AI Threads have exited ...")

    if nCPUthreads > 0:
        for i in range(nCPUthreads):
            if not results.empty():
                (_, _, _) = results.get(False)
            CPUt[i].join()
        print("[INFO] All CPU AI Threads have exited ...")

    if Nonvif > 0:
        for i in range(Nonvif):
            o[i].join()
    if Nrtsp > 0:
        for i in range(Nrtsp):
            o[i+Nonvif].join()
    if Nrr_rtsp > 0:    ## only single round-robin rtsp thread
            o[Nonvif+Nrtsp].join()
    print("[INFO] All Camera Threads have exited ...")

    
    # clean up rtsp streams
    if Nrtsp > 0:
        for i in range(Nrtsp):
            Rcap[i].release()
    # clean up rtsp streams
    if Nrr_rtsp > 0:
        for i in range(Nrr_rtsp):
            rr_Rcap[i].release()
            

    # display FPS information
    print("[INFO] Run elapsed time: {:.2f}".format(fps.elapsed()))
    print("[INFO] AI processing approx. FPS: {:.2f}".format(fps.fps()))
    print("[INFO] Frames processed by AI system: " + str(fps._numFrames))


    # destroy all windows if we are displaying them
    if args["display"] > 0:
        cv2.destroyAllWindows()


    # clean up the NCS graph and device
    if __WIN__ is False and Movidius is True:
        for devnum in range(len(devices)):
            graph[devnum].DeallocateGraph()
            device[devnum].CloseDevice()


    # Send a blank image the dashboard UI
    print("[INFO] Clearing dashboard ...")
    img = np.zeros((imwinHeight, imwinWidth, 3), np.uint8)
    img[:,:] = (64,64,64)
    retv, img_as_jpg = cv2.imencode('.jpg', img)
    client.publish("ImageName", "AI has exited.", 2, False)
    client.publish("ImageBuffer", bytearray(img_as_jpg), 2, False)
    time.sleep(1.0)


    # clean up MQTT
    currentDT = datetime.datetime.now()
    client.publish("AI/Status", "Python AI stopped." + currentDT.strftime("  %Y-%m-%d %H:%M:%S"), 2, True)
    print("AI/Status: Python AI stopped." + currentDT.strftime("  %Y-%m-%d %H:%M:%S"))
    client.disconnect()     # normal exit, Will message should not be sent.
    currentDT = datetime.datetime.now()
    print("Stopping MQTT Threads." + currentDT.strftime("  %Y-%m-%d %H:%M:%S"))
    time.sleep(1.0)
    client.loop_stop()      ### Stop MQTT thread
    if Nmqtt > 0:
        print("MQTT camera thread has dropped: " + str(mqttFrameDrops) + " frames out of: " + str(mqttFrames))
        mqttCam.loop_stop()

    # bye-bye
    currentDT = datetime.datetime.now()
    print("Program Exit." + currentDT.strftime("  %Y-%m-%d %H:%M:%S"))
    

# python boilerplate
if __name__ == '__main__':
    main()

