# Sigma Clip

Id: `sigma-clip`. This is the trader called **With the two exits**. It is Sigma Carry with two added exits and no other change. Strikes, distance, skips, loss-skip, costs, volatility, and the far-wing buyback are identical. Read `traders/SHARED.md` and `traders/sigma-carry.md` first. The only code difference is `clip=True` in `src/engine.py`.

## The two exits

Both are scaled dollars. Both are one order.

**Early buyback.** On a print where both wings are still the original 5-wide, compute the cost to buy the whole condor back at the model mid. If that cost is less than or equal to `0.40 ×` the opening credit, buy it back now and stop for the day.

```
cost = put_spread_mark + call_spread_mark
if cost <= 0.40 * opening_credit:
    pnl += −cost × 100 − $4 fee − $2 slippage
    done
```

This fires only while both wings are untouched. Once either wing has been cut to 2-wide, or bought back, the early buyback is no longer available. What remains is managed by the touch, the far-wing buyback, the stop below, and the 15:15 close.

Checked on each print after the pending-flag update and before the touch test. If the same print would also have touched a short, the buyback happens and the touch does not.

**$100 stop.** On a print where any wing is still open, compute the cash that would remain if the remains were bought back right now as one order (fee $1 per remaining leg, slippage $2). If that cash is `≤ −100`, flatten at that mark and stop for the day. The stop is checked after the touch step and before the far-wing buyback, so a touch and a stop can both happen on the same print: the wing is cut first, then the whole remainder is flattened if the loss has reached $100.

The stop is not a stop on one wing. It is a stop on the day's pnl.

There is still no restore, no rebuild, and no second condor.

## Daily procedure

Steps 1 through 9 are Sigma Carry's, unchanged, including the 10:30 entry, the `max(6, one sigma)` distance, the 0.11 volatility floor, the morning-range skip, the 16-point prior-range skip, and the loss-skip.

Then, on each later print, in this order:

1. Release the pending flag, same as Carry.
2. If both wings are still 5 wide and the condor can be bought for 40% of the opening credit or less, buy it, book the day, and stop.
3. Cut a touched 5-wide to a 2-wide, same as Carry.
4. If the day's liquidation value is $100 or worse, flatten everything and stop.
5. Before 14:30, buy back the far wing when price is `dist + 2` past the anchor, same as Carry.
6. At 15:15, close whatever is left, same as Carry.
7. A strictly negative day sets the loss-skip flag, same as Carry.

## Account, same window as Sigma Carry

| | Sigma Carry | Sigma Clip |
|---|---:|---:|
| Ending account | $15,843.35 | $10,815.17 |
| Low | $500.06 on 13 Jan 2022 | $628.88 on 11 Jan 2022 |
| Median month | +$243.61 | +$210.04 |
| Spread of the months | $322.22 | $201.71 |
| Biggest month | +$1,038.44 | +$751.65 |
| Worst month | −$384.98 | −$231.08 |
| Red months | 5, totaling −$873.24 | 4, totaling −$694.56 |

| | |
|---|---:|
| Profit | $10,115.17 |
| Trades | 519 |
| Wins / losses | 453 / 66 |
| Win rate | 87.3% |
| Median win / median loss | +$40.72 / −$109.61 |
| Average win / average loss | +$37.94 / −$107.16 |
| Days stood aside after a loss | 66 |
| Range skips | 79 |
| Other flat days | 287 |

The median loss sits near −$110 because the stop is checked on 5-minute prints. Price can move past −$100 between prints, and the flatten still pays a fee and $2 of slippage.

Ledger: `results/sigma-clip-daily.csv` and `results/sigma-clip-monthly.csv`.

### By year

| Year | P&L | Account at year end |
|---|---:|---:|
| 2022 | +$3,787.96 | $4,487.96 |
| 2023 | +$2,693.07 | $7,181.04 |
| 2024 | +$778.39 | $7,959.43 |
| 2025 | +$1,842.21 | $9,801.64 |
| 2026 | +$1,013.52 | $10,815.17 |

### Every month

| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 53.58 | 129.59 | 751.65 | 341.10 | 380.81 | 381.67 | 152.74 | 469.61 | 696.46 | −219.57 | 222.50 | 427.84 |
| 2023 | 230.68 | 296.74 | 406.01 | 244.93 | 344.45 | 22.67 | 126.52 | 290.83 | 122.97 | 426.93 | 40.31 | 140.02 |
| 2024 | 54.67 | 83.93 | 90.76 | −187.62 | 223.78 | 75.30 | −231.08 | 93.03 | 150.42 | 253.37 | 228.12 | −56.28 |
| 2025 | 197.59 | 309.91 | 182.80 | 372.99 | 363.67 | 256.08 | 111.79 | 47.38 | | | | |
| 2026 | | | | | | | | 33.64 | 477.32 | 408.14 | 94.42 | |

The four red months are October 2022 −$219.57, April 2024 −$187.62, July 2024 −$231.08, December 2024 −$56.28.

March, April, and May 2022, which were +$1,038.44, +$9.69, and +$168.08 under Sigma Carry, are +$751.65, +$341.10, and +$380.81 here.

## Why the account is smaller

The early buyback sells the rest of a quiet day's credit in exchange for not being there if the afternoon trends. The stop sells the last part of a trend day's loss, and it also cuts some days that would have come back after being down $100. Carry keeps both of those. Clip's 2023 has no red month and no month over $430. Carry's 2023 runs from −$32 to +$741.
