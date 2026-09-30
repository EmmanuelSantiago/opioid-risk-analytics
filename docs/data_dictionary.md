# Data dictionary

## Generated dimensions

| Dataset | Grain | Purpose |
|---|---|---|
| `customers` | One synthetic opioid customer | Insurer and general city relationship |
| `insurers` | One insurer | Six fictional insurance organizations |
| `locations` | One dispensing location | Approximately 100 individually monitored locations |
| `prescribers` | One provider | Context only; excluded from direct risk scoring |
| `molecules` | One regulated molecule | Eight public opioid molecule names |
| `molecule_thresholds` | One effective threshold per molecule | Auditable 30-day controls |
| `products` | One fictional product | Brand, molecule, package units, cost and reimbursement |

## Generated facts

| Dataset | Grain | Purpose |
|---|---|---|
| `prescriptions` | One synthetic prescription | Authorization, provider, supply duration and change approval |
| `dispensing_transactions` | One product-level dispensing attempt | Central threshold and financial analysis |
| `threshold_alerts` | One deterministic Year 2 alert | Approval or rejection workflow |
| `insurance_claims` | One claim for a dispensed product | Paid/rejected outcome and settlement lag |
| `investigation_cases` | One coordinated synthetic case | Group monitoring without police details |
| `case_customers` | One case-customer relationship | Many-to-many investigation membership |
| `daily_network_volume` | One location-day | Represents the complete 7.3M+ prescription environment |

## Analytical outputs

| Dataset | Grain | Purpose |
|---|---|---|
| `anomaly_scores` | One scored dispensing attempt | Behavioural, relationship and priority scores with reasons |
| `monthly_kpis` | One month | Historical loss and prevention trends |
| `molecule_summary` | One molecule | Volume, alerts and exposure prevented |
| `insurer_summary` | One insurer | Contextual transaction and financial comparison |
| `scenario_validation` | One injected scenario type | Model evaluation against hidden synthetic truth |

## Customer self-reference

`dispensing_transactions.recipient_customer_id` and
`dispensing_transactions.collector_customer_id` both reference `customers`.
This reproduces the approved self-join design and identifies customers who
collect prescriptions for other customers without a separate collector table.

