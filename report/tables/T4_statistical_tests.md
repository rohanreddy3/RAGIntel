# T4_statistical_tests: Formal Statistical Tests with Exact Binomial Sign Tests and Holm Adjustments

| Family                       | Contrast                           | Metric           |   N | W/T/L     |   p_raw |   Holm_Rank |   Holm_Alpha | Significant   |
|:-----------------------------|:-----------------------------------|:-----------------|----:|:----------|--------:|------------:|-------------:|:--------------|
| Primary Generation (M=4)     | GEN_02: CTI-ATTACK HD vs LLM-only  | f1_sub           | 229 | 44/102/83 | 0.00068 |           1 |       0.0125 | True          |
| Primary Generation (M=4)     | GEN_01: cti-ate HD vs LLM-only     | f1_sub           |  60 | 18/6/36   | 0.01984 |           2 |       0.0167 | False         |
| Primary Generation (M=4)     | GEN_03: CTI-ATTACK HD vs E0' (Raw) | f1_sub           | 229 | 64/112/53 | 0.35528 |           3 |       0.025  | False         |
| Primary Generation (M=4)     | GEN_04: cti-ate HD vs E0' (Raw)    | f1_sub           |  60 | 17/7/36   | 0.01266 |           4 |       0.05   | True          |
| Clean-40 Primary Gen (M=5)   | V0h vs V0                          | v2_alias         |  40 | 7/32/1    | 0.07031 |           1 |       0.01   | False         |
| Clean-40 Primary Gen (M=5)   | V0 vs LLM-only                     | v2_alias         |  40 | 2/31/7    | 0.17969 |           2 |       0.0125 | False         |
| Clean-40 Primary Gen (M=5)   | Vrel vs LLM-only                   | v2_alias         |  40 | 8/26/6    | 0.79053 |           3 |       0.0167 | False         |
| Clean-40 Primary Gen (M=5)   | Vrel vs V0h                        | v2_alias         |  40 | 3/35/2    | 1       |           4 |       0.025  | False         |
| Clean-40 Primary Gen (M=5)   | V0h vs LLM-only                    | v2_alias         |  40 | 7/27/6    | 1       |           5 |       0.05   | False         |
| Clean-40 Secondary Gen (M=5) | Vrel vs LLM-only                   | v2_alias         |  40 | 6/31/3    | 0.50781 |           1 |       0.01   | False         |
| Clean-40 Secondary Gen (M=5) | V0h vs V0                          | v2_alias         |  40 | 6/30/4    | 0.75391 |           2 |       0.0125 | False         |
| Clean-40 Secondary Gen (M=5) | V0h vs LLM-only                    | v2_alias         |  40 | 6/30/4    | 0.75391 |           3 |       0.0167 | False         |
| Clean-40 Secondary Gen (M=5) | Vrel vs V0h                        | v2_alias         |  40 | 4/33/3    | 1       |           4 |       0.025  | False         |
| Clean-40 Secondary Gen (M=5) | V0 vs LLM-only                     | v2_alias         |  40 | 4/32/4    | 1       |           5 |       0.05   | False         |
| Retrieval Clean-40 (M=2)     | V0h vs V0                          | Object_Recall@10 |  40 | 0/29/11   | 0.00098 |           1 |       0.025  | True          |
| Retrieval Clean-40 (M=2)     | Vrel vs V0h                        | Object_Recall@10 |  40 | 8/32/0    | 0.00781 |           2 |       0.05   | True          |
