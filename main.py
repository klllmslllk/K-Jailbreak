import argparse
from pathlib import Path

from config import CSV_PATH

from defenses.registry import AVAILABLE_DEFENSES
from runner import run_experiment


def main():
    parser = argparse.ArgumentParser(description="Collect LLM responses")
    parser.add_argument("--run-id", help="Run ID to resume; omit to start a new run.")
    parser.add_argument("--defense", nargs="+", choices=sorted(AVAILABLE_DEFENSES), metavar="DEFENSE_MODULE",
                        help="Defense modules to apply: " + ", ".join(sorted(AVAILABLE_DEFENSES)))
    parser.add_argument("--show-prompt", action="store_true",
                        help="Print the messages sent to Ollama for each request.")
    parser.add_argument("--dataset", type=Path, default=CSV_PATH, help="CSV dataset with the same columns as data.csv.")
    parser.add_argument("--dataset-type", choices=("attack", "benign"), default="attack")
    args = parser.parse_args()
    run_experiment(args.run_id, defense_module=args.defense, show_prompt=args.show_prompt,
                   dataset_type=args.dataset_type, csv_path=args.dataset)


if __name__ == "__main__":
    main()
