from azstorage import AzStorage
from config import Config

config = Config()
azstorage = AzStorage(config)
blob_service_client = azstorage.get_blob_client()
scan_report_container_name='clamblob-logs'

containers = blob_service_client.list_containers(include_metadata=True)
            
for container in containers:

    if container.name in [config.quarantine_container_name, scan_report_container_name]:
        continue

    container_client = blob_service_client.get_container_client(container=container.name)

    blobs = container_client.list_blobs()

    for blob in blobs:
        blob_client = blob_service_client.get_blob_client(container=container.name, blob=blob.name)
        blob_client.set_blob_metadata(metadata={})

print('clear metadata completed')


