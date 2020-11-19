"""
Views file - for the rendered view of image data
"""
from flask import render_template, redirect, Markup
from flask_appbuilder import ModelView
from flask_appbuilder.actions import action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.widgets import ShowWidget

import os
import sys
import traceback

from . import appbuilder, db
from .models import DetectionFrame

from azure.storage.blob import BlobServiceClient


def update_images():
    """
    If there are new images in blob storage, this action
    will update the view to contain them by adding their info
    to the existing database.
    """
    try:
        # Connect to Blob Storage
        local_account = os.getenv("STORAGE_ACCOUNT", "UNKNOWN_NAME")
        blob_connection_string = os.getenv("STORAGE_ACCOUNT_CONN_STRING", "UNKNOWN_KEY")
        local_container_name = os.getenv("STORAGE_CONTAINER", "UNKNOWN_NAME")
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        container_client = blob_service_client.get_container_client(
            local_container_name)
        blob_info = container_client.list_blobs()

        # Get metadata
        timestamps = []
        objects = []
        frame_names = []
        for blob in blob_info:
            blob_client = container_client.get_blob_client(blob.name)
            properties = blob_client.get_blob_properties()
            frame_names.append(blob.name)
            metadata_props = properties.metadata
            timestamps.append(metadata_props['timestamp'])
            objects.append(metadata_props['objects'])

        # Populate db with image names
        for i in range(len(frame_names)):
            detection_frame = DetectionFrame(name=frame_names[i],
                                            timestamp=timestamps[i],
                                            objects=objects[i])
            exists = db.session.query(db.exists().where(DetectionFrame.name == frame_names[i])).scalar()
            if not exists:
                db.session.add(detection_frame)
            db.session.commit()  # Commits all changes
    except Exception as err:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print({'[ERROR]': 
                'Error in view module: {}'.format(
                    repr(traceback.format_exception(
                        exc_type,
                        exc_value,
                        exc_traceback)))})
        db.session.rollback()


class DetectionModelView(ModelView):
    """Class for view for displaying images with detections"""
    datamodel = SQLAInterface(DetectionFrame, db.session)

    label_columns = {'name':'Name',
                     'timestamp':'TimeStamp',
                     'objects': 'Identified objects',
                     'photo_img':'Photo',
                     'photo_img_thumbnail':'Photo'}
    list_columns = ['photo_img_thumbnail', 'name']
    show_columns = ['photo_img','name', 'timestamp', 'objects']

    # @action("update_images", "Update images", icon="fa-rocket", single=False)
    # def update_image_action(self, items):
    #     """
    #     If there are new images in blob storage, this action
    #     will update the view to contain them by adding their info
    #     to the existing database.
    #     """
    #     update_images()

    #     self.update_redirect()
    #     return redirect(self.get_redirect())

# ------------- INITIALIZE THE DATABASE WITH CURRENT IMAGES IN BLOB -------------

db.create_all()
update_images()

# ------------- ADD VIEWS -------------

appbuilder.add_view(
    DetectionModelView(), "List Detections", icon="fa-folder-open-o", category="Detections"
)

@appbuilder.app.errorhandler(404)
def page_not_found(e):
    """Application wide 404 error handler"""
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )