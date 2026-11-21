# Manifesto

Sigma Carry and Sigma Clip sell one SPY zero-day iron condor a day, on a
price that has been scaled so the 09:30 open is always 691. They share the
entry, the skips, and the wing rules. Clip adds two exits. Each trader is a
separate program, with its own loss-skip record, and each program has a demo
mode and a live Tastytrade mode.

The backtest numbers in this document are the study, from 5 January 2022
through 20 November 2026, one contract, cold start at $700. They are not a
promise about a live account. A live fill is a listed strike and a walked
limit. The study fills at the model mid, on a synthetic whose open is 691.

## Scaled prices

`scaled = real price × 691 / that morning's open`.

Every distance in the rules is in these points.

| Rule | Scaled points | Share of the open |
| --- | ---: | ---: |
| Minimum short-strike distance | 6 | 0.868% |
| Far-wing buyback, beyond the short | +2 | 0.289% |
| Wing width | 5 | 0.724% |
| Touch, through the short | 1 | 0.145% |
| Return that clears a pending flag | 4 | 0.579% |
| Prior-day range that skips today | 16 | 2.32% |

Fees are $1 a leg. Slippage is $0.02 of premium once per order, which is $2.
Clip's stop is $100. None of those grow when the real SPY price grows, and
none of them grow with the account. The position is one contract. A real
premium profit is about `scaled profit × (open / 691)`. The $1 and $2 charges
stay as they are.

Listed strikes are chosen at the open: `real strike = scaled strike × open / 691`,
then the nearest listed strike. That choice will not reprint the ledger.

## The study

951 sessions, 5 January 2022 through 20 November 2026. Half days are out.
The hourly gap from 6 August 2025 through 27 August 2026 is out. The path is
5-minute SPY bars. Each bar becomes four prints, at the bar time and then
1.25, 2.50, and 3.75 minutes later. A bar that closes above its open is read
open, low, high, close. A bar that closes below is read open, high, low,
close. Trading looks at prints before minute 345. The 15:15 mark is a
separate close price.

The first hour is every print before minute 60. Entry is the first print at
or after minute 60, which is 10:30. That entry print is not scanned for a
touch or a far-wing buyback. Management starts on the next print. The far-wing
buyback is allowed before minute 300, which is 14:30. The close is minute 345.

Black-Scholes is European, rate 4.3%, dividend yield 1.2%. Time left at a
minute is `max((390 − minute) / 60, 0.02) / 6.5 / 252`. A call spread is the
call at the short minus the call five points higher, until a wing is cut. A
put spread is the put at the short minus the put five points lower. Prices
are floored at zero. Rounding of the distance and of the anchor uses
banker's rounding, the same as Python's `round`.

## Volatility

The study holds one volatility number for the whole session. It is known
before the open. It is not the same day's closing zero-day chain.

- 811 sessions use the prior close of the contract that expires today. The
  number is solved from the call and put mids, put-call parity, and
  Black-Scholes, with the sessions left divided by 252. Quotes wider than
  $0.40 are dropped. The solver searches from 2% to 350%.
- 80 Tuesday and Thursday sessions before the week of 14 November 2022 had no
  same-day expiry. Those use the nearest listed expiration.
- 60 sessions from 28 August 2026 through 20 November 2026, after the chain
  ends, use 0.83 times the 10:00 reading of the VIX. 0.83 is the median ratio
  of the solved chain volatility to the 10:00 VIX on 146 overlap days in 2025.

A live session does not use that prior-close number. Around 10:00 the program
takes one sanitized at-the-money snapshot and freezes it. That frozen number
is the skip and the strike distance for the day. The order itself is priced
from the live package median, not from the frozen number. The 20-cent model
screen compares the package to Black-Scholes at the frozen number. The
four-second quote loop does not recompute volatility.

## Shared rules

These are the rules of both traders. `src/engine.py` is the copy that the
backtest runs. The order inside a print is fixed.

1. If the prior session's high minus low was at least 16 scaled points, and
   the calendar gap to that session is 10 days or less, sell nothing. A longer
   gap drops the prior range. This skip does not consume a loss-skip, and it
   does not clear one that is already set.
2. If the frozen volatility is under 11%, sell nothing. Same treatment: no
   loss-skip is consumed or cleared.
3. If the first hour already ranged at least as far as today's short-strike
   distance, sell nothing. Same treatment.
4. Otherwise sell one iron condor at 10:30. The distance is
   `max(6, round(anchor × volatility × sqrt(time left)))`. The put short is
   `round(anchor) − distance`. The call short is `round(anchor) + distance`.
   The longs are five points further out. Opening is one order: four legs,
   $4 of fees, $2 of slippage.
5. If price trades one point through a short that is still five wide, buy the
   inner three-wide once and leave a two-wide. The put cut buys the put
   spread from `short − 2` with width 3. The call cut buys the call spread
   from `short + 2` with width 3. Two legs, $2 of fees, $2 of slippage. The
   wing is not restored and nothing is sold to replace it.
6. While no far-wing buyback is pending, and the minute is before 300, a
   print at least `distance + 2` points beyond the anchor buys back the far
   wing. The call wing is checked first, so a single print cannot bank both.
   That buyback sets a pending flag. The other wing cannot be banked until
   price comes back inside four points of the anchor on that side, or until
   30 minutes pass. The pending flag does nothing else, because a cut wing is
   never rebuilt.
7. At 15:15, buy back whatever is still open, as one order.

A finished day with pnl strictly below zero sets the loss-skip. The next
session that would actually have been traded is skipped, and the flag clears.
A win stays full size. An exact zero does not set the flag and does not clear
one. There is no half size. The account is one running balance from $700. The
model does not check buying power. A five-wide needs about `(5 − credit) × 100`
scaled dollars, usually a little over $400.

## Sigma Carry

Carry is the shared rules and nothing more. There is no early buyback and no
dollar stop.

Cold start 5 January 2022, one contract, through 20 November 2026:

| | |
| --- | ---: |
| Ending equity | $15,843.35 |
| Profit | $15,143.35 |
| Lowest equity | $500.06 on 13 January 2022 |
| Months | 48 |
| Median month | $243.61 |
| Month spread (sample) | $322.22 |
| Biggest month | March 2022, $1,038.44 |
| Worst month | December 2024, −$384.98 |
| Red months | 5, totaling −$873.24 |
| Trades | 499 |
| Wins / losses | 413 / 86 |
| Win rate | 82.77% |
| Median win / median loss | $59.58 / −$92.13 |
| Average win / average loss | $58.27 / −$103.76 |
| Loss-skips | 86 |
| Range skips | 79 |
| Other flat sessions | 287 |

Year-end equity: 2022 $5,369.30, 2023 $9,773.12, 2024 $11,270.99,
2025 $13,927.27, 2026 $15,843.35.

The five red months, to the cent: October 2022 −$205.49, June 2023 −$32.21,
May 2024 −$108.91, July 2024 −$141.65, December 2024 −$384.98. August 2025 is
$0.00 because the study stops on 5 August. The monthly file is
`results/sigma-carry-monthly.csv`. The daily file is
`results/sigma-carry-daily.csv`.

## Sigma Clip

Clip is Carry plus two exits. They are checked in this order, after the
pending flag has been updated and before the far-wing buyback.

1. Early buyback. While both wings are still the original five-wide, if the
   package costs 40% or less of the opening credit, buy the whole condor.
   One order, $4 of fees, $2 of slippage. The day is over. A print that would
   also touch takes this buyback instead.
2. Touch, under the shared rule.
3. Dollar stop. After the touch, if buying back whatever remains would leave
   the day at −$100 or worse, flatten and stop. A touch and a stop can both
   happen on the same print: cut first, then flatten.

| | Carry | Clip |
| --- | ---: | ---: |
| Ending equity | $15,843.35 | $10,815.17 |
| Lowest equity | $500.06 | $628.88 on 11 January 2022 |
| Median month | $243.61 | $210.04 |
| Month spread | $322.22 | $201.71 |
| Biggest month | $1,038.44 | March 2022, $751.65 |
| Worst month | −$384.98 | July 2024, −$231.08 |
| Red months | 5, −$873.24 | 4, −$694.56 |
| Trades | 499 | 519 |
| Wins / losses | 413 / 86 | 453 / 66 |
| Win rate | 82.77% | 87.28% |
| Median win / median loss | $59.58 / −$92.13 | $40.72 / −$109.61 |

Clip's red months: October 2022 −$219.57, April 2024 −$187.62,
July 2024 −$231.08, December 2024 −$56.28. Year-end equity: 2022 $4,487.96,
2023 $7,181.04, 2024 $7,959.43, 2025 $9,801.64, 2026 $10,815.17.
Files: `results/sigma-clip-daily.csv`, `results/sigma-clip-monthly.csv`.

Clip gives up the large months. March, April, and May 2022 were $1,038.44,
$9.69, and $168.08 under Carry, and $751.65, $341.10, and $380.81 under Clip.
Taking the early buyback at half the credit was tighter and made less money,
and it was not adopted. A $120 stop barely changed the account.

## What was tried and left out

These are one-lot variants of the same costs and the 11% floor. None of them
beat Carry on ending equity, the low, and the red months together.

- Shorts at one sigma with no six-point floor ended at $16,755, with a low of
  $472 and six red months.
- Shorts at three-quarters of a sigma ended at $16,342 and never went under
  the starting $700, with nine red months.
- A $120 stop on Carry ended at $15,597.
- Buying back at 30% of the credit ended at $12,543.
- Entering at 11:00 ended at $13,678. Entering at 11:30 ended at $13,117.
- A put spread only ended at $4,981. A call spread only ended at $10,063.
- Puts at 0.75 sigma and calls at 1.25 sigma ended at $12,745.
- Flattening a three-wide on a touch ended at $10,224.
- Fading the morning ended at $12,802. Chasing it with a debit spread lost
  money.

The losses that remain are quiet mornings whose prior-close volatility did
not price the afternoon. 18 December 2024 is the example: volatility 12.8%,
the short stayed at 6, and Carry lost $225.87 after the put was cut at 14:31.
Clip bought that condor back while it was still cheap and finished the day
up $21.65.

## The quote, and the walk

A package quote is admitted only when every leg has a bid above zero, an ask
above the bid, and a spread of 20 cents or less; the legs are within a second
of each other; an opening condor is still a credit; the package has not
jumped by 15 cents or more unless the underlying moved; and the package is
within 20 cents of the frozen Black-Scholes mark. A rejected tick does not
move the median. The last good median stands until a new valid one exists.
If that value is older than eight seconds, it is not tradable. A median needs
at least five samples inside the last four seconds, and it is rounded to the
nearest cent before anyone works an order.

Decisions are made on a four-second clock against that rolling median. The
program does not snapshot one tick every four seconds.

For a credit sale, a worse price is a smaller credit. The same arithmetic
applies to a debit by storing the debit as a number that gets worse in the
same direction inside the walker; the order sent to the broker carries the
real debit.

- Attempt 1 works the current median and records it as the first fire.
- Attempts 2 and 3: if the new median is worse than the working limit, replace
  with the new median. If it is the same or better, resubmit the previous
  working price.
- After three unfilled tries, the next limit is two cents worse than the
  median at that moment.
- The last try is five cents worse than the median at that moment. The five
  cents replaces the two. It is not added to it.
- If the current median itself is more than five cents worse than the first
  fire, cancel. The walk does not chase a market that has run away.
- A concession is always off the median in force at that attempt. A median
  that has already slid, plus the final five cents, can be up to about ten
  cents through the first price. That is the edge that was accepted.

There is one working order. A cancel is acknowledged before a replace. A fill
during the cancel ends the walk. The order is one complex order. If a leg
fills alone, the walk stops and the position is repaired. A second condor is
not sent.

The 10:30 entry and Clip's early buyback take the full six looks, about 24
seconds. A touch, a far-wing buyback, and the $100 stop take two looks: the
median, then five cents worse than the new median. If the underlying is
already another point through the short, the five cents is paid on the first
order. A 24-second walk during a stop can turn a $100 loss into something
much larger.

## Two programs

`programs/sigma-carry/main.py` runs Carry. `programs/sigma-clip/main.py` runs
Clip. They do not import each other. They can share the quote sanitation, the
walker, and the broker session in `programs/common`, because those pieces
have no position in them. Each program keeps its own loss-skip flag. Running
both against one account would put two condors on, so a live deployment runs
one of them.

```
python programs/sigma-carry/main.py --mode demo --day 2024-12-18
python programs/sigma-clip/main.py --mode demo --day 2024-12-18
python programs/sigma-carry/main.py --mode live
```

Demo replays the study. It opens no socket and sends no order. The day's pnl
is the backtest pnl. The quote tape shown at the open is a scripted tape
around the model credit, including one quote that is too wide to admit, so
the sanitation is visible. It is labeled as a tape, not as a historical quote.

Live talks only to `https://api.tastyworks.com`. It refuses to start unless
`TASTY_CLIENT_SECRET`, `TASTY_REFRESH_TOKEN`, and `TASTY_ACCOUNT_NUMBER` are
set. The quote stream is the production DXLink token from
`GET /api-quote-tokens`. Symbols come from the chain. They are not built by
hand. There is no paper flag on the production API, and the certification
site is not a mode of these programs. An order in live mode is a real order.

## The desk

`web/` is the desk. Demo mode loads a session and steps through every
decision: the skip, the entry, each fifteen-minute check, a touch, a
buyback, the stop, the close. The quote tape, the strikes, the wings, the
cash, and the running note are on the screen together. Live mode shows the
broker status and does not replay a day, because a live day is the socket.

```
cd web && npm run dev
```

The desk listens on port 4317.

`python src/run.py` rebuilds both ledgers and checks them against the numbers
in this document.
