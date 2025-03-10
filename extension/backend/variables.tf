variable "project" {
  description = "The GCP project to use"
  type        = string
  default     = "newsbias-438816"
}

variable "region" {
  description = "The GCP region to use"
  type        = string
  default     = "us-central1"
}

variable "network_name" {
  description = "The name of the network"
  type        = string
  default     = "k8s-net"
}

variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
  default     = "k8s-subnet"
}

variable "cluster_name" {
  description = "The name of the cluster"
  type        = string
  default     = "k8s-v2"
}

variable "node_count" {
  description = "The number of nodes in the cluster"
  type        = number
  default     = 3
}

