#!/usr/bin/env python

import logging
import threading
import time
import urllib.request
import boto3
import json
import os
from datetime import datetime
from time import sleep
import subprocess
import pynvml

logger = logging.getLogger()
logger.setLevel(logging.INFO)

pynvml.nvmlInit()
deviceCount = pynvml.nvmlDeviceGetCount()

### CHOOSE REGION ####
EC2_REGION = 'us-east-1'

### CHOOSE NAMESPACE PARMETERS HERE###
my_NameSpace = 'DeepLearningTrain-1' 

### CHOOSE PUSH INTERVAL ####
sleep_interval = 10

### CHOOSE STORAGE RESOLUTION (BETWEEN 1-60) ####
store_reso = 60

#Instance information
BASE_URL = 'http://169.254.169.254/latest/meta-data/'
INSTANCE_ID = urllib.request.urlopen(BASE_URL + 'instance-id').read().decode("utf-8")
IMAGE_ID = urllib.request.urlopen(BASE_URL + 'ami-id').read().decode("utf-8")
INSTANCE_TYPE = urllib.request.urlopen(BASE_URL + 'instance-type').read().decode("utf-8")
INSTANCE_AZ = urllib.request.urlopen(BASE_URL + 'placement/availability-zone').read()
EC2_REGION = INSTANCE_AZ[:-1]

TIMESTAMP = datetime.now().strftime('%Y-%m-%dT%H')
TMP_FILE = '/tmp/GPU_TEMP'
TMP_FILE_SAVED = TMP_FILE + TIMESTAMP

# Create CloudWatch client
cloudwatch = boto3.client('cloudwatch', region_name=EC2_REGION.decode('utf-8'))
    
# Flag to push to CloudWatch
PUSH_TO_CW = True

def getPowerDraw(handle):
    try:
        powDraw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        powDrawStr = '%.2f' % powDraw
    except pynvml.NVMLError as err:
        powDrawStr = handleError(err)
        PUSH_TO_CW = FalseG
    return powDrawStr

def getTemp(handle):
    try:
        temp = str(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
    except pynvml.NVMLError as err:
        temp = handleError(err) 
        PUSH_TO_CW = False
    return temp

def getUtilization(handle):
    try:
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_util = str(util.gpu)
        mem_util = str(util.memory)
    except pynvml.NVMLError as err:
        error = handleError(err)
        gpu_util = error
        mem_util = error
        PUSH_TO_CW = False
    return util, gpu_util, mem_util

def logResults(i, util, gpu_util, mem_util, powDrawStr, temp):
    try:
        gpu_logs = open(TMP_FILE_SAVED, 'a+')
        writeString = str(i) + ',' + gpu_util + ',' + mem_util + ',' + powDrawStr + ',' + temp + '\n'
        gpu_logs.write(writeString)
    except:
        print("Error writing to file ", gpu_logs)
    finally:
        gpu_logs.close()
    if (PUSH_TO_CW):
        MY_DIMENSIONS=[
                    {
                        'Name': 'InstanceId',
                        'Value': str(INSTANCE_ID)
                    },
                    {
                        'Name': 'ImageId',
                        'Value': str(IMAGE_ID)
                    },
                    {
                        'Name': 'InstanceType',
                        'Value': str(INSTANCE_TYPE)
                    },
                    {
                        'Name': 'GPUNumber',
                        'Value': str(i)
                    }
                ]
        cloudwatch.put_metric_data(
            MetricData=[
                {
                    'MetricName': 'GPU Usage',
                    'Dimensions': MY_DIMENSIONS,
                    'Unit': 'Percent',
                    'StorageResolution': store_reso,
                    'Value': util.gpu
                },
                {
                    'MetricName': 'Memory Usage',
                    'Dimensions': MY_DIMENSIONS,
                    'Unit': 'Percent',
                    'StorageResolution': store_reso,
                    'Value': util.memory
                },
                {
                    'MetricName': 'Power Usage (Watts)',
                    'Dimensions': MY_DIMENSIONS,
                    'Unit': 'None',
                    'StorageResolution': store_reso,
                    'Value': float(powDrawStr)
                },
                {
                    'MetricName': 'Temperature (C)',
                    'Dimensions': MY_DIMENSIONS,
                    'Unit': 'None',
                    'StorageResolution': store_reso,
                    'Value': int(temp)
                },            
        ],
            Namespace=my_NameSpace
        )

def log_custom_GPU_metrics():
    #for _ in range(1000):
    while True:
        time.sleep(.166)
        for gpu in range(deviceCount):
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu)
            util, gpu_util, mem_util =  getUtilization(handle)
            logResults(id, util, gpu_util, mem_util, getPowerDraw(handle), getTemp(handle))
            logger.info('Launched')
            
def main():
    cw_logger_thread = threading.Thread(target=log_custom_GPU_metrics)
    cw_logger_thread.setDaemon(True)
    print(cw_logger_thread.is_alive())
    cw_logger_thread.start()
    print('Started')
    #cw_logger_thread.join()
    print('Launched')
    
    time.sleep(3)
    print(cw_logger_thread.is_alive())
    
    while True:
        sleep(60)
        print(cw_logger_thread.is_alive())

    
if __name__=='__main__':
    main()
