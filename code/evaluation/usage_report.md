# Usage report

Final full-dataset run: local deterministic semantic fallback plus deterministic
financial engine.

| Provider | Model | Calls | Input tokens | Output tokens | Total tokens | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|
| None configured | None | 0 | 0 | 0 | 0 | $0.00 |

The provider abstraction is present but no credentialed, reviewed provider client
is configured in this environment. The 250-request final run made **zero** AI
model calls and used the deterministic semantic fallback **250** times. Exact
model token counts are therefore zero; no costs are estimated or invented.

The fallback extracts request intent/amount, profile preferences and priorities,
message/image references, and injection indicators. The deterministic engine
continues to make every arithmetic and safety decision.
