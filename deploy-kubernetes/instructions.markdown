1. install chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

2. choco install kubernetes-cli azure-kubelogin

2. deploy AKS with main.tf

3. create kube namespace
   kubectl create ns clamblob

4. create secret

kubectl create secret generic appinsights-conn-string -n clamblob --from-literal appinsightsconnstring=strgclamblob --from-literal azurestorageaccountkey="KEY" --type=Opaque

kubectl create secret generic azure-secrets -n clamblob 
   --from-literal APP_INSIGHTS_INSTRUMENTATION_CONN_STRING="" 
   --from-literal AZURE_STORAGE_KEY=""

1. In Portal, enable Entra authn and Azure RBAC

2. In Portal, grant user access to AKS with role "Azure Kubernetes Service RBAC Admin" 


