import argparse

from runner import run_experiment
from models.ollama_client import DEFENSES


def main():
    parser = argparse.ArgumentParser(description="Collect LLM responses")
    parser.add_argument("--run-id", help="Run ID to resume; omit to start a new run.")
    parser.add_argument("--defense", choices=sorted(DEFENSES), metavar="DEFENSE_MODULE",
                        help="Defense module to apply: " + ", ".join(sorted(DEFENSES)))
    parser.add_argument("--show-prompt", action="store_true",
                        help="Print the messages sent to Ollama for each request.")
    args = parser.parse_args()
    run_experiment(args.run_id, defense_module=args.defense, show_prompt=args.show_prompt)


if __name__ == "__main__":
    main()
