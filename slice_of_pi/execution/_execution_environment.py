"""
Execution Environment Interface

Abstract sandboxed execution environment for agent processes.

Replaces Docker-specific implementations with a generic abstraction
that can target Docker, Podman, Kubernetes pods, Firecracker
microVMs, or serverless functions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..shared import (
    ExecResult,
    Mount,
    NetworkPolicy,
    ResourceLimits,
    SandboxHandle,
)


class ExecutionEnvironment(ABC):
    """Generic sandboxed execution environment.

    Each agent gets its own sandbox with resource limits, filesystem
    mounts, environment variables, and network policies. The sandbox
    is ephemeral — destroying it removes all state.

    Implementations:
      - DockerSandbox:     Docker containers via docker-py
      - PodmanSandbox:     Podman containers (daemonless)
      - K8sSandbox:        Kubernetes pods
      - FirecrackerSandbox: Firecracker microVMs (stronger isolation)
      - ServerlessSandbox:  Cloud Run / Lambda / Fargate
      - ProcessSandbox:     Local subprocess (for testing)
    """

    # ------------------------------------------------------------------ lifecycle

    @abstractmethod
    async def create_sandbox(
        self,
        image: str,
        resources: ResourceLimits,
        mounts: list[Mount],
        env: dict[str, str],
        network: NetworkPolicy,
    ) -> SandboxHandle:
        """Create a new isolated sandbox.

        Args:
            image:     Container/VM image to run.
            resources: CPU and memory limits.
            mounts:    Filesystem mounts (volumes, bind mounts).
            env:       Environment variables to inject.
            network:   Egress/firewall policy.

        Returns:
            Handle to the running sandbox.
        """
        ...

    @abstractmethod
    async def exec_command(
        self,
        sandbox_id: str,
        command: list[str],
        timeout: int = 300,
    ) -> ExecResult:
        """Execute a command inside the sandbox.

        Args:
            sandbox_id: Sandbox handle id.
            command:    Command and args as list (never a shell string).
            timeout:    Max execution time in seconds.

        Returns:
            Exit code, stdout, stderr, and duration.
        """
        ...

    @abstractmethod
    async def stream_logs(
        self,
        sandbox_id: str,
    ) -> AsyncIterator[str]:
        """Stream real-time logs from the sandbox.

        Yields log lines (newline-delimited) as they are produced.
        """
        ...

    @abstractmethod
    async def snapshot(self, sandbox_id: str) -> bytes:
        """Take a filesystem snapshot for rollback capability.

        Returns opaque bytes that can be passed to rollback().
        Implementations may use image layers, tar archives,
        or ZFS snapshots.
        """
        ...

    @abstractmethod
    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Destroy a sandbox and release all resources.

        Must be idempotent. After destruction, the sandbox_id
        may be reused.
        """
        ...

    # ------------------------------------------------------------------ optional

    async def rollback(self, sandbox_id: str, snapshot: bytes) -> None:
        """Restore a sandbox to a previous snapshot.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError

    async def list_all(self) -> list[SandboxHandle]:
        """List all active sandboxes.

        Optional. Default returns empty list.
        """
        return []
