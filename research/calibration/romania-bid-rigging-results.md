136 rigged procedures in 23 decisions; SEAP years 2007-2024; 31160 candidate rows, 153026 rows of 48 labelled buyers
linked decisions: ['134/2024', '148/2025', '271/2024', '33/2017', '360/2025', '43/2020', '44/2013', '48/2019', '52/2020', '66/2015', '7/2015', '71/2012', '72/2012', '77/2015', '77/2017', '83/2016', '99/2021']
linking: {'unresolved: none': 11, 'resolved by notice': 20, 'unresolved: notice': 24, 'resolved by reviewed choice': 35, 'resolved by buyer name + winner': 16, 'unresolved: ambiguous': 20, 'unresolved: no notice match': 3, 'resolved by buyer CUI + winner': 5, 'resolved by buyer name + winner + date': 2} | challenged decisions: {'134/2024': 3, '148/2025': 4, '271/2024': 1, '43/2020': 1, '44/2013': 1, '48/2020': 1, '77/2017': 2, '80/2023': 2, '99/2021': 1}

### unchallenged, one per decision (decision rule): 10 labelled (9 buyers), 9838 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 22% (2/10) | 30% (1682/5778) | 0.869 [0.50, 1.32] | 0.894 / 0.909 | too few (9 buyers)  | fails rule |
| RO1 direct award | 0% (0/10) | 15% (592/9838) | 0.526 [0.42, 0.67] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| RO2 buyer share >= 5 % | 44% (5/10) | 16% (130/9352) | 1.756 [0.88, 3.05] | 1.526 / 1.357 | too few (9 buyers)  | fails rule |
| RO3 concentration | 0% (0/10) | 2% (198/9835) | 0.526 [0.42, 0.71] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| RO5 framework / subsequent | 44% (4/10) | 27% (5395/9831) | 1.28 [0.77, 2.10] | 1.111 / 1.253 | too few (9 buyers)  | fails rule |
| U1 repeated single offer | 11% (1/10) | 7% (748/6369) | 1.114 [0.46, 2.02] | 1.049 / 0.909 | too few (9 buyers)  | fails rule |
| U2 repeated direct award | 0% (0/10) | 4% (252/9835) | 0.526 [0.42, 0.71] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| N1 December signature | 22% (2/10) | 11% (591/9837) | 1.395 [0.50, 3.12] | 1.282 / 1.294 | too few (9 buyers)  | fails rule |
| N2 weekend signature | 0% (0/10) | 0% (22/9837) | 0.526 [0.42, 0.67] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| N4 supplier dependence >= 25 % | 44% (4/10) | 12% (189/9835) | 2.146 [0.94, 4.41] | 1.892 / 1.426 | too few (9 buyers)  | fails rule |
| N5 first-time supplier | 57% (4/7) | 37% (1637/8343) | 1.208 [0.80, 1.67] | 1.276 / None | too few (7 buyers)  | fails rule |

### unchallenged, all procedures: 21 labelled (12 buyers), 9838 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 25% (4/17) | 30% (1682/5778) | 0.898 [0.50, 1.34] | 0.847 / 1.029 | 0.0 [0.0, 4.2] | fails rule |
| RO1 direct award | 0% (0/21) | 15% (592/9838) | 0.455 [0.37, 0.59] | 0.526 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 38% (6/21) | 16% (130/9352) | 1.65 [0.88, 2.86] | 1.599 / 1.148 | 7.2 [0.0, 15.2] | fails rule |
| RO3 concentration | 0% (0/21) | 2% (198/9835) | 0.455 [0.37, 0.59] | 0.526 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 42% (10/21) | 27% (5395/9831) | 1.269 [0.74, 2.17] | 1.053 / 1.351 | 3.4 [0.0, 11.2] | fails rule |
| U1 repeated single offer | 17% (3/17) | 7% (748/6369) | 1.469 [0.43, 2.70] | 0.994 / 1.588 | 5.5 [0.0, 14.3] | fails rule |
| U2 repeated direct award | 0% (0/21) | 4% (252/9835) | 0.455 [0.37, 0.59] | 0.526 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 17% (2/21) | 11% (591/9837) | 1.205 [0.43, 2.70] | 1.215 / 1.095 | 2.7 [0.0, 14.3] | fails rule |
| N2 weekend signature | 0% (0/21) | 0% (22/9837) | 0.455 [0.37, 0.59] | 0.526 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 33% (5/21) | 12% (189/9835) | 1.853 [0.80, 3.89] | 1.792 / 1.206 | 8.9 [0.0, 19.6] | fails rule |
| N5 first-time supplier | 38% (6/17) | 37% (1637/8343) | 1.005 [0.68, 1.42] | 1.178 / 0.833 | 0.1 [0.0, 5.1] | fails rule |

### all Council findings, one per decision: 17 labelled (15 buyers), 9838 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 31% (4/15) | 30% (1682/5778) | 1.0 [0.59, 1.51] | 0.847 / 1.197 | 0.0 [0.0, 5.9] | fails rule |
| RO1 direct award | 0% (0/17) | 15% (592/9838) | 0.4 [0.33, 0.50] | 0.476 / 0.714 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 38% (7/17) | 16% (130/9352) | 1.725 [0.95, 3.02] | 1.771 / 1.066 | 7.9 [0.0, 15.9] | proposal |
| RO3 concentration | 7% (1/17) | 2% (198/9835) | 1.43 [0.36, 2.57] | 1.347 / 0.714 | 5.2 [0.0, 13.6] | fails rule |
| RO5 framework / subsequent | 47% (7/17) | 27% (5395/9831) | 1.403 [0.88, 2.25] | 1.111 / 1.525 | 4.9 [0.0, 11.7] | fails rule |
| U1 repeated single offer | 8% (1/15) | 7% (748/6369) | 0.92 [0.39, 1.75] | 0.994 / 0.714 | 0.0 [0.0, 8.0] | fails rule |
| U2 repeated direct award | 0% (0/17) | 4% (252/9835) | 0.4 [0.33, 0.50] | 0.476 / 0.714 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 20% (3/17) | 11% (591/9837) | 1.39 [0.48, 2.86] | 1.099 / 1.32 | 4.8 [0.0, 15.2] | fails rule |
| N2 weekend signature | 0% (0/17) | 0% (22/9837) | 0.4 [0.33, 0.50] | 0.476 / 0.714 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 40% (6/17) | 12% (189/9835) | 2.246 [1.13, 4.65] | 2.385 / 1.12 | 11.7 [1.7, 22.2] | proposal |
| N5 first-time supplier | 46% (5/12) | 37% (1637/8343) | 1.103 [0.72, 1.56] | 1.296 / 0.833 | 1.4 [0.0, 6.5] | fails rule |

### all Council findings, all procedures: 66 labelled (27 buyers), 9838 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 38% (15/57) | 30% (1682/5778) | 1.175 [0.76, 1.70] | 0.997 / 1.281 | 2.3 [0.0, 7.6] | fails rule |
| RO1 direct award | 0% (1/66) | 15% (592/9838) | 0.288 [0.27, 0.34] | 0.405 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 37% (19/66) | 16% (130/9352) | 1.862 [1.25, 3.13] | 1.746 / 1.414 | 9.0 [3.2, 16.5] | proposal |
| RO3 concentration | 0% (1/66) | 2% (198/9835) | 0.368 [0.27, 0.48] | 0.483 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 37% (20/65) | 27% (5395/9831) | 1.237 [0.80, 1.90] | 1.108 / 1.256 | 3.1 [0.0, 9.2] | fails rule |
| U1 repeated single offer | 16% (6/58) | 7% (748/6369) | 1.561 [0.59, 2.76] | 1.528 / 0.983 | 6.4 [0.0, 14.7] | fails rule |
| U2 repeated direct award | 0% (1/66) | 4% (252/9835) | 0.327 [0.27, 0.44] | 0.455 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 15% (5/66) | 11% (591/9837) | 1.194 [0.55, 2.12] | 0.958 / 1.082 | 2.6 [0.0, 10.9] | fails rule |
| N2 weekend signature | 0% (0/66) | 0% (22/9837) | 0.27 [0.27, 0.27] | 0.385 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 32% (12/66) | 12% (189/9835) | 2.098 [1.27, 4.39] | 1.862 / 1.558 | 10.7 [3.4, 21.3] | fails rule |
| N5 first-time supplier | 42% (15/59) | 37% (1637/8343) | 1.069 [0.77, 1.45] | 1.102 / 0.974 | 1.0 [0.0, 5.4] | fails rule |

### weighted by appeal outcome, one per decision (decision rule, amendment 2026-10-15): 17 labelled (15 buyers), 9883 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 30% (3.82/14.55) | 30% (1682.99/5781.6) | 0.986 [0.57, 1.45] | 0.851 / 1.165 | 0.0 [0.0, 5.4] | fails rule |
| RO1 direct award | 0% (0.0/16.37) | 15% (592.09/9842.05) | 0.409 [0.34, 0.51] | 0.482 / 0.728 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 38% (6.82/16.37) | 16% (131.17/9356.05) | 1.677 [0.95, 2.74] | 1.74 / 1.064 | 7.5 [0.0, 14.6] | proposal |
| RO3 concentration | 6% (0.91/16.37) | 2% (198.09/9839.05) | 1.373 [0.36, 2.48] | 1.285 / 0.728 | 4.6 [0.0, 13.1] | fails rule |
| RO5 framework / subsequent | 46% (6.73/16.37) | 27% (5395.9/9834.96) | 1.406 [0.89, 2.20] | 1.115 / 1.521 | 4.9 [0.0, 11.4] | fails rule |
| U1 repeated single offer | 8% (1.0/14.55) | 7% (748.27/6372.69) | 0.938 [0.38, 1.75] | 0.999 / 0.728 | 0.0 [0.0, 8.0] | fails rule |
| U2 repeated direct award | 0% (0.0/16.37) | 3% (252.09/9839.05) | 0.409 [0.34, 0.51] | 0.482 / 0.728 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 20% (2.91/16.37) | 10% (591.27/9841.05) | 1.398 [0.45, 2.90] | 1.113 / 1.331 | 4.8 [0.0, 15.3] | fails rule |
| N2 weekend signature | 0% (0.0/16.37) | 0% (22.0/9841.05) | 0.409 [0.34, 0.51] | 0.482 / 0.728 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 40% (5.82/16.37) | 12% (189.63/9839.05) | 2.149 [1.08, 4.26] | 2.329 / 1.111 | 11.0 [1.2, 20.9] | proposal |
| N5 first-time supplier | 46% (4.91/11.55) | 38% (1637.81/8346.78) | 1.101 [0.72, 1.57] | 1.292 / 0.846 | 1.4 [0.0, 6.5] | fails rule |

### weighted by appeal outcome, all procedures: 66 labelled (27 buyers), 9883 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 38% (14.01/53.4) | 30% (1682.99/5781.6) | 1.151 [0.75, 1.61] | 0.986 / 1.247 | 2.0 [0.0, 6.9] | fails rule |
| RO1 direct award | 0% (0.91/61.95) | 15% (592.09/9842.05) | 0.299 [0.28, 0.35] | 0.415 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 37% (17.83/61.95) | 16% (131.17/9356.05) | 1.784 [1.23, 2.85] | 1.714 / 1.34 | 8.4 [3.0, 15.1] | proposal |
| RO3 concentration | 0% (0.91/61.95) | 2% (198.09/9839.05) | 0.375 [0.28, 0.48] | 0.488 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 37% (19.1/61.04) | 27% (5395.9/9834.96) | 1.249 [0.81, 1.92] | 1.109 / 1.277 | 3.2 [0.0, 9.4] | fails rule |
| U1 repeated single offer | 16% (5.73/54.31) | 7% (748.27/6372.69) | 1.565 [0.60, 2.74] | 1.489 / 1.027 | 6.5 [0.0, 14.5] | fails rule |
| U2 repeated direct award | 0% (0.91/61.95) | 3% (252.09/9839.05) | 0.34 [0.28, 0.45] | 0.466 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 15% (4.73/61.95) | 10% (591.27/9841.05) | 1.201 [0.55, 2.18] | 0.977 / 1.095 | 2.6 [0.0, 11.2] | fails rule |
| N2 weekend signature | 0% (0.0/61.95) | 0% (22.0/9841.05) | 0.281 [0.28, 0.28] | 0.394 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 33% (11.37/61.95) | 12% (189.63/9839.05) | 1.995 [1.23, 3.83] | 1.841 / 1.458 | 10.0 [2.9, 19.4] | fails rule |
| N5 first-time supplier | 42% (14.19/55.22) | 38% (1637.81/8346.78) | 1.055 [0.76, 1.41] | 1.106 / 0.955 | 0.8 [0.0, 4.9] | fails rule |

### all findings, 2+ offers (sensitivity): 42 labelled (16 buyers), 4174 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 0% (0/42) | 0% (0/4094) | 0.385 [0.33, 0.48] | 0.5 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| RO1 direct award | 0% (0/42) | 3% (80/4174) | 0.385 [0.32, 0.48] | 0.5 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 34% (10/42) | 8% (62/4172) | 2.418 [1.09, 5.16] | 2.552 / 1.356 | 12.7 [1.3, 23.7] | proposal |
| RO3 concentration | 2% (1/42) | 1% (36/4174) | 0.814 [0.34, 1.72] | 0.875 / 0.625 | 0.0 [0.0, 7.8] | fails rule |
| RO5 framework / subsequent | 33% (9/42) | 22% (1443/4173) | 1.281 [0.76, 1.96] | 1.232 / 1.104 | 3.6 [0.0, 9.7] | fails rule |
| U1 repeated single offer | 0% (0/42) | 0% (0/4174) | 0.385 [0.32, 0.48] | 0.5 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| U2 repeated direct award | 0% (0/42) | 1% (18/4174) | 0.385 [0.33, 0.48] | 0.5 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 12% (2/42) | 10% (269/4174) | 1.068 [0.37, 2.35] | 0.5 / 1.215 | 1.0 [0.0, 12.3] | fails rule |
| N2 weekend signature | 0% (0/42) | 0% (15/4174) | 0.385 [0.32, 0.48] | 0.5 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 21% (4/42) | 6% (16/4174) | 2.046 [0.67, 7.27] | 1.763 / 1.431 | 10.3 [0.0, 28.6] | fails rule |
| N5 first-time supplier | 43% (8/36) | 44% (861/3135) | 0.99 [0.70, 1.41] | 0.947 / 1.05 | 0.0 [0.0, 4.9] | fails rule |
