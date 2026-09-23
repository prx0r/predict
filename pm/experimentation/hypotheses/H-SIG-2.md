# H-SIG-2: biweekly grid rescues the signal test

- status: open
- prediction: holdout Sharpe(composite) > Sharpe(momentum) on 8 biweekly dates
- falsifier: composite <= momentum (factors add nothing at any grid)
- data: data/predict/biwk-*.jsonl; parent H-SIG-1
