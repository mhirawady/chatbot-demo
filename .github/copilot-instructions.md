# Copilot Instructions

## Project overview
This is an extensible AI agent chatbot demo. It uses a pluggable LLM
provider (Anthropic direct, or OpenRouter), a decorator-based tool
registry, and mock data connectors (rebooking policy KB + mock API JSON).
Sessions are intentionally stateless — no conversation persistence.

## Architecture rules
- Keep `orchestration.py` provider-agnostic — it must not import or
  reference Anthropic or OpenRouter specifics directly.
- All providers implement the `LLMProvider` abstract interface
  (`chat(messages, tools, system, model)`), returning a normalized
  response shape. Provider-specific request/response translation stays
  inside that provider's own adapter file.
- New tools are added via `@register_tool(name, schema)` in `tools/`.
  Don't hand-wire tool dispatch elsewhere.
- Persona/hardening text lives in `config/persona.md`, loaded via
  `prompt_loader.py`. Don't hardcode prompt strings in orchestration code.
- Data connectors (knowledge base, mock API) sit behind an interface
  (e.g. `PolicyKnowledgeBase.search()`); callers must not depend on
  the underlying storage (file, JSON, future real API).

## General Python style
- Follow PEP 8. This repo uses Ruff for linting and formatting
  (`ruff check`, `ruff format`) — don't hand-format against its rules.
- All public functions and methods need type hints; run `mypy` (or
  rely on Pyright via the VS Code Python extension) before committing.
- Prefer dataclasses or Pydantic models over raw dicts for structured
  data (tool schemas, messages, config) — avoid "stringly typed" or
  loosely-shaped dict-passing between modules.
- Use explicit imports; avoid wildcard imports (`from x import *`).
- Keep functions small and single-purpose; extract helpers rather than
  deeply nesting logic.
- Use f-strings for string formatting, not `%` or `.format()`.
- Raise specific exceptions with clear messages; avoid bare `except:`.
- Use context managers (`with`) for resources (files, network clients)
  rather than manual open/close.
- Prefer `pathlib.Path` over raw string path manipulation.
- Write docstrings for public modules, classes, and functions —
  summarize purpose, not implementation detail.

## Security basics
- Never hardcode API keys or secrets; read from environment variables
  or a local `.env` (excluded via `.gitignore`).
- Validate/sanitize any external input before it reaches a tool
  function, especially anything that will be interpolated into a
  request or query.

## Testing
- New tools need at least one test verifying the schema and a mocked
  call — don't hit live provider APIs in tests.
- Provider adapters should be tested against fixture responses, not
  live calls.
- Use `pytest`; prefer fixtures over duplicated setup code.

## Things to avoid
- Don't add session/conversation persistence — this demo is
  intentionally stateless per session.
- Don't assume prompt caching behaves identically across providers —
  it's Anthropic/OpenRouter-specific (via `cache_control`), not
  universal; don't add caching logic to provider-agnostic code.
- Don't introduce a dependency to solve something the standard library
  already handles well.
