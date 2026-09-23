# H-SUP-1: bounce-near-trailing-low beats buy-hold

- status: open
- prediction: walk-forward Sharpe(bounce) > Sharpe(uniform buy-hold)
- falsifier: bounce <= buy-hold (fish edge was lookahead/HOLD-label artifact)
- data: atoms + NVDA, 2y daily, trailing-252d low, next-day execution
