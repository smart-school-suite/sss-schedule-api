#!/usr/bin/env python3
"""
Validate test_data JSON files against the API's SchedulingRequest schema.
Run from repo root: python examples/test_data/validate_test_data.py

Reports the first parsing/validation error for each file so you can fix
field names, types, and structure to match the API.
"""
import json
import sys
from pathlib import Path

# Allow importing from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pydantic import ValidationError
from models.schemas import BackendScheduleRequest


def main():
    test_data_dir = Path(__file__).resolve().parent
    json_files = sorted(test_data_dir.rglob("*.json"))
    if not json_files:
        print("No JSON files found under", test_data_dir)
        return

    print("Validating test_data JSON files against BackendScheduleRequest schema.\n")
    ok = 0
    fail = 0
    for path in json_files:
        rel = path.relative_to(test_data_dir)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            BackendScheduleRequest(**data)
            print(f"  OK   {rel}")
            ok += 1
        except ValidationError as e:
            print(f"  FAIL {rel}")
            errs = e.errors()
            for err in errs[:5]:
                loc = ".".join(str(x) for x in err["loc"])
                msg = err.get("msg", "")
                print(f"       {loc}: {msg}")
            if len(errs) > 5:
                print(f"       ... and {len(errs) - 5} more validation errors")
            print()
            fail += 1
        except Exception as e:
            print(f"  FAIL {rel}")
            print(f"       {type(e).__name__}: {e}")
            print()
            fail += 1

    print(f"\nResult: {ok} passed, {fail} failed.")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
