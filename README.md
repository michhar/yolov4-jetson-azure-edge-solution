# Tiny YOLOv4 TensorFlow Lite model on Jetson Xavier with Azure Blob Storage and Live Video Analytics

This repo is an example of running an AI container on the Jetson platform in conjunction with the [Azure Blob Storage IoT Edge module](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-store-data-blob?view=iotedge-2018-06) using the [Live Video Analytics](https://docs.microsoft.com/en-us/azure/media-services/live-video-analytics-edge/) as a platform ontop of [Azure IoT Edge](https://docs.microsoft.com/en-us/azure/iot-edge/?view=iotedge-2018-06) runtime.

The purpose of this architecture is to create a pipeline that can route video (frame-by-frame) into an AI module for inferencing on the edge (image classification, object detection, etc.) that, in turn, stores output frames in a Blob Storage IoT Edge module storage container (a storage container, here, is a unit of storage within the Blob Edge module).  The Blob Storage IoT storage container or set of containers essentially replicate to the Azure cloud (using some tunable user settings), to Azure Blob Storage, given internet connectivity (or stores on the edge until connectivity is achieved).  

In the diagram below, frames from an AI module are shown being sent on the edge to two storage containers in the Blob Edge module:  1) for highly confident detection frames and 2) for the more poorly scoring detections (an indication that objects might not be being detected well by the ML model).  Poorly performing frames from the AI edge module are good candidates for labeling and retraining the vision ML model to boost performance, thus have their own container, "unannotaed".  Once the frames are replicated in the cloud in Azure Blob Storage, [Azure Machine Learning](https://docs.microsoft.com/en-us/azure/machine-learning/) may be used to label and retrain the ML model.  The confident, annotated frames in the "annotated" conatiner could be reviewed, for instance, within an Azure Web App (code not provided, here).

![architecture of using Azure Blob Storage iot edge module with LVA](assets/LVA-AI-Blob.jpg)

This AI module (docker container) utilizes the GPU on the Jetson (with NVIDIA drivers, CUDA and cuDNN installed) using an NVIDIA L4T (linux for Tegra) base image with TensorFlow 2 installed.  The Jetson must have been flashed with Jetpack 4.4.

## Xavier Setup and requirements

- Flashed with JetPack 4.4 (L4T R32.4.3) with all ML and CV tools (including `nvidia-docker`)
- Samsung NVMe to store docker images and serve as location for Blob Storage data
- 16 GB swap file on NVMe mount
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt#manual-install-instructions) for pushing image to Azure Container Registry
- [Optional] Docker may be configured to run with non-root user as in [Manage Docker as a non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) allowing the omission of using `sudo` with docker

## Build image

The following instructions will enable you to build a docker container with a [YOLOv4 (tiny)](https://github.com//AlexeyAB/darknet) [TensorFlow Lite](https://www.tensorflow.org/lite) model using [nginx](https://www.nginx.com/), [gunicorn](https://gunicorn.org/), [flask](https://github.com/pallets/flask), and [runit](http://smarden.org/runit/).  The app code is based on the [tensorflow-yolov4-tflite](https://github.com/hunglc007/tensorflow-yolov4-tflite) project.  This project uses TensorFlow v2.

Note: References to third-party software in this repo are for informational and convenience purposes only. Microsoft does not endorse nor provide rights for the third-party software. For more information on third-party software please see the links provided above.

### Prerequisites for building image

1. [Ensure NVIDIA Docker](https://github.com/NVIDIA/nvidia-docker/wiki/NVIDIA-Container-Runtime-on-Jetson) on your Jetson
2. [Install curl](http://curl.haxx.se/)
3. [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt) to be able to push image to Azure Container Registry (ACR)

### Preparing for using Blob Storage on the Edge

1. Create a file in the `app/` folder called `.env` with the following contents:

```
LOCAL_STORAGE_ACCOUNT_NAME=<Name for local blob storage in IoT edge Blob Storage module>
LOCAL_STORAGE_ACCOUNT_KEY=<Key generated for local IoT edge Blob Storage module in double quotes>
```

### Building the docker container

1. Create a new directory on your machine and copy all the files (including the sub-folders) from this GitHub repo to that directory.
2. Build the container image (will take several minutes) by running the following docker command from a terminal window in that directory.

```bash
sudo nvidia-docker build . -t tiny-yolov4-tflite:arm64v8-cuda-cudnn -f arm64v8-gpu-cudnn.dockerfile
```

### Upload docker image to Azure Container Registry

Log in to ACR with the Azure CLI (also may use docker login):

```
az acr login --name <name of your ACR user>
```

Push the image to ACR:

```
docker push <your ACR URL>/tiny-yolov4-tflite:arm64v8-cuda-cudnn
```

Note:
- More instruction at [Push and Pull Docker images - Azure Container Registry](http://docs.microsoft.com/en-us/azure/container-registry/container-registry-get-started-docker-cli) to save your image for later use on another machine.
- IMPORTANT:  Docker may need to be configured to run with non-root user as in [Manage Docker as a non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).

    
## Deploy as an edge module for Live Video Analytics

In VSCode, the following will be needed:

1. Azure IoT Extension
1. Deployment manifest
2. LVA console app code

When the Live Video Analytics on Edge direct methods are invoked on device with the console app, images will appear in a folder with the name of your local container e.g. `/media/nvme/blob_storage/BlockBlob/annotatedimageslocal` and with default deployment manifest, will stick around on device for 60 minutes as well as being uploaded to the cloud Blob Storage container (in this example, called `annotated-images-xavier-yolo4`).

From VSCode, messages to IoT Hub should look similar to:
```
[IoTHubMonitor] [1:11:41 PM] Message received from [xavier-yolov4/lvaEdge]:
{
  "inferences": [
    {
      "type": "entity",
      "entity": {
        "tag": {
          "value": "car",
          "confidence": "0.43346554"
        },
        "box": {
          "l": "0.6137574",
          "t": "0.5797131",
          "w": "0.05888599",
          "h": "0.047415733"
        }
      }
    },
    {
      "type": "entity",
      "entity": {
        "tag": {
          "value": "truck",
          "confidence": "0.33760804"
        },
        "box": {
          "l": "0.6137574",
          "t": "0.5797131",
          "w": "0.05888599",
          "h": "0.047415733"
        }
      }
    }
  ]
}
```

## Troubleshooting

### Troubleshooting a running container

To troubleshoot a running container you may enter it with ssh by using the following command.

```
sudo docker exec -it my_yolo_container /bin/bash
```

For IoT Edge troubleshooting see [Troubleshoot your IoT Edge device](https://docs.microsoft.com/en-us/azure/iot-edge/troubleshoot).

### Azure Media Services

1.  If AMS account has changed, then on device delete and recreate the App Data Directory for AMS:
```
sudo rm -fr /var/lib/azuremediaservices
mdkir -p /var/lib/azuremediaservices
```
   - It is a good idea to then restart lvaEdge module
   ```
   iotedge restart lvaEdge
   ```

### Azure Blob Storage IoT Edge module

1. Check the logs for Permission denied errors for folder on device used as container.
```
iotedge logs <name of your edge container e.g. azureblobstorageoniotedge>
```
   - If there is a "Permission denied" error try changing the owner and group on the folder (see [Granting directory access to container user on Linux](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-store-data-blob?view=iotedge-2018-06#granting-directory-access-to-container-user-on-linux)).
   ```
   sudo chown -R 11000:11000 <local blob directory e.g. /media/nvme/blob_storage>
   ```
   - It is a good idea to then restart lvaEdge module
   ```
   iotedge restart lvaEdge
   ```


## Helpful links

- [`darknet` implementation for YOLOv4](https://github.com/AlexeyAB/darknet)
- [TensorFlow YOLOv4 converters and implementations](https://github.com/hunglc007/tensorflow-yolov4-tflite)
