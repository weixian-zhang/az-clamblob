from azstorage import AzStorage
from pathlib import Path  
import log as Log
from clamav import ClamAVManager, ScanStatus

class BlobScanStatus:
    IN_PROGRESS = "in_progress"
    ERROR = "error" 
    NO_VIRUS = "no_virus"
    VIRUS_FOUND = "virus_found"

class BlobScanner:
    '''
    each blob will be tagged with clamav_blob_scan with following status. If "clamav_blob_scan" is missing means
    blob has not been scanned yet.
    - in_progress: blob is being scanned
    - error: blob scan failed due to various reasons like download failed, upload failed, etc.
    - no_virus: blob scan was successful

    blob found with virus will be moved to quarantine container and tagged with clamav_blob_scan = virus_found
    '''
    def __init__(self, config):
        self.config = config
        self.azstorage = AzStorage(config)
        self.blob_service_client = self.azstorage.get_blob_client()
        self.clamav = ClamAVManager(config)
        
    def scan(self):
        
        try:

            containers = self.blob_service_client.list_containers(include_metadata=True)
            
            for container in containers:

                container_client = self.blob_service_client.get_container_client(container=container.name)

                blobs = container_client.list_blobs()

                for blob in blobs:

                    # self.set_blob_scan_status("in_progress", container.name, blob.name)

                    
                    # # download from blob
                    # blob_ok = self.azstorage.copy_blob_to_file_share(self.blob_service_client.url, container.name, blob.name)


                    # if not blob_ok:
                    #     self.set_blob_scan_status("error", container.name, blob.name)
                    #     Log.error(f"Error downloading blob {blob.name} from container {container.name}")
                    #     continue


                    blob_name_without_dir = Path(blob.name).name
                        
                    #scan file on file share using clamav
                    file_path = self.config.mount_path + "/" + blob_name_without_dir

                    scanresult = self.clamav.scan_file(file_path)

                    if scanresult.status == ScanStatus.FOUND:
                        self.azstorage.move_blob_to_quarantine(container.name, blob.name)
                        self.set_blob_scan_status("virus_found", self.config.quarantine_container_name, blob.name)
                        Log.info(f"Virus found in file {file_path}. Moved to quarantine container {self.config.quarantine_container_name}")
                    elif scanresult.status == ScanStatus.OK:
                        self.set_blob_scan_status("no_virus", container.name, blob.name)
                    elif scanresult.status == ScanStatus.ERROR:
                        self.set_blob_scan_status("error", container.name, blob.name)
                        Log.error(f"Scan - error scanning file {container.name}/{file_path}. {scanresult.message}")

                    
        

        except Exception as e:
            Log.error(f"BlobScanner - an error occurred: {str(e)}")

    
    def set_blob_scan_status(self, status, container_name, blob_name):
        self.azstorage.set_blob_metadata(container_name, blob_name, {"clamav_blob_scan": status})


    def move_blob_to_quarantine(self, blob_bytes, container_name, blob_name):
        # move blob to quarantine container
        ok = self.azstorage.upload_stream_to_blob(blob_bytes, blob_name, self.config.quarantine_container_name)

        if not ok:
            Log.error(f"Error moving blob {blob_name} to quarantine container {self.config.quarantine_container_name}")
            return False
        
        # delete blob from original container
        ok = self.azstorage.delete_blob(container_name, blob_name)

        if not ok:
            Log.error(f"Error deleting blob {blob_name} from container {container_name}")

    