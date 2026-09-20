#!/usr/bin/env python3
"""Score source-grounded answer values and cited source IDs; not free-form factuality."""
import argparse
import json
from pathlib import Path


def evaluate(cases, answers):
    ids = [a["id"] for a in answers]
    expected_ids = {c["id"] for c in cases}
    if len(ids) != len(set(ids)) or set(ids) - expected_ids:
        raise ValueError("duplicate or unknown answer IDs")
    indexed = {a["id"]: a for a in answers}
    rows = []
    for case in cases:
        answer = indexed.get(case["id"], {})
        expected = case["expected"]
        same_value = "value" in answer and json.dumps(answer["value"], sort_keys=True) == json.dumps(expected["value"], sort_keys=True)
        citations = answer.get("evidence_ids", [])
        cited = isinstance(citations, list) and all(isinstance(x, str) for x in citations) and set(citations) == set(expected["evidence_ids"])
        rows.append({"id":case["id"],"value_correct":same_value,"citations_correct":cited,"pass":same_value and cited})
    return {"scope":"synthetic_source_grounded_values_and_citations", "freeform_explanation":"not_automatically_scored",
            "passed":sum(r["pass"] for r in rows),"total":len(rows),"cases":rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path)
    parser.add_argument("--cases", type=Path, default=Path(__file__).resolve().parents[1]/"benchmarks/answer-cases.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(json.loads(args.cases.read_text())["cases"], json.loads(args.answers.read_text()))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    text = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
    return 0 if report["passed"] == report["total"] else 2


if __name__ == '__main__':
    raise SystemExit(main())
