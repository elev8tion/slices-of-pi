"""
Testing Layer

Test fixtures and scenario runners for verifying the agentic
framework end-to-end. These interfaces let test suites create
deterministic environments and run repeatable scenarios.

Interface catalog:
  TestFixtureFactory  — Deterministic test fixture creation
  ScenarioRunner      — End-to-end scenario testing
"""

from ._fixtures import TestFixtureFactory
from ._scenarios import ScenarioRunner

__all__ = [
    "TestFixtureFactory",
    "ScenarioRunner",
]
