136 rigged procedures in 23 decisions; SEAP years 2007-2024; 36448 candidate rows, 136889 rows of 47 labelled buyers
linked decisions: ['134/2024', '148/2025', '271/2024', '33/2017', '360/2025', '43/2020', '44/2013', '48/2019', '52/2020', '66/2015', '7/2015', '71/2012', '72/2012', '77/2015', '77/2017', '83/2016', '99/2021']
linking: {'unresolved: none': 12, 'resolved by notice': 18, 'unresolved: notice': 24, 'resolved by reviewed choice': 35, 'resolved by buyer name + winner': 16, 'unresolved: ambiguous': 20, 'unresolved: no notice match': 4, 'resolved by buyer CUI + winner': 5, 'resolved by buyer name + winner + date': 2} | challenged decisions: {'134/2024': 3, '148/2025': 4, '271/2024': 1, '43/2020': 1, '44/2013': 1, '48/2020': 1, '77/2017': 2, '80/2023': 2, '99/2021': 1}

### unchallenged, one per decision (decision rule): 10 labelled (9 buyers), 10287 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 22% (2/10) | 30% (1859/6474) | 0.868 [0.50, 1.32] | 0.9 / 0.909 | too few (9 buyers)  | fails rule |
| RO1 direct award | 0% (0/10) | 15% (593/10287) | 0.526 [0.42, 0.67] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| RO2 buyer share >= 5 % | 39% (4/10) | 16% (123/9713) | 1.588 [0.81, 2.71] | 1.325 / 1.38 | too few (9 buyers)  | fails rule |
| RO3 concentration | 0% (0/10) | 3% (304/10284) | 0.526 [0.42, 0.71] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| RO5 framework / subsequent | 44% (4/10) | 27% (5793/10280) | 1.275 [0.77, 2.10] | 1.104 / 1.256 | too few (9 buyers)  | fails rule |
| U1 repeated single offer | 11% (1/10) | 7% (811/7066) | 1.124 [0.46, 2.03] | 1.055 / 0.909 | too few (9 buyers)  | fails rule |
| U2 repeated direct award | 0% (0/10) | 3% (238/10284) | 0.526 [0.42, 0.71] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| N1 December signature | 22% (2/10) | 10% (617/10284) | 1.421 [0.50, 3.23] | 1.288 / 1.31 | too few (9 buyers)  | fails rule |
| N2 weekend signature | 0% (0/10) | 0% (23/10284) | 0.526 [0.42, 0.67] | 0.556 / 0.909 | too few (9 buyers)  | fails rule |
| N4 supplier dependence >= 25 % | 44% (4/10) | 11% (216/10284) | 2.19 [0.94, 4.53] | 1.944 / 1.432 | too few (9 buyers)  | fails rule |
| N5 first-time supplier | 57% (4/7) | 37% (1701/8747) | 1.21 [0.81, 1.68] | 1.288 / None | too few (7 buyers)  | fails rule |

### unchallenged, all procedures: 21 labelled (13 buyers), 10287 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 23% (4/18) | 30% (1859/6474) | 0.858 [0.48, 1.30] | 0.81 / 1.021 | 0.0 [0.0, 3.8] | fails rule |
| RO1 direct award | 0% (0/21) | 15% (593/10287) | 0.435 [0.36, 0.56] | 0.5 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 38% (6/21) | 16% (123/9713) | 1.688 [0.93, 2.94] | 1.607 / 1.168 | 7.6 [0.0, 15.5] | fails rule |
| RO3 concentration | 0% (0/21) | 3% (304/10284) | 0.435 [0.36, 0.56] | 0.5 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 38% (9/21) | 27% (5793/10280) | 1.208 [0.70, 2.01] | 0.993 / 1.356 | 2.7 [0.0, 10.1] | fails rule |
| U1 repeated single offer | 15% (3/18) | 7% (811/7066) | 1.423 [0.42, 2.72] | 0.949 / 1.605 | 5.1 [0.0, 14.4] | fails rule |
| U2 repeated direct award | 0% (0/21) | 3% (238/10284) | 0.435 [0.36, 0.56] | 0.5 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 15% (2/21) | 10% (617/10284) | 1.174 [0.42, 2.84] | 1.159 / 1.108 | 2.3 [0.0, 15.1] | fails rule |
| N2 weekend signature | 0% (0/21) | 0% (23/10284) | 0.435 [0.36, 0.56] | 0.5 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 38% (6/21) | 11% (216/10284) | 2.153 [0.99, 4.79] | 2.167 / 1.211 | 11.1 [0.0, 22.6] | proposal |
| N5 first-time supplier | 44% (7/17) | 37% (1701/8747) | 1.092 [0.72, 1.55] | 1.293 / 0.833 | 1.3 [0.0, 6.4] | fails rule |

### all Council findings, one per decision: 17 labelled (15 buyers), 10287 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 31% (4/15) | 30% (1859/6474) | 0.999 [0.58, 1.53] | 0.853 / 1.183 | 0.0 [0.0, 6.1] | fails rule |
| RO1 direct award | 0% (0/17) | 15% (593/10287) | 0.4 [0.33, 0.50] | 0.476 / 0.714 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 36% (6/17) | 16% (123/9713) | 1.629 [0.92, 2.77] | 1.618 / 1.084 | 7.0 [0.0, 14.7] | proposal |
| RO3 concentration | 7% (1/17) | 3% (304/10284) | 1.2 [0.36, 2.32] | 1.14 / 0.714 | 2.6 [0.0, 12.1] | fails rule |
| RO5 framework / subsequent | 47% (7/17) | 27% (5793/10280) | 1.396 [0.88, 2.23] | 1.103 / 1.531 | 4.8 [0.0, 11.6] | fails rule |
| U1 repeated single offer | 8% (1/15) | 7% (811/7066) | 0.929 [0.39, 1.76] | 0.999 / 0.714 | 0.0 [0.0, 8.2] | fails rule |
| U2 repeated direct award | 0% (0/17) | 3% (238/10284) | 0.4 [0.33, 0.50] | 0.476 / 0.714 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 20% (3/17) | 10% (617/10284) | 1.42 [0.48, 2.99] | 1.104 / 1.344 | 5.1 [0.0, 15.8] | fails rule |
| N2 weekend signature | 0% (0/17) | 0% (23/10284) | 0.4 [0.33, 0.50] | 0.476 / 0.714 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 40% (6/17) | 11% (216/10284) | 2.297 [1.15, 4.75] | 2.46 / 1.125 | 12.0 [2.0, 22.5] | proposal |
| N5 first-time supplier | 46% (5/12) | 37% (1701/8747) | 1.105 [0.72, 1.58] | 1.309 / 0.833 | 1.4 [0.0, 6.6] | fails rule |

### all Council findings, all procedures: 64 labelled (28 buyers), 10287 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 37% (15/58) | 30% (1859/6474) | 1.14 [0.73, 1.68] | 0.967 / 1.257 | 1.9 [0.0, 7.5] | fails rule |
| RO1 direct award | 0% (1/64) | 15% (593/10287) | 0.281 [0.26, 0.33] | 0.39 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 39% (19/64) | 16% (123/9713) | 1.927 [1.34, 3.33] | 1.8 / 1.463 | 9.5 [4.2, 17.4] | proposal |
| RO3 concentration | 0% (1/64) | 3% (304/10284) | 0.337 [0.26, 0.44] | 0.443 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 36% (17/63) | 27% (5793/10280) | 1.197 [0.81, 1.92] | 1.057 / 1.263 | 2.6 [0.0, 9.4] | fails rule |
| U1 repeated single offer | 15% (6/59) | 7% (811/7066) | 1.54 [0.55, 2.77] | 1.479 / 0.994 | 6.2 [0.0, 14.7] | fails rule |
| U2 repeated direct award | 0% (1/64) | 3% (238/10284) | 0.321 [0.26, 0.45] | 0.44 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 15% (5/64) | 10% (617/10284) | 1.189 [0.57, 2.11] | 0.927 / 1.106 | 2.5 [0.0, 10.8] | fails rule |
| N2 weekend signature | 0% (0/64) | 0% (23/10284) | 0.263 [0.26, 0.26] | 0.37 / 0.476 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 35% (13/64) | 11% (216/10284) | 2.299 [1.37, 4.90] | 2.157 / 1.571 | 12.0 [4.6, 22.9] | proposal |
| N5 first-time supplier | 44% (15/57) | 37% (1701/8747) | 1.118 [0.82, 1.51] | 1.189 / 0.966 | 1.6 [0.0, 5.9] | fails rule |

### weighted by appeal outcome, one per decision (decision rule, amendment 2026-10-15): 17 labelled (15 buyers), 10330 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 30% (3.82/14.55) | 30% (1859.99/6477.6) | 0.984 [0.57, 1.45] | 0.857 / 1.153 | 0.0 [0.0, 5.4] | fails rule |
| RO1 direct award | 0% (0.0/16.37) | 15% (593.09/10290.87) | 0.409 [0.34, 0.51] | 0.482 / 0.728 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 36% (5.82/16.37) | 17% (124.17/9716.87) | 1.584 [0.89, 2.62] | 1.586 / 1.08 | 6.6 [0.0, 13.9] | proposal |
| RO3 concentration | 6% (0.91/16.37) | 3% (304.09/10287.87) | 1.158 [0.36, 2.22] | 1.099 / 0.728 | 2.1 [0.0, 11.5] | fails rule |
| RO5 framework / subsequent | 46% (6.73/16.37) | 27% (5793.72/10283.78) | 1.397 [0.89, 2.20] | 1.105 / 1.527 | 4.8 [0.0, 11.4] | fails rule |
| U1 repeated single offer | 8% (1.0/14.55) | 7% (811.27/7069.69) | 0.945 [0.38, 1.75] | 1.004 / 0.728 | 0.0 [0.0, 8.1] | fails rule |
| U2 repeated direct award | 0% (0.0/16.37) | 3% (238.09/10287.87) | 0.409 [0.34, 0.51] | 0.482 / 0.728 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 20% (2.91/16.37) | 10% (617.27/10287.87) | 1.43 [0.45, 2.99] | 1.118 / 1.355 | 5.2 [0.0, 15.8] | fails rule |
| N2 weekend signature | 0% (0.0/16.37) | 0% (23.0/10287.87) | 0.409 [0.34, 0.51] | 0.482 / 0.728 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 40% (5.82/16.37) | 12% (216.63/10287.87) | 2.194 [1.12, 4.44] | 2.392 / 1.114 | 11.3 [1.6, 21.5] | proposal |
| N5 first-time supplier | 46% (4.91/11.55) | 38% (1701.72/8750.6) | 1.103 [0.73, 1.59] | 1.304 / 0.846 | 1.4 [0.0, 6.7] | fails rule |

### weighted by appeal outcome, all procedures: 64 labelled (28 buyers), 10330 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 36% (14.01/54.4) | 30% (1859.99/6477.6) | 1.116 [0.72, 1.62] | 0.955 / 1.226 | 1.6 [0.0, 7.0] | fails rule |
| RO1 direct award | 0% (0.91/60.13) | 15% (593.09/10290.87) | 0.291 [0.27, 0.34] | 0.399 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 39% (17.83/60.13) | 17% (124.17/9716.87) | 1.853 [1.31, 3.04] | 1.771 / 1.38 | 8.9 [3.9, 16.0] | proposal |
| RO3 concentration | 0% (0.91/60.13) | 3% (304.09/10287.87) | 0.344 [0.27, 0.45] | 0.448 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 36% (16.28/59.22) | 27% (5793.72/10283.78) | 1.206 [0.82, 1.94] | 1.056 / 1.283 | 2.7 [0.0, 9.5] | fails rule |
| U1 repeated single offer | 15% (5.73/55.31) | 7% (811.27/7069.69) | 1.537 [0.57, 2.75] | 1.44 / 1.039 | 6.2 [0.0, 14.6] | fails rule |
| U2 repeated direct award | 0% (0.91/60.13) | 3% (238.09/10287.87) | 0.333 [0.27, 0.46] | 0.451 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 15% (4.73/60.13) | 10% (617.27/10287.87) | 1.198 [0.56, 2.14] | 0.944 / 1.119 | 2.6 [0.0, 11.0] | fails rule |
| N2 weekend signature | 0% (0.0/60.13) | 0% (23.0/10287.87) | 0.273 [0.27, 0.28] | 0.379 / 0.493 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 35% (12.37/60.13) | 12% (216.63/10287.87) | 2.189 [1.35, 4.19] | 2.129 / 1.468 | 11.3 [4.4, 20.7] | proposal |
| N5 first-time supplier | 44% (14.28/53.4) | 38% (1701.72/8750.6) | 1.104 [0.82, 1.47] | 1.193 / 0.949 | 1.4 [0.0, 5.5] | fails rule |

### all findings, 2+ offers (sensitivity): 43 labelled (17 buyers), 4693 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 0% (0/43) | 0% (0/4613) | 0.37 [0.32, 0.46] | 0.476 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| RO1 direct award | 0% (0/43) | 3% (80/4693) | 0.37 [0.31, 0.46] | 0.476 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 37% (10/43) | 8% (54/4631) | 2.643 [1.25, 5.68] | 2.78 / 1.392 | 14.0 [3.2, 25.0] | proposal |
| RO3 concentration | 2% (1/43) | 3% (93/4693) | 0.635 [0.33, 1.31] | 0.71 / 0.625 | 0.0 [0.0, 3.9] | fails rule |
| RO5 framework / subsequent | 31% (9/43) | 23% (1850/4692) | 1.196 [0.71, 1.84] | 1.123 / 1.11 | 2.6 [0.0, 8.8] | fails rule |
| U1 repeated single offer | 0% (0/43) | 0% (0/4693) | 0.37 [0.31, 0.46] | 0.476 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| U2 repeated direct award | 0% (0/43) | 1% (17/4693) | 0.37 [0.31, 0.46] | 0.476 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 12% (2/43) | 9% (270/4691) | 1.052 [0.36, 2.47] | 0.476 / 1.235 | 0.7 [0.0, 13.0] | fails rule |
| N2 weekend signature | 0% (0/43) | 0% (15/4691) | 0.37 [0.31, 0.46] | 0.476 / 0.625 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 26% (5/43) | 7% (38/4693) | 2.285 [0.83, 7.13] | 2.266 / 1.416 | 11.9 [0.0, 28.3] | fails rule |
| N5 first-time supplier | 47% (9/37) | 45% (962/3613) | 1.031 [0.72, 1.49] | 1.004 / 1.041 | 0.4 [0.0, 5.8] | fails rule |
