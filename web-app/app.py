from app import app
from azure.storage.blob import BlobServiceClient
import os
import sys
import traceback


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
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print({'[ERROR]': 
            'Error in app module: {}'.format(
                repr(traceback.format_exception(
                    exc_type,
                    exc_value,
                    exc_traceback)))})
    blob_cnt = 'na'

basedir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(basedir, 'app', 'static', 'image_cnt.txt'), 'w') as fout:
    fout.write(str(blob_cnt) + '\n')


