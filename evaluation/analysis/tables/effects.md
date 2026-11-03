Paired mean differences, 95% BCa bootstrap CI (10,000 resamples, seed 0).
d_z = mean / sd of the per-uuid contrast. p_holm: Holm over the two main effects and the interaction per analysis and metric.

### A: model x prompt style (mm): CLIP

| Effect | Δ | 95% CI | d_z | p_boot | p_holm | n |
|---|---|---|---|---|---|---|
| model (CKPT8000 - INIT) | -0.0005 | [-0.0026, 0.0015] | -0.05 | 0.6484 | 1.0000 | 100 |
| factor (training - detailed) | 0.0427 | [0.0300, 0.0541] | 0.68 | <0.0001 | <0.0001 | 100 |
| interaction | -0.0005 | [-0.0041, 0.0031] | -0.03 | 0.7610 | 1.0000 | 100 |
| CKPT8000 - INIT within detailed | -0.0002 | [-0.0030, 0.0024] | -0.02 | 0.8814 |  | 100 |
| CKPT8000 - INIT within training | -0.0008 | [-0.0035, 0.0020] | -0.05 | 0.5830 |  | 100 |

### A: model x prompt style (mm): is_watertight

| Effect | Δ | 95% CI | d_z | p_boot | p_holm | n |
|---|---|---|---|---|---|---|
| model (CKPT8000 - INIT) | -0.0350 | [-0.1150, 0.0450] | -0.09 | 0.4072 | 1.0000 | 100 |
| factor (training - detailed) | -0.0450 | [-0.1450, 0.0600] | -0.09 | 0.3972 | 1.0000 | 100 |
| interaction | 0.0500 | [-0.1000, 0.2200] | 0.06 | 0.5884 | 1.0000 | 100 |
| CKPT8000 - INIT within detailed | -0.0600 | [-0.1800, 0.0600] | -0.10 | 0.3514 |  | 100 |
| CKPT8000 - INIT within training | -0.0100 | [-0.1100, 0.1000] | -0.02 | 0.9168 |  | 100 |

### A: model x prompt style (mm): time_shape

| Effect | Δ | 95% CI | d_z | p_boot | p_holm | n |
|---|---|---|---|---|---|---|
| model (CKPT8000 - INIT) | 0.6768 | [0.6622, 0.7070] | 6.51 | <0.0001 | <0.0001 | 100 |
| factor (training - detailed) | 0.0208 | [-0.0349, 0.0507] | 0.10 | 0.3010 | 0.3010 | 100 |
| interaction | 0.1073 | [0.0793, 0.1332] | 0.79 | <0.0001 | <0.0001 | 100 |
| CKPT8000 - INIT within detailed | 0.6232 | [0.6075, 0.6490] | 6.18 | <0.0001 |  | 100 |
| CKPT8000 - INIT within training | 0.7305 | [0.7075, 0.7668] | 5.08 | <0.0001 |  | 100 |

### B: model x unit (detailed): CLIP

| Effect | Δ | 95% CI | d_z | p_boot | p_holm | n |
|---|---|---|---|---|---|---|
| model (CKPT8000 - INIT) | 0.0164 | [0.0118, 0.0213] | 0.67 | <0.0001 | <0.0001 | 100 |
| factor (cm - mm) | -0.0164 | [-0.0211, -0.0122] | -0.74 | <0.0001 | <0.0001 | 100 |
| interaction | 0.0334 | [0.0247, 0.0427] | 0.73 | <0.0001 | <0.0001 | 100 |
| CKPT8000 - INIT within mm | -0.0002 | [-0.0030, 0.0024] | -0.02 | 0.8814 |  | 100 |
| CKPT8000 - INIT within cm | 0.0331 | [0.0246, 0.0422] | 0.73 | <0.0001 |  | 100 |

### B: model x unit (detailed): is_watertight

| Effect | Δ | 95% CI | d_z | p_boot | p_holm | n |
|---|---|---|---|---|---|---|
| model (CKPT8000 - INIT) | n/a: no per-uuid is_watertight for INIT/cm | | | | | |
| factor (cm - mm) | n/a: no per-uuid is_watertight for INIT/cm | | | | | |
| interaction | n/a: no per-uuid is_watertight for INIT/cm | | | | | |
| CKPT8000 - INIT within mm | n/a: no per-uuid is_watertight for INIT/cm | | | | | |
| CKPT8000 - INIT within cm | n/a: no per-uuid is_watertight for INIT/cm | | | | | |

### B: model x unit (detailed): time_shape

| Effect | Δ | 95% CI | d_z | p_boot | p_holm | n |
|---|---|---|---|---|---|---|
| model (CKPT8000 - INIT) | 0.6613 | [0.6355, 0.6865] | 5.04 | <0.0001 | <0.0001 | 100 |
| factor (cm - mm) | -0.0608 | [-0.0762, -0.0294] | -0.56 | <0.0001 | <0.0001 | 100 |
| interaction | 0.0762 | [0.0219, 0.1008] | 0.42 | 0.0004 | 0.0004 | 100 |
| CKPT8000 - INIT within mm | 0.6232 | [0.6075, 0.6490] | 6.18 | <0.0001 |  | 100 |
| CKPT8000 - INIT within cm | 0.6994 | [0.6491, 0.7300] | 3.47 | <0.0001 |  | 100 |
