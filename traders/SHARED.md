# Shared rules

Sigma Carry and Sigma Clip are the same trader until the exit. Everything in this file applies to both. Sigma Clip adds two exits, described in `traders/sigma-clip.md`. The normative code is `src/engine.py`. Running `python3 src/run.py` rebuilds both ledgers and checks them against the published accounts.

## What the dollars mean

The backtest does not mark listed SPY strikes. At 09:30 the real open `O` is mapped to 691:

```
scaled = real_price * 691 / O
real   = scaled * O / 691
```

One scaled point is `O / 691` real dollars. Every distance in the rules (6, 16, the short, the 5-wide, the 1-point touch, the 4-point pending release) is in scaled points. Strikes are integers on that scaled series.

Black-Scholes is run on the scaled spot and the scaled strikes. A spread worth 0.65 scaled points is booked as $65. Fees of $1 per leg and slippage of $0.02 per order are charged in that same scaled book. They are not scaled by `691 / O`.

So the published account is one contract on a synthetic whose open is always 691. It is the right account for comparing these two traders to each other. It is larger than one real SPY contract by about `691 / O` on the option-premium part, while the $1 fees stay $1.

To run the rules on real SPY, convert every print to scaled space first and apply the rules there. Map a strike back with `real = scaled * O / 691` and then to the nearest listed strike. A listed-strike fill will not reproduce the ledger, because the ledger never rounded to a listed strike.

Sigma Clip's $100 stop is 100 scaled dollars. In real premium on one SPY contract that is `100 * O / 691` dollars.

## Sample

- Instrument: SPY, regular hours.
- Clock: America/New_York. Minute 0 is 09:30. Minute 60 is 10:30. Minute 300 is 14:30. Minute 345 is 15:15. Minute 390 is 16:00.
- First session: Wednesday 5 January 2022. Cold start. Equity $700. The loss-skip flag is clear. The prior session is 4 January 2022, whose full-session range was 6.34 scaled points, so the range skip does not fire.
- Last session: Friday 20 November 2026.
- Included sessions: 951 from the start date, plus 4 January for the opening range only.
- Excluded: any day with no bar at 15:00 or later, and the stretch from 6 August 2025 through 27 August 2026, which exists only as hourly bars. August 2025 in the ledger is the sessions through 5 August. August 2026 starts 28 August.
- One contract per leg. The account growing from $700 to five figures does not add contracts. The model does not refuse a day whose max loss exceeds equity.

## The day's volatility

`sig` is one number for the whole session, known before the open, and it does not update at 10:30.

Build it at the prior close from the live chain.

1. The contract is the expiration of the next session. On a normal Thursday that is Friday. Across a weekend or a holiday it is the next session, and `T` below counts trading sessions, not calendar days.
2. `T = N / 252`, where `N` is the number of trading sessions from this close until that expiration. For a next-session expiration, `N = 1` and `T = 1/252`.
3. Keep strikes with a bid above zero, an ask at least the bid, and a spread of 0.40 or less.
4. Pair the call and the put at each strike. Mid is `(bid + ask) / 2`.
5. Spot from put-call parity, with `r = 0.043` and `q = 0.012`:

```
S = exp(q T) * (call_mid - put_mid) + K * exp((q - r) T)
```

6. Use the strike closest to that spot, inside 2% of spot.
7. Solve the Black-Scholes volatility of the call mid and of the put mid separately. `sig` is the average of the two. The solver searches from 0.02 to 3.50 for 50 bisections.
8. Discard the same-day 0DTE close. At 16:00 a contract expiring that day is a few cents and its implied volatility is not a usable number. The reading for Wednesday is Tuesday's close of the Wednesday expiration.

When that expiration does not exist, use the nearest listed expiration the same way and keep its `T = N / 252`. In this study that is 80 sessions, all of them Tuesdays and Thursdays before the week of 14 November 2022, which is when SPY started listing an expiration every weekday. Column `iv_source = front`.

When no chain is available, `sig = 0.83 ×` the VIX print at 10:00 ET. The 0.83 is the median, on the 146 sessions in 2025 where both existed, of this prior-close chain volatility divided by that morning's 10:00 VIX. In this study that proxy is 60 sessions, 28 August 2026 through 20 November 2026. Column `iv_source = vix10`. Do not use it on a day that has a chain. The chain days are `iv_source = 0dte` (811 sessions).

Of the 951 sessions, the sources are 811 prior-close 0DTE, 80 nearest listed expiration, 60 VIX proxy.

## Black-Scholes

European, dividend yield `q = 0.012`, rate `r = 0.043`, volatility `sig`, no update during the day.

```
T(minute) = max((390 - minute) / 60, 0.02) / 6.5 / 252
```

The 0.02 hour floor is 1.2 minutes. It applies only if a mark is requested at or after 16:00. The 15:15 close uses `T(345) = 0.75 / 6.5 / 252`.

Call spread, short strike `k`, width `w`: `C(S, k) − C(S, k+w)`.
Put spread, short strike `k`, width `w`: `P(S, k) − P(S, k−w)`.
Each option price is floored at zero.

## Costs

- Fee: $1 per leg, in cash. Opening the condor is four legs, $4. Cutting a wing is two legs, $2. Buying back one wing is two legs, $2. Closing whatever remains charges $1 for each remaining leg.
- Slippage: $0.02 of premium, once per order, which is $2 of cash. The iron condor is one order. Each wing cut is one order. Each far-wing buyback is one order. The 15:15 close of whatever is left is one order, whether one wing or both remain. Sigma Clip's early buyback is one order. Sigma Clip's $100 flatten is one order.
- Slippage is not charged per leg.

## The three skips

A skip books $0 and does not set the loss-skip flag. A skip also does not clear a loss-skip flag that is already set. Only an actual trade can clear it.

1. **Range skip.** Let `R` be the prior session's full-session high minus low, in scaled points, measured through 16:00, not through 15:15. If that prior session is more than 10 calendar days ago, ignore it. If `R ≥ 16`, sell nothing.
2. **Volatility skip.** If `sig < 0.11`, sell nothing.
3. **Morning skip.** Computed at 10:30, after the distance is known. If the high minus low of every path print with minute `< 60` is greater than or equal to that distance, sell nothing. The 10:30 bar itself is not part of the morning range.

## Loss skip

After a trade whose pnl is strictly negative, the next session that is not already a range skip, a volatility skip, or a morning skip is stood aside. That stand-aside books $0 and is not itself a loss. The trade after it is a full condor again. A winning trade leaves the flag clear. A pnl of exactly zero does not set the flag.

There is no quarter-size and no half-size.

## Entry, every traded day

At the first path print with minute `≥ 60`:

```
anchor = that print's scaled price
sigma_points = anchor * sig * sqrt(T(minute))
dist = max(6, round_half_even(sigma_points))     # Python 3 round, then int
```

`round_half_even` is banker's rounding: 0.5 rounds to the even integer.

```
put short  = round_half_even(anchor) - dist
call short = round_half_even(anchor) + dist
put long   = put short - 5
call long  = call short + 5
```

Sell one of each spread. Credit is the sum of the two spread marks at the anchor, at the entry minute. Cash increases by `credit × 100 − 4 − 2`.

The entry print is not scanned for a touch or a bank. Management starts at the next print.

## Management, both traders

Walk prints in time order. On each print, do these steps in this order. Sigma Clip inserts two extra steps, specified in its own file, at the positions marked there. Do not reorder.

1. **Pending release.** If a far wing was bought back and the pending flag is set:
   - direction down, and price has risen to `anchor − 4` or higher: clear the flag
   - direction up, and price has fallen to `anchor + 4` or lower: clear the flag
   - otherwise, if this print's minute is at least 30 minutes after the buyback: clear the flag
   While the flag is set, the other wing cannot be bought back. Nothing is sold to replace a wing. Ever.

2. **Put touch.** If the put wing is still 5 wide and price is at or below `put short − 1`: buy the 3-wide put spread whose short strike is `put short − 2` (long strike `put short − 5`). That converts the position into a 2-wide: short the original put, long the put 2 points below it. Pay the 3-wide's mark times 100, plus $2 fee, plus $2 slippage. This can happen only once on a wing.

3. **Call touch.** Mirror. If the call wing is still 5 wide and price is at or above `call short + 1`: buy the 3-wide call spread whose short strike is `call short + 2`. The wing becomes short the original call, long the call 2 points above it. Same costs.

4. **Far-wing buyback.** Only if the pending flag is clear and the minute is strictly less than 300 (before 14:30):
   - If the call wing is still open and price is at or below `anchor − (dist + 2)`: buy that call wing back at its current width, whatever width the touch step left it. $2 fee, $2 slippage. Set pending direction down, stamped with this minute.
   - Else if the put wing is still open and price is at or above `anchor + (dist + 2)`: buy that put wing back the same way. Set pending direction up.
   - The two sides are not both bought back on the same print. The call is checked first.
   - At or after 14:30 this step does nothing. A wing left on is carried to the close.

5. **Close.** If any wing is still open after the last managed print, buy the remains at minute 345 using `close_px`, the stored 15:15 scaled price, with `T(345)`. One order. Fee $1 per remaining leg. Slippage $2 once.

## What a day of pnl is

Start the day at cash 0. Apply every credit, debit, fee, and slippage above. The resulting cash is the day's pnl in scaled dollars. Add it to equity. Equity starts at $700 before 5 January 2022. Months are calendar months of those daily pnls. A month with no session in the file is absent. August 2025 is present and can be $0. The spread of the months is the sample standard deviation of the monthly sums, divisor `n − 1`, across the 48 months that exist.
