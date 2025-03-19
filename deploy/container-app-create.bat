az containerapp create -n clamblob-clamav -g rg-clamblob --yaml "clamav_container_app.yaml"
az containerapp update -n clamblob-scanner -g rg-clamblob --set-env-vars "MAX_FILE_SIZE=40000M" "MAX_SCAN_SIZE=40000M" "MAX_FILES=50000"

az containerapp create -n clamblob-scanner -g rg-clamblob --yaml "clamblob_scanner_container_app.yaml"
az containerapp update -n clamblob-scanner -g rg-clamblob --set-env-vars "MOUNT_PATH=/mnt" "APP_INSIGHTS_INSTRUMENTATION_KEY=5bb85efc-b516-4116-aebb-65ca9dcd876f" "CLAMAV_HOST=clamblob-clamav" "CLAMAV_PORT=3310" "QUARANTINE_CONTAINER_NAME=quarantine"