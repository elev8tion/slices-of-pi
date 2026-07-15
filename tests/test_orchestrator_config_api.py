"""Track D3 — safe orchestrator.json get/put (fixed path only)."""

from __future__ import annotations


class TestOrchestratorConfigApi:
    async def test_get_and_put_orchestrator_config(self, async_client):
        get1 = await async_client.get("/api/settings/orchestrator-config")
        assert get1.status_code == 200
        data = get1.json()
        assert "config" in data
        assert "path" in data
        assert "text" in data
        assert isinstance(data["config"], dict)

        # Round-trip with a profile key
        cfg = dict(data["config"])
        cfg.setdefault("profiles", {})
        cfg["profiles"].setdefault("default", {})
        cfg["profiles"]["default"]["default_model"] = "test-model-d3"

        put = await async_client.put(
            "/api/settings/orchestrator-config",
            json={"config": cfg},
        )
        assert put.status_code == 200
        assert put.json()["status"] == "saved"

        get2 = await async_client.get("/api/settings/orchestrator-config")
        assert get2.status_code == 200
        assert get2.json()["config"]["profiles"]["default"]["default_model"] == "test-model-d3"

    async def test_put_rejects_non_object(self, async_client):
        res = await async_client.put(
            "/api/settings/orchestrator-config",
            json={"config": ["not", "an", "object"]},
        )
        assert res.status_code == 422
