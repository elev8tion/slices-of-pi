"""End-to-end API tests for Slice of Pi.

Run with:
    pytest tests/test_e2e_api.py -v

Requires the orchestrator running on localhost:8420 with PI_NO_AUTH=1.
"""

import json
import urllib.request
import urllib.error

import pytest

BASE = "http://127.0.0.1:8420"


def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r, timeout=30)
        text = resp.read().decode()
        return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            return json.loads(body_text)
        except Exception:
            return {"_error": e.code, "_body": body_text[:200]}
    except Exception as e:
        return {"_error": str(e)}


class TestSystem:
    def test_health(self):
        r = req("GET", "/health")
        assert r.get("status") == "ok"
        assert "version" in r

    def test_pi_version(self):
        r = req("GET", "/api/system/version")
        assert r.get("version") and len(r["version"]) > 0

    def test_settings(self):
        r = req("GET", "/api/settings")
        assert "_error" not in r


class TestAgents:
    agent_id = ""

    def test_create(self):
        r = req("POST", "/api/agents", {"name": "e2e-test-agent", "tools": ["read", "bash"]})
        assert "id" in r and r.get("status") == "idle"
        TestAgents.agent_id = r["id"]

    def test_list(self):
        r = req("GET", "/api/agents")
        assert isinstance(r, list) and len(r) > 0

    def test_get(self):
        r = req("GET", f"/api/agents/{TestAgents.agent_id}")
        assert r.get("name") == "e2e-test-agent"

    def test_update(self):
        r = req("PATCH", f"/api/agents/{TestAgents.agent_id}", {"tools": ["read", "bash", "web_search"]})
        assert "_error" not in r

    def test_delete(self):
        r = req("DELETE", f"/api/agents/{TestAgents.agent_id}")
        assert r.get("status") == "deleted"


class TestChat:
    agent_id = ""

    def setup_method(self):
        if not TestChat.agent_id:
            r = req("POST", "/api/agents", {"name": "e2e-chat-test", "tools": ["read", "bash"]})
            TestChat.agent_id = r.get("id", "")

    def test_chat_streams(self):
        if not TestChat.agent_id:
            pytest.skip("No agent created")
        url = f"{BASE}/api/agents/{TestChat.agent_id}/chat"
        data = json.dumps({"message": "say hello in exactly 3 words"}).encode()
        r = urllib.request.Request(url, data=data, method="POST")
        r.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(r, timeout=60)
        body = resp.read().decode()

        chunks = []
        for line in body.split("\n"):
            if line.startswith("data: "):
                try:
                    chunks.append(json.loads(line[6:]))
                except Exception:
                    pass

        text_deltas = [c for c in chunks if c.get("type") == "text_delta"]
        turn_end = [c for c in chunks if c.get("type") == "turn_end"]
        assert len(text_deltas) > 0, "No text_delta chunks received"
        assert turn_end, "No turn_end received"
        assert turn_end[0].get("tokens_used", 0) > 0
        full_text = "".join(c.get("content", "") for c in text_deltas)
        assert len(full_text) > 0

    def test_session_resume(self):
        if not TestChat.agent_id:
            pytest.skip("No agent created")
        url = f"{BASE}/api/agents/{TestChat.agent_id}/chat"
        data = json.dumps({"message": "say hello in exactly 3 words", "resume": True}).encode()
        r = urllib.request.Request(url, data=data, method="POST")
        r.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(r, timeout=60)
        body = resp.read().decode()
        assert "hello" in body.lower() or "3 words" in body.lower()

    def teardown_method(self):
        if TestChat.agent_id:
            req("DELETE", f"/api/agents/{TestChat.agent_id}")
            TestChat.agent_id = ""


class TestSessions:
    agent_id = ""

    def setup_method(self):
        r = req("POST", "/api/agents", {"name": "e2e-session-test", "tools": ["read"]})
        TestSessions.agent_id = r.get("id", "")

    def test_list_sessions(self):
        r = req("GET", "/api/sessions")
        assert isinstance(r, list)

    def test_fork_session(self):
        if not TestSessions.agent_id:
            pytest.skip("No agent")
        r = req("POST", f"/api/agents/{TestSessions.agent_id}/fork")
        assert "_error" not in r or r.get("status") == "forked"

    def teardown_method(self):
        if TestSessions.agent_id:
            req("DELETE", f"/api/agents/{TestSessions.agent_id}")
            TestSessions.agent_id = ""


@pytest.mark.skipif(True, reason="Requires running orchestrator — run manually")
class TestManual:
    """Marker for tests that require external setup."""
    pass
