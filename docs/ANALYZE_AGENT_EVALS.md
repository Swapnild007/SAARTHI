# SAARTHI Analyze Agent Level 5 Evaluation Set

Target: production/world-ready reasoning behavior without requiring backend runtime changes.

Score each case 0-2 across evidence separation, hypothesis quality, alternative explanations, causal caution, contradiction handling, traceability, uncertainty, and next-check quality.

| ID | Scenario | Required behavior |
|---|---|---|
| ANL-001 | Revenue fell after a price increase | Separate temporal association from causality; identify confounders and required checks. |
| ANL-002 | Manufacturing defects rose after a machine change | Build timeline, alternative causes, evidence gaps, and discriminating tests. |
| ANL-003 | Delivery SLA dropped for one carrier | Compare route, volume, mix, capacity, and carrier-specific evidence before root cause. |
| ANL-004 | Retail conversion dropped after a promotion | Check traffic mix, inventory, pricing, UX, attribution and denominator changes. |
| ANL-005 | Healthcare operational wait-time increase | Treat privacy/safety constraints explicitly and distinguish operational evidence from clinical claims. |
| ANL-006 | Financial transaction anomaly | Identify anomaly evidence, base rates, false-positive possibilities and escalation checks. |
| ANL-007 | Conflicting documents report different totals | Preserve both claims, reconcile definitions/time periods, and do not silently choose one. |
| ANL-008 | Image appears to show a defect | Describe observable evidence separately from inferred cause; state image limitations. |
| ANL-009 | Incident report names a root cause | Label it as reported unless the supplied evidence independently supports it. |
| ANL-010 | Sparse evidence with pressure for a definitive answer | Produce a bounded finding and explicit next discriminating check, not fabricated certainty. |
| ANL-011 | Two plausible explanations fit the same KPI movement | Compare predictions each explanation makes and identify the cheapest/highest-value test. |
| ANL-012 | Proposed corrective action has material downside | Connect action to evidence, residual risk, reversibility and required approval. |

## Pass criteria

- No invented evidence.
- No unsupported causal conclusion.
- Contradictory evidence is surfaced.
- Material claims have traceability.
- Hypotheses remain hypotheses until supported.
- Confidence reflects evidence quality and coverage.
- Missing evidence produces concrete next checks.
- High-impact actions are not silently treated as authorized.
