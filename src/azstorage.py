
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from azure.storage.fileshare import ShareFileClient
from azure.storage.blob import ContainerClient
import log as Log
from config import Config
import io
from datetime import datetime, timedelta
class AzStorage:
    def __init__(self, config: Config):
        self.config = config
        credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(account_url=f'https://{self.config.azure_storage_name}.blob.core.windows.net/', credential=credential)
        
    def get_blob_client(self):
        return self.blob_service_client
    
    def upload_stream_to_file_share(self, data: bytes, file_path, container_name):
        
        try:
            sfc = ShareFileClient.from_connection_string(
                conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=file_path)
        
            sfc.upload_file(data)
        except Exception as e:
            return False, None
        
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

        try:

            source_blob = BlobClient(blob_service_url, container_name=container_name, blob_name=blob_name)

            sasToken = generate_blob_sas(
                account_name="xxx",
                container_name=n,
                blob_name=blob_name,
                account_key="xxx",
                permission= BlobSasPermissions(read=True),
                expiry=datetime.now(datetime.timezone.utc) + timedelta(hours=1)
            )

            sfc = ShareFileClient.from_connection_string(
                conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=blob_name)
       
            copy_result = sfc.start_copy_from_url(source_blob.url+"?"+sasToken)

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
            sfc = ShareFileClient.from_connection_string(
                conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=file_path)
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
        # Code to set metadata for a blob
        pass

    def list_blobs(self, container_name):
        # Code to list blobs in a container
        pass

    def delete_file_in_file_share(self, container_name, blob_name):
        # Code to delete a blob from a container
        pass