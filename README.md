# Launch Shape Matcher

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/tuyulsembilandua-beep/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/tuyulsembilandua-beep/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast for [make.fun](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) competition `gta6-twitch-ccu-forecast-01`: given Twitch's
viewer count for Grand Theft Auto VI up to the end of the first hour of its
release day (2026-11-19 UTC), forecast the count in each of hours 2–24 as
five quantiles (5%, 25%, 50%, 75%, 95%).

## How it works

A launch day on Twitch has a *shape*, not a level: viewers dip in the small
hours, jump when the US East Coast unlocks, sag around midday, then climb to
an evening peak as the US wakes up and Europe settles in. The shape depends
mostly on how much of the audience is already watching in hour 1 — when hour
1 is already huge the day stays flat (peak barely above hour 1); when hour 1
is small the day climbs many-fold. Across the 26 clean past launches in the
kit, log(peak ratio) correlates −0.94 with log(hour-1 print).

For each hour h = 2..24, the program takes the log-ratio
log(viewers_h / viewers_1) of every comparable past launch and combines them
with a Gaussian kernel centred on this case's hour-1 print (bandwidth 0.75
in log space): launches whose hour-1 print was close to ours count most.
The forecast median is the kernel-weighted TRIMMED MEAN of the log-ratios
— the lowest and highest 20% of the total kernel weight are dropped before
averaging. The plain weighted median is robust but throws away most of the
information in the matched launches; the plain weighted mean uses it all
but is dragged by the odd launch whose shape is nothing like the rest.
The trimmed mean sits between them, and beats the median on both the
practice cases (0.171 vs 0.186) and leave-one-out cross-validation over
the 18 big comparables (0.258 vs 0.261).
The spread is the kernel-weighted standard deviation around it, shrunk by 0.75
(the raw cross-launch spread overstates how uncertain a matched launch is),
with a floor of 0.25 in log space. Quantiles are the normal quantiles of
that log-scale distribution, exponentiated and scaled by the hour-1 print.

Only comparables marked `Tier: comparable` are used. Early-access
contaminated launches, weak analogues and the target game's own pre-release
history are left out. With too few clean comparables it falls back to every
comparable that is not early-access, weak or the target's own history; with
none at all it falls back to a flat forecast (median = hour-1 print, spread
widening as 0.15·√(h−1)).

## Local practice scores

The kit's `grade-local` cannot grade this competition (scorer and reference
data are not published in the kit), so the practice answers were rebuilt
from the same public source the kit used (SullyGnome hourly averages) and
scored with a local pinball-loss scorer. All four practice hour-1 prints
reproduced exactly from that source, and the scorer reproduces the house
baseline's published practice numbers (loss 0.387, typical miss 82.8%,
90% coverage 0.783), which validates both.

| case | game | Launch Shape Matcher | house baseline |
| ---- | ---- | -------------------- | -------------- |
| p00 | Marvel's Wolverine | 0.2508 | 0.7436 |
| p01 | Red Dead Redemption 2 | 0.1327 | 0.2868 |
| p02 | God of War Ragnarök | 0.1037 | 0.2146 |
| p03 | Marvel's Spider-Man 2 | 0.1981 | 0.3033 |
| **mean** | | **0.1713** | **0.3871** |

Typical miss 29.5% (baseline 82.7%), 90% coverage 0.935 (baseline 0.783).
Leave-one-out cross-validation over the 18 big comparables (hour-1 ≥ 10k)
gives 0.258 vs the baseline's 0.392, so the edge is not just the four
practice cases. (Before the trimmed-mean centre: practice 0.1862 —
p00 0.3048, p01 0.1316, p02 0.1182, p03 0.1903 — LOO 0.261, miss 35.0%.)

## Running

```sh
MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` in the input directory and writes one `*.out` per case.
Standard library only, deterministic (two runs are byte-identical), ~0.05 s
per case — well inside the 8 s cap.

---

<sub>Entered on [make.fun](https://make.fun/?ref=h914r6pd&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
