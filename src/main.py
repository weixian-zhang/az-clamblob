from clamav import ClamAVManager
import time
import log as Log
from config import Config

config = Config()

def scan():

    Log.info(f'clamav host:port - {config.clamav_host}:{config.clamav_port}')

    cvm = ClamAVManager(config)

    result1 = cvm.scan_file("/azfile/eicar_com.zip")

    result2 = cvm.scan_file("/azfile/testfile.org-5GB.dat")

    result3 = cvm.scan_file("/azfile/10GB.bin")

    Log.info(f'{result1.file_path} - {result1.status} - {result1.message}')

    Log.info(f'{result2.file_path} - {result2.status} - {result2.message}')

    Log.info(f'{result3.file_path} - {result3.status} - {result3.message}')


try:
    while True:
        scan()
        time.sleep(3)
except Exception as e:
    Log.error(f"An error occurred: {str(e)}")
except KeyboardInterrupt:
    pass



