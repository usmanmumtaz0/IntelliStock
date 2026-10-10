"""Score explicit held-out ground-truth/prediction CSVs without touching inventory."""
import argparse
import json

from app.cv.count_evaluation import evaluate_counts, read_counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", required=True)
    parser.add_argument("--predictions", required=True)
    args = parser.parse_args()
    try:
        report = evaluate_counts(read_counts(args.truth), read_counts(args.predictions))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
