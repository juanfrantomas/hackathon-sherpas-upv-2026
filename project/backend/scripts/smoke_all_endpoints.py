"""Smoke test of every endpoint of the backend against a running instance."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8021"
API = f"{BASE}/api"
CASE = "timothy-melanie-weah"

ok = 0
fail = 0


def call(method: str, path: str, body=None, timeout: int = 200, expected=(200,)):
    global ok, fail
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode()
            payload = json.loads(raw) if raw else None
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read().decode()
        payload = json.loads(raw) if raw else None
        status = error.code
    except Exception as error:  # noqa: BLE001
        print(f"  ERROR {method:6s} {path:52s} {type(error).__name__}: {error}")
        fail += 1
        return None

    if status in expected:
        ok += 1
        print(f"  OK    {method:6s} {path:52s} {status}")
    else:
        fail += 1
        print(
            f"  FAIL  {method:6s} {path:52s} {status} "
            f"(esperado {expected}) {str(payload)[:120]}"
        )
    return payload


print("== catálogos y salud ==")
call("GET", "/health")
call("GET", "/environment")
call("GET", "/categories")
call("GET", "/sections")
call("GET", "/cases")

print("\n== hitos ==")
call("POST", f"/cases/{CASE}/milestones/generate", {"force": True})
listing = call("GET", f"/cases/{CASE}/milestones")
call("GET", f"/cases/{CASE}/milestones?group_by=category")
call("GET", f"/cases/{CASE}/milestones?status=not_started")
call("GET", f"/cases/{CASE}/milestones?type=financial")

milestones = listing["milestones"] if listing else []
educational = next((m for m in milestones if m["type"] == "educational"), None)
financial = next((m for m in milestones if m["type"] == "financial"), None)
if educational:
    mid = educational["id"]
    call("GET", f"/cases/{CASE}/milestones/{mid}")
    call("GET", f"/cases/{CASE}/milestones/{mid}/progress")
    call("PATCH", f"/cases/{CASE}/milestones/{mid}/status", {"status": "in_progress"})
    tasks = call("GET", f"/cases/{CASE}/milestones/{mid}/tasks")
    if tasks:
        call(
            "PATCH",
            f"/cases/{CASE}/milestones/{mid}/tasks/{tasks[0]['id']}",
            {"status": "completed"},
        )
        call(
            "POST",
            f"/cases/{CASE}/milestones/{mid}/tasks",
            {"title": "Call the bank on Monday"},
            expected=(201,),
        )
    call("GET", f"/cases/{CASE}/milestones/{mid}/checkins")
    call(
        "POST",
        f"/cases/{CASE}/milestones/{mid}/checkins/complete",
        {"effective_date": "2026-11-17"},
    )
    call("POST", f"/cases/{CASE}/milestones/{mid}/complete", {"confirmed": True})

if financial:
    fid = financial["id"]
    call("GET", f"/cases/{CASE}/milestones/{fid}/financial-progress")
    call(
        "POST",
        f"/cases/{CASE}/milestones/{fid}/observations",
        {
            "metric_key": financial.get("financial_metric_key") or "liability_chase_cc",
            "metric_type": "balance",
            "value": "12000",
            "unit": "USD",
        },
        expected=(201,),
    )
    call("GET", f"/cases/{CASE}/milestones/{fid}/observations")
    call("GET", f"/cases/{CASE}/milestones/{fid}/financial-progress")

call("GET", f"/cases/{CASE}/checkins")
call("GET", f"/cases/{CASE}/notifications")
call("GET", f"/cases/{CASE}/progress")
call("GET", f"/cases/{CASE}/sync")
call("POST", f"/cases/{CASE}/sync", {"force": False})

print("\n== mentor ==")
call("GET", "/voice/styles")
call(
    "POST",
    "/voice/ask",
    {
        "case_id": CASE,
        "question": "¿Qué me recommends hacer primero con la tarjeta?",
        "style": "auto",
        "partner": "both",
    },
)

print("\n== pilares ==")
call("GET", f"/cases/{CASE}/simulator")
call(
    "POST",
    f"/cases/{CASE}/simulator",
    {"active_ids": ["pay-down-revolving-card", "add-life-cover"]},
)
call("GET", f"/cases/{CASE}/mentor/insights")
couple = call("GET", f"/cases/{CASE}/couple")
if couple and couple.get("members"):
    call(
        "POST",
        f"/cases/{CASE}/couple/high-five",
        {
            "from_member": couple["members"][0]["name"],
            "to_member": couple["members"][-1]["name"],
            "milestone_title": "A step forward",
            "message": "Well done",
        },
    )
    call("GET", f"/cases/{CASE}/couple")
call("GET", f"/cases/{CASE}/story")

print("\n== errores ==")
call("GET", "/cases/not-allowed/milestones", expected=(403,))
call("GET", f"/cases/{CASE}/milestones/ms_nope", expected=(404,))
call("GET", f"/cases/{CASE}/milestones/ms_nope/progress", expected=(404,))

print(f"\n{ok} OK · {fail} FAIL")
sys.exit(1 if fail else 0)
