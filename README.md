# Sigma Carry and Sigma Clip

Two SPY 0DTE iron-condor traders, saved so either one can be pulled back up by name. They share one entry. They differ only in how the condor is closed.

| | Sigma Carry | Sigma Clip |
|---|---:|---:|
| Also called | Current | With the two exits |
| Ending account | $15,843 | $10,815 |
| Low | $500 | $629 |
| Median month | +$244 | +$210 |
| Spread of the months | $322 | $202 |
| Biggest month | +$1,038 | +$752 |
| Worst month | −$385 | −$231 |
| Red months | 5 | 4 |

Cents, the daily ledger, and the monthly ledger are in the trader files and in `results/`.

## Where each piece lives

| Ask for | Read |
|---|---|
| Sigma Carry, or the current trader | `traders/sigma-carry.md` |
| Sigma Clip, or the two-exit trader | `traders/sigma-clip.md` |
| Strikes, skips, volatility, costs, the scaled dollar | `traders/SHARED.md` |
| The rules as code | `src/engine.py` |
| Rebuild both ledgers and check the accounts | `python3 src/run.py` |
| What the data files are | `data/README.md` |

Sigma Carry holds the condor to 15:15. Sigma Clip buys an untouched condor back once it can be repurchased for 40% of the credit, and flattens the day at a $100 loss. Same distance, same 10:30 entry, same three skips, same loss-skip, same $1-per-leg fee, same $0.02-per-order slippage.

The window is 5 January 2022 through 20 November 2026, one contract, starting equity $700. Dollars are scaled dollars, defined in `traders/SHARED.md`. The open of each session is mapped to 691 before any distance is measured.

## Rebuild

```
pip install -r requirements.txt
python3 src/run.py
```

The script reruns both traders from `data/` and stops if the ending account, the low, or the red-month count drifts from the published figures.
