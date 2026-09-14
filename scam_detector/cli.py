from __future__ import annotations

import argparse

from scam_detector.classifier import classify_message
from scam_detector.evaluation import evaluate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Scam detection runner")
    parser.add_argument("--message", help="Classify a single message")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate data/raw/dataset.csv")
    parser.add_argument("--dry", type=int, default=0, help="Dry run: evaluate first N rows")
    parser.add_argument("--out", help="Output CSV path for predictions")
    parser.add_argument("--max-examples", type=int, default=1000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.message:
        print(classify_message(args.message))
    elif args.evaluate:
        evaluate_dataset(
            dry=args.dry,
            out_path=args.out,
            max_examples=args.max_examples,
            force=args.force,
        )
    else:
        test_message = "The checkout page is confusing and I could not complete my order."
        print("Parsed result:", classify_message(test_message))


if __name__ == "__main__":
    main()
