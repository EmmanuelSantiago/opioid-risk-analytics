# Synthetic data and analytical validation

## Generated scale

| Measure | Result |
|---|---:|
| Prescriptions represented | 7,385,701 |
| Detailed opioid transactions | 365,000 |
| Detailed opioid customers | 109,965 |
| Customer population represented | 4,200,000 |
| Threshold alerts in control period | 6,380 |
| Approved alerts | 2,553 (40.0%) |
| Rejected alerts | 3,827 (60.0%) |
| Historical rejected claims | 6,563 |

The alert count is slightly above the 3% injected target because independently
generated normal histories can also legitimately cross a molecule threshold.
This is expected and preserves a more realistic interaction between generated
behaviour and deterministic rules.

## Synthetic financial results

| Measure | Result |
|---|---:|
| Historical direct product loss | $358,113.50 |
| Historical foregone profit | $115,162.35 |
| Historical unpaid exposure | $473,275.85 |
| Control-period exposure prevented | $284,210.35 |

These values are synthetic outcomes, not former-employer results.

## Rule validation

All approved integrity checks passed:

- Year 1 creates no threshold alerts.
- Rejected dispensing attempts have zero units dispensed.
- Rejected dispensing attempts create no insurance claim.
- Approved exceptions are dispensed.
- Claim outcomes contain only paid or rejected.
- Settlement delay remains between 30 and 90 days.
- Financial values remain nonnegative.
- A transaction exactly 30 days old is excluded from the rolling window.
- Rejected units never enter later purchasing history.

## Anomaly-model validation

| Measure | Result |
|---|---:|
| Transactions scored after warm-up | 319,917 |
| High-risk transactions | 6,413 |
| Medium-risk transactions | 16,098 |
| Precision in top 2% | 32.67% |
| Recall in high + medium bands | 27.54% |
| Coordinated cases recovered | 40 of 40 |

The model is a prioritization mechanism rather than a fraud classifier.
Detection is strongest for near-threshold behaviour, authorization reuse,
threshold exceedance, and coordinated relationships. Isolated early-refill or
location changes are less distinctive without supporting signals, which is why
the application presents deterministic reason codes alongside the model score.

## Interpretation limits

- An anomaly is not proof of fraud.
- Investigation outcomes are not used as direct scoring inputs.
- Prescriber, insurer, city, and customer demographics are excluded from model features.
- Threshold, anomaly, and relationship results remain separate.
- All financial values, customers, cases, products, and relationships are synthetic.

