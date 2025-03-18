import clamd
from enum import Enum
from config import Config
import log as Log

class ScanStatus(Enum):
    OK = 1
    FOUND = 2
    ERROR = 3
    ConnectionError = 4

class ScanResult:
    '''
        ScanResult.status can be the following:
        - OK: No virus found
        - FOUND: Virus found
        - ERROR: Error occurred while processing the file
        - ConnectionError: Error occurred while connecting to ClamAV server
    '''

    def __init__(self, file_path, status='FOUND', message=''):
        self.file_path = file_path
        self.status = status
        self.message = message


class ClamAVManager:
    def __init__(self, config: Config):
        self.clamav = clamd.ClamdNetworkSocket(config.clamav_host, config.clamav_port)

    def ping(self) -> list[bool,str]:
        
        try:
            result = self.clamav.ping()
            return True, result
        except Exception as e:
            return False, str(e)

    def scan_file(self, file_path) -> ScanResult:

        try:

            pingok, _ = self.ping()
            if not pingok:
                Log.error(f"ClamAV server '{self.clamav.host}:{self.clamav.port}' is not reachable")
                return ScanResult(file_path, ScanStatus.ConnectionError, "ClamAV server is not reachable")

            sr = ScanResult(file_path)

            response = self.clamav.scan(file_path)
            first_dict_key = next(iter(response))
            status, sr.message = response[first_dict_key]

            # for k, v in  items():
            #     status, message = v
            #     message = k

            if (status == 'OK'):
                sr.message = 'file is clean'
                sr.status = ScanStatus.OK
            # <write the code to save file in local or push file to remote storage>
            elif (status == 'FOUND'):
                sr.message = 'file contains virus'
                sr.status = ScanStatus.FOUND
            else:
                sr.status = ScanStatus.ERROR

            return sr
        
        except Exception as e:
            sr.message = str(e)
            sr.status = ScanStatus.ERROR
            return sr
        
