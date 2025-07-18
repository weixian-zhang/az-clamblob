from azstorage import AzStorage
from pathlib import Path  
import log as Log
from clamav import ClamAVManager, ScanStatus
import json
from datetime import datetime
from model import BlobScanStatus
from util import Util
import platform
from multiprocessing import Process

# class BlobScanStatus:
#     IN_PROGRESS = "in_progress"
#     ERROR = "error" 
#     NO_VIRUS = "no_virus"
#     VIRUS_FOUND = "virus_found"

class FileToScan:
    def __init__(self, container_name, file_path):
        self.container_name = container_name
        self.file_path = file_path

class BatchToScan:
    def __init__(self, id, files_to_scan: list[FileToScan], clamv: ClamAVManager):
        self.id = id
        self.files_to_scan = files_to_scan
        self.clamav = clamv


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
            

            batches, total_files_to_scan = self.create_batches_to_scan()

            init_message = f'total {total_files_to_scan} files to scan divided into {len(batches)} batches, ignoring blob_tier=Cool and scan_status=No_Virus'
            Log.info(init_message, 'BlobScanner')
            self.update_scan_report('summary', '', init_message)

            threads = []
            for batch in batches:
                Log.info(f'starting batch {batch.id} with {len(batch.files_to_scan)} files', 'BlobScanner')

                # create a new process for each batch
                p = Process(target=self._scan_batch, args=(batch,))

                threads.append(p)
                p.start()


            for t in threads:
                t.join()

            # save scan report
            self.save_scan_report()
            Log.info('scan completed', 'BlobScanner')

        except Exception as e:
            Log.error(f"an error occurred: {str(e)}", 'BlobScanner')


    def _scan_batch(self, batch):

        clamav = batch.clamav
        host = clamav.host
        port = clamav.port
        batch_id = batch.id

        for file in batch.files_to_scan:
            
            container = file.container_name
            file_path = file.file_path

            try:

                Log.info(f'scanning {file_path} in batch {batch_id} with clamav: {host}:{port}', 'BlobScanner')

                #self._set_file_scan_status(status=BlobScanStatus.IN_PROGRESS, file_path=file_path)

                # set blob scan in progress
                self.update_scan_report(container, file_path, f'batch: {batch_id}, status: {BlobScanStatus.IN_PROGRESS}, scan by clamav: {host}:{port}')

                clamav_full_mount_path = self.config.mount_path + "/" + file_path

                scanresult = clamav.scan_file(clamav_full_mount_path)

                if scanresult.status == ScanStatus.FOUND:
                    Log.info(f'Virus found in {file_path} in batch {batch_id} by scanner {host}:{batch.clamav.port}, moving file to quarentine container', 'BlobScanner')
                    self.update_scan_report(container, file_path, f'batch: {batch_id}, status: {BlobScanStatus.VIRUS_FOUND}, scan by clamav: {host}:{port}')                          
                    self.quarantine_blob(container, file_path)

                elif scanresult.status == ScanStatus.OK:
                    #self._set_file_scan_status(status=BlobScanStatus.NO_VIRUS, file_path=file_path)
                    self.azstorage.set_blob_tier_to_cool(container, file_path)
                    self.update_scan_report(container, file_path, f'batch: {batch_id}, status: {BlobScanStatus.NO_VIRUS}, scan by clamav: {host}:{port}')
                    Log.info(f"No virus found for {Util.full_blob_name(container, file_path)}", 'BlobScanner')

                elif scanresult.status == ScanStatus.ERROR:
                    #self._set_file_scan_status(status=BlobScanStatus.ERROR, file_path=file_path)
                    self.update_scan_report(container, file_path, f'batch: {batch_id}, status: {BlobScanStatus.ERROR}, scan by clamav: {host}:{port}, error: {scanresult.message}')
                    Log.error(f"Scan - error scanning file {Util.full_blob_name(container, file_path)}. {scanresult.message}", 'BlobScanner')


            except Exception as e:
                #self._set_file_scan_status(status=BlobScanStatus.ERROR, file_path=file_path)
                self.update_scan_report(container, file_path, f'batch: {batch_id}, status: {BlobScanStatus.ERROR}, scan by clamav: {host}:{port}, error: {str(e)}')
                Log.error(f"Error scanning blob {Util.full_blob_name(container, file_path)}: {str(e)}", 'BlobScanner')


    def create_batches_to_scan(self) -> list[list[BatchToScan], int]:
        ''' create batches of files to scan based on the number of clamav hosts.
            return a list of BatchToScan objects and total number of files to scan
        '''
        no_of_batches = len(self.config.clamav_hosts)

        # get all file paths in all containers to scan
        files_to_scan = self.get_all_files_to_scan()

        file_batches = [files_to_scan[i::no_of_batches] for i in range(no_of_batches)]

        batches = []

        for i in range(no_of_batches):
            clamav_host = self.config.clamav_hosts[i]
            host = clamav_host.host
            port = clamav_host.port
            batch = BatchToScan(i, file_batches[i], ClamAVManager(host, port))
            batches.append(batch)

        return batches, len(files_to_scan)


    def get_all_files_to_scan(self) -> list[FileToScan]:
        '''
        get all file paths in all containers to scan
        '''
        files_to_scan = []
        for container in self.config.containers_to_scan:
            file_system_client = self.azstorage.set_current_dlfs_client(container)
            for item in file_system_client.get_paths(recursive=True):
                if item.is_directory or item.name in [self.config.quarantine_container_name, self.scan_report_container_name]:
                    continue

                if self.azstorage._is_blob_scanned(container, item.name):
                    self.update_scan_report(container, item.name, f'no virus, in Cool tier')
                    continue
                
                files_to_scan.append(FileToScan(container, item.name))

        return files_to_scan

    
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