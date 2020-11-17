"""
Models file - for the data model
"""
from flask import Markup, url_for
from flask_appbuilder import Model
from flask_appbuilder.models.mixins import ImageColumn
from flask_appbuilder.filemanager import ImageManager

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text

import os

class DetectionFrame(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    timestamp = Column(String(100), unique=True, nullable=False)
    objects = Column(String(400), unique=False, nullable=False)

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