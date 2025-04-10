REM create container app environment
az containerapp env create --assign-identity --enable-workload-profiles --resource-group "rg-clamblob" --name "cae-common" --location "southeastasia" --infrastructure-subnet-resource-id /subscriptions/c9061bc7-fa28-41d9-a783-2600b29c6e2f/resourceGroups/rg-clamblob/providers/Microsoft.Network/virtualNetworks/vnet-clamblob/subnets/CAEnvironment --logs-workspace-id c596239e-beda-4999-a79f-58e34d9881e4
az containerapp env workload-profile set --resource-group rg-clamblob --name cae-common --workload-profile-type D4 --workload-profile-name dedicated-d4-1 --min-nodes 1 --max-nodes 1

REM mount azure file share to container app environment
az containerapp env storage set \
  --access-mode ReadWrite \
  --azure-file-account-name {$STORAGE_ACCOUNT_NAME} \
  --azure-file-account-key {$STORAGE_ACCOUNT_KEY} \
  --azure-file-share-name clamblob-scan \
  --storage-name clamblob-scan \
  --name cae-common \
  --resource-group rg-clamblob \
  --output table


  REM create clamav container app
  az containerapp create -n clamblob-clamav -g rg-clamblob --yaml "clamav_container_app.yaml"

  REM update clamav container app env var
  az containerapp update -n clamblob-clamav -g rg-clamblob --set-env-vars "MAX_FILE_SIZE=40000M" "MAX_SCAN_SIZE=40000M" "MAX_FILES=50000"

  REM create scanner container app
  az containerapp create -n clamblob-scanner -g rg-clamblob --yaml "scanner_container_app.yaml" --system-assigned
  az containerapp identity assign -n clamblob-scanner -g rg-clamblob --system-assigned

  REM update scanner container app env var
  az containerapp update -n clamblob-scanner -g rg-clamblob --set-env-var "MOUNT_PATH=/azfile" "APP_INSIGHTS_INSTRUMENTATION_CONN_STRING={appinsights_conn_string}" "CLAMAV_HOST=clamblob-clamav" "CLAMAV_PORT=3310" "QUARANTINE_CONTAINER_NAME=quarantine" "AZURE_FILE_SHARE_NAME=clamblob-scan" "AZURE_STORAGE_NAME={azure_storage_name}" "AZURE_STORAGE_KEY={storage_account_key}"