from scan import BlobScanner
import time
import log as Log
from config import Config
from clamav import ClamAVManager

config = Config()
clamav = ClamAVManager(config)

def scan():

    try:

        scanner = BlobScanner(config)
        
        scanner.scan()

    except Exception as e:
        Log.error(f"Main - an error occurred: {str(e)}")
    
    # cvm = ClamAVManager(config)

    # result1 = cvm.scan_file("/azfile/eicar_com.zip")

    # result2 = cvm.scan_file("/azfile/testfile.org-5GB.dat")

    # result3 = cvm.scan_file("/azfile/10GB.bin")

    # Log.info(f'{result1.file_path} - {result1.status} - {result1.message}')

    # Log.info(f'{result2.file_path} - {result2.status} - {result2.message}')

    # Log.info(f'{result3.file_path} - {result3.status} - {result3.message}')


try:
    while True:
        
        ok, _ = clamav.ping()
        if not ok:
            Log.error(f"ClamAV server '{config.clamav_host}:{config.clamav_port}' is not ready or not reachable.")
            time.sleep(5)
            continue

        scan()
        time.sleep(3)
except Exception as e:
    Log.error(f"An error occurred: {str(e)}")
except KeyboardInterrupt:
    pass



