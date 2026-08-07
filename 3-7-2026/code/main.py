# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

# Add current folder to path to allow track_a & track_b imports
sys.path.append(str(Path(__file__).resolve().parent))

# Reconfigure console output encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def main():
    parser = argparse.ArgumentParser(description="SecurePrep Unified Generation Runner")
    parser.add_argument("--track", choices=["A", "B"], required=True, help="Track to execute (A: Form-driven, B: Scenario-driven)")
    parser.add_argument("--num", type=int, default=2, help="Number of records to generate (default: 2)")
    parser.add_argument("--patch", type=str, help="Profile ID to patch/regenerate (only applies to Track A/form-driven)")
    parser.add_argument("--mode", choices=["default", "register"], default="default", help="Batch mode for Track B (default or register)")
    parser.add_argument("--output", "-o", type=str, help="Custom output dataset filename (e.g., custom_dataset.jsonl)")
    parser.add_argument("--offset", type=int, default=0, help="Start offset index for generation (default: 0)")
    parser.add_argument("--profile-offset", type=int, help="Deterministic starting index offset in the adult profile bank (defaults to 0 for deepseek-3.2, 8263 for glm-5)")
    parser.add_argument("--plan", type=str, help="Path or filename of an existing plan JSON to reuse")
    parser.add_argument("--direct", action="store_true", help="Bypass 9Router and call OpenRouter/third-party API directly using the DEEPSEEKV4FLASH key in .env")

    args = parser.parse_args()

    if args.output:
        import os
        os.environ["SECUREPI_OUT_NAME"] = args.output
    if args.offset is not None:
        import os
        os.environ["SECUREPI_OFFSET"] = str(args.offset)
    if args.profile_offset is not None:
        import os
        os.environ["SECUREPI_PROF_OFFSET"] = str(args.profile_offset)
    if args.plan:
        import os
        os.environ["SECUREPI_PLAN_PATH"] = args.plan
    if args.direct:
        import os
        os.environ["SECUREPI_DIRECT_OPENROUTER"] = "1"

    if args.track == "A":
        import track_a.main as track_a
        if args.patch:
            track_a.patch_profile_in_dataset(args.patch)
        else:
            track_a.run_batch(args.num)
    elif args.track == "B":
        import track_b.main as track_b
        if args.mode == "register":
            docs_per_register = max(1, args.num // 3)
            track_b.run_batch_by_register(docs_per_register)
        else:
            track_b.run_batch(args.num)

if __name__ == "__main__":
    main()
