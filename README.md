# chatbot-demo

An airline customer service chatbot demo. "Sunny" is a support agent for the
fictional SkyHop Airlines who answers policy questions and looks up booking and
flight data through LLM tool calls.

The point of the project is the shape, not the airline. It's a small, readable
reference for a tool-calling agent with a provider-agnostic core: swap the LLM
backend or replace the mock data layer with a real API without touching the
orchestration logic.

- Interactive terminal chat, no server or frontend
- Pluggable LLM providers behind a single abstract interface (Anthropic, OpenRouter)
- Four LLM-callable tools registered by decorator
- Mock airline APIs backed by JSON, behind a connector boundary
- Policy answers grounded in a knowledge base file, with a "don't guess" guardrail
- ~62 tests, no live API calls

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) for dependency management
- An API key for Anthropic or OpenRouter

## Quickstart

```bash
git clone <repo-url>
cd chatbot-demo

cp .env.example .env
# edit .env and fill in your key(s)

uv sync
uv run python cli.py
```

You'll get a banner, a welcome message, and a `You:` prompt.

```
SkyHop Airlines — customer service assistant
Provider: openrouter (anthropic/claude-sonnet-5)

Type your question, or "exit" to quit.

Sunny: Hi, I'm Sunny with SkyHop Airlines. I can help with bookings, flight
status, changes, and cancellations — what can I do for you today?

You:
```

Type `exit` or `quit` to leave. Ctrl+C and Ctrl+D also exit cleanly. Saying
something like "let's start over" resets the conversation without quitting.

## Configuration

Secrets live in `.env`, which is gitignored. Everything else is a constant in
`config/__init__.py`.

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Key for Anthropic's Messages API |
| `OPENROUTER_API_KEY` | Key for OpenRouter's OpenAI-compatible endpoint |

Both keys are currently validated at import time, so both must be present even
if you only use one provider.

Notable constants in `config/__init__.py`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `ACTIVE_PROVIDER` | `"openrouter"` | Which backend to use. Edit this to switch. |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Model ID for the Anthropic path |
| `OPENROUTER_MODEL` | `anthropic/claude-sonnet-5` | Model ID for the OpenRouter path |
| `MAX_TOKENS` | `2048` | Response cap per call |
| `REQUEST_TIMEOUT_SECONDS` | `60` | HTTP timeout |
| `MAX_TOOL_ROUNDTRIPS` | `3` | Tool calls allowed per user turn before the turn is abandoned |
| `RESET_PHRASES` | see file | Keyword backstop for conversation reset |

## Try it

The mock data is built around one scenario: it's the evening of
**July 9, 2026**, and thunderstorms over Denver have cancelled most SkyHop
departures between 18:00 and 22:00.

Sample things to ask:

- *"What's the status of SH412 on July 9th?"* — a cancelled flight
- *"My booking code is GH7X2P, last name Webb"* — pulls a real record
- *"What am I entitled to if my flight is cancelled?"* — answered from the policy KB
- *"Are there other flights to SFO?"* — triggers a route search for alternatives
- *"What's SkyHop's pet travel policy?"* — not in the KB, so Sunny should decline rather than guess

Useful booking codes from `mock_data/bookings.json`: `GH7X2P` (Webb),
`K4LM89` (Sharma, lap infant), `UM4KDX` (Okafor, unaccompanied minor),
`WC3H3L` (Fontenot, wheelchair assistance), `R2D4C6` (Ramirez, family of five).

## Architecture

```
cli.py                    stdin/stdout loop
   |
   v
Orchestrator              agent loop, tool roundtrips, reset/exit control
   |------------------> Session          in-memory transcript
   |------------------> prompt_loader    persona + policies -> system prompt
   |
   |------------------> LLMProvider (ABC)
   |                       |- AnthropicProvider     Messages API via SDK
   |                       '- OpenRouterProvider    OpenAI-compatible via requests
   |
   '------------------> tools/registry
                           |- get_booking ------> BookingsConnector -> bookings.json
                           |- get_flight_status -> FlightsConnector -> flights.json
                           |- search_flights ---> FlightsConnector -> flights.json
                           '- end_conversation
```

Three boundaries carry the design:

**`LLMProvider`** (`providers/base.py`) is an abstract base class with a single
`chat()` method. Providers translate to and from their own wire format and
return a normalized `ProviderResponse`. `orchestration.py` never imports
provider-specific code.

**The tool registry** (`tools/registry.py`) maps a name to a handler and a JSON
schema via the `@register_tool` decorator. A tool's docstring becomes the
description the model reads, so registration fails if the docstring is missing.

**`LookupResult`** (`connectors/base.py`) is the contract between tools and the
data layer. Connectors return a status plus records; tools call `.to_payload()`
and hand the result to the model. Replacing JSON files with HTTP calls means
rewriting connector internals only.

### One turn, step by step

1. `cli.py` reads a line and calls `Orchestrator.handle_input()`.
2. Exit commands and reset phrases are handled before any LLM call.
3. The text is appended to the `Session` transcript.
4. `_run_turn()` calls `provider.chat()` with the full transcript, all tool
   schemas, and the system prompt.
5. If the response has no tool calls, the text is returned and printed.
6. If it does, the calls are dispatched, results are appended to the transcript,
   and the loop repeats — up to `MAX_TOOL_ROUNDTRIPS` times.
7. `end_conversation` is intercepted before dispatch and resets the session.

Both provider APIs are stateless, so the entire transcript is re-sent on every
call. The system prompt is marked with `cache_control: ephemeral` to reduce the
cost of that repetition.

### State

Everything is in memory and nothing survives a restart. `Session` holds a list
of frozen `Message` dataclasses. The system prompt, tool schemas, and loaded
data files are built once per process — connectors, the policy KB, and the
persona loader are all `@lru_cache(maxsize=1)` singletons, so editing a JSON or
markdown file requires a restart to take effect.

## Project structure

```
cli.py                       entry point, REPL
orchestration.py             agent loop, turn outcomes
session.py                   in-memory transcript
prompt_loader.py             persona + policies -> system prompt

config/
  __init__.py                env loading, constants, file paths
  persona.md                 Sunny's role, tone, and hard rules

providers/
  base.py                    Message/ToolCall/ToolSchema types, LLMProvider ABC
  factory.py                 build_provider(), resolve_model()
  anthropic_provider.py      Anthropic Messages API adapter
  openrouter_provider.py     OpenRouter chat/completions adapter

tools/
  registry.py                @register_tool, get_tool_schemas(), dispatch()
  get_booking.py
  get_flight_status.py
  search_flights.py
  end_conversation.py

connectors/
  base.py                    LookupResult, LookupStatus, JSON loading, date humanizing
  bookings_connector.py      booking lookup by code + last name
  flights_connector.py       flight status and route search

knowledge_base/
  policy_kb.py               read-only policy access
  policies.md                IROPS policy document

mock_data/
  bookings.json              10 bookings covering UMNR, WCHR, INFT, family cases
  flights.json               storm-disruption scenario with a fixed "current time"

tests/                       pytest suite with recorded provider fixtures
```

## Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `get_booking` | `booking_code`, `last_name` | Itinerary, passengers, contact info, segment statuses |
| `get_flight_status` | `flight_number`, `date` | Scheduled times, status, aircraft, seat availability |
| `search_flights` | `origin`, `destination`, `date` (optional) | Non-cancelled future flights on the route |
| `end_conversation` | none | Signals the orchestrator to reset the session |

All data-returning tools pass their records through `humanize_record()`, which
rewrites ISO timestamps into passenger-readable strings such as
`Thursday Jul 9, 2026 6:45PM`. They also append `API_TERMINOLOGY_NOTE` to their
description so the model knows to say "booking code" rather than "PNR" and to
read dates as-is instead of reformatting them.

## Development

```bash
uv run pytest                 # run the suite
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy .                 # type check
```

Ruff is configured at line length 88 targeting Python 3.12, with pycodestyle
errors, pyflakes, isort, pyupgrade, bugbear, simplify, and comprehension rules
enabled. mypy runs close to strict: untyped and incomplete definitions are
rejected, and `warn_return_any` plus `no_implicit_optional` are on. Both are
configured in `pyproject.toml`; there is no separate `ruff.toml` or `mypy.ini`.

There is no CI pipeline and no pre-commit hook, so run these yourself before
committing.

Tests never hit a live API. Provider tests replay recorded JSON from
`tests/fixtures/` to verify both the outbound wire format and the parsing of
responses back into `ProviderResponse`.

## Extending

**Add a tool.** Create a module in `tools/`, define a JSON schema, and decorate
the handler. Write a real docstring — it becomes the model-facing description.
Then add the module to the import list in `tools/__init__.py` so the decorator
runs at import time.

```python
@register_tool("cancel_booking", SCHEMA, extra_description=API_TERMINOLOGY_NOTE)
def cancel_booking(booking_code: str, last_name: str) -> dict[str, Any]:
    """Cancel a confirmed booking and issue a refund to the original payment method."""
    ...
```

**Add a provider.** Subclass `LLMProvider`, implement `chat()`, translate to and
from your API's wire format, and wrap failures in `ProviderError`. Register it
in `providers/factory.py` and add its name to the `ProviderName` literal.

**Use a real API.** Rewrite the connector internals. Take a base URL and
credentials in `__init__` instead of a `Path`, make the HTTP call inside
`find()`, and map failures onto `LookupStatus`. Keep returning `LookupResult`
and nothing above the connector changes. Watch out for three things: set a
timeout, catch network exceptions rather than letting them escape `dispatch()`,
and keep `humanize_record()` on the response so the date-formatting promise in
the tool description stays true.

## Known limitations

This is a demo, and it makes demo-scale tradeoffs:

- `ACTIVE_PROVIDER` is a constant, not an environment variable, so switching
  backends means editing source.
- Both API keys are required at import even if only one provider is used.
- `PolicyKnowledgeBase.search()` ignores its query and returns the whole policy
  document. The signature is retrieval-shaped so it can be replaced, but there
  is no actual retrieval today.
- Reset detection uses substring matching, so a message containing a phrase like
  "something else" can reset the session before the model ever sees it.
- The transcript grows without truncation or summarization and will eventually
  hit the context window.
- Responses are not streamed; each turn blocks until the full reply arrives.
- No structured logging, tracing, or token accounting.
- `FlightsConnector` reads "now" from `meta.current_time` in the JSON file to keep
  the storm scenario reproducible. Real data would need `datetime.now()`.
