from scan import BlobScanner
import time
import log as Log
from config import Config
from clamav import ClamAVManager
from fastapi import FastAPI
import uvicorn
import threading

config = Config()
clamav = ClamAVManager(config)

app = FastAPI()

#required by container app startup check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# def scan():

#     try:
#         scanner = BlobScanner(config)
#         scanner.scan()
#     except Exception as e:
#         Log.error(f"Main - an error occurred: {str(e)}", 'Main')

def scan():
    try:
        while True:
            
            ok, _ = clamav.ping()
            if not ok:
                Log.error(f"ClamAV server '{config.clamav_host}:{config.clamav_port}' is not ready or not reachable.")
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



