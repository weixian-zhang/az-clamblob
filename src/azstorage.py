
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.fileshare import ShareFileClient
from config import Config
import io
class AzStorage:
    def __init__(self, config: Config):
        self.config = config
        credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(account_url=f'https://{self.config.azure_storage_name}.blob.core.windows.net/', credential=credential)
        

    def list_containers(self, blob_service_client: BlobServiceClient):
        containers = blob_service_client.list_containers(include_metadata=True)
        result = []
        for container in containers:
            result.append(container)
        return result

    def upload_stream_to_file_share(self, data: bytes, file_path, container_name, blob_name):
        
        sfc = ShareFileClient.from_connection_string(
            conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=blob_name)
        
        sfc.upload_file(data)

    def download_blob_to_stream(self, container_name, blob_name):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # readinto() downloads the blob contents to a stream and returns the number of bytes read
        stream = io.BytesIO()
        num_bytes = blob_client.download_blob().readinto(stream)
        print(f"Number of bytes: {num_bytes}")

    def quarentine_blob(self, src_container_name, dest_container_name, blob_name):
        pass


    def set_blob_metadata(self, container_name, blob_name, metadata):
        # Code to set metadata for a blob
        pass

    def list_blobs(self, container_name):
        # Code to list blobs in a container
        pass

    def delete_file_in_file_share(self, container_name, blob_name):
        # Code to delete a blob from a container
        pass