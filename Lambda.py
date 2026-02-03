import os
import json
import boto3
import urllib.request
import re

# ---------- CONFIG ----------
BUCKET = "ai-log-analyzer-maith"
KEY = "system.log"
MODEL = "gpt-4o-mini"   # low cost, good for this use
TIMEOUT_SECONDS = 20

s3 = boto3.client("s3")


# ---------- HELPERS ----------
def fetch_logs_from_s3(bucket: str, key: str) -> str:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read().decode("utf-8")


def call_openai_for_analysis(logs: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY is missing in Lambda environment variables")

    # Ask model to return STRICT JSON only (no backticks)
    prompt = f"""
Return ONLY valid JSON (no markdown, no backticks, no extra text).

Analyze the system logs and output JSON with keys:
- risk_level: one of ["low","medium","high"]
- root_cause: string
- recommended_actions: array of strings

Logs:
{logs}
""".strip()

    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 300
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        body = resp.read().decode("utf-8")

    result = json.loads(body)
    content = result["choices"][0]["message"]["content"].strip()

    # Safety: if model still returns extra text, extract JSON object
    content = content.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise Exception(f"AI did not return JSON. Raw content: {content}")

    analysis = json.loads(match.group(0))

    # Normalize fields (defensive)
    analysis.setdefault("risk_level", "medium")
    analysis.setdefault("root_cause", "unknown")
    analysis.setdefault("recommended_actions", [])

    return analysis


def decide_action(analysis: dict) -> dict:
    """
    PHASE 6: "Self-healing" action simulation.
    We DON'T actually restart anything (no EC2). We just return what we would do.
    """
    risk = (analysis.get("risk_level") or "").lower()

    if risk == "high":
        action = {
            "action_taken": "SIMULATED_REMEDIATION",
            "what_it_would_do": [
                "Restart nginx service",
                "Restart mysql service",
                "Raise incident / page on-call",
                "Capture diagnostics (top, df, journalctl excerpts)"
            ],
            "priority": "P1"
        }
    elif risk == "medium":
        action = {
            "action_taken": "SIMULATED_ALERT_ONLY",
            "what_it_would_do": [
                "Send alert to Slack/Email",
                "Create ticket for investigation"
            ],
            "priority": "P2"
        }
    else:
        action = {
            "action_taken": "NO_ACTION",
            "what_it_would_do": ["Log and continue monitoring"],
            "priority": "P3"
        }

    return action


# ---------- LAMBDA HANDLER ----------
def lambda_handler(event, context):
    # Phase 4: fetch logs
    logs = fetch_logs_from_s3(BUCKET, KEY)

    # Keep CloudWatch logs readable
    print("===== LOGS FROM S3 =====")
    print(logs)

    # Phase 5: AI analysis
    analysis = call_openai_for_analysis(logs)

    print("===== AI ANALYSIS (JSON) =====")
    print(json.dumps(analysis, indent=2))

    # Phase 6: decision + simulated remediation
    action = decide_action(analysis)

    print("===== DECISION / ACTION =====")
    print(json.dumps(action, indent=2))

    # Clean Lambda return
    return {
        "ok": True,
        "bucket": BUCKET,
        "key": KEY,
        "analysis": analysis,
        "decision": action
    }