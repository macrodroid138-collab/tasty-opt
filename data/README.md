# Inputs the two traders read

These files are the study, Wednesday 5 January 2022 through Friday 20 November 2026, plus Tuesday 4 January 2022 so the first day has a prior range. Half-days are already removed. The hourly-bar stretch from 6 August 2025 through 27 August 2026 is not in the files.

`sessions.parquet`

| column | meaning |
|---|---|
| day | session date |
| close_px | scaled price used as the 15:15 mark |
| range_pts | full-session high minus low, in scaled points, through 16:00 |
| label | path label from the older census. The traders do not read it. |

`path.parquet`

| column | meaning |
|---|---|
| day | session date |
| minute | minutes after 09:30. Every value is strictly less than 345. |
| scaled | price after the open has been mapped to 691 |

Each 5-minute bar, stamped at its start, contributes four prints at +0, +1.25, +2.5 and +3.75 minutes. If the bar's close is at or above its open, the four prices are open, low, high, close. If the bar's close is below its open, they are open, high, low, close.

`session_iv.csv`

| column | meaning |
|---|---|
| day | session the volatility is used on |
| sig | annualized volatility, held constant for that entire session |
| iv_source | `0dte`, `front`, or `vix10`. See `traders/SHARED.md`. |

`sig` on a day is known before that day's open. It is the prior close, not a 10:30 print.
