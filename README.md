# AI_enhanced_video_security
Python MobileNet-SSD AI using Movidius NCS and/or CPU OpenCV dnn module AI with "netcam" security cameras.

This is the evolution of, and essentially the end of, this initial project:
https://github.com/wb666greene/SecurityDVR_AI_addon

It supports inputs from "Onvif" cameras uisng HTTP "jpeg snapshot" URLs, rtsp stream URLs, or jpeg images sent via MQTT messages.

This is a heavily threaded, stand alone Python program that has been developed on Ubuntu-Mate 16.04 and tested on: Raspberry Pi3B Raspbian "stretch", Ubuntu-Mate 18.04, Ubuntu 16.04 Virtualbox VM (CPU AI only, VM NCS function is not reliable), Windows 7, and Windows 10.  It should still run with Python 2.7 (only tested on Pi3B+) but Python 3.5.2 or newer is recommended.

**Note:** There is no NCS support on Windows, but the OpenCV dnn module running on a decent i3 (4025U) gets about the same frame rate as does the NCS running on a Pi3B+, ~6 fps.  The dnn module on the Pi3B+ is too slow to be of much use at ~0.6 fps.

# Requirements:
  - Python 3.5.2 or newer, 2.7 should work if you can find all the modules.
  - pip to install:
    - paho-mqtt
    - numpy
    - requests
    - imutils
    - pillow
    - opencv-contrib-python
    
  
