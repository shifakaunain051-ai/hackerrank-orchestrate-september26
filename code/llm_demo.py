import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from main import Engine, rows
from agent_layer import FinancialAgent, OllamaProvider

engine = Engine()
provider = OllamaProvider(timeout=30)
agent = FinancialAgent(engine, provider)

requests = rows("requests.csv")

selected = []
for request in requests:
    evidence, image_events, image_paths = agent.related_evidence(request)
    if evidence or image_paths:
        selected.append(request)
    if len(selected) == 5:
        break

print(f"Selected {len(selected)} real evidence-bearing requests.")
print("Provider:", provider.name)
print("Model:", provider.model)
print()

for n, request in enumerate(selected, 1):
    print(f"--- DEMO REQUEST {n}/5 ---")
    print("request_id:", request["request_id"])
    print("request:", request["request_text"])

    evidence, image_events, image_paths = agent.related_evidence(request)
    print("messages:", len(evidence))
    print("images:", len(image_paths))

    facts = agent.facts_for(request)

    print("LLM source:", facts.source)
    print("item:", facts.item)
    print("amount:", facts.mentioned_amount)
    print("currency:", facts.currency)
    print("preferences:", facts.preferences)
    print("priorities:", facts.priorities)
    print("injection_detected:", facts.injection_detected)
    print()

report = ROOT / "code" / "evaluation" / "llm_demo_report.md"
report.write_text(
    "# LLM Demo Report\n\n"
    f"- Provider: {provider.name}\n"
    f"- Model: {provider.model}\n"
    f"- Requests attempted: {len(selected)}\n"
    f"- Successful Ollama calls: {provider.calls}\n"
    f"- Fallback count: {agent._fallback_requests}\n"
    f"- Input tokens: {provider.prompt_tokens}\n"
    f"- Output tokens: {provider.output_tokens}\n"
    f"- Total tokens: {provider.prompt_tokens + provider.output_tokens}\n"
    "- Estimated cost: $0.00 (local Ollama inference)\n"
    "- Root output.csv modified: No\n",
    encoding="utf-8",
)

print("Demo report written to:", report)
print("output.csv was not modified.")
