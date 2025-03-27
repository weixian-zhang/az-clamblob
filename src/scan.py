from azstorage import AzStorage
from pathlib import Path  
import log as Log
from clamav import ClamAVManager, ScanStatus
import json
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
        self.scan_report_file_name='scan_report.json'
        self.scan_report_container_name='clamblob-logs'
        self.scan_report = {}

    def scan(self):
        
        try:
            self.load_scan_report()

            containers = self.blob_service_client.list_containers(include_metadata=True)
            
            for container in containers:

                container_client = self.blob_service_client.get_container_client(container=container.name)

                blobs = container_client.list_blobs()

                for blob in blobs:
                    
                    try:

                        if self._is_blob_scanned(container.name, blob.name):
                            self.update_scan_report(container.name, blob.name, BlobScanStatus.NO_VIRUS, msg)
                            continue

                        self._set_blob_scan_status(BlobScanStatus.IN_PROGRESS, container.name, blob.name)
                        self.update_scan_report(container.name, blob.name, BlobScanStatus.IN_PROGRESS)

                        # copy blob to file share for scanning
                        blob_ok, msg = self.azstorage.copy_blob_to_file_share(self.blob_service_client.url, container.name, blob.name)

                        if not blob_ok:
                            self._set_blob_scan_status(BlobScanStatus.ERROR, container.name, blob.name)
                            self.update_scan_report(container.name, blob.name, "error", msg)
                            Log.error(f'Error copying blob {blob.name} from container {container.name}" to file share for scanning', 'BlobScanner')
                            continue

                        #scan file on file share using clamav
                        blob_name_without_dir = Path(blob.name).name
                        full_container_blob_name = f'{container.name}/{blob.name}'
                        file_path_on_share = self.config.mount_path + "/" + blob_name_without_dir

                        scanresult = self.clamav.scan_file(file_path_on_share)

                        if scanresult.status == ScanStatus.FOUND:
                            self.update_scan_report(container.name, blob.name, "virus_found")                          
                            self.quarantine_blob(container.name, blob.name)
                        elif scanresult.status == ScanStatus.OK:
                            self._set_blob_scan_status("no_virus", container.name, blob.name)
                            self.update_scan_report(container.name, blob.name, "no_virus")
                            Log.info(f"No virus found for {full_container_blob_name}", 'BlobScanner')

                        elif scanresult.status == ScanStatus.ERROR:
                            self._set_blob_scan_status("error", container.name, blob.name)
                            self.update_scan_report(container.name, blob.name, "no_virus", scanresult.message)
                            Log.error(f"Scan - error scanning file {full_container_blob_name}. {scanresult.message}", 'BlobScanner')

                        
                        ok = self.azstorage.delete_blob_in_file_share(blob_name_without_dir)
                        if not ok:
                            Log.error(f"deleting file {blob_name_without_dir} on file share", 'BlobScanner')
                            continue

                    except Exception as e:
                        self._set_blob_scan_status("error", container.name, blob.name)
                        self.update_scan_report(container.name, blob.name, "error", str(e))
                        Log.error(f"Error scanning blob {blob.name} in container {container.name}: {str(e)}", 'BlobScanner')

            # save scan report
            self.save_scan_report()

        except Exception as e:
            Log.error(f"an error occurred: {str(e)}", 'BlobScanner')


    def _is_blob_scanned(self, container_name, blob_name):
        '''
        check if blob is already scanned by checking the metadata'
        '''
        try:
            metadata = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).get_blob_properties().metadata
            val = metadata.get("clamav_blob_scan", None)
            if val is None and val != 'no_virus':
                return False
            return True
        except Exception as e:
            Log.error(f"Error checking blob scan status: {str(e)}", 'BlobScanner')
            return False

    
    def _set_blob_scan_status(self, status, container_name, blob_name):
        self.azstorage.set_blob_metadata(container_name, blob_name, {"clamav_blob_scan": status})


    def quarantine_blob(self, container_name, blob_name):
        full_container_blob_name = f"{container_name}/{blob_name}"
        ok = self.azstorage.move_blob_to_quarantine(container_name, blob_name)
        if not ok:
            Log.error(f"Error moving virus-found blob {full_container_blob_name} to quarantine container {self.config.quarantine_container_name}", 'BlobScanner')
        else:
            Log.info(f"Virus found in file {full_container_blob_name}. Moved to quarantine container {self.config.quarantine_container_name}", 'BlobScanner')


    def update_scan_report(self, container_name, blob_name, status, message=''):
        key = f"{container_name}/{blob_name}"
        self.scan_report[key] = {
            "status": status,
            "message": message
        }
            

    def load_scan_report(self):
        '''
        load scan report from blob storage
        '''
        try:
            # createscan report container if not exists
            self.azstorage.create_container(self.scan_report_container_name)

            if not self.azstorage.is_blob_exists(self.scan_report_container_name, self.scan_report_file_name):
                return True

            ok, bytes = self.azstorage.download_blob_to_stream(container=self.scan_report_container_name, blob=self.scan_report_file_name).upload_blob(scan_report)
            if not ok:
                Log.error(f"Error downloading scan report from container {self.scan_report_container_name}", 'BlobScanner')
                return False
            
            srStr = bytes.decode("utf-8")
            self.scan_report = json.loads(srStr)
            return True
        except Exception as e:
            Log.error(f"Error saving scan report: {str(e)}", 'BlobScanner')
            return False

    def save_scan_report(self):
        '''
        save scan report to blob storage
        '''
        try:
            if len(self.scan_report) == 0:
                return True
            
            srJson = json.dumps(self.scan_report, indent=4)
            b = bytes(srJson, 'utf-8')
            self.azstorage.upload_blob_stream(data=b, container=self.scan_report_container_name, blob=self.scan_report_file_name)
            Log.info(f"Scan report saved to {self.scan_report_container_name}/{self.scan_report_file_name}", 'BlobScanner')
            return True
        except Exception as e:
            Log.error(f"Error saving scan report: {str(e)}", 'BlobScanner')
            return False