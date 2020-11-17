"""
Views file - for the rendered view of image data
"""
from flask import render_template, redirect
from flask_appbuilder import ModelView
from flask_appbuilder.actions import action
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.widgets import ShowWidget

import os

from . import appbuilder, db
from .models import DetectionFrame

from azure.storage.blob import BlobServiceClient


class DetectionModelView(ModelView):
    datamodel = SQLAInterface(DetectionFrame)

    label_columns = {'name':'Name',
                     'time':'TimeStamp',
                     'photo_img':'Photo',
                     'photo_img_thumbnail':'Photo'}
    list_columns = ['photo_img_thumbnail', 'name']
    show_columns = ['photo_img','name']

    @action("update_images", "Update images", icon="fa-rocket")
    def update_images(self, items):
        # Connect to Blob Storage
        local_account = os.getenv("STORAGE_ACCOUNT", "UNKNOWN_NAME")
        blob_connection_string = os.getenv("STORAGE_ACCOUNT_CONN_STRING", "UNKNOWN_KEY")
        local_container_name = os.getenv("STORAGE_CONTAINER", "UNKNOWN_NAME")
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        container_client = blob_service_client.get_container_client(
            local_container_name)
        frame_names = container_client.list_blobs()
        frame_names = [f['name'] for f in frame_names]
        

        # Populate db with image names
        for frame_name in frame_names:
            detection_frame = DetectionFrame(name=frame_name)
            exists = db.session.query(db.exists().where(DetectionFrame.name == frame_name)).scalar()
            if not exists:
                db.session.add(detection_frame)  # Adds new User record to database
            db.session.commit()  # Commits all changes

        self.update_redirect()
        return redirect(self.get_redirect())

db.create_all()

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