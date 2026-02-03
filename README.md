# Self-Healing Cloud Log Analyzer (On-Demand AIOps Simulation)

This project demonstrates an **event-driven, cost-controlled** approach to log monitoring using AWS + AI.

Instead of running 24/7 infrastructure, the workflow is **on-demand**:
- A log file is stored in S3
- AWS Lambda pulls the logs and sends them to an AI model for analysis
- The function returns a structured risk assessment and a **simulated remediation plan**
- GitHub Actions can manually trigger the Lambda (one-click run)

---

## ✅ What it does

- Reads Linux/system logs from **Amazon S3**
- Uses an AI call to classify:
  - `risk_level` (low/medium/high)
  - likely `root_cause`
  - `recommended_actions`
- Produces a “decision” object that mimics what an AIOps tool might trigger:
  - restart services (simulated)
  - page on-call (simulated)
  - capture diagnostics (simulated)

---

## Architecture

**S3 (logs)** → **AWS Lambda (Python)** → **OpenAI API** → **Decision Output**  
Manual trigger via **GitHub Actions** (workflow_dispatch)

---

## Why this is safe on cost

- No EC2
- No scheduled triggers
- No always-on monitoring
- Runs only when invoked manually (or via GitHub Actions)

---

## Tech Stack

- AWS Lambda (Python)
- Amazon S3
- CloudWatch Logs
- GitHub Actions
- OpenAI API (via HTTPS call)

---

## How to Run

### 1) Upload sample logs
Upload `system.log` to your S3 bucket.

### 2) Configure Lambda environment variables
Set in Lambda → Configuration → Environment variables:
- `OPENAI_API_KEY` = your key

### 3) Test in Lambda
Run a test event `{}` and check CloudWatch logs:
- `LOGS_FROM_S3=...`
- `AI_ANALYSIS=...`
- `DECISION=...`

### 4) Run from GitHub Actions
Go to **Actions** → “Run Log Analyzer” → **Run workflow**.

---

## Output Example (sample)

- `risk_level`: high
- `root_cause`: memory exhaustion + service failures
- `recommended_actions`: restart services, investigate memory, check logs
- `decision`: simulated remediation steps and priority

---

## What I learned

- Building an end-to-end serverless workflow
- Secure API key handling with environment variables / secrets
- Connecting GitHub Actions to AWS for manual deployments/triggers
- Structuring operational outputs like real AIOps systems
