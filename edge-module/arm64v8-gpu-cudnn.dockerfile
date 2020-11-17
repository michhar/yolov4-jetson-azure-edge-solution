########################################################################
#
# Dockerfile to build ARM64 image with CUDA and sample of YOLO v4 with
# TensorFlow Lite.
#
#######################################################################
FROM nvcr.io/nvidia/l4t-tensorflow:r32.4.3-tf2.2-py3
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install runit, python, nginx, and necessary python packages
# Download the Tiny Yolov4 model
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev unzip \
    make cmake automake gcc g++ pkg-config \
    python3-numpy python3-opencv python3-h5py \
    libhdf5-serial-dev hdf5-tools libhdf5-dev \
    libhdf5-100 zlib1g-dev zip libjpeg8-dev liblapack-dev \
    libblas-dev gfortran vim \
    && cd /usr/local/bin \
    && ln -s /usr/bin/python3 python \
    && pip3 install --upgrade pip \
    && apt-get clean \
    && apt-get update && apt-get install -y --no-install-recommends \
    wget runit nginx \
    && cd /app \
    && wget https://github.com/Azure/Azure-AI-Camp/releases/download/v1.0/yolov4-tiny.tflite \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get purge -y --auto-remove wget

# Copy the app file
COPY app/ .

# Install requirements for jetson arm64v8
RUN pip install setuptools wheel testresources
RUN pip install -r requirements-arm64v8-gpu.txt

# Copy nginx config file
COPY yolov4-tf-tiny-app.conf /etc/nginx/sites-available

# Setup runit file for nginx and gunicorn
RUN mkdir /var/runit && \
    mkdir /var/runit/nginx && \
    /bin/bash -c "echo -e '"'#!/bin/bash\nexec nginx -g "daemon off;"\n'"' > /var/runit/nginx/run" && \
    chmod +x /var/runit/nginx/run && \
    ln -s /etc/nginx/sites-available/yolov4-tf-tiny-app.conf /etc/nginx/sites-enabled/ && \
    rm -rf /etc/nginx/sites-enabled/default && \
    mkdir /var/runit/gunicorn && \
    /bin/bash -c "echo -e '"'#!/bin/bash\nexec gunicorn -b 127.0.0.1:8888 --chdir /app yolov4-tf-tiny-app:app\n'"' > /var/runit/gunicorn/run" && \
    chmod +x /var/runit/gunicorn/run && \
    cd /app

# Start runsvdir
CMD ["runsvdir","/var/runit"]

