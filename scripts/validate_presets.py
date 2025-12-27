#!/usr/bin/env python3
# coding: utf-8
"""
validate_presets.py
Validiert presets/preset_*.json gegen ein JSON Schema und führt Cross‑Checks aus.
Bietet:
 - run_validation(presets_dir, schema_path, out_dir) -> dict
 - CLI mit argparse (--presets, --schema, --out)
Exitcodes (CLI):
 - 0 : alle Presets ready_for_analysis
 - 2 : mindestens ein Preset needs_review
 - 3 : JSON/Schema Fehler oder JSON‑Ladefehler
"""
from __future__ import annotations
import os
import json
import glob
import csv
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

try:
    from jsonschema import Draft7Validator, ValidationError
except Exception:
    raise RuntimeError("jsonschema fehlt. Installiere mit: pip install jsonschema")

# --- Default schema path if not provided externally ---
DEFAULT_SCHEMA_PATH = "scripts/preset_schema.json"

# --- Cross-check helpers (angepasst) ---
def check_trade_vs_gdp(snapshots: Dict[str, Dict[str, Any]]) -> Tuple[bool, Any]:
    gdp = snapshots.get("NY_GDP_MKTP_CD", {}).get("value")
    exp = snapshots.get("NE_EXP_GNFS_CD", {}).get("value") or 0
    imp = snapshots.get("NE_IMP_GNFS_CD", {}).get("value") or 0
    try:
        if gdp and isinstance(gdp, (int, float)) and gdp > 0:
            ratio = (exp + imp) / gdp
            if ratio > 3 or ratio < 0.01:
                return False, round(ratio, 6)
    except Exception as e:
        return False, str(e)
    return True, None

def check_reserves_months(snapshots: Dict[str, Dict[str, Any]]) -> Tuple[bool, Any]:
    """
    Prüft Reserven in Monaten.
    - Wenn FI_RES_TOTL_MO vorhanden: prüfe direkt (0.5 - 60 Monate).
    - Sonst, wenn FI_RES_TOTL (USD) vorhanden: berechne months = reserves_usd / monthly_imports_usd.
    - Wenn keine relevanten Daten vorhanden: OK.
    """
    # Prefer explicit months indicator
    months_val = snapshots.get("FI_RES_TOTL_MO", {}).get("value")
    # If FI_RES_TOTL (USD) exists, compute months = reserves_usd / monthly_imports_usd
    reserves_usd = snapshots.get("FI_RES_TOTL", {}).get("value")
    imp_yearly = snapshots.get("NE_IMP_GNFS_CD", {}).get("value")

    # If explicit months provided, validate directly
    if months_val is not None:
        try:
            months = float(months_val)
        except Exception:
            return False, "invalid_months_value"
        if months < 0.5 or months > 60:
            return False, round(months, 6)
        return True, None

    # Otherwise try to compute from reserves in USD
    if reserves_usd is None:
        return True, None  # nothing to check

    monthly_imports = snapshots.get("NE_IMP_GNFS_CD", {}).get("monthly_imports_usd")
    if monthly_imports is None and imp_yearly is not None:
        monthly_imports = imp_yearly / 12.0 if imp_yearly else None

    if monthly_imports and monthly_imports > 0:
        months = reserves_usd / monthly_imports
        if months < 0.5 or months > 60:
            return False, round(months, 6)
    return True, None

# --- Core function ---
def run_validation(presets_dir: str = "presets",
                   schema_path: str = DEFAULT_SCHEMA_PATH,
                   out_dir: str = "reports") -> Dict[str, Any]:
    """
    Validiert alle presets/preset_*.json im Verzeichnis presets_dir gegen schema_path.
    Schreibt reports/validation_report.json und reports/validation_report.csv in out_dir.
    Gibt ein Summary‑Dict zurück.
    """
    if not os.path.isdir(presets_dir):
        raise FileNotFoundError(f"Presets directory not found: {presets_dir}")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    validator = Draft7Validator(schema)
    preset_files = sorted(glob.glob(os.path.join(presets_dir, "preset_*.json")))

    reports: List[Dict[str, Any]] = []
    summary = {'total_presets': len(preset_files), 'by_status': {}, 'validated_at': datetime.now(timezone.utc).isoformat()}

    CURRENT_YEAR = datetime.now(timezone.utc).year

    for p in preset_files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            reports.append({
                'preset_file': p,
                'country': None,
                'errors': [{'type': 'json_load', 'message': str(e)}],
                'status': 'json_error',
                'indicator_count': 0
            })
            summary['by_status'].setdefault('json_error', 0)
            summary['by_status']['json_error'] += 1
            continue

        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # Schema validation
        for err in sorted(validator.iter_errors(data), key=lambda e: e.path):
            path = '.'.join([str(x) for x in err.path]) if err.path else ''
            errors.append({'type': 'schema', 'path': path, 'message': err.message})

        snapshots = data.get('indicator_snapshot', {})

        # Cross checks
        trade_ok, trade_info = check_trade_vs_gdp(snapshots)
        if not trade_ok:
            errors.append({'type': 'cross_check', 'check': 'trade_vs_gdp', 'info': trade_info})
        reserves_ok, reserves_info = check_reserves_months(snapshots)
        if not reserves_ok:
            # reserves_months treated as warning by default; promote to error only if policy requires
            warnings.append({'type': 'cross_check', 'check': 'reserves_months', 'info': reserves_info})

        # Freshness/stale detection
        stale: List[str] = []
        volatile_inds = ['FP.CPI.TOTL.ZG', 'BX.KLT.DINV.CD.WD']
        for key, snap in snapshots.items():
            year = snap.get('year')
            if year is None:
                continue
            try:
                y = int(year)
            except Exception:
                errors.append({'type': 'schema', 'path': f'indicator_snapshot.{key}.year', 'message': 'invalid_year_format'})
                continue
            age = CURRENT_YEAR - y
            ind_code = snap.get('indicator', '')
            if ind_code in volatile_inds:
                if age > 3:
                    stale.append(key)
            else:
                if age > 10:
                    stale.append(key)
        if stale:
            # stale wird als Warnung, nicht als blockierender Fehler, aufgenommen
            warnings.append({'type': 'stale', 'indicators': stale})

        # Determine status: errors => needs_review; warnings alone => ready_for_analysis (but reported)
        if errors:
            status = 'needs_review'
        else:
            status = 'ready_for_analysis'

        combined = errors + warnings
        reports.append({
            'preset_file': p,
            'country': data.get('metadata', {}).get('country_info', {}).get('alpha2'),
            'errors': combined,
            'status': status,
            'indicator_count': len(snapshots)
        })
        summary['by_status'].setdefault(status, 0)
        summary['by_status'][status] += 1

    # Write outputs
    os.makedirs(out_dir, exist_ok=True)
    out = {'generated_at': datetime.now(timezone.utc).isoformat(), 'summary': summary, 'reports': reports}
    json_path = os.path.join(out_dir, 'validation_report.json')
    csv_path = os.path.join(out_dir, 'validation_report.csv')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['preset_file', 'country', 'status', 'indicator_count', 'error_types']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in reports:
            types = ';'.join(sorted(set([e['type'] for e in r.get('errors', [])])))
            writer.writerow({
                'preset_file': r['preset_file'],
                'country': r.get('country'),
                'status': r['status'],
                'indicator_count': r['indicator_count'],
                'error_types': types
            })

    return {'json_report': json_path, 'csv_report': csv_path, 'summary': summary, 'reports': reports}

# --- CLI wrapper ---
def _cli():
    parser = argparse.ArgumentParser(description="Validate presets/preset_*.json against a JSON schema and run cross-checks.")
    parser.add_argument("--presets", "-p", default="presets", help="Presets directory (default: presets)")
    parser.add_argument("--schema", "-s", default=DEFAULT_SCHEMA_PATH, help="Path to JSON schema (default: scripts/preset_schema.json)")
    parser.add_argument("--out", "-o", default="reports", help="Output reports directory (default: reports)")
    args = parser.parse_args()

    try:
        result = run_validation(presets_dir=args.presets, schema_path=args.schema, out_dir=args.out)
    except FileNotFoundError as e:
        print("ERROR:", e)
        raise SystemExit(3)
    except Exception as e:
        print("ERROR during validation:", e)
        raise SystemExit(3)

    summary = result.get('summary', {})
    by_status = summary.get('by_status', {})
    total = summary.get('total_presets', 0)
    ready = by_status.get('ready_for_analysis', 0)
    needs = by_status.get('needs_review', 0)
    json_report = result.get('json_report')
    csv_report = result.get('csv_report')

    print(f"Validated {total} presets. ready_for_analysis={ready}, needs_review={needs}")
    print(f"Reports written: {json_report}, {csv_report}")

    # Exit codes: 0 OK, 2 needs_review present, 3 errors (handled above)
    if needs > 0:
        raise SystemExit(2)
    raise SystemExit(0)

if __name__ == "__main__":
    _cli()
