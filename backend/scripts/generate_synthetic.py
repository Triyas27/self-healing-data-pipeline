import argparse

from app.synthetic.generator import FailureMode, generate_batch, to_csv_string


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic order batch")
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--failure-rate", type=float, default=0.2)
    parser.add_argument("--failure-mode", choices=[m.value for m in FailureMode], default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=str, default=None, help="Write CSV to this path instead of stdout")
    args = parser.parse_args()

    mode = FailureMode(args.failure_mode) if args.failure_mode else None
    batch = generate_batch(args.rows, args.failure_rate, failure_mode=mode, seed=args.seed)

    injected_count = sum(1 for f in batch.injected_failures if f is not None)
    print(f"Generated {len(batch.rows)} rows, {injected_count} with an injected failure")

    csv_text = to_csv_string(batch.rows)
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            f.write(csv_text)
        print(f"Wrote CSV to {args.out}")
    else:
        print(csv_text)


if __name__ == "__main__":
    main()
