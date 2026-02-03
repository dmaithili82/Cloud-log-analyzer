import os
import json
import boto3
import urllib.request
import urllib.error

BUCKET = "ai-log-analyzer-maith"
KEY = "system.log"

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"


def call_openai_for_json(logs: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in Lambda environment variables")

    prompt = (
        "You are a site reliability assistant. "
        "Analyze the logs and return ONLY valid JSON with keys:\n"
        "risk_level (low|medium|high), root_cause (string), recommended_actions (array of strings).\n\n"
        f"LOGS:\n{logs}\n"
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Return ONLY JSON. No markdown, no backticks."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }

    req = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI HTTPError {e.code}: {err_body}")
    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {str(e)}")

    result = json.loads(raw)
    content = result["choices"][0]["message"]["content"].strip()

    # Parse the model output into a dict
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # If it still returns extra text, try to salvage JSON portion
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise RuntimeError(f"AI did not return valid JSON. Raw content: {content}")


def decide_action(analysis: dict) -> dict:
    risk = (analysis.get("risk_level") or "").lower()

    if risk == "high":
        return {
            "action_taken": "SIMULATED_REMEDIATION",
            "priority": "P1",
            "what_it_would_do": [
                "Restart nginx service",
                "Restart mysql service",
                "Raise incident / page on-call",
                "Capture diagnostics (top, df, journalctl excerpts)",
            ],
        }
    elif risk == "medium":
        return {
            "action_taken": "SIMULATED_ALERT",
            "priority": "P2",
            "what_it_would_do": [
                "Create ticket for investigation",
                "Capture diagnostics snapshot",
                "Monitor memory/CPU trends",
            ],
        }
    else:
        return {
            "action_taken": "NO_ACTION",
            "priority": "P3",
            "what_it_would_do": ["Continue monitoring"],
        }


def lambda_handler(event, context):
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=BUCKET, Key=KEY)
    logs = obj["Body"].read().decode("utf-8", errors="ignore").strip()

    # Print logs as ONE block (CloudWatch may still show multiple lines, but it’s one print call)
    print("LOGS_FROM_S3=" + logs.replace("\n", "\\n"))

    analysis = call_openai_for_json(logs)
    decision = decide_action(analysis)

    # Clean: print compact JSON in single lines
    print("AI_ANALYSIS=" + json.dumps(analysis, separators=(",", ":")))
    print("DECISION=" + json.dumps(decision, separators=(",", ":")))

    return {
        "ok": True,
        "bucket": BUCKET,
        "key": KEY,
        "analysis": analysis,
        "decision": decision,
    }