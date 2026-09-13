 # Buy or Wait? — AI Financial Decision Agent

An AI-assisted financial decision agent built for the **HackerRank Orchestrate September 2026** challenge **“Buy or Wait?”**

The system analyzes a user's financial position and purchase request to determine whether they should pay now, use an available payment plan, make a partial payment, wait until a safer date, or avoid the purchase.

## Problem

A purchase that looks affordable from the current bank balance may not remain affordable after considering:

* Upcoming essential expenses
* Recurring income and expenses
* Pending and scheduled transactions
* Minimum balance requirements
* User payment preferences
* Installment options
* Partial-payment eligibility
* Flexible spending that the user is willing to reduce or stop
* Financial information contained in messages and images

The goal is therefore not simply to check the current balance, but to determine whether the requested payment remains financially safe over a **90-day forecast**.

## Solution Overview

The solution uses a hybrid architecture:

```text
User Request
     ↓
Evidence Layer
(messages, images, profiles, events)
     ↓
Trust Boundary
     ↓
AI Semantic Agent
     ↓
Structured Semantic Facts
     ↓
Deterministic Financial Engine
     ↓
Independent Validator
     ↓
output.csv
```

### Core Design Principle

> **AI interprets messy evidence; deterministic code makes the financial decision.**

The AI layer is intentionally not responsible for financial calculations. This prevents an AI-generated response from directly changing the affordability decision or payment plan.

## AI Semantic Agent

`code/agent_layer.py` provides the semantic-agent boundary.

It is responsible for interpreting information such as:

* Natural-language purchase/request intent
* Mentioned amounts
* Payment preferences
* User priorities
* Commitment-related terms
* Relevant messages
* Linked image evidence
* Instruction-like or prompt-injection text

The semantic layer produces structured `SemanticFacts` that can be used by the financial engine.

### Trust Boundary

Messages and images are treated as **untrusted evidence**, not instructions.

Instruction-like text such as attempts to override system or challenge rules is detected and ignored rather than being executed.

The semantic agent cannot directly modify:

* `amount_safe_to_pay`
* Affordability status
* Recommended payment method
* Payment plan
* Earliest safe payment date
* Spending changes

## Deterministic Financial Decision Engine

The financial engine in `code/main.py` is the authority for financial decisions.

It considers:

* Current available balance
* Minimum balance to maintain
* Historical and scheduled financial events
* Recurring income and expenses
* Confirmed future transactions
* Fixed exchange-rate data
* User financial priorities
* Protected spending categories
* Flexible spending categories
* Payment preferences
* Available installment options
* Partial-payment rules
* Desired completion date

The engine performs a **90-day cash-flow safety simulation** and ensures that the projected balance does not fall below the user's required minimum.

## Decision Options

For each request, the system can recommend:

### Full Payment

Pay the complete requested amount immediately when the 90-day forecast remains safe.

### Partial Payment

Make a safe payment today and pay the remaining amount on the earliest safe date when the request and user preferences allow partial payment.

### Installments

Use an eligible payment option when it satisfies the user's preferences, maximum installment limit, total cost, and completion deadline.

### Wait

Delay the purchase until the earliest date on which paying the full amount becomes financially safe.

### Not Recommended

If no valid option can complete the request safely within the required conditions, the system recommends not proceeding.

## Spending Changes

The system can consider permitted changes to flexible recurring spending.

Examples include:

```text
stop:<event_id>
reduce_to:<event_id>:<new_amount>
```

Only eligible flexible spending can be changed. Protected or essential spending is not modified.

The system ranks plans according to the challenge requirements, including preference for plans that avoid spending changes.

## Payment Plan Ranking

Candidate plans are ranked using the challenge's decision priorities:

1. Complete the request by the required deadline
2. Avoid spending changes
3. Minimize total amount paid
4. Start payment earlier
5. Use fewer payments
6. Use the lowest payment option ID as the final tie-breaker

## Output

The final predictions are written to:

```text
output.csv
```

The output contains exactly:

```text
request_id
amount_safe_to_pay
affordability_status
recommended_payment_method
payment_plan
earliest_date_for_full_payment
spending_changes_needed
decision_explanation
```

The system generates one prediction for every request in:

```text
dataset/requests.csv
```

## Validation

An independent validator is included at:

```text
code/evaluation/main.py
```

It verifies:

* Output schema and column order
* Correct number of requests
* Request IDs
* Safe payment amount bounds
* Payment-plan chronology
* Payment totals
* Partial-payment rules
* Installment eligibility
* Spending-change rules
* Minimum-balance safety
* Deterministic recomputation of recommendations
* Presence of a personalized explanation

The current full-dataset output has been validated successfully:

```text
PASS: schema, IDs, values, totals, chronology, option rules, cash safety, and spending changes validated
```

## Running the Project

Run these commands from the repository root.

### Generate the output

```powershell
python code/main.py
```

### Run the independent validator

```powershell
python code/evaluation/main.py
```

### Run the tests

```powershell
python -m unittest discover -s code/tests -v
```

## Optional Local AI Provider

The semantic layer supports a local **Ollama** provider.

The default model is:

```text
gemma3:4b
```

If Ollama is available:

```powershell
ollama serve
```

and verify the installed model:

```powershell
ollama list
```

The provider can be configured using:

```text
OLLAMA_BASE_URL
OLLAMA_MODEL
BUY_OR_WAIT_LLM_PROVIDER
```

The deterministic fallback is also supported when no local model is available.

The financial engine does not depend on an external cloud API or live financial/market data.

## Safety Approach

The system follows a strict separation between **semantic interpretation** and **financial computation**.

```text
Untrusted Evidence
       ↓
AI interprets evidence
       ↓
Structured facts
       ↓
Deterministic financial calculations
       ↓
Validated recommendation
```

This design means an instruction hidden inside a message or image cannot directly override financial constraints.

The system also avoids treating unsupported future income as available cash and protects the user's minimum balance throughout the forecast.

## Project Structure

```text
.
├── README.md
├── problem_statement.md
├── dataset/
│   ├── exchange_rates.csv
│   ├── financial_events.csv
│   ├── financial_profiles.csv
│   ├── images.csv
│   ├── messages.csv
│   ├── requests.csv
│   ├── request_payment_options.csv
│   └── media/
│       └── images/
├── code/
│   ├── main.py
│   ├── agent_layer.py
│   ├── llm_demo.py
│   ├── README.md
│   ├── evaluation/
│   │   ├── main.py
│   │   ├── usage_report.md
│   │   └── llm_demo_report.md
│   └── tests/
│       └── test_engine.py
└── output.csv
```

## Key Idea

The project combines the flexibility of an AI semantic layer with the reliability of deterministic financial rules.

**AI handles interpretation.
The financial engine handles decisions.
The validator checks the result.**

