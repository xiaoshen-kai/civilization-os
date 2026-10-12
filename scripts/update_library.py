#!/usr/bin/env python3
"""Check or explicitly refresh model reverse links and the library manifest."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/"skills"/"civilization-os"
sys.path.insert(0,str(SKILL/"scripts"))
import catalog

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write",action="store_true",help="Refresh only model.case_ids and manifest counts.")
    a=p.parse_args()
    try:
        db=catalog.load_database(SKILL)
        reverse={x["id"]:[] for x in db["models"]}
        for case in db["cases"]:
            for mid in case["model_ids"]:
                if mid not in reverse:
                    raise ValueError("Case refers to an unknown model")
                reverse[mid].append(case["id"])
        errors=[]
        for filename in ("models-01.json","models-02.json"):
            path=SKILL/"references"/filename
            rows=json.loads(path.read_text(encoding="utf-8-sig"))
            for row in rows:
                expected=sorted(reverse[row["id"]],key=lambda s:int(s[1:]))
                if a.write:
                    row["case_ids"]=expected
                elif row["case_ids"]!=expected:
                    errors.append(row["id"]+": stale reverse links")
            if a.write:
                path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        path=SKILL/"references"/"manifest.json"
        if a.write:
            old=json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}
            manifest={"schema_version":"2.0","library_version":old.get("library_version","2.0.0"),
                      "checked_on":old.get("checked_on","2026-10-12"),
                      "counts":catalog.database_counts(db)}
            path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        else:
            manifest=json.loads(path.read_text(encoding="utf-8-sig"))
            errors.extend(catalog.check_manifest(manifest,db))
        if errors:
            print("\n".join(errors[:20])); return 1
        print("Reverse links and manifest: "+("refreshed." if a.write else "match."))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("library error: "+type(e).__name__,file=sys.stderr); return 1
if __name__=="__main__":
    raise SystemExit(main())
