# Phase 5 Plain List of Contrasts (Numbers Only)

## Summary of Statistical Decisions

### A. Contrasts that Improved Statistically Significantly (Post-Hoc Round 2)
1. **P3_03** (cti-taa B2, Object-Level Recall@10): Vrel vs V0h
   - Treatment Mean: 0.3200, Control Mean: 0.1400
   - Delta: +0.1800 (95% Bootstrap CI [+0.0600, +0.3000])
   - W/T/L: 10/39/1, p_exact = 0.0117, p_boot = 0.0054 (Holm critical alpha = 0.00625)
   - Decision: Statistically significant increase under Holm step-down.

2. **P3_11** (cti-taa B2, Secondary Text-Inclusive Recall@10): Vrel vs V0h
   - Treatment Mean: 0.5000, Control Mean: 0.3000
   - Delta: +0.2000 (95% Bootstrap CI [+0.0800, +0.3200])
   - W/T/L: 11/38/1, p_exact = 0.0063, p_boot = 0.0020 (Holm critical alpha = 0.00625)
   - Decision: Statistically significant increase under Holm step-down.

3. **P3_12** (cti-taa B2, Secondary Text-Inclusive MRR): Vrel vs V0h
   - Treatment Mean: 0.2931, Control Mean: 0.1455
   - Delta: +0.1475 (95% Bootstrap CI [+0.0446, +0.2502])
   - W/T/L: 19/29/2, p_exact = 0.0002, p_boot = 0.0048 (Holm critical alpha = 0.00714)
   - Decision: Statistically significant increase under Holm step-down.

4. **Hygiene Effect Alone** (E0' HD vs E0' Raw):
   - cti-ate B2: HD = 0.3061 vs Raw = 0.1514 (Delta = +0.1547, 95% CI [+0.0956, +0.2184], p < 0.0001, W/T/L: 44/4/12)
   - cti-ate B3: HD = 0.3096 vs Raw = 0.2052 (Delta = +0.1044, 95% CI [+0.0385, +0.1750], p = 0.0032, W/T/L: 36/7/17)
   - CTI-ATTACK B2: HD = 0.6401 vs Raw = 0.2216 (Delta = +0.4185, 95% CI [+0.3537, +0.4844], p < 0.0001, W/T/L: 122/97/10)
   - Decision: Statistically significant increase across all datasets.

### B. Contrasts that Decreased Statistically Significantly (Control Arms Maintained Advantage)
1. **P4_01** (cti-ate B2, Mean Binding Recall): E1a vs E0'-TECH
   - Treatment Mean: 0.2053, Control Mean: 0.2973
   - Delta: -0.0920 (95% Bootstrap CI [-0.1491, -0.0366]), p = 0.0010 (Holm alpha = 0.01667)
   - Decision: Significant decrease (control E0'-TECH is superior).

2. **P4_02** (cti-ate B2, Mean Binding Recall): E1-MIXED vs E0'
   - Treatment Mean: 0.2124, Control Mean: 0.3061
   - Delta: -0.0936 (95% Bootstrap CI [-0.1479, -0.0407]), p = 0.0006 (Holm alpha = 0.01250)
   - Decision: Significant decrease (control E0' is superior).

3. **P4_03** (cti-ate B3, Mean Binding Recall): E1a vs E0'-TECH
   - Treatment Mean: 0.2154, Control Mean: 0.2924
   - Delta: -0.0771 (95% Bootstrap CI [-0.1306, -0.0247]), p = 0.0040 (Holm alpha = 0.05000)
   - Decision: Significant decrease (control E0'-TECH is superior).

4. **P4_04** (cti-ate B3, Mean Binding Recall): E1-MIXED vs E0'
   - Treatment Mean: 0.2196, Control Mean: 0.3096
   - Delta: -0.0900 (95% Bootstrap CI [-0.1444, -0.0368]), p = 0.0010 (Holm alpha = 0.02500)
   - Decision: Significant decrease (control E0' is superior).

5. **P4_05** (CTI-ATTACK B2, Mean Binding Recall): E1a vs E0'-TECH
   - Treatment Mean: 0.5146, Control Mean: 0.6543
   - Delta: -0.1397 (95% Bootstrap CI [-0.1764, -0.1030]), p < 0.0001 (Holm alpha = 0.00833)
   - Decision: Significant decrease (control E0'-TECH is superior).

6. **P4_06** (CTI-ATTACK B2, Mean Binding Recall): E1-MIXED vs E0'
   - Treatment Mean: 0.4687, Control Mean: 0.6401
   - Delta: -0.1714 (95% Bootstrap CI [-0.2084, -0.1348]), p < 0.0001 (Holm alpha = 0.01000)
   - Decision: Significant decrease (control E0' is superior).

### C. Contrasts that Did Not Achieve Statistical Significance
1. **P3_01** (cti-taa B2, Object-Level Recall@10): V1h vs V0h (Delta = +0.0200, p_exact = 1.0000, p_boot = 0.7644)
2. **P3_02** (cti-taa B2, Object-Level MRR): V1h vs V0h (Delta = +0.0010, p_exact = 1.0000, p_boot = 0.9844)
3. **P3_04** (cti-taa B2, Object-Level MRR): Vrel vs V0h (Delta = +0.1449, p_exact = 0.0042, p_boot = 0.0121, Holm alpha = 0.00714 -> not significant under bootstrap)
4. **P3_05** (cti-taa B3, Object-Level Recall@10): V1h vs V0h (Delta = +0.0000, p_exact = 1.0000, p_boot = 1.0000)
5. **P3_06** (cti-taa B3, Object-Level MRR): V1h vs V0h (Delta = +0.0272, p_exact = 0.6875, p_boot = 0.2446)
6. **P3_07** (cti-taa B3, Object-Level Recall@10): Vrel vs V0h (Delta = +0.0800, p_exact = 0.2188, p_boot = 0.1399)
7. **P3_08** (cti-taa B3, Object-Level MRR): Vrel vs V0h (Delta = +0.0610, p_exact = 0.2891, p_boot = 0.0434, Holm alpha = 0.00833)
8. **P3_09** (cti-taa B2, Text-Inclusive Recall@10): V1h vs V0h (Delta = +0.0800, p_exact = 0.2891, p_boot = 0.2098)
9. **P3_10** (cti-taa B2, Text-Inclusive MRR): V1h vs V0h (Delta = +0.1203, p_exact = 0.3018, p_boot = 0.0218, Holm alpha = 0.01000)
10. **P3_13** (cti-taa B3, Text-Inclusive Recall@10): V1h vs V0h (Delta = +0.0200, p_exact = 1.0000, p_boot = 0.8463)
11. **P3_14** (cti-taa B3, Text-Inclusive MRR): V1h vs V0h (Delta = +0.1048, p_exact = 0.1460, p_boot = 0.0149, Holm alpha = 0.00833)
12. **P3_15** (cti-taa B3, Text-Inclusive Recall@10): Vrel vs V0h (Delta = +0.1000, p_exact = 0.1250, p_boot = 0.0797)
13. **P3_16** (cti-taa B3, Text-Inclusive MRR): Vrel vs V0h (Delta = +0.0868, p_exact = 0.2668, p_boot = 0.0310, Holm alpha = 0.01250)
14. **Cross-Dataset Transfer Check** (V1h vs V0h):
    - cti-ate B2: Delta = -0.0009 (passes non-inferiority margin -0.03)
    - CTI-ATTACK B2: Delta = +0.0000 (passes non-inferiority margin -0.03)
