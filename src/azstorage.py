
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from azure.storage.fileshare import ShareFileClient
from pathlib import Path  
import log as Log
import pytz
from config import Config
import io
from datetime import datetime, timedelta
import time

class AzStorage:
    def __init__(self, config: Config):
        self.config = config
        credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(account_url=f'https://{self.config.azure_storage_name}.blob.core.windows.net/', 
                                                     credential=credential)
        
    def get_blob_client(self):
        return self.blob_service_client
    
    # def upload_stream_to_file_share(self, data: bytes, file_path, container_name):
        
    #     try:
    #         sfc = ShareFileClient.from_connection_string(
    #             conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=file_path)
        
    #         sfc.upload_file(data)
    #     except Exception as e:
    #         return False, None
        
    # def download_stream_from_file_share(self, file_path) -> list[bool, bytes]:
        
    #     try:
    #         sfc = ShareFileClient.from_connection_string(
    #         conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=file_path)
        
    #         data = sfc.download_file()
    #         stream = io.BytesIO()
    #         data.readinto(stream)

    #         return True, stream.read()

    #     except Exception as e:
    #         return False, None
        
    def upload_stream_to_blob(self, data: bytes, container_name, blob_name) -> bool:
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.upload_blob(data, overwrite=True)
            return True
        except Exception as e:
            return False
    
    def copy_blob_to_file_share(self, blob_service_url, container_name, blob_name) -> bool:
        '''
        blob name is expected to container virtual directory structure and this method will handle this.
        e.g. 'dir1/dir2/dir3/file.txt'
        '''

        try:
            src_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            
            sasToken = generate_blob_sas(
                account_name=self.config.azure_storage_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=self.config.storage_account_key,
                permission= BlobSasPermissions(read=True),
                expiry=datetime.now(pytz.utc) + timedelta(hours=1)
            )

            blob_name_without_dir = Path(blob_name).name

            sfc = self._get_share_client(file_path=blob_name_without_dir)

            Log.info(f"Start copying blob:{blob_name} to fileshare:{self.config.azure_file_share_name} for scanning...")
       
            sfc.start_copy_from_url(src_blob_client.url+"?"+sasToken) # async call

            # poll copy status
            while True:
                properties = sfc.get_file_properties()
                copy_props = properties.copy
                if copy_props["status"] == 'pending':
                    time.sleep(4.0)
                elif copy_props["status"] == 'success':
                     break 
                else:
                    break
            
            Log.info(f"Copy blob {blob_name} to fileshare for scanning completed successfully")

            return True
        
        except Exception as e:
            return False
        

    def move_blob_to_quarantine(self, container_name, blob_name) -> bool:
        
        try:
            blob_name_in_quarantine = f'{container_name}/{blob_name}'
            src_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            dest_blob_client = self.blob_service_client.get_blob_client(container=self.config.quarantine_container_name, blob=blob_name_in_quarantine)

            Log.info(f"Start moving blob {blob_name} to quaratine container {self.config.quarantine_container_name}...")

            dest_blob_client.start_copy_from_url(src_blob_client.url) # async call

            # poll move status
            while True:
                properties = dest_blob_client.get_blob_properties()
                copy_props = properties.copy
                if copy_props["status"] == 'pending':
                    time.sleep(4.0)
                elif copy_props["status"] == 'success':
                     break 
                else:
                    break

            src_blob_client.delete_blob(delete_snapshots='include') # delete the original blob
            
            Log.info(f"Moving blob {blob_name} to quaratine container completed successfully")

            self.set_blob_metadata(self.config.quarantine_container_name,
                                   blob_name_in_quarantine, 
                                   {"clamav_blob_scan": 'virus_found'})

            return True

        except Exception as e:
            return False
        

    # def download_blob_to_stream(self, container_name, blob_name) -> list[bool, bytes]:

    #     try:
    #         blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    #         stream = io.BytesIO()
    #         blob_client.download_blob().readinto(stream)
    #         return True, stream.read()
    #     except Exception as e:
    #         return False, None
        
    
    def delete_blob(self, container_name, blob_name) -> bool:

        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.delete_blob()
            return True
        except Exception as e:
            return False
        

    def delete_blob_in_file_share(self, file_path) -> bool:
        try:
            sfc = self._get_share_client(file_path=file_path)
            sfc.delete_file()
            return True
        except Exception as e:
            return False
        
        
    # def move_blob_from_blob_to_fileshare(self, file_path, dest_container_name, fsdata: bytes = None) -> bool:

    #     cc = self.blob_service_client.get_container_client(dest_container_name)

    #     if not cc.exists():
    #         cc.create_container()

    #     # download from file share
    #     dsffs_ok, fsbytes = self.download_stream_from_file_share(file_path)

    #     if not dsffs_ok:
    #         Log.error(f"Error downloading file from file share: {file_path}")
    #         return False
        

    def set_blob_metadata(self, container_name, blob_name, metadata: dict):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Retrieve existing metadata, if desired
        blob_metadata = blob_client.get_blob_properties().metadata
        blob_metadata.update(metadata)
        blob_client.set_blob_metadata(metadata=blob_metadata)


    def _get_share_client(self, file_path) -> ShareFileClient:
        return ShareFileClient.from_connection_string(
                conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=file_path)



    # def delete_file_in_file_share(self, container_name, blob_name):
    #     # Code to delete a blob from a container
    #     pass