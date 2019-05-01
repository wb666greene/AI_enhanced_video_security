# AI_enhanced_video_security
Python MobileNet-SSD AI using Movidius NCS and/or CPU OpenCV dnn module AI with "netcam" security cameras.

This is the evolution of, and essentially the end of, this initial project:
https://github.com/wb666greene/SecurityDVR_AI_addon
Further developement is moving to OpenVINO (for NCS2 support) and/or Google's new Coral TPU USB accelerator.
This code supports inputs from "Onvif" cameras using HTTP "jpeg snapshot" URLs, rtsp stream URLs, or jpeg images sent via MQTT messages.

This is a heavily threaded, stand alone Python program that has been developed on Ubuntu-Mate 16.04 and tested on: Raspberry Pi3B Raspbian "stretch", Ubuntu-Mate 18.04, Ubuntu 16.04 Virtualbox VM (CPU AI only, VM NCS function is not reliable), Windows 7, and Windows 10.  It should still run with Python 2.7 (only tested on Pi3B+) but Python 3.5.2 or newer is recommended.

**Note:** There is no NCS SDK support on Windows, but the OpenCV dnn module running on a decent i3 (4025U) gets about the same frame rate as does the NCS running on a Pi3B+, ~6 fps.  The dnn module on the Pi3B+ is too slow to be of much use at ~0.6 fps.  I do not run Windows or have a Windows machine.  My Windows comments are notes I took installing on friend's machines.

### **New**
In the extras folder is AI_OVmt.py, a simple modification to turn a CPU AI thread into an OpenVINO NCS/NCS2 thread. Some performance tests:
  - Using 5 Onvif snaphot netcams.
    Pi3B+:
     - NCS v1 SDK ~6.5 fps
     - 2 NCS v1 SDK ~11.6 fps
     - NCS OpenVINO ~5.9 fps
     - 2 NCS OpenVINO ~9.9 fps
     - NCS2 OpenVINO ~8.3 fps
  - Odroid XU-4:
     - NCS OpenVINO ~8.5 fps
     - 2 NCS OpenVINO ~15.9 fps
     - NCS2 OpenVINO ~15.5 fps


# Requirements:
  - Python 3.5.2 or newer, 2.7 should work if you can find all the modules.
  - pip to install:
    - paho-mqtt
    - numpy
    - requests
    - imutils
    - pillow
    - opencv-contrib-python
  - MQTT broker
    - runing locally is fine, actually prefered in many ways.
      - **Linux/Raspbian:**
        - sudo apt-get install mosquitto mosquitto-dev mosquitto-clients
      - **Windows:**
        - easy way: http://www.steves-internet-guide.com/install-mosquitto-broker/
        - official way, download it here: https://mosquitto.org/download/

# You will most likely want:
Some way to enable/disable the system and send alerts when the AI detects a person in the camera's view.  

The easiest way is to use the sample node-red "flow" **FTP_image_to_AI_via_MQTT.json** that I've included to get motion detected images from your Security DVR, systems like Zoneminder, Motioneye, motion etc., or your stand-alone netcams directly via FTP and let them handle the scheduling.  

The **AI_mt.py_Controller-Viewer.json** provides an example of how I send notifications and control the schedule (MQTT messages from a couple of PiZero-W systems that detect our presence or absense via BLE Radius Dot Beacons attaced to key fobs) and monitors the state of the door locks.  Giving three system "modes" Idle: when a door is unlocked (ignore all detections);  Audio: all doors locked and a BLE beacon is in range (announce detections using Espeak-ng speech synthesizer); and Notify: all doors locked and no BLE beacons in range (send SMS alert and Email with jpeg attachment of the detection image).

## Install node-red and learn about it here:
   https://nodered.org/  I think its ideal for this purpose and pretty easy to learn and modify the "flows" (programs) for your use case.
##   Questions about my node-red sample flows should go here: 
   https://discourse.nodered.org/t/final-version-of-security-cameras-with-ai-person-detection/9510/2 
   So we can get answers and imputs from the real node-red experts.
   
## Python code: 
   Issues/questions or installation and usasge questions, please raise an issue here.


# Usage Notes:

"logical cameras" are assigned one thread per physical camera for Onvif snapshot or rtsp stream cameras, numbered from zero in sequence Onvif, rtsp, MQTT (one thread handles all MQTT cameras).  The camera URLs are specified on the command line with options:
  - for Onvif (http jpeg): -cam or --cameraURLs  PathTo/OnvifCameraURLsFile
  - for rtsp streams: -rtsp or --rtspURLs  PathTo/rtspURLsFile
  - for MQTT (ftp) cameras Nmqtt or --NmqttCams  N, where N is the number of MQTT topics subscribed to as MQTTcam/0 ... MQTTcam/N-1 for each of the N cameras sending images via ftp using the node-red ftp server flow.
  - **for example:** command line
    - **python3 AI_mt.py -rtsp ./rtspStreams -Nmqtt 3 -cam ./httpCams** and files:
      - ./httpCams containg:
      
         `http://192.168.2.219:85/images/snapshot.jpg`
         
         `http://192.168.2.53/webcapture.jpg?command=snap&channel=1&user=admin&password=tlJwpbo6`
      - will create two Onvif snapshots cameras, Cam0 & Cam1
        
      - ./rtspStreams containing: 
      
        `rtsp://192.168.2.124:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream`
        
        `rtsp://admin:xyzzy@192.168.2.164:554/cam/realmonitor?channel=4&subtype=0`
        
        `rtsp://admin:xyzzy@192.168.2.164:554/cam/realmonitor?channel=11&subtype=0`
       - will create three rtsp stream cameras, Cam2, Cam3, & Cam4
        
        Along with 3 MQTT cameras Cam5, Cam6 & Cam7
         - on MQTT topics:
           - MQTTcam/0
           - MQTTcam/1
           - MQTT/cam2
         - **Note:** In the node-red ftp server flow you need to map the ftp file names to the cam0 ... cam2 topics.  The info in the comment node has a bit more details.
         
     - if one or more NCS sticks are plugged in one AI thread per NCS stick will be created along with one CPU AI thread unless the -nt 0 option is given to suppress the dnn AI thread (should always be given for Raspberry Pi).  A seperate thread is created to handle the MQTTcam/N messages.  Thus there always is a main thread and a thread for the mundane MQTT messages, along with one thread per Onvif camera and rtsp stream, a thread for the MQTT cameras if necessary, one AI thread per NCS stick and one thread per dnn AI (it rarely makes sense to have -nt >1) -- in this case 2+5+1+1+1=10 threads will be running assumig a single NCS still is plugged in.
     - **Important!** no blank lines or blank line at the end of the URL files or a null URL camera will be created that causes errors while running.
           

# Some performance numbers:
   - **Pi3B+:**   CPU AI is too slow to be useful ~0.6 fps,  start program with option:  - nt 0
     - Python 2.7:
       - 5 Onvif cameras 1 NCS gets ~6.5 fps, 2 NCS doesn't run reliably, NCS timeout errors, power suppy issue?  
     - Python 3.5  
       - 5 Onvif cameras 1 NCS gets ~6.6 fps, same erratic results with two NCS sticks, but short runs do ~11.7 fps
           with a 3.5A powered hub two NCS sticks got ~11.6 fps for a 15 minute run.
       - 5 rtsp streams gets ~4.5 fps, 2 NCS gets ~6.2 fps  I don't think the Pi is a very good for rtsp streams.           
   - **i3 4025U:**
     - Windows7:
       - 5 Onvif cameras gets ~6.2 fps.
       - 5 rtsp streams gets ~5.2fps.
     - Windows10
       - 5 Onvif cameras gets ~6.1 fps.
       - 5 rtsp streams gets ~5.3 fps.
     - Ubuntu16.04:   same hardware, CPU AI only, No NCS installed to compare with Windows (dual boot)
       - 5 Onvif cameras gets ~8.4 fps.
       - 5 rtsp streams ~7.4 fps.
   - **i5 M540:**    old CPU without AVX, AVX2,  lack of USB3 holds back NCS performance
     - Ubuntu-Mate16.04: 
       - 5 Onvif, CPU AI does poorly ~3.9 fps, better than Pi3 but worse than i3 4025U.
       - 5 Onvif, 1 NCS, no CPU AI gets ~8.8 fps, 2 NCS ~17.0 fps, 1 NCS + 1 CPU AI ~12.0 fps.
       - 5 rtsp, 1 NCS, no CPU AI ~8.8 fps.
   - **i5 4200U:**
     - Ubuntu-Mate16.04 
       - 5 rtsp, CPU AI ~9.7 fps.
       - 5 rtsp, CPU AI + 1 NCS ~18.1 fps.
   - **i7 4500U:**    
     - Ubuntu-Mate16.04 
       - 5 rtsp, CPU AI gets ~10.6 fps
       - 5 rtsp, 1 NCS, no CPU AI gets ~10.7 fps
       - 5 rtsp, CPU AI + 1 NCS gets ~20.1 fps
       - 5 rtsp, CPU AI + 2 NCS gets ~24.4 fps, likely camera limited, as each stream is set to 5 fps.
     - Ubuntu-Mate18.04
       - 5 rtsp, CPU AI + 1 NCS ~19.5 fps.
   - **i7-6700K:** 4 GHz quad core, my development system, while "everything else" I do is running.
     - Ubuntu-Mate16.04  
       - 2 Onvif, 5 rtsp, 1 mqtt (ftp)  gets ~29.4 fps wtih one NCS and one CPU AI thread.
        



# If using NCS:
  - Install NCS v1 SDK:
    - **Linux:** (Debian derived)
      - sudo apt-get install git build-essential
      - mkdir ncs
      - cd ncs
      - git clone https://github.com/movidius/ncsdk.git
      - cd ncsdk
      - make install
      - **important** close all terminals and re-opoen to get the new invironment that is setup
      - test the installation, plug in NCS stick then do:
      - make examples
    - **Raspbian:**
      - On fresh Pi Raspbian Stretch install as root do:
      - apt-get update || apt-get upgrade
      - `apt-get install libusb-1.0-0-dev libprotobuf-dev libleveldb-dev libsnappy-dev libopencv-dev libhdf5-serial-dev protobuf-compiler libatlas-base-dev git automake byacc lsb-release cmake libgflags-dev libgoogle-glog-dev liblmdb-dev swig3.0 graphviz libxslt-dev libxml2-dev gfortran`
      - then install python3 stuff:
      - `apt-get install python3-dev python-pip python3-pip python3-setuptools python3-markdown python3-pillow python3-yaml  python3-pygraphviz python3-h5py python3-nose python3-lxml python3-matplotlib python3-numpy python3-protobuf python3-dateutil python3-skimage python3-scipy python3-six python3-networkx`
      - exit root and download and install NCS SDK:
      - mkdir ncs
      - cd ncs
      - git clone https://github.com/movidius/ncsdk
      - git clone https://github.com/movidius/ncappzoo
      - cd ~/ncs/ncsdk/api/src
      - make
      - sudo make install
      - test it: (make sure the NCS sick is plugged in!)
      - cd ~/ncs/ncappzoo/apps/hello_ncs_py
      - make run
        - should return:
        
           `Hello NCS! Device opened normally.`
           
           `Goodbye NCS! Device closed normally.`
           
           `NCS device working.`
  

# Windows notes:
  - Download python3 ( https://www.python.org/downloads/windows/ ) and install (includes Idle & pip).
  - open a command window and run:
    - pip install opencv-contrib-python requests pillow imutils paho-mqtt
    - For OpenCV on Windows7 vc_redist.X64 and vc_redist.x86 may need to be installed, api-ms-win-downlevel-shlwapi-l1-1-0.dll may be missing, we found it here https://www.dll-files.com/



  
