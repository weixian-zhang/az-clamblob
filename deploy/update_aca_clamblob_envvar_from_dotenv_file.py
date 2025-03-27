
from dotenv import load_dotenv
import os
import subprocess
from pathlib import Path

env_path = os.path.abspath(os.path.join(Path(os.path.dirname(__file__)).parent, 'src', '.env'))
load_dotenv(dotenv_path=env_path)

#azure params
container_app_name = 'clamblob-scanner'
rg = 'rg-clamblob'


mount_path = os.getenv('MOUNT_PATH')
clamav_host = os.getenv('CLAMAV_HOST') if os.getenv('CLAMAV_HOST') else 'localhost'
clamav_port = int(os.getenv('CLAMAV_PORT')) if os.getenv('CLAMAV_PORT') else 3310
appinsights_conn_string = os.getenv('APP_INSIGHTS_INSTRUMENTATION_CONN_STRING')
quarantine_container_name = os.getenv('QUARANTINE_CONTAINER_NAME') if os.getenv('QUARANTINE_CONTAINER_NAME') else 'quarantine'
azure_storage_name = os.getenv('AZURE_STORAGE_NAME') if os.getenv('AZURE_STORAGE_NAME') else ''
azure_file_share_conn_string = os.getenv('AZURE_FILE_SHARE_CONN_STRING') if os.getenv('AZURE_FILE_SHARE_CONN_STRING') else ''
azure_file_share_name = os.getenv('AZURE_FILE_SHARE_NAME') if os.getenv('AZURE_FILE_SHARE_NAME') else 'clamblob-scan'
storage_account_key = os.getenv('AZURE_STORAGE_KEY') if os.getenv('AZURE_STORAGE_KEY') else ''


p = subprocess.Popen(f'az containerapp update -n {container_app_name} -g {rg} --set-env-var "MOUNT_PATH={mount_path}" "APP_INSIGHTS_INSTRUMENTATION_CONN_STRING={appinsights_conn_string}" CLAMAV_HOST={clamav_host} CLAMAV_PORT={clamav_port} QUARANTINE_CONTAINER_NAME={quarantine_container_name} AZURE_STORAGE_NAME={azure_storage_name} AZURE_FILE_SHARE_CONN_STRING={azure_file_share_conn_string} AZURE_FILE_SHARE_NAME={azure_file_share_name} AZURE_STORAGE_KEY={storage_account_key}"', 
                     shell=True, 
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.STDOUT)
for line in p.stdout.readlines():
    print(line.decode('utf-8').strip())
retval = p.wait()