"""
Template Engine Interface

Abstract template system for agent instantiation. Templates
define agent configuration presets that users can instantiate
with optional overrides.

Template sources:
  - Local filesystem (built-in templates)
  - Git repositories (version-controlled templates)
  - Marketplace API (community templates)
  - Environment-specific catalogs
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..shared import Template, ValidationResult


class TemplateEngine(ABC):
    """Abstract template system for agent instantiation.

    Templates are blueprints. The engine resolves a template ID
    to a full AgentConfig, applying user overrides on top of the
    template defaults.

    Example:
        engine = FileSystemTemplateEngine("/etc/slice-of-pi/templates")
        config = await engine.instantiate("business-assistant", {
            "name": "my-assistant",
            "resources": {"cpu": "4", "memory": "8Gi"},
        })
    """

    @abstractmethod
    async def list_templates(self, category: str | None = None) -> list[Template]:
        """List all available templates, optionally filtered by category.

        Categories: "assistant", "research", "analyst", "devops",
                    "custom", etc.
        """
        ...

    @abstractmethod
    async def get_template(self, template_id: str) -> Template:
        """Get detailed information about a single template.

        Raises:
            TemplateNotFoundError: If template_id doesn't exist.
        """
        ...

    @abstractmethod
    async def instantiate(
        self,
        template_id: str,
        overrides: dict,
    ) -> dict:
        """Resolve template + overrides into a complete agent configuration.

        This is the core operation: take a template and user-provided
        overrides, merge them according to the template's merge strategy
        (deep merge, shallow merge, replace), and return a complete
        configuration dict ready for AgentRuntime.create().

        Args:
            template_id: Which template to use.
            overrides:   User-specified overrides (name, resources, etc.).

        Returns:
            Complete agent configuration dict.
        """
        ...

    @abstractmethod
    async def validate(self, template_id: str) -> ValidationResult:
        """Validate a template's structure and references.

        Checks that all referenced skills, tools, MCP servers,
        and credentials exist and are compatible.
        """
        ...

    # ------------------------------------------------------------------ optional

    async def register(self, template: Template) -> str:
        """Register a new template.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError

    async def unregister(self, template_id: str) -> None:
        """Remove a template.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError
