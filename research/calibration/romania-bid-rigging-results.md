149 rigged procedures in 29 decisions; SEAP years 2007-2024; 36575 candidate rows, 169885 rows of 55 labelled buyers
linked decisions: ['118/2022', '127/2022', '134/2024', '148/2025', '225/2024', '271/2024', '33/2017', '360/2025', '43/2020', '44/2013', '48/2019', '52/2020', '66/2015', '7/2015', '71/2012', '72/2012', '77/2015', '77/2017', '83/2016', '99/2021']
linking: {'unresolved: none': 15, 'resolved by notice': 24, 'unresolved: notice': 26, 'resolved by reviewed choice': 35, 'resolved by buyer name + winner': 21, 'unresolved: ambiguous': 20, 'unresolved: no notice match': 1, 'resolved by buyer CUI + winner': 5, 'resolved by buyer name + winner + date': 2} | challenged decisions: {'118/2022': 2, '134/2024': 3, '148/2025': 4, '271/2024': 1, '43/2020': 1, '44/2013': 1, '48/2020': 1, '77/2017': 2, '80/2023': 2, '99/2021': 1}

### unchallenged, one per decision (decision rule): 12 labelled (11 buyers), 12469 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 18% (2/12) | 30% (1750/5860) | 0.79 [0.46, 1.23] | 0.925 / 0.769 | 0.0 [0.0, 3.0] | fails rule |
| RO1 direct award | 0% (0/12) | 13% (599/12469) | 0.476 [0.39, 0.62] | 0.556 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 46% (6/12) | 18% (137/12461) | 1.718 [0.93, 3.08] | 1.355 / 1.587 | 7.8 [0.0, 16.2] | fails rule |
| RO3 concentration | 0% (0/12) | 3% (316/12466) | 0.476 [0.39, 0.62] | 0.556 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 40% (4/11) | 26% (7441/12460) | 1.258 [0.71, 2.16] | 1.212 / 1.105 | 3.3 [0.0, 11.1] | fails rule |
| U1 repeated single offer | 9% (1/12) | 7% (764/6458) | 1.064 [0.42, 1.99] | 1.145 / 0.769 | 0.9 [0.0, 9.9] | fails rule |
| U2 repeated direct award | 0% (0/12) | 3% (261/12466) | 0.476 [0.39, 0.62] | 0.556 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 18% (2/12) | 10% (876/12468) | 1.295 [0.46, 2.84] | 1.404 / 1.084 | 3.7 [0.0, 15.1] | fails rule |
| N2 weekend signature | 0% (0/12) | 0% (21/12468) | 0.476 [0.39, 0.62] | 0.556 / 0.769 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 36% (4/12) | 12% (233/12466) | 1.905 [0.83, 3.71] | 1.853 / 1.208 | 9.3 [0.0, 18.9] | fails rule |
| N5 first-time supplier | 56% (5/9) | 44% (1966/10968) | 1.123 [0.78, 1.56] | 1.117 / 1.023 | too few (9 buyers)  | fails rule |

### unchallenged, all procedures: 24 labelled (14 buyers), 12469 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 21% (4/19) | 30% (1750/5860) | 0.829 [0.46, 1.25] | 0.876 / 0.872 | 0.0 [0.0, 3.3] | fails rule |
| RO1 direct award | 2% (1/24) | 13% (599/12469) | 0.512 [0.37, 0.83] | 0.623 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 39% (7/24) | 18% (137/12461) | 1.612 [0.91, 2.88] | 1.41 / 1.375 | 6.9 [0.0, 15.3] | fails rule |
| RO3 concentration | 0% (0/24) | 3% (316/12466) | 0.417 [0.34, 0.53] | 0.526 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 38% (10/23) | 26% (7441/12460) | 1.259 [0.68, 2.21] | 1.148 / 1.18 | 3.3 [0.0, 11.4] | fails rule |
| U1 repeated single offer | 14% (3/20) | 7% (764/6458) | 1.445 [0.39, 2.75] | 1.085 / 1.365 | 5.3 [0.0, 14.6] | fails rule |
| U2 repeated direct award | 0% (0/24) | 3% (261/12466) | 0.417 [0.34, 0.53] | 0.526 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 14% (2/24) | 10% (876/12468) | 1.133 [0.40, 2.51] | 1.33 / 0.939 | 1.8 [0.0, 13.3] | fails rule |
| N2 weekend signature | 0% (0/24) | 0% (21/12468) | 0.417 [0.34, 0.53] | 0.526 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 29% (5/24) | 12% (233/12466) | 1.667 [0.72, 3.24] | 1.755 / 1.047 | 7.4 [0.0, 17.0] | fails rule |
| N5 first-time supplier | 40% (7/19) | 44% (1966/10968) | 0.952 [0.66, 1.33] | 1.034 / 0.877 | 0.0 [0.0, 4.2] | fails rule |

### all Council findings, one per decision: 20 labelled (17 buyers), 12469 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 20% (3/17) | 30% (1750/5860) | 0.796 [0.43, 1.25] | 0.832 / 0.872 | 0.0 [0.0, 3.3] | fails rule |
| RO1 direct award | 0% (0/20) | 13% (599/12469) | 0.37 [0.31, 0.46] | 0.455 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 45% (9/20) | 18% (137/12461) | 1.852 [1.09, 3.20] | 1.691 / 1.375 | 8.9 [1.3, 16.8] | proposal |
| RO3 concentration | 6% (1/20) | 3% (316/12466) | 1.131 [0.32, 2.46] | 1.432 / 0.667 | 1.8 [0.0, 13.0] | fails rule |
| RO5 framework / subsequent | 38% (7/19) | 26% (7441/12460) | 1.259 [0.72, 2.12] | 1.17 / 1.18 | 3.3 [0.0, 10.8] | fails rule |
| U1 repeated single offer | 7% (1/17) | 7% (764/6458) | 0.894 [0.34, 1.74] | 1.031 / 0.667 | 0.0 [0.0, 7.9] | fails rule |
| U2 repeated direct award | 0% (0/20) | 3% (261/12466) | 0.37 [0.31, 0.46] | 0.455 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 18% (3/20) | 10% (876/12468) | 1.325 [0.40, 2.81] | 1.149 / 1.212 | 4.1 [0.0, 14.9] | fails rule |
| N2 weekend signature | 0% (0/20) | 0% (21/12468) | 0.37 [0.31, 0.46] | 0.455 / 0.667 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 41% (7/20) | 12% (233/12466) | 2.315 [1.19, 4.37] | 2.577 / 1.047 | 12.1 [2.5, 21.3] | proposal |
| N5 first-time supplier | 50% (7/15) | 44% (1966/10968) | 1.075 [0.77, 1.45] | 1.118 / 0.944 | 1.0 [0.0, 5.3] | fails rule |

### all Council findings, all procedures: 75 labelled (31 buyers), 12469 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 30% (14/61) | 30% (1750/5860) | 0.981 [0.60, 1.46] | 0.932 / 1.015 | 0.0 [0.0, 5.4] | fails rule |
| RO1 direct award | 1% (2/75) | 13% (599/12469) | 0.318 [0.24, 0.47] | 0.429 / 0.455 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 45% (23/75) | 18% (137/12461) | 2.036 [1.41, 3.26] | 1.847 / 1.662 | 10.3 [5.0, 17.1] | proposal |
| RO3 concentration | 0% (1/75) | 3% (316/12466) | 0.314 [0.24, 0.43] | 0.449 / 0.455 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 30% (23/73) | 26% (7441/12460) | 1.096 [0.67, 1.80] | 1.111 / 0.989 | 1.3 [0.0, 8.5] | fails rule |
| U1 repeated single offer | 14% (6/63) | 7% (764/6458) | 1.522 [0.58, 2.79] | 1.55 / 0.931 | 6.1 [0.0, 14.8] | fails rule |
| U2 repeated direct award | 0% (1/75) | 3% (261/12466) | 0.302 [0.24, 0.42] | 0.418 / 0.455 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 14% (6/75) | 10% (876/12468) | 1.131 [0.52, 1.98] | 0.992 / 1.012 | 1.8 [0.0, 9.8] | fails rule |
| N2 weekend signature | 0% (0/75) | 0% (21/12468) | 0.244 [0.24, 0.24] | 0.345 / 0.455 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 35% (14/75) | 12% (233/12466) | 2.218 [1.33, 3.97] | 2.167 / 1.491 | 11.5 [4.1, 19.9] | proposal |
| N5 first-time supplier | 50% (21/67) | 44% (1966/10968) | 1.101 [0.85, 1.40] | 1.083 / 1.068 | 1.4 [0.0, 4.8] | fails rule |

### weighted by appeal outcome, one per decision (decision rule, amendment 2026-10-15): 20 labelled (17 buyers), 12520 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 20% (2.91/16.55) | 30% (1750.9/5863.78) | 0.793 [0.44, 1.22] | 0.84 / 0.861 | 0.0 [0.0, 2.8] | fails rule |
| RO1 direct award | 0% (0.0/19.28) | 13% (599.09/12473.59) | 0.378 [0.32, 0.47] | 0.462 / 0.675 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 45% (8.73/19.28) | 19% (138.44/12465.59) | 1.793 [1.07, 3.01] | 1.646 / 1.345 | 8.4 [1.0, 15.9] | proposal |
| RO3 concentration | 6% (0.91/19.28) | 3% (316.09/12470.59) | 1.089 [0.33, 2.33] | 1.366 / 0.675 | 1.2 [0.0, 12.2] | fails rule |
| RO5 framework / subsequent | 38% (6.73/18.28) | 25% (7442.17/12464.5) | 1.268 [0.73, 2.16] | 1.178 / 1.182 | 3.4 [0.0, 11.1] | fails rule |
| U1 repeated single offer | 7% (1.0/16.55) | 7% (764.27/6461.87) | 0.91 [0.36, 1.73] | 1.04 / 0.675 | 0.0 [0.0, 7.9] | fails rule |
| U2 repeated direct award | 0% (0.0/19.28) | 3% (261.09/12470.59) | 0.378 [0.32, 0.47] | 0.462 / 0.675 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 18% (2.91/19.28) | 10% (876.36/12472.59) | 1.329 [0.41, 2.77] | 1.168 / 1.212 | 4.1 [0.0, 14.7] | fails rule |
| N2 weekend signature | 0% (0.0/19.28) | 0% (21.0/12472.59) | 0.378 [0.32, 0.47] | 0.462 / 0.675 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 41% (6.73/19.28) | 13% (233.81/12470.59) | 2.193 [1.16, 3.89] | 2.483 / 1.032 | 11.3 [2.1, 19.6] | proposal |
| N5 first-time supplier | 50% (6.82/14.46) | 44% (1967.26/10972.32) | 1.07 [0.74, 1.42] | 1.114 / 0.946 | 1.0 [0.0, 5.0] | fails rule |

### weighted by appeal outcome, all procedures: 75 labelled (31 buyers), 12520 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 29% (13.1/57.22) | 30% (1750.9/5863.78) | 0.968 [0.60, 1.41] | 0.93 / 0.997 | 0.0 [0.0, 5.0] | fails rule |
| RO1 direct award | 2% (1.91/70.41) | 13% (599.09/12473.59) | 0.331 [0.25, 0.49] | 0.443 / 0.468 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 45% (21.56/70.41) | 19% (138.44/12465.59) | 1.948 [1.39, 2.99] | 1.789 / 1.568 | 9.6 [4.7, 15.8] | proposal |
| RO3 concentration | 0% (0.91/70.41) | 3% (316.09/12470.59) | 0.321 [0.25, 0.44] | 0.455 / 0.468 | 0.0 [0.0, 0.0] | fails rule |
| RO5 framework / subsequent | 30% (21.83/68.5) | 25% (7442.17/12464.5) | 1.113 [0.68, 1.81] | 1.118 / 1.01 | 1.6 [0.0, 8.6] | fails rule |
| U1 repeated single offer | 14% (5.73/59.13) | 7% (764.27/6461.87) | 1.525 [0.58, 2.77] | 1.52 / 0.966 | 6.1 [0.0, 14.7] | fails rule |
| U2 repeated direct award | 0% (0.91/70.41) | 3% (261.09/12470.59) | 0.314 [0.25, 0.43] | 0.432 / 0.468 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 14% (5.64/70.41) | 10% (876.36/12472.59) | 1.136 [0.52, 2.00] | 1.013 / 1.018 | 1.8 [0.0, 10.0] | fails rule |
| N2 weekend signature | 0% (0.0/70.41) | 0% (21.0/12472.59) | 0.253 [0.25, 0.26] | 0.356 / 0.468 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 34% (13.19/70.41) | 13% (233.81/12470.59) | 2.094 [1.29, 3.54] | 2.108 / 1.393 | 10.7 [3.7, 18.2] | proposal |
| N5 first-time supplier | 50% (19.74/62.68) | 44% (1967.26/10972.32) | 1.086 [0.84, 1.36] | 1.08 / 1.043 | 1.2 [0.0, 4.5] | fails rule |

### all findings, 2+ offers (sensitivity): 47 labelled (21 buyers), 4189 comparisons

| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |
|---|---|---|---|---|---|---|
| RO0 single offer | 0% (0/47) | 0% (0/4108) | 0.323 [0.29, 0.39] | 0.435 / 0.556 | 0.0 [0.0, 0.0] | fails rule |
| RO1 direct award | 0% (0/47) | 2% (81/4189) | 0.323 [0.29, 0.39] | 0.435 / 0.556 | 0.0 [0.0, 0.0] | fails rule |
| RO2 buyer share >= 5 % | 45% (14/47) | 13% (62/4185) | 2.466 [1.51, 4.76] | 2.262 / 1.621 | 13.0 [6.0, 22.5] | proposal |
| RO3 concentration | 2% (1/47) | 2% (54/4189) | 0.618 [0.29, 1.39] | 0.826 / 0.556 | 0.0 [0.0, 4.8] | fails rule |
| RO5 framework / subsequent | 27% (9/46) | 20% (1398/4188) | 1.182 [0.68, 1.93] | 1.199 / 1.018 | 2.4 [0.0, 9.5] | fails rule |
| U1 repeated single offer | 0% (0/47) | 0% (0/4189) | 0.323 [0.29, 0.39] | 0.435 / 0.556 | 0.0 [0.0, 0.0] | fails rule |
| U2 repeated direct award | 0% (0/47) | 1% (18/4189) | 0.323 [0.29, 0.39] | 0.435 / 0.556 | 0.0 [0.0, 0.0] | fails rule |
| N1 December signature | 10% (2/47) | 9% (269/4189) | 0.956 [0.31, 2.23] | 0.435 / 1.094 | 0.0 [0.0, 11.6] | fails rule |
| N2 weekend signature | 0% (0/47) | 0% (14/4189) | 0.323 [0.29, 0.39] | 0.435 / 0.556 | 0.0 [0.0, 0.0] | fails rule |
| N4 supplier dependence >= 25 % | 25% (6/47) | 8% (30/4189) | 2.067 [0.86, 5.52] | 2.184 / 1.246 | 10.5 [0.0, 24.6] | fails rule |
| N5 first-time supplier | 54% (12/41) | 51% (897/3147) | 1.032 [0.78, 1.34] | 1.002 / 1.061 | 0.5 [0.0, 4.3] | fails rule |
