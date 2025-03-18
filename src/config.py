
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        self.mount_path = ''
        self.clamav_host = 'localhost'
        self.clamav_port = 3310
        self.appinsights_key = ''
        self.load()

    def load(self):
        self.mount_path = os.getenv('MOUNT_PATH')
        self.clamav_host = os.getenv('CLAMAV_HOST') if os.getenv('CLAMAV_HOST') else 'localhost'
        self.clamav_port = int(os.getenv('CLAMAV_PORT')) if os.getenv('CLAMAV_PORT') else 3310
        self.appinsights_key = os.getenv('APP_INSIGHTS_INSTRUMENTATION_KEY')

