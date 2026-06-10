"""
Platform Deployment Manifest

Declarative platform deployment specification. Replaces
docker-compose / helm / terraform with a provider-agnostic
deployment model that describes the entire platform topology.

The manifest is the single source of truth for deploying the
agentic framework itself (not individual agents — those use
AgentManifest/SystemManifest).

Example YAML:
  platform:
    name: slice-of-pi
    version: 1.0.0
  providers:
    - docker
    - kubernetes
  services:
    api:
      replicas: 1
      resources: {cpu: "2", memory: "4Gi"}
      ports: [8000]
    frontend:
      replicas: 1
      resources: {cpu: "1", memory: "512Mi"}
    scheduler:
      replicas: 1
      resources: {cpu: "0.5", memory: "256Mi"}
    database:
      type: postgres
      version: "16"
      storage: 50Gi
    redis:
      version: "7"
      storage: 10Gi
  agents:
    default_runtime: docker
    resource_pool:
      max_cpu: "32"
      max_memory: "128Gi"
    isolation: container
  networking:
    ingress:
      type: traefik
      tls: letsencrypt
    internal:
      encrypted: true
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ServiceSpec:
    """Specification for a single platform service."""
    replicas: int = 1
    resources: dict[str, str] = field(default_factory=lambda: {"cpu": "1", "memory": "512Mi"})
    ports: list[int] = field(default_factory=list)
    health_check: Optional[dict[str, str]] = None  # e.g., {"path": "/health", "interval": "30s"}
    image: Optional[str] = None
    type: Optional[str] = None     # For databases: "postgres", "redis", etc.
    version: Optional[str] = None  # For databases: version tag
    storage: Optional[str] = None  # For databases: persistent storage size


@dataclass
class AgentPoolSpec:
    """Resource pool for agent sandboxes."""
    default_runtime: str = "docker"
    resource_pool: dict[str, str] = field(default_factory=lambda: {
        "max_cpu": "32",
        "max_memory": "128Gi",
    })
    isolation: str = "container"  # "container" | "vm" | "process"


@dataclass
class IngressSpec:
    """Ingress / reverse proxy configuration."""
    type: str = "traefik"          # "traefik" | "nginx" | "envoy" | "cloud-lb"
    tls: str = "letsencrypt"       # "letsencrypt" | "self-signed" | "none"


@dataclass
class NetworkingSpec:
    """Networking configuration for the platform."""
    ingress: IngressSpec = field(default_factory=IngressSpec)
    internal: dict[str, bool] = field(default_factory=lambda: {"encrypted": True})


@dataclass
class PlatformDeployment:
    """Declarative platform deployment manifest.

    This is the top-level deployment specification. It describes
    all services, agents, and infrastructure needed to run the
    agentic framework. Provider-agnostic: the same manifest can
    be deployed to Docker Compose, Kubernetes, or Nomad by
    swapping the deployment engine.
    """

    platform: dict[str, str] = field(default_factory=lambda: {
        "name": "slice-of-pi",
        "version": "1.0.0",
    })
    providers: list[str] = field(default_factory=lambda: ["docker"])
    services: dict[str, ServiceSpec] = field(default_factory=dict)
    agents: AgentPoolSpec = field(default_factory=AgentPoolSpec)
    networking: NetworkingSpec = field(default_factory=NetworkingSpec)

    # Optional: arbitrary provider-specific extensions
    extensions: dict[str, dict] = field(default_factory=dict)
