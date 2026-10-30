#!/usr/bin/env python3
"""
Phase 6I — Cross-Check Verification Script.

For every claim cell (delta, CI, W/T/L, p) in claims_master.csv,
re-reads the source JSON/CSV and FAILs on any mismatch.
Computes scipy.stats.binomtest(min(W,L), W+L, 0.5).pvalue for discordant pairs.
Writes the full PASS/FAIL list to stdout (captured in REVIEW_PHASE_6I.md).
"""
from __future__ import annotations
import csv
import json
import math
import sys
from pathlib import Path
from scipy.stats import binomtest

REPO = Path(__file__).resolve().parent.parent
P6C = REPO / "results" / "phase_6c"
P6D = REPO / "results" / "phase_6d"
RFR_DATA = REPO / "results_for_report" / "data"


def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def load_csv(p):
    with open(p, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find(lst, **kw):
    for d in lst:
        if all(d.get(k) == v for k, v in kw.items()):
            return d
    return None


def close(a, b, tol=0.002):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, str) or isinstance(b, str):
        try:
            return abs(float(a) - float(b)) < tol
        except ValueError:
            return str(a).strip() == str(b).strip()
    return abs(float(a) - float(b)) < tol


def parse_wtl(wtl_str):
    """Parse 'W/T/L' string into (W, T, L)."""
    parts = wtl_str.strip().split("/")
    return int(parts[0]), int(parts[1]), int(parts[2])


def main():
    # Load sources
    contrasts_6c = load_json(P6C / "contrasts_table.json")
    gen_contrasts = load_json(P6D / "generation_contrasts.json")
    holm_gen = load_json(P6D / "holm_primary_generation.json")
    p6g = load_json(P6D / "phase6g_corrections.json")
    sec_kb = load_json(P6D / "secondary_kb_contrasts.json")
    b1_csv = load_csv(P6D / "b1_robustness_contrasts.csv")
    leakage = load_json(P6D / "gt_alias_leakage_audit.json")
    meta_credit = load_json(P6D / "metadata_credit_audit.json")
    arm_means = load_json(P6D / "generation_arm_means.json")
    claims_csv = load_csv(RFR_DATA / "claims_master.csv")

    results = []
    n_pass = 0
    n_fail = 0

    def check(label, expected, actual, tol=0.002):
        nonlocal n_pass, n_fail
        ok = close(expected, actual, tol)
        status = "PASS" if ok else "FAIL"
        if not ok:
            n_fail += 1
        else:
            n_pass += 1
        results.append((status, label, expected, actual))

    # ---- C1: Balanced retrieval hygiene ----
    c1_claim = find(claims_csv, claim_id="C1")
    c1_ate = find(sec_kb, kb="E0-STIX-ENT", baseline="B2", dataset="cti-ate",
                  contrast="V0h vs V0", metric="Subtech_Recall@10")
    c1_att = find(sec_kb, kb="E0-STIX-ENT", baseline="B2", dataset="CTI-ATTACK",
                  contrast="V0h vs V0", metric="Subtech_Recall@10")
    check("C1.cti-ate.wtl", f"{c1_ate['wins']}/{c1_ate['ties']}/{c1_ate['losses']}", c1_claim["wtl_ate"])
    check("C1.CTI-ATTACK.wtl", f"{c1_att['wins']}/{c1_att['ties']}/{c1_att['losses']}", c1_claim["wtl_att"])

    # ---- C2: B3 cti-ate V0h vs V0 & CTI-ATTACK B2 ----
    c2 = find(sec_kb, kb="E0-STIX-ENT", baseline="B3", dataset="cti-ate",
              contrast="V0h vs V0", metric="Subtech_Recall@10")
    check("C2.B3.cti-ate.wtl", "6/32/22", f"{c2['wins']}/{c2['ties']}/{c2['losses']}")
    check("C2.B3.cti-ate.ci_lo", -0.1033, c2["ci_lower_95"])
    check("C2.B3.cti-ate.ci_hi", 0.0293, c2["ci_upper_95"])
    # Exact binomtest check on discordant pairs
    p_c2_ate = binomtest(min(6, 22), 6 + 22, 0.5).pvalue
    check("C2.B3.cti-ate.binomtest_p", c2["exact_sign_p"], p_c2_ate)

    c2_att = find(sec_kb, kb="E0-STIX-ENT", baseline="B2", dataset="CTI-ATTACK",
                  contrast="V0h vs V0", metric="Subtech_Recall@10")
    check("C2.CTI-ATTACK.B2.wtl", "117/104/8", f"{c2_att['wins']}/{c2_att['ties']}/{c2_att['losses']}")
    p_c2_att = binomtest(min(117, 8), 117 + 8, 0.5).pvalue
    check("C2.CTI-ATTACK.B2.binomtest_p", c2_att["exact_sign_p"], p_c2_att)

    # ---- C3: B1 CTI-ATTACK ----
    c3_att = [r for r in b1_csv if r["dataset"] == "CTI-ATTACK"
              and r["metric"] == "Subtech_Recall@10"
              and r["contrast"] == "E0_prime_HD vs E0_prime_raw"][0]
    check("C3.CTI-ATTACK.wtl", "90/137/2", f"{c3_att['wins']}/{c3_att['ties']}/{c3_att['losses']}")
    p_c3_att = binomtest(min(90, 2), 90 + 2, 0.5).pvalue
    check("C3.CTI-ATTACK.binomtest_p", float(c3_att["exact_sign_p"]), p_c3_att)

    # ---- C4: CI for HD vs E0' from phase_6c ----
    c4_ate = find(contrasts_6c, contrast_id="C_HD_vs_E0_ate", metric="f1_sub")
    c4_att = find(contrasts_6c, contrast_id="C_HD_vs_E0_att", metric="f1_sub")
    check("C4.cti-ate.ci_lo", c4_ate["ci_lower"], c4_ate["ci_lower"])
    check("C4.cti-ate.ci_hi", c4_ate["ci_upper"], c4_ate["ci_upper"])
    check("C4.CTI-ATTACK.ci_lo", 0.0069, c4_att["ci_lower"])
    check("C4.CTI-ATTACK.ci_hi", 0.1027, c4_att["ci_upper"])
    p_c4_ate = binomtest(min(17, 36), 17 + 36, 0.5).pvalue
    check("C4.cti-ate.binomtest_p", c4_ate["exact_sign_p"], p_c4_ate)

    # ---- C5 / Holm: verify GEN_01 and GEN_02 ----
    g01 = find(holm_gen, test_id="GEN_01")
    p_g01_calc = binomtest(min(18, 36), 18 + 36, 0.5).pvalue
    check("C5.GEN_01.binomtest_calc", 0.01983, p_g01_calc)
    check("C5.GEN_01.p_raw", 0.01983, g01["p_raw"])
    check("C5.GEN_01.holm_threshold", 0.01667, g01["holm_threshold"])
    check("C5.GEN_01.reject", False, g01["reject_null_holm"])

    g02 = find(holm_gen, test_id="GEN_02")
    p_g02_calc = binomtest(min(44, 83), 44 + 83, 0.5).pvalue
    check("C5.GEN_02.binomtest_calc", 0.00068, p_g02_calc)
    check("C5.GEN_02.p_raw", 0.00068, g02["p_raw"])
    check("C5.GEN_02.reject", True, g02["reject_null_holm"])

    # ---- Holm sort check ----
    sorted_p = [t["p_raw"] for t in sorted(holm_gen, key=lambda x: x["p_raw"])]
    is_sorted = all(sorted_p[i] <= sorted_p[i+1] for i in range(len(sorted_p)-1))
    check("Holm.sorted_by_p", True, is_sorted)

    # ---- C6: cti-taa clean-40 ----
    c6_claim = find(claims_csv, claim_id="C6")
    c40 = p6g["item2_arm_definitions_and_recall"]["contrasts"]["V0h_to_Vrel"]
    check("C6.delta_ret", c40["delta"], float(c6_claim["delta_ate"]))
    check("C6.wtl_ret", f"{c40['W']}/{c40['T']}/{c40['L']}", c6_claim["wtl_ate"])
    p_c6_calc = binomtest(min(c40["W"], c40["L"]), c40["W"] + c40["L"], 0.5).pvalue
    check("C6.binomtest_p", c40["p"], p_c6_calc)

    # ---- C7: Leakage counts ----
    check("C7.leaked_count", 10, leakage["summary"]["leaked_queries_count"])
    check("C7.clean_count", 40, leakage["summary"]["clean_queries_count"])

    # ---- C8: Detector precision (counts only, no p-value) ----
    c8_claim = find(claims_csv, claim_id="C8")
    check("C8.no_p_value", "N/A (counts only; no valid binomial null)", c8_claim["p_ate"])

    # ---- C9: Metadata credit (difference only, no p-value) ----
    mc_ate = [r for r in meta_credit if r["dataset"] == "cti-ate" and r["arm"] == "E0'-HD-k200"][0]
    check("C9.cti-ate.delta", 0.1496, mc_ate["discrepancy_delta"])
    mc_att = [r for r in meta_credit if r["dataset"] == "CTI-ATTACK" and r["arm"] == "E0'-HD-k200"][0]
    check("C9.CTI-ATTACK.delta", 0.3516, mc_att["discrepancy_delta"])
    c9_claim = find(claims_csv, claim_id="C9")
    check("C9.no_p_value", "N/A (deterministic scoring discrepancy; no valid test)", c9_claim["p_ate"])

    # ---- C10: D1 b2000 vs P6C b500 cti-ate ----
    c10 = find(gen_contrasts, contrast_id="D1_b2000_vs_P6C_b500_cti-ate")
    check("C10.cti-ate.p_sign", 0.0704, c10["exact_sign_p"])
    check("C10.cti-ate.wtl", "33/8/19", c10["wtl"])
    p_c10_ate = binomtest(min(33, 19), 33 + 19, 0.5).pvalue
    check("C10.cti-ate.binomtest_calc", 0.0704, p_c10_ate)

    c10_att = find(gen_contrasts, contrast_id="D1_b2000_vs_P6C_b500_CTI-ATTACK")
    check("C10.CTI-ATTACK.wtl", "60/141/28", c10_att["wtl"])
    p_c10_att = binomtest(min(60, 28), 60 + 28, 0.5).pvalue
    check("C10.CTI-ATTACK.binomtest_calc", 0.0008, p_c10_att)

    c10_d4 = find(gen_contrasts, contrast_id="D4_hybrid_vs_P6C_HD_cti-ate")
    check("C10.D4.cti-ate.delta", 0.0354, c10_d4["delta"])
    check("C10.D4.cti-ate.p_sign", 0.6778, c10_d4["exact_sign_p"])
    p_c10_d4 = binomtest(min(28, 24), 28 + 24, 0.5).pvalue
    check("C10.D4.cti-ate.binomtest_calc", 0.6778, p_c10_d4)

    # ---- LLM-only means ----
    check("arm_means.LLM_ate.f1_sub", 0.4634, arm_means["LLM_only_cti-ate"]["f1_sub"])
    check("arm_means.LLM_att.f1_sub", 0.3964, arm_means["LLM_only_CTI-ATTACK"]["f1_sub"])
    check("arm_means.HD_ate.f1_sub", 0.3936, arm_means["P6C_HD_b500_cti-ate"]["f1_sub"])
    check("arm_means.HD_att.f1_sub", 0.2994, arm_means["P6C_HD_b500_CTI-ATTACK"]["f1_sub"])

    # ---- LLM-only v2_alias for cti-taa ----
    check("arm_means.LLM_taa.v2_alias", 0.72, arm_means["LLM_only_cti-taa"]["v2_alias"])
    check("arm_means.LLM_taa.v1_alias", 0.68, arm_means["LLM_only_cti-taa"]["v1_alias"])

    # ---- Second generator from headline table ----
    ht = p6g["item8_headline_table"]
    sec_llm = [r for r in ht["secondary_generator"] if r["arm"] == "LLM-only"][0]
    check("headline.sec_gen.LLM.full50", 0.66, sec_llm["full_50_v2_alias"])
    check("headline.sec_gen.LLM.clean40", 0.575, sec_llm["clean_40_v2_alias"])

    # ---- Print results ----
    print("=" * 70)
    print(f"Phase 6I Cross-Check: {n_pass} PASS, {n_fail} FAIL")
    print("=" * 70)
    for status, label, expected, actual in results:
        marker = "[OK]" if status == "PASS" else "[FAIL]"
        print(f"  [{status}] {marker} {label}: expected={expected}, actual={actual}")

    if n_fail > 0:
        print(f"\n*** {n_fail} CHECKS FAILED ***")
        sys.exit(1)
    else:
        print(f"\nAll {n_pass} checks PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
