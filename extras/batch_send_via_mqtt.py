#!/usr/bin/python
# USAGE
# python batch_send_via_mqtt.py 
#
# sends all the files in the test_pics directory via mqtt
# 20MAR2019wbk
# derived from code shared by @krambriw on the node-red user forum

import argparse
import os
import paho.mqtt.client as mqtt
import glob
import time

def on_publish(mosq, userdata, mid):
    mosq.disconnect()
    exit(0)
    

ap = argparse.ArgumentParser()
#ap.add_argument( "-p",  "--pic",  required=True,  help="path and filename")
#ap.add_argument( "-c",  "--camera_nbr",  required=True,  help="camera number" )
ap.add_argument( "-i",  "--pathToImages",  required=True,  help="path to folder of jpeg images to be sent via MQTT" )
args = vars(ap.parse_args())
pathToImages = args['pathToImages']

client = mqtt.Client()

# Just edit the ip address and port number to fit your setup for
# the computer running the Centralized DNN analyzer
#client.connect("192.168.10.252", 1883, 60)
client.connect("localhost", 1883, 60)

#f = open(args['pic'], "rb")
for filename in glob.glob(pathToImages + '/*.jpg'):
    # Read an image
    f=open(filename,'rb')
    fileContent = f.read()
    f.close()
    byteArr = bytearray(fileContent)
    #client.publish("image/"+args['camera_nbr'], byteArr, 1, False)
    client.publish("MQTTcam/0", byteArr, 1, False)
    client.loop(0.100)
    time.sleep(0.100)
# quick and dirty exit just send the last image a second time and exit
client.publish("MQTTcam/0", byteArr, 1, False)
client.on_publish = on_publish
client.loop_forever()
