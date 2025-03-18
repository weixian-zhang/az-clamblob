az containerapp create -n clamblob-clamav -g rg-clamblob --yaml "clamav_container_app.yaml"
az containerapp create -n clamblob-scanner -g rg-clamblob --yaml "clamblob_scanner_container_app.yaml"