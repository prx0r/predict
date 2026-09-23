# H-SIG-1: composite beats momentum out-of-sample

- status: open
- prediction: holdout Sharpe(composite) > Sharpe(momentum), same dates/costs
- falsifier: composite <= momentum (factors add nothing)
- data: 12mo monthly panel; train m1-9, holdout m10-12; verdict needs n>=30 rows
