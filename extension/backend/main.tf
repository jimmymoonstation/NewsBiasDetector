provider "google" {
  project = var.project
  region  = "us-central1"  # Specify your region
}

# Create the VPC network
resource "google_compute_network" "vpc_network" {
  name                    = var.network_name
  auto_create_subnetworks  = false
}

# Create a subnet in the VPC
resource "google_compute_subnetwork" "subnet" {
  name                        = var.subnet_name
  region                      = "us-central1"
  network                     = google_compute_network.vpc_network.name
  ip_cidr_range              = "10.0.0.0/24"  # Adjust the CIDR range as needed
  private_ip_google_access   = true
}

# Firewall rule for internal traffic (Optional)
resource "google_compute_firewall" "allow_internal" {
  name    = "allow-internal"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  source_ranges = ["10.0.0.0/24"]  # Allow internal IP range to access all ports
}

# Create GKE Cluster
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  deletion_protection = false

  # Enable private endpoint
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = true
  }

  # Master Authorized Networks Configuration
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "10.0.0.0/24"  # Example: allow access from your internal subnet
      display_name = "Allow internal subnet"
    }
  }

  network   = google_compute_network.vpc_network.name  # This should be your custom VPC
  subnetwork = google_compute_subnetwork.subnet.name    # Reference the subnet you created
  # endpoint = "10.0.0.2"
  # Define the node pool
  node_pool {
    name               = "default-pool"
    initial_node_count = 3  # Set the number of nodes here
    node_config {
      machine_type = "e2-medium"
      disk_size_gb = 50  # Specify the size in GB
      disk_type    = "pd-ssd"  # Set disk type to SSD (Persistent Disk SSD)
    }
  }
}
