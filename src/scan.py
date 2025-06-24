from azstorage import AzStorage
from pathlib import Path  
import log as Log
from clamav import ClamAVManager, ScanStatus
import json
from datetime import datetime
from model import BlobScanStatus
from util import Util
import platform

# class BlobScanStatus:
#     IN_PROGRESS = "in_progress"
#     ERROR = "error" 
#     NO_VIRUS = "no_virus"
#     VIRUS_FOUND = "virus_found"

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
        #self.blob_service_client = self.azstorage.get_blob_client()
        self.clamav = ClamAVManager(config)
        self.hostname = platform.uname()[1]
        self.scan_report_file_name=f'{self.hostname}-scan_report.json'
        self.scan_report_container_name='clamblob-logs'
        self.scan_report = {}

    def scan(self):
        
        try:

            Log.info('starting scan', 'BlobScanner')
            
            ok = self.load_scan_report()
            if not ok:
                return
            
            #  clean up file share in case previous scan was previously interrupted
            self.azstorage.delete_all_in_file_share()

            for container in self.config.containers_to_scan:

                file_system_client = self.azstorage.set_current_dlfs_client(container) #self.blob_service_client.list_containers(include_metadata=True)

                for item in file_system_client.get_paths(recursive=True):#containers:

                    if item.is_directory or item.name in [self.config.quarantine_container_name, self.scan_report_container_name]:
                        continue

                    try:
                        if self.azstorage._is_blob_scanned(container, item.name):
                            self.update_scan_report(container, item.name, BlobScanStatus.NO_VIRUS)
                            continue

                        Log.info(f'scanning {item.name}', 'BlobScanner')

                        self._set_file_scan_status(status=BlobScanStatus.IN_PROGRESS, file_path=item.name)

                        # set blob scan in progress
                        self.update_scan_report(container, item.name, BlobScanStatus.IN_PROGRESS)

                        # no need to copy to file share as blob containre is directly mounted
                        # copy blob to file share for scanning
                        # blob_ok, msg = self.azstorage.copy_blob_to_file_share(container, item.name)

                        # if not blob_ok:
                        #     self._set_file_scan_status(status=BlobScanStatus.ERROR, file_path=item.name)
                        #     self.update_scan_report(container, item.name, "error", msg)
                        #     Log.error(f'Error copying blob {item.name} from container {container}" to file share for scanning', 'BlobScanner')
                        #     continue

                        #scan file on file share using clamav
                        # blob_name_without_dir = Util.get_blob_name_to_file_share(container, item.name) #Path(blob.name).name
                        # file_path_on_share = self.config.mount_path + "/" + blob_name_without_dir

                        blob_mount_path = self.config.mount_path + "/" + item.name

                        scanresult = self.clamav.scan_file(blob_mount_path)

                        if scanresult.status == ScanStatus.FOUND:
                            Log.info(f'Virus found on {item.name}, moving file to quarentine container', 'BlobScanner')
                            self.update_scan_report(container, item.name, "virus_found")                          
                            self.quarantine_blob(container, item.name)
                        elif scanresult.status == ScanStatus.OK:
                            self._set_file_scan_status(status=BlobScanStatus.NO_VIRUS, file_path=item.name)
                            self.update_scan_report(container, item.name, BlobScanStatus.NO_VIRUS)
                            Log.info(f"No virus found for {Util.full_blob_name(container, item.name)}", 'BlobScanner')

                        elif scanresult.status == ScanStatus.ERROR:
                            self._set_file_scan_status(status=BlobScanStatus.ERROR, file_path=item.name)
                            self.update_scan_report(container, item.name, BlobScanStatus.NO_VIRUS, scanresult.message)
                            Log.error(f"Scan - error scanning file {Util.full_blob_name(container, item.name)}. {scanresult.message}", 'BlobScanner')

                        
                        # ok = self.azstorage.delete_blob_in_file_share(blob_name_without_dir)
                        # if not ok:
                        #     Log.error(f"deleting file {blob_name_without_dir} on file share", 'BlobScanner')
                        #     continue


                    except Exception as e:
                        self._set_file_scan_status(status=BlobScanStatus.ERROR, file_path=item.name)
                        self.update_scan_report(container, item.name, "error", str(e))
                        Log.error(f"Error scanning blob {Util.full_blob_name(container, item.name)}: {str(e)}", 'BlobScanner')
                    
                    # if len(self.config.containers_to_scan) > 0 and container not in self.config.containers_to_scan:
                    #     continue

                    # container_client = self.blob_service_client.get_container_client(container=container)

                    # blobs = container_client.list_blobs()

                    # for blob in item:
                        
                    #     try:

                    #         if self._is_blob_scanned(container.name, blob.name):
                    #             self.update_scan_report(container.name, blob.name, BlobScanStatus.NO_VIRUS)
                    #             continue

                    #         self._set_file_scan_status(BlobScanStatus.IN_PROGRESS, container.name, blob.name)

                    #         # set blob scan in progress
                    #         self.update_scan_report(container.name, blob.name, BlobScanStatus.IN_PROGRESS)

                    #         # copy blob to file share for scanning
                    #         blob_ok, msg = self.azstorage.copy_blob_to_file_share(container.name, blob.name)

                    #         if not blob_ok:
                    #             self._set_file_scan_status(BlobScanStatus.ERROR, container.name, blob.name)
                    #             self.update_scan_report(container.name, blob.name, "error", msg)
                    #             Log.error(f'Error copying blob {blob.name} from container {container.name}" to file share for scanning', 'BlobScanner')
                    #             continue

                    #         #scan file on file share using clamav
                    #         blob_name_without_dir = Util.get_blob_name_to_file_share(container.name, blob.name) #Path(blob.name).name
                    #         file_path_on_share = self.config.mount_path + "/" + blob_name_without_dir

                    #         scanresult = self.clamav.scan_file(file_path_on_share)

                    #         if scanresult.status == ScanStatus.FOUND:
                    #             self.update_scan_report(container.name, blob.name, "virus_found")                          
                    #             self.quarantine_blob(container.name, blob.name)
                    #         elif scanresult.status == ScanStatus.OK:
                    #             self._set_file_scan_status("no_virus", container.name, blob.name)
                    #             self.update_scan_report(container.name, blob.name, "no_virus")
                    #             Log.info(f"No virus found for {Util.full_blob_name(container.name, blob.name)}", 'BlobScanner')

                    #         elif scanresult.status == ScanStatus.ERROR:
                    #             self._set_file_scan_status("error", container.name, blob.name)
                    #             self.update_scan_report(container.name, blob.name, "no_virus", scanresult.message)
                    #             Log.error(f"Scan - error scanning file {Util.full_blob_name(container.name, blob.name)}. {scanresult.message}", 'BlobScanner')

                            
                    #         ok = self.azstorage.delete_blob_in_file_share(blob_name_without_dir)
                    #         if not ok:
                    #             Log.error(f"deleting file {blob_name_without_dir} on file share", 'BlobScanner')
                    #             continue


                    #     except Exception as e:
                    #         self._set_file_scan_status("error", container.name, blob.name)
                    #         self.update_scan_report(container.name, blob.name, "error", str(e))
                    #         Log.error(f"Error scanning blob {Util.full_blob_name(container.name, blob.name)}: {str(e)}", 'BlobScanner')

            # save scan report
            self.save_scan_report()
            Log.info('scan completed', 'BlobScanner')

        except Exception as e:
            Log.error(f"an error occurred: {str(e)}", 'BlobScanner')


    # def _is_blob_scanned(self, container_name, blob_name):
    #     '''
    #     check if blob is already scanned by checking the metadata'
    #     '''
    #     try:
    #         props = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).get_blob_properties()
    #         metadata = props.metadata # self.blob_service_client.get_blob_client(container=container_name, blob=blob_name).get_blob_properties().metadata
    #         val = metadata.get("clamav_blob_scan", None)

    #         # if blob is in progress, check if last modified is >= 120 minutes and rescan blob if it is.
    #         if val is not None and val == BlobScanStatus.IN_PROGRESS:
    #             now = datetime.now(pytz.utc)
    #             fmt = '%Y-%m-%d %H:%M:%S'
    #             last_modified = datetime.strptime(f'{props.last_modified.year}-{props.last_modified.month}-{props.last_modified.day} {props.last_modified.hour}:{props.last_modified.minute}:{props.last_modified.second}', fmt)
    #             now = datetime.strptime(f'{now.year}-{now.month}-{now.day} {now.hour}:{now.minute}:{now.second}', fmt)
    #             minuteDiff = (now-last_modified).total_seconds() / 60
    #             if minuteDiff >= 120:
    #                 return False

    #         if val is not None and val == BlobScanStatus.NO_VIRUS:
    #             return True
            
    #         return False
        
    #     except Exception as e:
    #         Log.error(f"Error checking blob scan status: {str(e)}", 'BlobScanner')
    #         return False

    
    def _set_file_scan_status(self, status, file_path):
        status = {"clamav_blob_scan": status}
        self.azstorage.set_blob_scan_status(path=file_path, status=status)


    def quarantine_blob(self, container_name, blob_name):
        ok = self.azstorage.move_blob_to_quarantine(container_name, blob_name)
        if not ok:
            Log.error(f"Error moving virus-found blob {Util.full_blob_name(container_name, blob_name)} to quarantine container {self.config.quarantine_container_name}", 'BlobScanner')
        else:
            Log.info(f"Virus found in file {Util.full_blob_name(container_name, blob_name)}. Moved to quarantine container {self.config.quarantine_container_name}", 'BlobScanner')


    def update_scan_report(self, container_name, blob_name, status, message=''):
        key = f"{container_name}/{blob_name}"
        self.scan_report[key] = {
            "timestamp": Util.friendly_date(),
            "status": status,
            "message": message
        }
            

    def load_scan_report(self) -> bool:
        '''
        load scan report from blob storage
        '''
        try:
            # createscan report container if not exists
            self.azstorage.create_container(self.scan_report_container_name)

            _ = self.azstorage.set_current_dlfs_client(self.scan_report_container_name)

            if not self.azstorage.is_blob_exists(self.scan_report_container_name, self.scan_report_file_name):
                return True

            ok, bytes = self.azstorage.download_blob_to_stream(container_name=self.scan_report_container_name, 
                                                               blob_name=self.scan_report_file_name)
            if not ok:
                Log.error(f"Error downloading scan report from container {self.scan_report_container_name}", 'BlobScanner')
                return False
            
            srStr = bytes.decode("utf-8")
            self.scan_report = json.loads(srStr)
            return True
        except Exception as e:
            Log.error(f"Error loading scan report: {str(e)}", 'BlobScanner')
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
            ok = self.azstorage.upload_blob_stream(data=b, 
                                              container_name=self.scan_report_container_name, 
                                              blob_name=self.scan_report_file_name)
            
            if not ok:
                Log.error(f"Error uploading scan report {self.scan_report_file_name} to container {self.scan_report_container_name}", 'BlobScanner')
                return False
            
            Log.info(f"Scan report saved to {self.scan_report_container_name}/{self.scan_report_file_name}", 'BlobScanner')
            
            return True
        except Exception as e:
            Log.error(f"Error saving scan report: {str(e)}", 'BlobScanner')
            return False