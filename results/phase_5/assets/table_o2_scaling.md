### Table: Unified 4-Budget Scaling (k=50 vs Candidate Pool=200)

*Note: Cells labeled [B] indicate binding token budgets; cells labeled [C] indicate non-binding budgets capped by candidate pool.*

| Dataset | Baseline | Arm | B=500 | B=1000 | B=2000 | B=4000 | Binding Mean (AUC) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **cti-ate** | B2 | E0_prime (k=50) | 0.2091 [B] | 0.2853 [B] | 0.4239 [B] | 0.4719 [C] | **0.3061** |
| **cti-ate** | B2 | E0_prime_tech (k=50) | 0.1900 [B] | 0.2834 [B] | 0.4186 [B] | 0.4842 [C] | **0.2973** |
| **cti-ate** | B2 | E1a (k=50) | 0.1634 [B] | 0.1970 [B] | 0.2557 [B] | 0.3854 [B] | **0.2053** |
| **cti-ate** | B2 | E1_mixed (k=50) | 0.1585 [B] | 0.2054 [B] | 0.2735 [B] | 0.3895 [B] | **0.2124** |
| **cti-ate** | B2 | E0_prime_k200 (pool=200) | 0.2042 [B] | 0.2812 [B] | 0.4201 [B] | 0.5695 [B] | **0.3688** |
| **cti-ate** | B2 | E0_prime_tech_k200 (pool=200) | 0.1768 [B] | 0.2899 [B] | 0.4168 [B] | 0.5704 [B] | **0.3635** |
| **CTI-ATTACK** | B2 | E0_prime (k=50) | 0.5953 [B] | 0.6849 [B] | 0.6914 [C] | 0.6914 [C] | **0.6401** |
| **CTI-ATTACK** | B2 | E0_prime_tech (k=50) | 0.6237 [B] | 0.6849 [B] | 0.7023 [C] | 0.7023 [C] | **0.6543** |
| **CTI-ATTACK** | B2 | E1a (k=50) | 0.4316 [B] | 0.5975 [B] | 0.6805 [B] | 0.7475 [B] | **0.5146** |
| **CTI-ATTACK** | B2 | E1_mixed (k=50) | 0.4054 [B] | 0.5320 [B] | 0.6477 [B] | 0.7023 [B] | **0.4687** |
| **CTI-ATTACK** | B2 | E0_prime_k200 (pool=200) | 0.5670 [B] | 0.6477 [B] | 0.7525 [B] | 0.8159 [B] | **0.6958** |
| **CTI-ATTACK** | B2 | E0_prime_tech_k200 (pool=200) | 0.5713 [B] | 0.6543 [B] | 0.7438 [B] | 0.8202 [B] | **0.6974** |
