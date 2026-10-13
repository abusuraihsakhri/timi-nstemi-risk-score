"""Local deterministic mock provider with PHI-pattern checks.

External provider labels remain compatibility aliases; no network model is called.
"""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Timi Nstemi Risk Score"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            f"[{self.system_name} Offline Mock]: No external model was invoked. "
            "This simulated response does not verify clinical claims or standards "
            f"compliance. Query preview: '{prompt[:60]}...'."
        )


class LLMFactory:
    """Return an offline mock; provider aliases do not enable external services."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Timi Nstemi Risk Score"):
        return MockLLM(system_name)
