# Buy or Wait? AI financial agent

Run from the repository root:

```powershell
python code/main.py
python code/evaluation/main.py
python -m unittest discover -s code/tests -v
```

## Architecture

`agent_layer.py` is the semantic-agent boundary. It interprets natural-language
request intent and amount, gathers relevant messages and linked image evidence,
captures payment preferences/priorities, and writes a concise personalized
explanation. `main.py` passes the resulting structured facts around the existing
`Engine`, which remains the sole authority for balances, currency conversion,
recurrence, 90-day forecasting, plan candidates, minimum-balance protection,
and all payment constraints.

The semantic layer is deliberately unable to alter `amount_safe_to_pay`, status,
method, plan, date, or spending changes. The independent validator recomputes
those fields from the deterministic engine for every output row.

## Evidence and safety

Messages and images are untrusted data. The agent records instruction-like text
such as “ignore previous rules” as an injection signal and never executes it or
lets it override financial/challenge rules. Image-backed financial amounts remain
the reviewed `IMAGE_AMOUNTS` evidence mapping in the deterministic engine.

## Provider and fallback

The project includes a provider protocol and environment-only configuration
boundary (`BUY_OR_WAIT_LLM_PROVIDER`, `BUY_OR_WAIT_LLM_API_KEY`); no key is
hard-coded. This submission has no reviewed configured provider client, so it
uses a deterministic semantic fallback safely for every request. It never
fabricates LLM facts or usage. A future reviewed provider implementation may
implement `SemanticProvider`, but its output must remain prose/evidence-only and
cannot change the engine's validated financial fields.

No network, credential, or live financial data is required for the current run.
