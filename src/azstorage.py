


class AzStorage:
    def __init__(self, account_name, account_key):
        self.account_name = account_name
        self.account_key = account_key

    def upload_file_share(self, file_path, container_name, blob_name):
        # Code to upload a file to Azure Blob Storage
        pass

    def download_from_blob_storage(self, container_name, blob_name, download_path):
        # Code to download a file from Azure Blob Storage
        pass

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