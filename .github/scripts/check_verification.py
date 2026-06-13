"""
Smoke-test assertion: confirms the Lambda response contains a well-formed
`verification` block at body.audit_data.verification.

Task 3 (claim_truth_scorer) requires every audit to ship with:
  - truth_score (int, 0-100)
  - tier       (str: high | medium | low)
  - summary    (str, <= 25 words)

If any of these are missing or the block is absent, the script exits 1 and
the deploy rolls back to the previous Lambda digest.

Usage: python3 check_verification.py /tmp/smoke_response.json
"""
import json
import sys


def main(path: str) -> int:
    try:
        with open(path) as f:
            envelope = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: cannot read {path}: {e}")
        return 1

    body = envelope.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"FAIL: envelope.body is not valid JSON: {e}")
            return 1
    if not isinstance(body, dict):
        print(f"FAIL: envelope.body is not a dict: {type(body).__name__}")
        return 1

    audit = body.get("audit_data", body)
    if not isinstance(audit, dict):
        print(f"FAIL: body.audit_data is not a dict: {type(audit).__name__}")
        return 1

    if "verification" not in audit:
        print("FAIL: missing 'verification' block in body.audit_data — Task 3 regressed?")
        return 1

    v = audit["verification"]
    if not isinstance(v, dict):
        print(f"FAIL: verification block is not a dict: {type(v).__name__}: {v}")
        return 1

    required = ("truth_score", "tier", "summary")
    missing = [k for k in required if k not in v]
    if missing:
        print(f"FAIL: verification block missing keys {missing}: {v}")
        return 1

    ts = v["truth_score"]
    if not isinstance(ts, int) or not 0 <= ts <= 100:
        print(f"FAIL: truth_score out of range or wrong type: {ts!r}")
        return 1

    if v["tier"] not in ("high", "medium", "low"):
        print(f"FAIL: tier not in (high, medium, low): {v['tier']!r}")
        return 1

    print(
        f"PASS: verification block present "
        f"(truth_score={ts}, tier={v['tier']}, summary='{v['summary'][:60]}')"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/smoke_response.json"))
