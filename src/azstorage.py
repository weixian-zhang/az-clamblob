
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, BlobType
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
from azure.storage.filedatalake import (
    DataLakeServiceClient,
    DataLakeDirectoryClient,
    FileSystemClient,
    generate_file_system_sas,
    FileSystemSasPermissions,
    PathProperties
)
from model import BlobScanStatus
from azure.core.exceptions import ResourceExistsError
import log as Log
import pytz
from config import Config
import io
from datetime import datetime, timedelta
import time
from util import Util



class AzStorage:
    def __init__(self, config: Config):
        self.config = config
        credential = DefaultAzureCredential()

        account_url = f"https://{self.config.azure_storage_name}.dfs.core.windows.net"

        self.blob_service_client = BlobServiceClient(account_url=f'https://{self.config.azure_storage_name}.blob.core.windows.net/', 
                                                     credential=credential)
    
        self.dls_client = DataLakeServiceClient(account_url, credential=credential)

        self.current_dlfs_client = None

        self.scan_status_metadata_name = 'clamav_blob_scan'
        
        
    def get_blob_client(self):
        return self.blob_service_client
    
    def set_current_dlfs_client(self, container_name=None) -> FileSystemClient:
        self.current_dlfs_client = self.dls_client.get_file_system_client(file_system=container_name)
        return self.current_dlfs_client
    
    def get_dlfs_client(self, container_name=None) -> FileSystemClient:
        return self.dls_client.get_file_system_client(file_system=container_name)
    

    def create_container(self, container_name) -> bool:
        try:
            self.dls_client.create_file_system(file_system=container_name)  # For Data Lake Storage Gen2
            #container_client = self.blob_service_client.get_container_client(container_name)
            # if not container_client.exists():
            #     container_client.create_container()
            return True
        except ResourceExistsError as ree:
            return True
        except Exception as e:
            Log.error(f"Error creating container: {str(e)}", 'AzStorage')
            return False
    
        
    # def upload_stream_to_blob(self, data: bytes, container_name, blob_name) -> bool:
    #     try:
    #         blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    #         blob_client.upload_blob(data, overwrite=True)
    #         return True
    #     except Exception as e:
    #         return False
    
    def copy_blob_to_file_share(self, container_name, path: PathProperties) -> bool:
        '''
        blob name is expected to container virtual directory structure and this method will handle this.
        e.g. 'dir1/dir2/dir3/file.txt'
        '''

        try:
            #src_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            directory_name = os.path.dirname(path)

            src_file_url = f'{self.current_dlfs_client.url}/{path}'

            sasToken = generate_file_system_sas(
                account_name=self.config.azure_storage_name,
                file_system_name=container_name,
                credential=self.config.storage_account_key,
                permission= FileSystemSasPermissions(read=True),
                expiry=datetime.now(pytz.utc) + timedelta(hours=1)
            )

            blob_name_without_dir = Util.get_blob_name_to_file_share(container_name, path) #Path(blob_name).name

            sfc = self._get_share_client(file_path=blob_name_without_dir)

            Log.info(f"Start copying {Util.full_blob_name(container_name, path)} to fileshare:{self.config.azure_file_share_name} for scanning...", 'AzStorage')
       
            sfc.start_copy_from_url(src_file_url+"?"+sasToken) # async call

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
            
            Log.info(f"Copy blob {Util.full_blob_name(container_name, path)} to fileshare for scanning completed successfully", 'AzStorage')

            return True, ''
        
        except Exception as e:
            return False, str(e)
        

    def is_blob_exists(self, container_name, blob_name) -> bool:
        try:
            if self.current_dlfs_client is None:
                raise ValueError("Current Data Lake File System Client is not set. Call set_current_dlfs_client() first.")
            
            file = self.current_dlfs_client.get_file_client(blob_name)
            return file.exists()
            # blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            # return blob_client.exists()
        except Exception as e:
            Log.error(f"Error checking if blob exists: {str(e)}", 'AzStorage')
            return False
        
    def download_blob_to_stream(self, container_name, blob_name) -> list[bool,bytes]:
        try:
            
            dlfs = self.get_dlfs_client(container_name)

            file = dlfs.get_file_client(blob_name)
            
            stream = io.BytesIO()

            num_bytes = file.download_file().readinto(stream)

            b = stream.getvalue() if num_bytes > 0 else b'{}'

            return True, b

        except Exception as e:
            Log.error(f"Error downloading blob: {str(e)}", 'AzStorage')
            return None

    def upload_blob_stream(self, data: bytes, container_name,  blob_name) -> bool:
        try:
            
            dlfs = self.get_dlfs_client(container_name)

            file = dlfs.get_file_client(blob_name)

            input_stream = io.BytesIO(data)

            file.upload_data(input_stream, overwrite=True)

            return True
        except Exception as e:
            return False

    def move_blob_to_quarantine(self, container_name, blob_name) -> bool:
        
        try:

            blob_name_in_quarantine = f'{container_name}/{blob_name}'

            src_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            
            dest_blob_client = self.blob_service_client.get_blob_client(container=self.config.quarantine_container_name, blob=blob_name_in_quarantine)

            Log.info(f"Start moving blob {blob_name} to quaratine container {self.config.quarantine_container_name}...", 'AzStorage')

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
            
            Log.info(f"Moving blob {blob_name} to quaratine container completed successfully", 'AzStorage')

            # set metadata for file in quarantine
            quarantine_dlfs = self.get_dlfs_client(self.config.quarantine_container_name)
            file = quarantine_dlfs.get_file_client(file_path=blob_name_in_quarantine)
            file.set_metadata(metadata={self.scan_status_metadata_name: BlobScanStatus.VIRUS_FOUND})

            return True

        except Exception as e:
            return False
        
        
    # def delete_blob(self, container_name, blob_name) -> bool:

    #     try:
    #         blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    #         blob_client.delete_blob()
    #         return True
    #     except Exception as e:
    #         return False
        

    def delete_blob_in_file_share(self, file_path) -> bool:
        try:
            sfc = self._get_share_client(file_path=file_path)
            sfc.delete_file()
            return True
        except Exception as e:
            return False
        
        
    def set_blob_scan_status(self, path, status: dict) -> None:
        if self.current_dlfs_client is None:
            raise ValueError("Current Data Lake File System Client is not set. Call set_current_dlfs_client() first.")
        
        file = self.current_dlfs_client.get_file_client(file_path=path)
        file.set_metadata(metadata=status)

        # Retrieve existing metadata, if desired
        # blob_metadata = blob_client.get_blob_properties().metadata
        # blob_metadata.update(metadata)
        # blob_client.set_blob_metadata(metadata=metadata) #blob_metadata)


    def _get_share_client(self, file_path) -> ShareFileClient:
        return ShareFileClient.from_connection_string(
                conn_str=self.config.azure_file_share_conn_string, share_name=self.config.azure_file_share_name, file_path=file_path)


    def delete_all_in_file_share(self) -> bool:
        '''
        delete all files in the file share. Typically used for cleanup before scan.
        '''
        try:
            sdc = ShareDirectoryClient.from_connection_string(self.config.azure_file_share_conn_string, 
                                                              self.config.azure_file_share_name, directory_path='')
            
            for item in sdc.list_directories_and_files():
                self.delete_blob_in_file_share(item.name)

            return True
        except Exception as e:
            return False
        
    
    def _is_blob_scanned(self,container_name, blob_name) -> bool:
        '''
        check if blob is already scanned by checking the metadata'
        '''
        try:
            if self.current_dlfs_client is None:
                raise ValueError("azstorage/move_blob_to_quarantine - Current Data Lake File System Client is not set. Call set_current_dlfs_client() first.")

            file = self.current_dlfs_client.get_file_client(blob_name)
            props = file.get_file_properties() # self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).get_blob_properties().metadata
            val = props.metadata.get("clamav_blob_scan", None)

            # if blob is in progress, check if last modified is >= 120 minutes and rescan blob if it is.
            if val is not None and val == BlobScanStatus.IN_PROGRESS:
                now = datetime.now(pytz.utc)
                fmt = '%Y-%m-%d %H:%M:%S'
                last_modified = datetime.strptime(f'{props.last_modified.year}-{props.last_modified.month}-{props.last_modified.day} {props.last_modified.hour}:{props.last_modified.minute}:{props.last_modified.second}', fmt)
                now = datetime.strptime(f'{now.year}-{now.month}-{now.day} {now.hour}:{now.minute}:{now.second}', fmt)
                minuteDiff = (now-last_modified).total_seconds() / 60
                if minuteDiff >= 120:
                    Log.info(f'{Util.full_blob_name(container_name, blob_name)} in_progress status over 120 mins, rescanning file', 'AzStorage')
                    return False

            if val is not None and val == BlobScanStatus.NO_VIRUS:
                return True
            
            return False
        
        except Exception as e:
            Log.error(f"azstorage - Error checking blob scan status: {str(e)}", 'AzStorage')
            return False