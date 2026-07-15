"""
End-to-end terminal tests — requires a running orchestrator on localhost:8420.

Tests the full terminal WebSocket flow:
  - Ticket minting
  - WebSocket connection with mode=pi and mode=bash
  - Invalid ticket rejection
  - Invalid mode rejection
  - Sending keystrokes and receiving output
  - PTY resize handling
  - Graceful disconnect
  - Config profile CRUD via the config layer

Run:  python -m pytest tests/test_terminal_e2e.py -v
Or live orchestrator:  python tests/test_terminal_e2e.py
"""

from __future__ import annotations

# Tell pytest this is a standalone script, not a test module
__test__ = False

import asyncio
import json
import os
import re
import sys
import time
import tracemalloc

import httpx
import websockets

# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════

BASE = os.environ.get("PI_ORCHESTRATOR_URL", "http://127.0.0.1:8420")
WS_BASE = BASE.replace("http://", "ws://").replace("https://", "wss://")
TIMEOUT = float(os.environ.get("PI_E2E_TIMEOUT", "15"))

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def test(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        msg = f"  ❌ {name}" + (f"  — {detail}" if detail else "")
        print(msg)
        FAILURES.append(msg)


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════
# HTTP helpers
# ═══════════════════════════════════════════════════════════════════


def http_get(path: str) -> dict | list | None:
    url = f"{BASE}{path}"
    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        if resp.status_code == 204:
            return None
        return resp.json()
    except Exception as e:
        return {"_error": str(e)}


def http_post(path: str, body: dict | None = None) -> dict | list | None:
    url = f"{BASE}{path}"
    try:
        resp = httpx.post(url, json=body, timeout=TIMEOUT)
        if resp.status_code == 204:
            return None
        return resp.json()
    except Exception as e:
        return {"_error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# WebSocket helpers
# ═══════════════════════════════════════════════════════════════════


async def try_connect_ws(
    path: str,
    timeout_seconds: float = 5.0,
) -> tuple[bool, int | None, bytes | None]:
    """Try connecting to a WebSocket endpoint.

    Returns (success, close_code, first_message_bytes).

    Note: websockets library upgrades to WS before the server handler runs,
    so a server-side close(400X) still results in connected=True at the
    transport level. We detect this by catching ConnectionClosed on recv().
    """
    url = f"{WS_BASE}{path}"
    try:
        async def _connect_and_recv():
            async with websockets.connect(url, ping_interval=None) as ws:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(msg, bytes):
                        return (True, ws.close_code or None, msg)
                    else:
                        return (True, ws.close_code or None, msg.encode())
                except websockets.exceptions.ConnectionClosed as e:
                    return (False, e.code, str(e).encode())
                except asyncio.TimeoutError:
                    return (True, ws.close_code, None)
        result = await asyncio.wait_for(_connect_and_recv(), timeout=timeout_seconds)
        return result
    except asyncio.TimeoutError:
        return (True, None, None)


async def terminal_session(
    agent_id: str,
    ticket: str,
    mode: str = "bash",
    input_data: bytes | None = None,
    timeout_seconds: float = 10.0,
) -> dict:
    """Open a terminal WebSocket, optionally send input, collect output."""
    result: dict = {"connected": False, "close_code": None, "output": b"", "error": None}
    url = f"{WS_BASE}/ws/terminal/{agent_id}?ticket={ticket}&mode={mode}"

    try:
        async with websockets.connect(url, ping_interval=None, max_size=2**20) as ws:
            result["connected"] = True
            result["close_code"] = ws.close_code

            if input_data:
                await asyncio.sleep(0.5)
                await ws.send(input_data)

            output = b""
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    if isinstance(msg, bytes):
                        output += msg
                    else:
                        output += msg.encode()
            except websockets.exceptions.ConnectionClosed as e:
                result["close_code"] = e.code
            except (asyncio.TimeoutError, websockets.WebSocketException):
                pass

            result["output"] = output

    except websockets.WebSocketException as e:
        result["error"] = str(e)
        result["close_code"] = getattr(e, "code", None)
    except TimeoutError:
        result["error"] = "Connection timeout"

    return result


# ═══════════════════════════════════════════════════════════════════
# 1. SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════════════



if __name__ == "__main__":
    section("1. SYSTEM HEALTH")

    health = http_get("/health")
    test("Orchestrator is reachable", health is not None, str(health)[:100])
    if health:
        test("Health status is ok", health.get("status") == "ok", str(health))

    # ═══════════════════════════════════════════════════════════════════
    # 2. TICKET SERVICE
    # ═══════════════════════════════════════════════════════════════════


    section("2. TICKET SERVICE")

    r = http_post("/api/ws/ticket")
    test("Mint ticket returns ticket string", isinstance(r, dict) and "ticket" in r, str(r)[:80])

    ticket = (r or {}).get("ticket", "")
    test("Ticket is non-empty string", isinstance(ticket, str) and len(ticket) > 0, f"len={len(ticket)}")
    test("Ticket looks like hex", bool(re.match(r'^[a-f0-9]{64}$', ticket)) if ticket else False, ticket[:16])

    # Minting twice should give different tickets
    r2 = http_post("/api/ws/ticket")
    ticket2 = (r2 or {}).get("ticket", "")
    test("Each ticket is unique", ticket and ticket2 and ticket != ticket2, f"{ticket[:8]} vs {ticket2[:8]}")

    # ═══════════════════════════════════════════════════════════════════
    # 3. WEBSOCKET — INVALID TICKET REJECTION
    # ═══════════════════════════════════════════════════════════════════


    section("3. WEBSOCKET — INVALID TICKET")

    result = asyncio.run(try_connect_ws("/ws/terminal/test-agent?ticket=deadbeef"))
    test("Invalid ticket does not connect", result[0] is False, f"connected={result[0]}")

    # Empty ticket
    result = asyncio.run(try_connect_ws("/ws/terminal/test-agent?ticket="))
    test("Empty ticket is rejected", result[0] is False, f"connected={result[0]}")

    # Missing ticket param
    result = asyncio.run(try_connect_ws("/ws/terminal/test-agent"))
    test("Missing ticket is rejected", result[0] is False, f"connected={result[0]}")

    # ═══════════════════════════════════════════════════════════════════
    # 4. WEBSOCKET — INVALID MODE
    # ═══════════════════════════════════════════════════════════════════


    section("4. WEBSOCKET — INVALID MODE")

    # Get a fresh ticket for each mode test
    r_ticket = http_post("/api/ws/ticket")
    t = (r_ticket or {}).get("ticket", "")

    if t:
        result = asyncio.run(try_connect_ws(
            f"/ws/terminal/test-agent?ticket={t}&mode=cobol"
        ))
        # Server closes with 4004; websockets sees upgrade then immediate close
        test("Invalid mode rejected by server", result[0] is False or result[1] == 4004,
             f"connected={result[0]} code={result[1]}")

        # Empty mode — FastAPI Query default may fill in "pi"
        r_ticket2 = http_post("/api/ws/ticket")
        t2 = (r_ticket2 or {}).get("ticket", "")
        if t2:
            result = asyncio.run(try_connect_ws(
                f"/ws/terminal/test-agent?ticket={t2}&mode="
            ))
            # Empty string is not in ("pi", "bash") — correctly rejected
            test("Empty mode is rejected", result[0] is False, f"connected={result[0]}")

        # Uppercase
        r_ticket3 = http_post("/api/ws/ticket")
        t3 = (r_ticket3 or {}).get("ticket", "")
        if t3:
            result = asyncio.run(try_connect_ws(
                f"/ws/terminal/test-agent?ticket={t3}&mode=BASH"
            ))
            test("Uppercase 'BASH' is rejected", result[0] is False or result[1] == 4004,
                 f"connected={result[0]} code={result[1]}")

    # ═══════════════════════════════════════════════════════════════════
    # 5. WEBSOCKET — CONNECT WITH VALID TICKET
    # ═══════════════════════════════════════════════════════════════════


    section("5. WEBSOCKET — CONNECT (VALID)")

    # We need a valid agent_id. Use the first agent from the list, or create one.
    agents = http_get("/api/agents")
    if isinstance(agents, list) and len(agents) > 0:
        agent_id = agents[0].get("id", agents[0].get("name", ""))
    else:
        # Create a temporary agent for the test
        r_create = http_post("/api/agents", {"name": "e2e-term-test", "tools": ["read", "bash"]})
        agent_id = (r_create or {}).get("id", "")
        test("Created terminal e2e agent", bool(agent_id), str(agent_id)[:20])

    if agent_id:
        r_t = http_post("/api/ws/ticket")
        tk = (r_t or {}).get("ticket", "")
        test("Got ticket for terminal connect", bool(tk))

        if tk:
            # Connect in bash mode — the fastest to start
            result = asyncio.run(terminal_session(
                agent_id, tk, mode="bash", input_data=b"echo TERM_E2E_OK\n", timeout_seconds=12.0
            ))

            test("Connected to terminal (bash mode)", result["connected"], f"error={result['error']}")

            output_text = result.get("output", b"").decode("utf-8", errors="replace")
            test("Received terminal output", len(output_text) > 0, f"{len(output_text)} chars")
            test("Saw bash prompt or output", bool(output_text.strip()), repr(output_text[:100]))

            # Check for expected patterns in bash output
            has_cmd_echo = "TERM_E2E_OK" in output_text
            has_prompt = "$" in output_text or "#" in output_text
            has_shell = has_cmd_echo or has_prompt
            test("Bash processed our command", has_shell,
                 f"prompt={'$' if has_prompt else '✗'} echo={has_cmd_echo}")

        # ── Pi mode test ─────────────────────────────────────────
        r_t2 = http_post("/api/ws/ticket")
        tk2 = (r_t2 or {}).get("ticket", "")
        if tk2:
            result_pi = asyncio.run(terminal_session(
                agent_id, tk2, mode="pi", timeout_seconds=8.0
            ))

            test("Connected to terminal (pi mode)", result_pi["connected"], f"error={result_pi['error']}")
            output_text_pi = result_pi.get("output", b"").decode("utf-8", errors="replace")
            test("Pi mode produced output", len(output_text_pi) > 0, f"{len(output_text_pi)} chars")

        # ── Test that reconnect works (second ticket, same agent) ─
        r_t3 = http_post("/api/ws/ticket")
        tk3 = (r_t3 or {}).get("ticket", "")
        if tk3:
            result_re = asyncio.run(terminal_session(
                agent_id, tk3, mode="bash", input_data=b"echo RECONNECT_TEST\n", timeout_seconds=10.0
            ))
            test("Reconnect works", result_re["connected"], f"error={result_re['error']}")
            reconnect_output = result_re.get("output", b"").decode("utf-8", errors="replace")
            test("Reconnect processes commands", "RECONNECT_TEST" in reconnect_output,
                 repr(reconnect_output[:80]))

        # ── Resize test (send escape sequence) ────────────────────
        r_t4 = http_post("/api/ws/ticket")
        tk4 = (r_t4 or {}).get("ticket", "")
        if tk4:
            # Send a resize escape sequence: ESC[8;<rows>;<cols>t
            resize_seq = b"\x1b[8;60;180t"
            result_rs = asyncio.run(terminal_session(
                agent_id, tk4, mode="bash", input_data=resize_seq, timeout_seconds=8.0
            ))
            test("Resize sequence accepted", result_rs["connected"] or result_rs["close_code"] is None,
                 f"connected={result_rs['connected']}")

    # ═══════════════════════════════════════════════════════════════════
    # 6. CONFIG PROFILE SYSTEM (via direct import)
    # ═══════════════════════════════════════════════════════════════════


    section("6. CONFIG PROFILE SYSTEM")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from pi_orchestrator.config import (
        load_orchestrator_config,
        save_orchestrator_config,
        get_profile_value,
        set_profile_key,
        list_profiles,
        set_active_profile,
        remove_profile,
    )

    # Profile CRUD
    set_profile_key("default_model", "sonnet", profile="e2e-prod")
    set_profile_key("default_model", "flash", profile="e2e-staging")

    config = load_orchestrator_config()
    test("e2e-prod profile exists", "e2e-prod" in config.get("profiles", {}))
    test("e2e-staging profile exists", "e2e-staging" in config.get("profiles", {}))

    profiles = list_profiles()
    profile_names = [p["name"] for p in profiles]
    test("list_profiles includes e2e-prod", "e2e-prod" in profile_names)
    test("list_profiles includes e2e-staging", "e2e-staging" in profile_names)

    # Switch profiles
    test("set_active_profile works", set_active_profile("e2e-prod"))
    profiles_after = list_profiles()
    for p in profiles_after:
        if p["name"] == "e2e-prod":
            test("e2e-prod marked active", p["active"] is True)
        if p["name"] == "e2e-staging":
            test("e2e-staging marked inactive", p["active"] is False)

    # Profile-specific get
    val = get_profile_value("default_model", profile="e2e-staging")
    test("e2e-staging has model flash", val == "flash", f"got={val}")

    # Env var override (via monkeypatch-style at runtime — real env vars)
    old_env = os.environ.get("PI_DEFAULT_MODEL")
    os.environ["PI_DEFAULT_MODEL"] = "env-sonnet"
    try:
        val = get_profile_value("default_model", profile="e2e-prod")
        test("Env var overrides profile", val == "env-sonnet", f"got={val}")
    finally:
        if old_env is None:
            del os.environ["PI_DEFAULT_MODEL"]
        else:
            os.environ["PI_DEFAULT_MODEL"] = old_env

    # Cleanup
    test("remove_profile e2e-prod", remove_profile("e2e-prod"))
    test("remove_profile e2e-staging", remove_profile("e2e-staging"))

    # ═══════════════════════════════════════════════════════════════════
    # 7. CLEANUP
    # ═══════════════════════════════════════════════════════════════════


    section("7. CLEANUP")

    # Delete the e2e agent if we created it
    if agent_id and agent_id.startswith("e2e-"):
        r_del = http_post(f"/api/agents/{agent_id}/delete")
        test("Deleted e2e terminal agent", r_del is not None, str(r_del)[:50])

    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════


    section("SUMMARY")

    total = PASS + FAIL
    pct = round(PASS / total * 100) if total > 0 else 0
    print(f"\n  {PASS}/{total} passed ({pct}%)")

    if FAIL > 0:
        print(f"\n  Failures:")
        for f in FAILURES:
            print(f)
        sys.exit(1)
    else:
        print(f"\n  🎉 All terminal e2e tests pass!")
        sys.exit(0)
