# Skript: scripts/preset_quality_check.py
# Zweck: Prüft alle presets/*.json auf Plausibilität, berechnet Scores und erzeugt Reports.
# Nutzung: python scripts/preset_quality_check.py
# Output: reports/quality_report.json, reports/quality_report.csv

import os
import json
import glob
import csv
from datetime import datetime, timezone

CURRENT_YEAR = datetime.now().year

# Konfiguration: Schwellenwerte und Vertrauensstufen
TRUST = {
    "WB": 1.0,
    "IMF": 1.0,
    "COFER": 1.0,
    "fallback_csv": 0.75,
    "manual_fallback": 0.6,
    "manual": 0.5,
    "unknown": 0.6
}
AUTO_SCORE_MIN = 0
AUTO_SCORE_MAX = 100

# Plausibilitäts-Checks (Regeln)
def check_source(snapshot):
    src = snapshot.get("source")
    if not src:
        return False, "missing_source"
    return True, None

def check_type_and_range(snapshot):
    val = snapshot.get("value")
    ind = snapshot.get("indicator", "")
    if val is None:
        return False, "missing_value"
    if not isinstance(val, (int, float)):
        return False, "non_numeric_value"
    # basic non-negativity for many nominal indicators
    non_negative_inds = ["NY.GDP.MKTP.CD", "NE.IMP.GNFS.CD", "NE.EXP.GNFS.CD", "FI.RES.TOTL"]
    if ind in non_negative_inds and val < 0:
        return False, "negative_value_for_nominal_indicator"
    # percent-like indicators
    percent_inds = ["FP.CPI.TOTL.ZG", "GC.XPN.TOTL.GD.ZS", "DT.DOD.DECT.GN.ZS"]
    if ind in percent_inds and (val < -100 or val > 100):
        return False, "percent_out_of_bounds"
    return True, None

def check_freshness(snapshot, volatile_threshold=3, stable_threshold=10):
    year = snapshot.get("year")
    if not year:
        return False, "missing_year"
    try:
        y = int(year)
    except Exception:
        return False, "invalid_year"
    age = CURRENT_YEAR - y
    ind = snapshot.get("indicator","")
    # treat CPI and FDI as volatile
    volatile_inds = ["FP.CPI.TOTL.ZG", "BX.KLT.DINV.CD.WD"]
    if ind in volatile_inds:
        if age > volatile_threshold:
            return False, "stale_volatile"
    else:
        if age > stable_threshold:
            return False, "stale_stable"
    return True, None

def check_monthly_consistency(snapshot, indicator):
    # If monthly_* present, check monthly*12 approx equals yearly value
    val = snapshot.get("value")
    if val is None:
        return False, "no_yearly_value"
    # find monthly field if exists
    monthly_keys = [k for k in snapshot.keys() if k.startswith("monthly_")]
    if not monthly_keys:
        return True, None
    for mk in monthly_keys:
        mval = snapshot.get(mk)
        if mval is None:
            continue
        # allow relative tolerance 1%
        yearly_from_monthly = mval * 12.0
        if val == 0:
            if abs(yearly_from_monthly) > 1e-6:
                return False, f"monthly_mismatch_{mk}"
        else:
            rel_err = abs(yearly_from_monthly - val) / (abs(val) + 1e-12)
            if rel_err > 0.02:  # 2% tolerance
                return False, f"monthly_mismatch_{mk}"
    return True, None

def check_trade_vs_gdp(preset_snapshot):
    gdp = preset_snapshot.get("NY_GDP_MKTP_CD", {}).get("value")
    exp = preset_snapshot.get("NE_EXP_GNFS_CD", {}).get("value") or 0
    imp = preset_snapshot.get("NE_IMP_GNFS_CD", {}).get("value") or 0
    if gdp and isinstance(gdp, (int,float)) and gdp > 0:
        ratio = (exp + imp) / gdp
        if ratio > 3 or ratio < 0.01:
            return False, ratio
    return True, None

def check_reserves_months(preset_snapshot):
    # reserves_months = reserves / monthly_imports
    res = preset_snapshot.get("FI_RES_TOTL", {}).get("value")
    imp_monthly = preset_snapshot.get("NE_IMP_GNFS_CD", {}).get("value")
    if res is None or imp_monthly is None:
        return True, None
    # if imports are yearly, convert to monthly
    # our presets store yearly imports in NE_IMP_GNFS_CD; monthly_imports_usd may exist
    monthly_imports = preset_snapshot.get("NE_IMP_GNFS_CD", {}).get("monthly_imports_usd")
    if monthly_imports is None:
        # assume yearly -> monthly
        monthly_imports = imp_monthly / 12.0 if imp_monthly else None
    if monthly_imports and monthly_imports > 0:
        months = res / monthly_imports
        if months < 0.5 or months > 60:
            return False, months
    return True, None

# Scoring function per snapshot
def quality_score(snapshot):
    score = 100.0
    src = snapshot.get("source","unknown")
    trust = TRUST.get(src, TRUST["unknown"])
    score *= trust
    # completeness penalty
    if snapshot.get("value") is None:
        score -= 40
    # freshness penalty
    year = snapshot.get("year")
    if year:
        try:
            age = CURRENT_YEAR - int(year)
            if age > 3:
                score -= min(30, (age-3)*5)
        except Exception:
            score -= 10
    # type/range penalties
    ok, reason = check_type_and_range(snapshot)
    if not ok:
        score -= 30
    # monthly consistency
    ok, reason = check_monthly_consistency(snapshot, snapshot.get("indicator",""))
    if not ok:
        score -= 10
    return max(AUTO_SCORE_MIN, min(AUTO_SCORE_MAX, int(score)))

# Evaluate a single preset file
def evaluate_preset(path):
    data = json.load(open(path, "r", encoding="utf-8"))
    snapshots = data.get("indicator_snapshot", {})
    per_indicator = {}
    failed_rules = {}
    scores = {}
    for key, snap in snapshots.items():
        # normalize indicator code if missing
        ind = snap.get("indicator") or key.replace("_", ".")
        snap["indicator"] = ind
        issues = []
        # source check
        ok, reason = check_source(snap)
        if not ok:
            issues.append(reason)
        # type/range
        ok, reason = check_type_and_range(snap)
        if not ok:
            issues.append(reason)
        # freshness
        ok, reason = check_freshness(snap)
        if not ok:
            issues.append(reason)
        # monthly consistency
        ok, reason = check_monthly_consistency(snap, ind)
        if not ok:
            issues.append(reason)
        per_indicator[key] = {
            "indicator": ind,
            "value": snap.get("value"),
            "year": snap.get("year"),
            "source": snap.get("source"),
            "issues": issues
        }
        scores[key] = quality_score(snap)
        if issues:
            failed_rules[key] = issues

    # cross-indicator checks
    trade_ok, trade_info = check_trade_vs_gdp(snapshots)
    reserves_ok, reserves_info = check_reserves_months(snapshots)
    cross_issues = {}
    if not trade_ok:
        cross_issues["trade_vs_gdp"] = trade_info
    if not reserves_ok:
        cross_issues["reserves_months"] = reserves_info

    overall_score = int(sum(scores.values()) / max(1, len(scores)))
    status = "ready_for_analysis" if overall_score >= 85 else ("needs_review" if overall_score >= 60 else "blocked")

    report = {
        "preset_file": path,
        "country": data.get("metadata", {}).get("country_info", {}).get("alpha2"),
        "created_at": data.get("metadata", {}).get("created_at"),
        "indicator_count": len(per_indicator),
        "per_indicator": per_indicator,
        "failed_rules": failed_rules,
        "cross_issues": cross_issues,
        "scores": scores,
        "overall_score": overall_score,
        "status": status
    }
    return report

def main():
    os.makedirs("reports", exist_ok=True)
    preset_files = sorted(glob.glob("presets/preset_*.json"))
    reports = []
    summary = {"total_presets": len(preset_files), "by_status": {}, "avg_score": None}
    total_score = 0
    for p in preset_files:
        try:
            r = evaluate_preset(p)
            reports.append(r)
            total_score += r["overall_score"]
            summary["by_status"].setdefault(r["status"], 0)
            summary["by_status"][r["status"]] += 1
            print(f"Evaluated {p}: score={r['overall_score']} status={r['status']}")
        except Exception as e:
            print(f"Error evaluating {p}: {e}")

    if reports:
        summary["avg_score"] = int(total_score / len(reports))
    else:
        summary["avg_score"] = 0

    out_json = {"generated_at": datetime.now(timezone.utc).isoformat(), "summary": summary, "reports": reports}
    with open("reports/quality_report.json", "w", encoding="utf-8") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)

    # CSV summary: one row per preset
    csv_path = "reports/quality_report.csv"
    with open(csv_path, "w", newline='', encoding="utf-8") as csvfile:
        fieldnames = ["preset_file", "country", "overall_score", "status", "indicator_count", "failed_indicators"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in reports:
            failed = ";".join(sorted(r["failed_rules"].keys()))
            writer.writerow({
                "preset_file": r["preset_file"],
                "country": r.get("country"),
                "overall_score": r["overall_score"],
                "status": r["status"],
                "indicator_count": r["indicator_count"],
                "failed_indicators": failed
            })

    print("Wrote reports/quality_report.json and reports/quality_report.csv")
    print("Summary:", summary)

if __name__ == "__main__":
    main()
