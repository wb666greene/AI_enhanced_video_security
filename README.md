# AI_enhanced_video_security
Python MobileNet-SSD AI using Movidius NCS and/or CPU OpenCV dnn module AI with "netcam" security cameras.

This is the evolution of, and essentially the end of, this initial project:
https://github.com/wb666greene/SecurityDVR_AI_addon
Further developement is moving to OpenVINO (for NCS2 support) and or Google's new Coral TPU USB accelerator.

It supports inputs from "Onvif" cameras using HTTP "jpeg snapshot" URLs, rtsp stream URLs, or jpeg images sent via MQTT messages.

This is a heavily threaded, stand alone Python program that has been developed on Ubuntu-Mate 16.04 and tested on: Raspberry Pi3B Raspbian "stretch", Ubuntu-Mate 18.04, Ubuntu 16.04 Virtualbox VM (CPU AI only, VM NCS function is not reliable), Windows 7, and Windows 10.  It should still run with Python 2.7 (only tested on Pi3B+) but Python 3.5.2 or newer is recommended.

**Note:** There is no NCS support on Windows, but the OpenCV dnn module running on a decent i3 (4025U) gets about the same frame rate as does the NCS running on a Pi3B+, ~6 fps.  The dnn module on the Pi3B+ is too slow to be of much use at ~0.6 fps.  I do not run Windows or have a Windows machine.  My Windows comments are notes I took installing on friend's machines.

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

The easiest way is to use the sample node-red "flow" **FTP_image_to_AI_via_MQTT.json** that I've included to get motion detected images from your Security DVR, systems like Zoneminder, Motioneye, motion etc., or your directly netcams via FTP and let them handle the scheduling.  

The **AI_mt.py_Controller-Viewer.json** provides an example of how I end notifications and control the schedule (MQTT messages from a couple of PiZero-W systems that detect our presence or absense via BLE Radius Dot Beacons attaced to key fobs) and monitors the state of the door locks.  Giving three system "modes" Idle: when a door is unlocked (ignore all detections);  Audio: all doors locked and a BLE beacon is in range (announce detections using Espeak-ng speech synthesizer); and Notify: all doors locked and no BLE beacons in range (send SMS alert and Email with jpeg attachment of the detection image).


## Usage Notes:




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



  
