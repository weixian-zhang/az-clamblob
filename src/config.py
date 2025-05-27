
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
        self.appinsights_conn_str = ''
        self.quarantine_container_name = 'quarantine'
        self.azure_storage_name = ''
        self.azure_file_share_conn_string = ''
        self.azure_file_share_name = 'clamblob-scan'
        self.storage_account_key = ''
        self.port = 8080
        self.load()

    def load(self):
        self.mount_path = os.getenv('MOUNT_PATH')
        self.clamav_host = os.getenv('CLAMAV_HOST') if os.getenv('CLAMAV_HOST') else 'localhost'
        self.clamav_port = int(os.getenv('CLAMAV_PORT')) if os.getenv('CLAMAV_PORT') else 3310
        self.appinsights_conn_str = os.getenv('APP_INSIGHTS_INSTRUMENTATION_CONN_STRING') if os.getenv('APP_INSIGHTS_INSTRUMENTATION_CONN_STRING') else ''
        self.quarantine_container_name = os.getenv('QUARANTINE_CONTAINER_NAME') if os.getenv('QUARANTINE_CONTAINER_NAME') else 'quarantine'
        self.azure_storage_name = os.getenv('AZURE_STORAGE_NAME') if os.getenv('AZURE_STORAGE_NAME') else ''
        self.storage_account_key = os.getenv('AZURE_STORAGE_KEY') if os.getenv('AZURE_STORAGE_KEY') else ''
        self.azure_file_share_conn_string = f'DefaultEndpointsProtocol=https;AccountName={self.azure_storage_name};AccountKey={self.storage_account_key};EndpointSuffix=core.windows.net'
        self.azure_file_share_name = os.getenv('AZURE_FILE_SHARE_NAME') if os.getenv('AZURE_FILE_SHARE_NAME') else 'clamblob-scan'
        self.containers_to_scan = [x.strip() for x in os.getenv('CONTAINERS_TO_SCAN').split(',')] if os.getenv('CONTAINERS_TO_SCAN') else []
        self.port = int(os.getenv('PORT')) if os.getenv('PORT') else 8080
        self.azure_metadata_store_table_name = os.getenv('AZURE_METADATA_STORE_TABLE_NAME') if os.getenv('AZURE_METADATA_STORE_TABLE_NAME') else 'metadata'
        
        if self.azure_storage_name == '':
            raise ValueError("AZURE_STORAGE_NAME is not set in the environment variables.")
        if self.azure_file_share_conn_string == '':
            raise ValueError("AZURE_FILE_SHARE_CONN_STRING is not set in the environment variables.")
