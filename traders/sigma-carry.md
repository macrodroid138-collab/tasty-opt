# Sigma Carry

Id: `sigma-carry`. This is the trader called **Current** in the comparison. It sells the condor and carries whatever survives to 15:15. It has no profit target and no dollar stop. Every shared rule is in `traders/SHARED.md` and is part of this trader.

## Daily procedure

Do this in order. Prices below are scaled: `scaled = real * 691 / open_0930`.

**Prior close, once the chain is up**

1. Solve `sig` for the expiration of the next session, using the procedure in SHARED. Hold that number. Do not replace it with a 10:30 reading.
2. Record today's full-session high minus low, in scaled points. That is tomorrow's prior range.

**10:30:00**

3. If the prior session ended more than 10 calendar days ago, forget its range. If the prior range is 16 scaled points or more, stop. Book $0. Leave any loss-skip flag as it is.
4. If `sig < 0.11`, stop. Book $0. Leave the flag.
5. Let `anchor` be the scaled price of the first print at or after 10:30.
6. `dist = max(6, round_half_even(anchor * sig * sqrt(T(entry minute))))`, with `T` from SHARED.
7. If the high minus the low of every print from 09:30 up to but not including 10:30 is `≥ dist`, stop. Book $0. Leave the flag.
8. If the loss-skip flag is set, clear it and stop. Book $0. This is the stand-aside day. It is not a loss.
9. Otherwise sell one iron condor:
   - put short `round_half_even(anchor) − dist`, long 5 scaled points lower
   - call short `round_half_even(anchor) + dist`, long 5 scaled points higher
   - one order, at the model mid. Receive `credit × 100`. Pay $4 fees and $2 slippage.

**Each print after the entry print, in time order**

10. Release the pending flag if price has come back inside 4 scaled points of the anchor on the banked side, or if 30 minutes have passed. See SHARED.
11. If price trades 1 scaled point through a short that is still 5 wide, buy the inner 3-wide and leave a 2-wide. Once per wing. One order, $2 fee, $2 slippage.
12. Before 14:30, if price is `dist + 2` scaled points beyond the anchor and the pending flag is clear, buy back the far wing at whatever width it still has. One order. Set the pending flag. Do not sell a replacement. Do not restore the wing if price returns.
13. There is no take-profit. A condor that is up a large credit is held.

**15:15**

14. Buy back every wing that is still open, as one order, marked at the 15:15 scaled price with `T(345)`. Fee $1 per remaining leg, slippage $2.
15. The day's cash is the pnl. If it is strictly negative, set the loss-skip flag. Add the pnl to equity.

## Account, 5 January 2022 through 20 November 2026

One contract, scaled dollars, cold start at $700. Rebuilt by `python3 src/run.py`. Ledger: `results/sigma-carry-daily.csv` and `results/sigma-carry-monthly.csv`.

| | |
|---|---:|
| Ending account | $15,843.35 |
| Profit | $15,143.35 |
| Low | $500.06 on 13 January 2022 |
| Median month | +$243.61 |
| Spread of the months (sample std. dev.) | $322.22 |
| Biggest month | +$1,038.44 (March 2022) |
| Worst month | −$384.98 (December 2024) |
| Red months | 5, totaling −$873.24 |
| Months in the ledger | 48 |
| Trades | 499 |
| Wins / losses | 413 / 86 |
| Win rate | 82.8% |
| Median win / median loss | +$59.58 / −$92.13 |
| Average win / average loss | +$58.27 / −$103.76 |
| Days stood aside after a loss | 86 |
| Range skips | 79 |
| Other flat days (volatility or morning) | 287 |

A 5-wide condor can lose `5 × 100` scaled dollars minus the credit, usually about $440 of buying power. The model never checks that reserve. It sells one condor on every day the rules allow, including days when equity is near the $500 low.

### By year

| Year | P&L | Account at year end | Lowest end-of-day equity |
|---|---:|---:|---:|
| 2022 | +$4,669.30 | $5,369.30 | $500.06 on 13 Jan |
| 2023 | +$4,403.82 | $9,773.12 | $5,339.58 on 25 Jan |
| 2024 | +$1,497.87 | $11,270.99 | $9,773.12 on 2 Jan |
| 2025 | +$2,656.28 | $13,927.27 | $11,223.48 on 2 Jan |
| 2026 | +$1,916.08 | $15,843.35 | $13,957.39 on 28 Aug |

2025 stops at 5 August. 2026 starts at 28 August.

### Every month

Blank cells are the missing hourly stretch, not zeros. August 2025 is present and is $0.00.

| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 71.83 | 254.53 | 1,038.44 | 9.69 | 168.08 | 325.99 | 159.93 | 811.33 | 989.16 | −205.49 | 443.89 | 601.91 |
| 2023 | 123.35 | 706.80 | 537.64 | 493.16 | 710.78 | −32.21 | 232.69 | 359.50 | 359.94 | 740.75 | 76.50 | 94.91 |
| 2024 | 81.17 | 200.99 | 214.29 | 70.98 | −108.91 | 144.09 | −141.65 | 150.92 | 397.85 | 464.56 | 408.56 | −384.98 |
| 2025 | 268.66 | 407.51 | 202.77 | 57.76 | 857.01 | 779.20 | 83.37 | 0.00 | | | | |
| 2026 | | | | | | | | 70.01 | 660.09 | 739.34 | 446.64 | |

The five red months are October 2022 −$205.49, June 2023 −$32.21, May 2024 −$108.91, July 2024 −$141.65, December 2024 −$384.98.

## What this trader will and will not do

It will hold a winning condor until 15:15, so a high-volatility month can print several hundred to a thousand dollars. March 2022 is +$1,038.44. It will also hold a tested 2-wide until 15:15, so a trend that runs through the short and stays there finishes near a $200 loss. December 2024, July 2024, and October 2022 are that loss, repeated. Sigma Clip exists to cut both of those tails.
