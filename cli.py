"""Interactive CLI for the Meridian Airlines customer service agent."""

import sys

from config import ACTIVE_PROVIDER, WELCOME_MESSAGE
from orchestration import Orchestrator, TurnOutcome
from providers import build_provider, resolve_model

BANNER = """SkyHop Airlines — customer service assistant
Provider: {provider} ({model})

Type your question, or "exit" to quit.
"""


def _print_reply(reply: str | None) -> None:
    if reply:
        print(f"\nSunny: {reply}\n")


def main() -> int:
    provider_name = ACTIVE_PROVIDER
    model = resolve_model(provider_name)
    orchestrator = Orchestrator(build_provider(provider_name), model)

    print(BANNER.format(provider=provider_name, model=model))
    _print_reply(WELCOME_MESSAGE)

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0

        if not user_input:
            continue

        result = orchestrator.handle_input(user_input)
        _print_reply(result.reply)

        if result.outcome is TurnOutcome.EXIT:
            print("Goodbye.")
            return 0
        if result.outcome is TurnOutcome.RESET:
            print("— new conversation —\n")


if __name__ == "__main__":
    sys.exit(main())
