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

## Ollama provider and fallback

The runtime provider is local Ollama, using `gemma3:4b` by default. Start it in
another terminal with `ollama serve` (if it is not already running) and ensure
the model is present with `ollama list`. No API key, cloud model, model download,
or model weights in this repository are required. Override the local endpoint or
model only with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`; set
`BUY_OR_WAIT_LLM_PROVIDER=none` to force the fallback.

For each uncached request, Ollama receives a short prompt plus only its relevant
untrusted messages and linked images. It must return a constrained JSON semantic
schema. Responses are parsed, type-checked, normalized, and intersected with
trusted profile values before use. Malformed JSON, an unavailable server, or an
unsafe response automatically use deterministic semantic extraction instead.
Ollama is never asked to calculate affordability or payment plans.

The run writes measured local API token counters to `evaluation/usage_report.md`
when Ollama returns them. Local inference is reported at $0.00; no token or cost
value is guessed when unavailable.
