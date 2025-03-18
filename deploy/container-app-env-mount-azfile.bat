az containerapp env storage set \
  --access-mode ReadWrite \
  --azure-file-account-name $STORAGE_ACCOUNT_NAME \
  --azure-file-account-key $STORAGE_ACCOUNT_KEY \
  --azure-file-share-name $STORAGE_SHARE_NAME \
  --storage-name $STORAGE_MOUNT_NAME \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table