1. install chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

2. choco install kubernetes-cli azure-kubelogin k9s
3. choco install terraform --pre 

### Deploy and configure AKS Cluster

4. deploy AKS using Terraform
   terraform apply --auto-approve

5. In Portal, AKS -> Security Configuration
    - Enable Entra authentication and Azure RBAC
    - Menu -> Service Connectors -> create service connection to Storage Blob
   
6. In Portal, grant user access to AKS with role "Azure Kubernetes Service RBAC Admin"
   
7. connect to AKS
az aks get-credentials --resource-group rg-clamblob-aks --name aks-clamblob --overwrite-existing

### Setup Kubernetes artifacts  

8. create kube namespace
   kubectl create ns clamblob

9. create kubernetes secret to mount Storage container.
(create once only as all pods will use the same secret)

kubectl create secret generic azure-secrets -n clamblob 
   --from-literal APP_INSIGHTS_INSTRUMENTATION_CONN_STRING="" 
   --from-literal azurestorageaccountname="strgclamblob"
   --from-literal azurestorageaccountkey=""

10. update scanner.yaml spec.serviceAccountName with service account name from Service Connection

11. deploy pv.yaml
    - change resource group
    - change storageAccount
    - 
12. deploy pvc.yaml
13. deploy deployment-clamav.yaml
14. deploy deployment-scanner.yaml
    - change container name


