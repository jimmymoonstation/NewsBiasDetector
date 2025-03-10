# Provider for Kubernetes (Connects to GKE)
provider "kubernetes" {
  host                   = "https://${google_container_cluster.primary.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.primary.master_auth[0].cluster_ca_certificate)
}

# Data source for Google client config (for access token)
data "google_client_config" "default" {}

# Create a namespace for the EFK Stack
resource "kubernetes_namespace" "logging" {
  metadata {
    name = "logging"
  }
}

# Deploy Elasticsearch using Helm
resource "helm_release" "elasticsearch" {
  name       = "elasticsearch"
  repository = "https://helm.elastic.co"
  chart      = "elasticsearch"
  namespace  = kubernetes_namespace.logging.metadata[0].name

  values = [
    <<-EOT
    replicas: 3
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "1"
    EOT
  ]
}

# Deploy Fluentd using Helm
resource "helm_release" "fluentd" {
  name       = "fluentd"
  repository = "https://helm.fluentd.io"
  chart      = "fluentd"
  namespace  = kubernetes_namespace.logging.metadata[0].name

  values = [
    <<-EOT
    image:
      repository: fluent/fluentd-kubernetes-daemonset
      tag: v1-debian-elasticsearch
    env:
      - name: FLUENT_ELASTICSEARCH_HOST
        value: "elasticsearch.logging.svc.cluster.local"
      - name: FLUENT_ELASTICSEARCH_PORT
        value: "9200"
    EOT
  ]
}

# Deploy Kibana using Helm
resource "helm_release" "kibana" {
  name       = "kibana"
  repository = "https://helm.elastic.co"
  chart      = "kibana"
  namespace  = kubernetes_namespace.logging.metadata[0].name

  values = [
    <<-EOT
    service:
      type: LoadBalancer
    elasticsearchHosts:
      - "http://elasticsearch.logging.svc.cluster.local:9200"
    EOT
  ]
}
