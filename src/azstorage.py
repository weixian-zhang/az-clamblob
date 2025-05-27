
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, BlobType
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
from azure.data.tables import TableServiceClient
from pathlib import Path  
import log as Log
import pytz
from config import Config
import io
from datetime import datetime, timedelta
import time
from util import Util
from datetime import datetime

class BlobScanStatus:
    IN_PROGRESS = "in_progress"
    ERROR = "error" 
    NO_VIRUS = "no_virus"
    VIRUS_FOUND = "virus_found"

class AzStorage:

    def __init__(self, config: Config):
        self.config = config
        credential = DefaultAzureCredential()
        self.table_service = TableServiceClient(credential=credential, endpoint=f'https://{self.config.azure_storage_name}.table.core.windows.net/')
        self.blob_service_client = BlobServiceClient(account_url=f'https://{self.config.azure_storage_name}.blob.core.windows.net/', 
                                                     credential=credential)
        self.metadata_store = None
        
    def get_blob_client(self):
        return self.blob_service_client

    def create_metadata_store_table(self) -> bool:
        try:
            self.metadata_store = self.table_service.create_table_if_not_exists(table_name=self.config.azure_metadata_store_table_name)
            return True
        except Exception as e:
            Log.error(f"Error creating metadata table: {str(e)}", 'AzStorage')
            return False
    

    def create_container(self, container_name) -> bool:
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
            return True
        except Exception as e:
            Log.error(f"Error creating container: {str(e)}", 'AzStorage')
            return False
    
        
    def upload_stream_to_blob(self, data: bytes, container_name, blob_name) -> bool:
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.upload_blob(data, overwrite=True)
            return True
        except Exception as e:
            return False
    
    def copy_blob_to_file_share(self, container_name, blob_name) -> bool:
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

            blob_name_without_dir = Util.get_blob_name_to_file_share(container_name, blob_name) #Path(blob_name).name

            sfc = self._get_share_client(file_path=blob_name_without_dir)

            Log.info(f"Start copying {Util.full_blob_name(container_name, blob_name)} to fileshare:{self.config.azure_file_share_name} for scanning...", 'AzStorage')
       
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
            
            Log.info(f"Copy blob {Util.full_blob_name(container_name, blob_name)} to fileshare for scanning completed successfully", 'AzStorage')

            return True, ''
        
        except Exception as e:
            return False, str(e)
        
    def is_blob_exists(self, container_name, blob_name) -> bool:
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            return blob_client.exists()
        except Exception as e:
            Log.error(f"Error checking if blob exists: {str(e)}", 'AzStorage')
            return False
        
    def download_blob_to_stream(self, container_name, blob_name) -> list[bool,bytes]:
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            stream = io.BytesIO()
            num_bytes = blob_client.download_blob().readinto(stream)
            b = stream.getvalue() if num_bytes > 0 else b'{}'
            return True, b

        except Exception as e:
            Log.error(f"Error downloading blob: {str(e)}", 'AzStorage')
            return None

    def upload_blob_stream(self, data: bytes, container_name,  blob_name) -> bool:
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            input_stream = io.BytesIO(data)
            blob_client.upload_blob(input_stream, blob_type=BlobType.BLOCKBLOB, overwrite=True)
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

            self.set_blob_metadata(self.config.quarantine_container_name,
                                   blob_name_in_quarantine, BlobScanStatus.VIRUS_FOUND)

            return True

        except Exception as e:
            return False
        
        
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
        
        
    def set_blob_metadata(self, container_name, blob_name, status: str):
        # blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # # Retrieve existing metadata, if desired
        # blob_metadata = blob_client.get_blob_properties().metadata
        # blob_metadata.update(metadata)
        # blob_client.set_blob_metadata(metadata=blob_metadata)
        rowkey = f"{container_name}_{blob_name}"

        entity = {
            u'PartitionKey': container_name,
            u'RowKey': rowkey,
            u'status': status,
            u'last_updated': datetime.now(pytz.utc).isoformat(),
        }

        self.metadata_store.upsert_entity(entity)

    def _is_blob_scanned(self, container_name, blob_name):
        '''
        check if blob is already scanned by checking the metadata'
        '''

        try:
            # props = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).get_blob_properties()
            # metadata = props.metadata # self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).get_blob_properties().metadata
            # val = metadata.get("clamav_blob_scan", None)

            entity = self.metadata_store.get_entity(container_name, self._metadata_store_row_key(container_name, blob_name))
            status = entity.get('status', None)
            last_updated = entity.get('last_updated', None)

            # if blob is in progress, check if last modified is >= 120 minutes and rescan blob if it is.
            if status is not None and status == BlobScanStatus.IN_PROGRESS:
                now = datetime.now(pytz.utc)
                fmt = '%Y-%m-%d %H:%M:%S'
                last_modified = datetime.strptime(f'{props.last_modified.year}-{props.last_modified.month}-{props.last_modified.day} {props.last_modified.hour}:{props.last_modified.minute}:{props.last_modified.second}', fmt)
                now = datetime.strptime(f'{now.year}-{now.month}-{now.day} {now.hour}:{now.minute}:{now.second}', fmt)
                minuteDiff = (now-last_modified).total_seconds() / 60
                if minuteDiff >= 120:
                    return False

            if val is not None and val == BlobScanStatus.NO_VIRUS:
                return True
            
            return False
        
        except Exception as e:
            Log.error(f"Error checking blob scan status: {str(e)}", 'BlobScanner')
            return False


    def _metadata_store_row_key(self, container_name, blob_name) -> str:
        '''
        create a row key for the metadata store table.
        '''
        return f"{container_name}_{blob_name}"

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