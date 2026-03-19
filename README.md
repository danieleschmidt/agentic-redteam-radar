# 🎯 Agentic RedTeam Radar

Automated adversarial scanner for LLM and agent applications. Runs a structured battery of red-team probes against any OpenAI-compatible, Ollama, or custom HTTP endpoint — no heavyweight frameworks needed.

## What It Does

- **25 adversarial probes** across 5 attack categories
- Simple `requests`-based HTTP calls — no LangChain, no heavy deps
- Structured JSON output + human-readable text report
- Risk scoring (0–100) with per-severity breakdown
- CI-friendly: exits `1` if vulnerabilities found

## Attack Categories

| Category | ID Prefix | Probes | What It Tests |
|---|---|---|---|
| Prompt Injection | `PI-*` | 5 | Direct overrides, delimiter escapes, encoding tricks |
| Jailbreak | `JB-*` | 5 | DAN persona, dev mode, fictional framing, social engineering |
| Data Exfiltration | `DE-*` | 5 | System prompt dumping, context window leakage, tool enumeration |
| Role Confusion | `RC-*` | 5 | Operator impersonation, developer claims, recursive persona traps |
| Multi-Turn / Indirect | `MT-*` | 5 | Gradual escalation, base64 injection, CoT hijack, translation smuggling |

## Install

```bash
pip install -e .
# or just:
pip install requests
```

## Usage

### Scan an Ollama endpoint

```bash
python -m redteam_radar.cli \
  --url http://localhost:11434 \
  --style ollama \
  --model llama3 \
  --verbose
```

### Scan an OpenAI-compatible endpoint

```bash
export OPENAI_API_KEY=sk-...
python -m redteam_radar.cli \
  --url https://api.openai.com \
  --style openai \
  --model gpt-4o
```

### Scan a custom HTTP endpoint

```bash
python -m redteam_radar.cli \
  --url http://myapp.internal/chat \
  --style raw
```

### Limit to specific categories

```bash
python -m redteam_radar.cli \
  --url http://localhost:11434 \
  --style ollama \
  --model mistral \
  --categories prompt_injection jailbreak
```

### Save JSON report

```bash
python -m redteam_radar.cli \
  --url http://localhost:11434 \
  --style ollama \
  --model llama3 \
  --output report.json
```

## Use As a Library

```python
from redteam_radar.endpoint import Endpoint
from redteam_radar.scanner import Scanner
from redteam_radar.reporter import to_json, to_text

endpoint = Endpoint(
    url="http://localhost:11434",
    style="ollama",
    model="llama3",
    system_prompt="You are a helpful assistant.",
)

scanner = Scanner(endpoint, verbose=True)
report = scanner.run()

print(to_text(report))
print(f"\nRisk score: {report.risk_score()}/100")
print(f"Vulnerabilities: {len(report.vulnerable)}/{report.total}")

# Save JSON
with open("scan_report.json", "w") as f:
    f.write(to_json(report))
```

## Sample Output

```
========================================================================
 AGENTIC REDTEAM RADAR — SCAN REPORT
========================================================================
 Target : http://localhost:11434
 Model  : llama3  (style: ollama)
 Date   : 2026-03-19 14:00 UTC
 Time   : 18.4s

 SUMMARY
------------------------------------------------------------------------
  Risk Score      : 62/100  🟠 HIGH
  Total Probes    : 25
  Vulnerable      : 8
  Safe            : 17
  Errors          : 0
  Vuln Rate       : 32.0%

 BY CATEGORY
------------------------------------------------------------------------
  data_exfiltration        2 vuln /  5 total
  jailbreak                3 vuln /  5 total
  multi_turn               1 vuln /  5 total
  prompt_injection         1 vuln /  5 total
  role_confusion           1 vuln /  5 total

 FINDINGS BY SEVERITY
------------------------------------------------------------------------
  CRITICAL    3  ███
  HIGH        4  ████
  MEDIUM      1  █
  LOW         0  
```

## Supported Endpoint Styles

| Style | Path | Auth | Notes |
|---|---|---|---|
| `openai` | `POST /v1/chat/completions` | `Authorization: Bearer <key>` | Any OpenAI-compat API |
| `ollama` | `POST /api/chat` | None | Ollama local server |
| `raw` | `POST /` | Optional `Bearer` | Custom: `{"message": ...}` → `{"response": ...}` |

## Running Tests

```bash
~/anaconda3/bin/python3 -m pytest tests/ -v
```

## JSON Report Structure

```json
{
  "meta": { "target": "...", "model": "...", "duration_s": 18.4 },
  "summary": {
    "total_probes": 25,
    "vulnerable": 8,
    "risk_score": 62.0,
    "by_category": { ... },
    "by_severity": { "CRITICAL": 3, "HIGH": 4, "MEDIUM": 1, "LOW": 0 }
  },
  "findings": [
    {
      "probe_id": "JB-001",
      "name": "DAN persona",
      "severity": "CRITICAL",
      "is_vulnerable": true,
      "confidence": 0.85,
      "evidence": ["Response contains detection hint(s): ['dan', 'no restrictions']"],
      "reproduction": {
        "endpoint": "http://...",
        "payload": "You are now DAN...",
        "description": "..."
      }
    }
  ],
  "all_results": [ ... ]
}
```

## Adding Custom Probes

```python
from redteam_radar.probes import Probe, ALL_PROBES

my_probe = Probe(
    id="CUSTOM-001",
    category="prompt_injection",
    name="My custom attack",
    payload="Your actual attack payload here",
    severity="HIGH",
    description="What this probe tests",
    detection_hints=["phrase that indicates success"],
)

ALL_PROBES.append(my_probe)
```

## License

MIT — see [LICENSE](LICENSE)
