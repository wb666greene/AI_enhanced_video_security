# AI_enhanced_video_security
Python MobileNet-SSD AI using Movidius NCS and/or CPU OpenCV dnn module AI with "netcam" security cameras.
It supports inputs from "Onvif" cameras uisng HTTP "jpeg snapshot" URLs, rtsp stream URLs, or jpeg images send via MQTT messages.

This is a heavily threaded, stand alone Python program that has been developed on Ubuntu-Mate 16.04 and tested on: Raspberry Pi3B Raspbian "stretch", Ubuntu-Mate 18.04, Ubuntu 16.04 Virtualbox VM (CPU AI only, VM NCS function is not reliable), Windows 7, and Windows 10.  It should still run with Python 2.7 (only tested on Pi3B+) but Python 3.5.2 or newer is recommended.
