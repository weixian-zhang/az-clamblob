from scan import BlobScanner
import time
import log as Log
from config import Config, ClamAvHost
from clamav import ClamAVManager
from fastapi import FastAPI
import uvicorn
import threading

config = Config()

app = FastAPI()

def are_all_clamav_hosts_reachable(hosts: list[ClamAvHost]) -> bool:
    success_count = len(hosts)
    for h in hosts:
        try:
            ok, msg = ClamAVManager(h.host, h.port).ping()
            if ok:
                success_count -= 1
            else:
                Log.error(f"ClamAV server '{h.host}:{h.port}' is not reachable: {msg}", 'Main')
                return False
        except Exception as e:
            Log.error(f"ClamAV server '{h.host}:{h.port}' is not reachable: {str(e)}", 'Main')
            return False
    return True if success_count == 0 else False

#required by container app startup check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def scan():
    try:
        while True:
            
            ok = are_all_clamav_hosts_reachable(config.clamav_hosts)
            if not ok:
                time.sleep(5)
                continue

            scanner = BlobScanner(config)
            scanner.scan()

            time.sleep(5)
    except Exception as e:
        Log.error(f"An error occurred: {str(e)}", 'Main')
    except KeyboardInterrupt:
        pass



if __name__ == "__main__":
    new_thread = threading.Thread(target=scan)
    new_thread.start()
    uvicorn.run(app, host='0.0.0.0', port=config.port)



