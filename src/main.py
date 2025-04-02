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
        Log.error(f"Main - an error occurred: {str(e)}", 'Main')


try:
    while True:
        
        ok, _ = clamav.ping()
        if not ok:
            Log.error(f"ClamAV server '{config.clamav_host}:{config.clamav_port}' is not ready or not reachable.")
            time.sleep(5)
            continue

        scan()

        time.sleep(5)
except Exception as e:
    Log.error(f"An error occurred: {str(e)}", 'Main')
except KeyboardInterrupt:
    pass



