variable "location" {
  type    = string
  default = "Southeast Asia"
}

variable "rg" {
  type    = string
  default = "rg-clamblob-aks"
}

#-------------------------------------------------------
# Resource Group
#-------------------------------------------------------
resource "azurerm_resource_group" "rg" {
  name     = var.rg
  location = var.location
}

#-------------------------------------------------------
# Virtual Network and Subnets
#-------------------------------------------------------
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-clamblob-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["15.0.0.0/16"]
}

resource "azurerm_subnet" "aks_subnet" {
  name                 = "subnet-aks"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["15.0.0.0/24"]
}

# resource "azurerm_virtual_network" "vnet_mgt" {
#   name                = "vnet-aks-management"
#   location            = azurerm_resource_group.rg.location
#   resource_group_name = azurerm_resource_group.rg.name
#   address_space       = ["15.0.0.0/16"]
# }

resource "azurerm_subnet" "bastion_subnet" {
  name                 = "AzureBastionSubnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["15.0.1.0/24"]
}

resource "azurerm_subnet" "vm_subnet" {
  name                 = "VM"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["15.0.2.0/28"]
}

#-------------------------------------------------------
# AKS Cluster with Blob Driver and Managed Identity
#-------------------------------------------------------
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-clamblob"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "aksdns"

  default_node_pool {
    name                = "default"
    node_count          = 2
    vm_size             = "standard_d4s_v3"
    vnet_subnet_id      = azurerm_subnet.aks_subnet.id
  }

  identity {
    type = "SystemAssigned"
  }

  storage_profile {
    blob_driver_enabled = true
  }

  network_profile {
    network_plugin    = "azure"
    network_plugin_mode = "overlay"
    load_balancer_sku = "standard"
  }

  role_based_access_control_enabled = true
  oidc_issuer_enabled               = true
  workload_identity_enabled = true
}

#-------------------------------------------------------
# Windows VM (no public IP, Bastion access only)
#-------------------------------------------------------
# resource "azurerm_network_interface" "vm_nic" {
#   name                = "nic-winvm"
#   location            = azurerm_resource_group.rg.location
#   resource_group_name = azurerm_resource_group.rg.name

#   ip_configuration {
#     name                          = "internal"
#     subnet_id                     = azurerm_subnet.aks_subnet.id
#     private_ip_address_allocation = "Dynamic"
#   }
# }

# resource "azurerm_windows_virtual_machine" "win_vm" {
#   name                  = "windows-vm"
#   resource_group_name   = azurerm_resource_group.rg.name
#   location              = azurerm_resource_group.rg.location
#   size                  = "Standard_DS1_v2"
#   admin_username        = "azureuser"
#   admin_password        = "P@ssword1234!"
#   network_interface_ids = [azurerm_network_interface.vm_nic.id]

#   os_disk {
#     caching              = "ReadWrite"
#     storage_account_type = "Standard_LRS"
#   }

#   source_image_reference {
#     publisher = "MicrosoftWindowsServer"
#     offer     = "WindowsServer"
#     sku       = "2022-Datacenter"
#     version   = "latest"
#   }
# }

#-------------------------------------------------------
# Public IP for Azure Bastion
#-------------------------------------------------------
# resource "azurerm_public_ip" "bastion_ip" {
#   name                = "bastion-ip"
#   location            = azurerm_resource_group.rg.location
#   resource_group_name = azurerm_resource_group.rg.name
#   allocation_method   = "Static"
#   sku                 = "Standard"
# }

#-------------------------------------------------------
# Azure Bastion Host
#-------------------------------------------------------
# resource "azurerm_bastion_host" "bastion" {
#   name                = "bastion-host"
#   location            = azurerm_resource_group.rg.location
#   resource_group_name = azurerm_resource_group.rg.name

#   ip_configuration {
#     name                 = "bastion-ipconf"
#     subnet_id            = azurerm_subnet.bastion_subnet.id
#     public_ip_address_id = azurerm_public_ip.bastion_ip.id
#   }
# }

#-------------------------------------------------------
# Random DNS suffix for Bastion
#-------------------------------------------------------
resource "random_id" "rand" {
  byte_length = 4
}
