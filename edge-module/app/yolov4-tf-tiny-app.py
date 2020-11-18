# Copyright (c) Micheleen Harris
# Licensed under the MIT License.
"""
App to run inference server for YOLO v4 TFLite model and send
frames to Azure Blob IoT Edge module.
"""
import core.utils as utils
from core.yolov4 import filter_boxes

import tensorflow as tf
from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession

import threading
import io
import json
import os
import copy
import time
import datetime
import base64
import traceback
import sys

from PIL import Image
import cv2
import numpy as np
from flask import Flask, request, jsonify, Response

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv, find_dotenv

# Look for a file called .env that contains necessary environment variables
load_dotenv(find_dotenv())


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

FLAGS = dotdict({
    'framework': 'tflite',
    'weights':  os.path.join(os.getcwd(), 'yolov4-tiny.tflite'),
    'output':  os.path.join('/home','results.jpg'), # debugging
    'size': 416,
    'tiny': True,
    'model': 'yolov4',
    'iou': 0.45,
    'score': 0.25
})

class YoloV4TinyModel:
    def __init__(self):
        """Initialize class object"""
        self._lock = threading.Lock()

        with open('./data/classes/coco.names', "r") as f:
            self._labelList = [l.rstrip() for l in f]

        config = ConfigProto()
        session = InteractiveSession(config=config)
        STRIDES, ANCHORS, NUM_CLASS, XYSCALE = utils.load_config(FLAGS)

        self.input_size = FLAGS.size

        self.interpreter = tf.lite.Interpreter(model_path=FLAGS.weights)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Connect to local, edge Blob Storage
        self._local_account = os.getenv("LOCAL_STORAGE_ACCOUNT_NAME", "UNKNOWN_NAME")
        self._local_blob_key = os.getenv("LOCAL_STORAGE_ACCOUNT_KEY", "UNKNOWN_KEY")
        self.local_container_name = os.getenv("LOCAL_STORAGE_CONTAINER_NAME", "UNKNOWN_NAME")
        super_str = 'DefaultEndpointsProtocol=http;AccountName=' + \
            self._local_account + \
            ';AccountKey=' + self._local_blob_key + \
            ';BlobEndpoint=http://azureblobstorageoniotedge:11002/' + \
            self._local_account + ';'
        self.blob_service_client = BlobServiceClient.from_connection_string(super_str,
            api_version='2019-07-07')
        self.container_client = self.blob_service_client.get_container_client(
            self.local_container_name)
        try:
            self.container_client.create_container()
        except Exception as err: # Error because already exists
            print([{'[INFO]': 
                'Problem during creation of storage container : {}'.format(repr(err))}])

    def Preprocess(self, cvImage):
        """Preprocess cv2/opencv formatted image: convert to RGB, resize, 
        normalize, expand dimensions and convert to uint8 for quantized tflite model.
        """
        imageBlob = cv2.cvtColor(cvImage, cv2.COLOR_BGR2RGB)
        imageBlob = cv2.resize(imageBlob, (self.input_size, self.input_size))
        imageBlob = imageBlob / 255. # normalize
        imageBlob = imageBlob[np.newaxis, ...].astype(np.float32) # batch size 1
        return imageBlob

    def Postprocess(self, boxes, scores, indices):
        detectedObjects = []

        if len(indices) > 0:
            for i in range(len(indices)):
                if scores[i] > FLAGS.score:
                    idx = int(indices[i])
                    temp = boxes[i] # ymin, xmin, ymax, xmax
                    
                    dobj = {
                        "type" : "entity",
                        "entity" : {
                            "tag" : {
                                "value" : self._labelList[idx],
                                "confidence" : str(scores[i])
                            },
                            "box" : {
                                "l" : str(temp[1]), # xmin
                                "t" : str(temp[0]), # ymax (from top)
                                "w" : str(temp[3]-temp[1]), # xmax-xmin
                                "h" : str(temp[2]-temp[0]) # ymax-ymin
                            }
                        }
                    }

                    detectedObjects.append(dobj)

        return detectedObjects

    def Score(self, cvImage):
        """Use tflite interpreter to predict bounding boxes and 
        confidence score."""
        with self._lock:
            timestamp = datetime.datetime.now()
            # Predict
            try:
                image_data = self.Preprocess(cvImage)
                self.interpreter.set_tensor(self.input_details[0]['index'], image_data)
                self.interpreter.invoke()
                pred = [self.interpreter.get_tensor(
                    self.output_details[i]['index']) for i in range(len(self.output_details))]
            except Exception as err:
                return [{'[ERROR]': 'Error during prediciton: {}'.format(repr(err))}]

            # Filter and NMS
            try:
                boxes, pred_conf = filter_boxes(pred[0], pred[1], score_threshold=0.25,
                                                    input_shape=tf.constant([self.input_size,
                                                                            self.input_size]))
                boxes, scores, indices, valid_detections = tf.image.combined_non_max_suppression(
                    boxes=tf.reshape(boxes, (tf.shape(boxes)[0], -1, 1, 4)),
                    scores=tf.reshape(
                        pred_conf, (tf.shape(pred_conf)[0], -1, tf.shape(pred_conf)[-1])),
                    max_output_size_per_class=50,
                    max_total_size=50,
                    iou_threshold=FLAGS.iou,
                    score_threshold=FLAGS.score)
            except Exception as err:
                return [{'[ERROR]': 'Error during filter and NMS: {}'.format(repr(err))}]

            try:
                # Save image w/ annotations to Blob Storage (through IoT module 
                # and then to cloud Azure Storage pending connectivity)
                pred_bbox = [boxes.numpy(),
                             scores.numpy(),
                             indices.numpy(),
                             valid_detections.numpy()]
                image = cv2.cvtColor(cvImage, cv2.COLOR_BGR2RGB)
                image = utils.draw_bbox(image, pred_bbox)
                #image = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_BGR2RGB)
                image = image.astype(np.uint8)[:, :, [2, 1, 0]]
                pil_image = Image.fromarray(image)
                # To check if there are bboxes
                indices_check = np.squeeze(indices.numpy(), axis=0)
                scores_check = np.squeeze(scores.numpy(), axis=0)
                if scores_check.any() > FLAGS.score:
                    # Save image to buffer
                    bytes_io = io.BytesIO()
                    pil_image.save(bytes_io, format='JPEG')
                    bytes_im = bytes_io.getvalue()
                    # Name in blob to use
                    blob_name = str(timestamp.strftime(
                        "%d-%b-%Y-%H-%M-%S.%f")) +"_annotated.jpg"
                    blob_metadata = {'timestamp': str(timestamp.strftime("%d-%b-%Y-%H-%M-%S.%f")),
                            'objects': ','.join(set([self._labelList[int(indices_check[i])] for i in range(
                                len(indices_check)) if scores_check[i] > FLAGS.score]))}
                    try:
                        container_client = self.blob_service_client.get_container_client(
                            self.local_container_name)
                        props = container_client.get_container_properties()
                    except Exception as err:
                        # Local container needs to be created if not
                        container_client.create_container()
                    # Upload pil image as buffer
                    container_client.upload_blob(blob_name, bytes_im, metadata=blob_metadata)
            except Exception as err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                return [{'[ERROR]': 
                    'Error sending image to local blob storage: {}'.format(
                     repr(traceback.format_exception(
                         exc_type,
                         exc_value,
                         exc_traceback)))}]

            # Postprocess
            try:
                boxes = np.squeeze(boxes.numpy(), axis=0)
                scores = np.squeeze(scores.numpy(), axis=0)
                indices = np.squeeze(indices.numpy(), axis=0)
                results = self.Postprocess(boxes, scores, indices)
            except Exception as err:
                return [{'[ERROR]': 'Error during postprocess: {}'.format(repr(err))}]

        return results

# global ml model class
yolo = YoloV4TinyModel()

app = Flask(__name__)

# / routes to the default function which returns 'Hello World'
@app.route('/', methods=['GET'])
def defaultPage():
    return Response(response='Hello from Tiny Yolov4 inferencing based on TensorFlow Lite', status=200)

# /score routes to scoring function 
# This function returns a JSON object with inference duration and detected objects
@app.route('/score', methods=['POST'])
def score():
    global yolo
    try:
        # get request as byte stream
        reqBody = request.get_data(False)

        # convert from byte stream
        inMemFile = io.BytesIO(reqBody)

        # load a sample image
        inMemFile.seek(0)
        fileBytes = np.asarray(bytearray(inMemFile.read()), dtype=np.uint8)

        cvImage = cv2.imdecode(fileBytes, cv2.IMREAD_COLOR)

        # Infer Image
        detectedObjects = yolo.Score(cvImage)

        if len(detectedObjects) > 0:
            respBody = {                    
                        "inferences" : detectedObjects
                    }

            respBody = json.dumps(respBody)
            return Response(respBody, status= 200, mimetype ='application/json')
        else:
            return Response(status= 204)

    except Exception as err:
        return Response(response='[ERROR] Exception in score : {}'.format(repr(err)), status=500)

if __name__ == '__main__':
    # Run the server
    app.run(host='0.0.0.0', port=8888)
