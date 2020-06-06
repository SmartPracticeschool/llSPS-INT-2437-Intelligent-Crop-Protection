import json
import datetime
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import cv2
import numpy as np
import sys
import ibmiotf.application
import ibmiotf.device
import random
import time
from playsound import playsound
import random

from cloudant.client import Cloudant
from cloudant.error import CloudantException 
from cloudant.result import Result, ResultByKey

from ibm_watson import VisualRecognitionV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

#twillio api credentials
from twilio.rest import Client

account_sid = 'AC8d25604e8b8c8016030f2f6e3a315241' 
auth_token = 'ff3f493c41df60b00f809af4cf603f14' 
FROM_NUMBER = '+12029329375'
TO_NUMBER = '+919963095773'          #number you want to send sms             


client2 = Client(account_sid, auth_token)

#Provide your IBM Watson Device Credentials
organization = "plwr0o"
deviceType = "rsip"
deviceId = "1711"
authMethod = "token"
authToken = "1234567890"

def myCommandCallback(cmd):
        print("Command received: %s" % cmd.data)
        print(cmd.data['command'])
        
        if(cmd.data['command']=="Servomotoron"):
                print("Servo motor on")
        if(cmd.data['command']=="Servomotoroff"):
                print("Servo motor off")

try:
	deviceOptions = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}
	deviceCli = ibmiotf.device.Client(deviceOptions)
	#..............................................
	
except Exception as e:
	print("Caught exception connecting device: %s" % str(e))
	sys.exit()

# Connect and send a datapoint "hello" with value "world" into the cloud as an event of type "greeting" 10 times
deviceCli.connect()

COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "JbmF_lEZF2mWhacw46Ga3S9dAYtBinyX4PHuLJM6q7-_" # eg "W00YiRnLW4a3fTjMB-oiB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/d39ef40c5e3e4377a6e97f47bdc16759:39c97034-7cb0-433c-843b-36d20adae79f::"

authenticator = IAMAuthenticator('AZ9mqzUZP8bIJTl0AzUAuvd7-gyFb1TsbOdAwZNTCO1P')
visual_recognition = VisualRecognitionV3(
    version='2018-03-19',
    authenticator=authenticator
)

visual_recognition.set_service_url('https://api.us-south.visual-recognition.watson.cloud.ibm.com/instances/07910fc0-f78a-4e64-b003-d8c8748d5df1')

client = Cloudant("28b096b5-d5c8-4ea1-8ac6-3142ff57803b-bluemix", "5399e404598b8afad48f4e7b6b67bcf3031bb3f201e2979cfb53852596b3c607", url="https://28b096b5-d5c8-4ea1-8ac6-3142ff57803b-bluemix:5399e404598b8afad48f4e7b6b67bcf3031bb3f201e2979cfb53852596b3c607@28b096b5-d5c8-4ea1-8ac6-3142ff57803b-bluemix.cloudantnosqldb.appdomain.cloud")
client.connect()
database_name = "animal"
picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
picname=picname+".jpg"
pic=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_RESOURCE_CRN,
    ibm_auth_endpoint=COS_AUTH_ENDPOINT,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # set 5 MB chunks
        part_size = 1024 * 1024 * 5

        # set threadhold to 15 MB
        file_threshold = 1024 * 1024 * 15

        # set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # the upload_fileobj method will automatically execute a multi-part upload
        # in 5 MB chunks for all files over 15 MB
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))


cam = cv2.VideoCapture(0)
cv2.namedWindow("Animal")



while True:
    ret, frame = cam.read()
    animal=0
    if not ret:
        print("failed to grab frame")
        break
    cv2.imshow("Animal", frame)

    
    k = cv2.waitKey(1) & 0xFF
    if  k== ord('q'):
        # q pressed
        print("q hit, closing...")
        break
    else:
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        picname=picname+".jpg"
        pic=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        cv2.imwrite(picname, frame)
        print("{} written!".format(picname))
        with open(picname, 'rb') as images_file:
            classes = visual_recognition.classify(
                images_file=images_file,
                threshold='0.6').get_result()
        print(json.dumps(classes, indent=2))
        for i in classes['images'][0]['classifiers'][0]['classes']:
            if i['class']=='animal':
                animal=1
        if animal==1:
                print("animal found turning on siren and leds")
                playsound('siren.mp3')
                print("sending message to user")
                message = client2.messages.create(      #sending sms to the user
                                   to=TO_NUMBER, 
                                   from_=FROM_NUMBER,
                                    body="Alert! animal has entered into your farm")
                print(message.sid)
                my_database = client.create_database(database_name)
                multi_part_upload("cloud-object-storage-dsx-cos-standard-60v",picname,pic+".jpg")
                if my_database.exists():
                        print("'{database_name}' successfully created.")
                        json_document = {
                                "_id": pic,
                                "link":COS_ENDPOINT+"/cloud-object-storage-dsx-cos-standard-60v/"+picname
                                }
                        new_document = my_database.create_document(json_document)
                        if new_document.exists():
                                print("Document '{new_document}' successfully created.")
        else :
                print("no animal found")
                my_database = client.create_database(database_name)
                multi_part_upload("cloud-object-storage-dsx-cos-standard-60v",picname,"none.jpg")
                if my_database.exists():
                        print("'{database_name}' successfully created.")
                        json_document = {
                                "_id": pic,
                                "link":COS_ENDPOINT+"/cloud-object-storage-dsx-cos-standard-60v/"+picname
                                }
                        new_document = my_database.create_document(json_document)
                        if new_document.exists():
                                print("Document '{new_document}' successfully created.")
                

        time.sleep(1)
        t=random.randint(1,100)
        h=random.randint(1,100)
        data = {"d":{ 'temperature' : t, 'humidity': h, 'animal': animal}}
        
        #print data
        def myOnPublishCallback():
            print ("Published data to IBM Watson")

        success = deviceCli.publishEvent("Data", "json", data, qos=0, on_publish=myOnPublishCallback)
        if not success:
            print("Not connected to IoTF")
        time.sleep(1)
        deviceCli.commandCallback = myCommandCallback

          

cam.release()
cv2.destroyAllWindows()
deviceCli.disconnect()
