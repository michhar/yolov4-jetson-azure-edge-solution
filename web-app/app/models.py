"""
Models file - for the data model
"""
from flask import Markup, url_for
from flask_appbuilder import Model
from flask_appbuilder.models.mixins import ImageColumn
from flask_appbuilder.filemanager import ImageManager

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from azure.storage.blob import BlobServiceClient

import os


class DetectionFrame(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    timestamp = Column(String(100), unique=True, nullable=False)
    objects = Column(String(400), unique=False, nullable=False)

    def check_for_images(self):
        # Let's create an extra file that monitors the count of images
        # in Blob Storage
        try:
            # Connect to Blob Storage
            local_account = os.getenv("STORAGE_ACCOUNT", "UNKNOWN_NAME")
            blob_connection_string = os.getenv("STORAGE_ACCOUNT_CONN_STRING", "UNKNOWN_KEY")
            local_container_name = os.getenv("STORAGE_CONTAINER", "UNKNOWN_NAME")
            blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
            container_client = blob_service_client.get_container_client(
                local_container_name)
            blob_info = container_client.list_blobs()
            blob_cnt = len(blob_info)
        except Exception:
            blob_cnt = 'na'

        basedir = os.path.abspath(os.path.dirname(__file__))
        # This will reload flask app and trigger repopulating db with all images
        with open(os.path.join(basedir, 'static', 'image_cnt.txt'), 'w') as fin:
            fin.write(str(blob_cnt) + '\n')

    def photo_img(self):
        im = ImageManager()
        if self.name:
            return Markup('<a href="' + url_for('DetectionModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="' + "https://{}.blob.core.windows.net/{}/{}{}".format(
                                                os.getenv('STORAGE_ACCOUNT', ''), 
                                                os.getenv('STORAGE_CONTAINER', ''),
                                                self.name,
                                                os.getenv('SAS_STRING', '')) +\
              '" alt="Photo" class="img-responsive"></a>')
        else:
            return Markup('<a href="' + url_for('DetectionModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="//:0" alt="Photo" class="img-responsive"></a>')

    def photo_img_thumbnail(self):
        self.check_for_images()
        im = ImageManager()
        if self.name:
            return Markup('<a href="' + url_for('DetectionModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="' + "https://{}.blob.core.windows.net/{}/{}{}".format(
                                                os.getenv('STORAGE_ACCOUNT', ''),
                                                os.getenv('STORAGE_CONTAINER', ''),
                                                self.name,
                                                os.getenv('SAS_STRING', '')) +\
              '" alt="Photo" class="img-responsive"></a>')
        else:
            return Markup('<a href="' + url_for('DetectionModelView.show',pk=str(self.id)) +\
             '" class="thumbnail"><img src="//:0" alt="Photo" class="img-responsive"></a>')