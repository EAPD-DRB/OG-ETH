# Corrected-run interpretation notes (working)

All figures = % deviation of reform path from the CORRECT Ethiopia baseline
(g_n_ss ~2.0%/yr). Variables are intensive (per effective worker), detrended.
Columns shown: 2025 (impact), 2026, 2030, avg 2025-34, SS (long run).

## Dimension 1 — Demographics (DONE)

### D2 — Accelerated fertility decline (-25% fertility)
GDP +7.1 -> +0.08 SS; Cons +32.5 -> +0.15; Capital +20.9 -> +0.11;
Labour -11.2 -> 0; r -17.3 -> -0.05; wage +20.6 -> +0.08.

### D3 — Youth-mortality shock (+15% mortality ages 20-35)
GDP +7.35 -> +0.23 SS; Cons +31.8 -> +0.22; Capital +21.2 -> +0.42;
Labour -10.8 -> -0.03; r -17.2 -> -0.29; wage +20.4 -> +0.26.

### D4 — High fertility (+20% fertility)
GDP +7.08 -> -0.04 SS; Cons +32.6 -> -0.08; Capital +20.9 -> -0.06;
Labour -11.2 -> 0; r -17.3 -> +0.03; wage +20.6 -> -0.04.

KEY READINGS:
- Demographic variants reshape the TRANSITION strongly but leave the long-run
  per-worker steady state almost unchanged (SS ~0). Long-run signs are correct:
  lower fertility (D2) slightly raises per-worker GDP (+0.08), higher fertility
  (D4) slightly lowers it (-0.04). Capital-deepening channel.
- The large positive short-run per-worker GDP/Cons/Capital/wage and negative
  Labour are a CAPITAL-PER-WORKER (denominator) effect: a predetermined capital
  stock spread over fewer effective workers raises K/L, wages, output per worker
  and lowers r. This is intensive-margin, NOT aggregate welfare.
- CAUTION for policymakers: D3 (a youth-mortality CRISIS) shows +7% GDP/worker
  and +32% consumption/worker. This is NOT good news — it is the arithmetic of a
  smaller workforce sharing the same capital. Aggregate output and population are
  lower; welfare is worse. Per-worker intensive metrics mechanically rise.
- Implication: the dividend that matters for living standards comes from raising
  productivity PER worker (Dimensions 2-4), not from shrinking the denominator.

## Dimension 2 — Education & Human Capital (E3/E4 DONE; E2 FAILED to converge)

### E2 — Moderate TVET (+10% youth efficiency)  [SOLVER FAILED, skipped]
No usable solution this run (TPI did not converge). By near-linear E3->E4
dose-response, long-run GDP ~ +4 to +5%.

### E3 — Strong university quality (+20% youth efficiency)
GDP +16.0 -> +8.93 SS; Cons +37.2 -> +8.80; Capital +28.4 -> +8.82;
Labour +0.9 -> +9.07; r -14.7 -> +0.15; wage +15.0 -> -0.13.

### E4 — Combined max (+25% youth efficiency)
GDP +18.2 -> +11.15 SS; Cons +38.6 -> +11.00; Capital +30.3 -> +11.03;
Labour +3.9 -> +11.31; r -14.1 -> +0.16; wage +13.7 -> -0.14.

KEY READINGS:
- A PERMANENT per-worker dividend: raising youth productivity lifts long-run
  GDP/consumption/capital per worker ~one-for-one with the efficiency gain
  (+20% -> +8.9%, +25% -> +11.2%). This is genuine living-standards growth.
- Capital fully chases the more-productive workforce: K rises ~in line with
  effective labour, so the long-run interest rate and capital-output ratio
  return to baseline (r SS ~ +0.15%). Wage per efficiency unit ~flat long run,
  but total labour income per worker rises with productivity.
- Front-loaded consumption: +37-39% on impact (households anticipate higher
  lifetime income and borrow/dissave early) easing to a +9-11% permanent level.
- Dose-response is near-linear, so reform intensity maps cleanly to the gain.
