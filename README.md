# Launch Shape Matcher

Forecast for make.fun competition `gta6-twitch-ccu-forecast-01`: given Twitch's
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
The forecast median is the kernel-weighted median of the log-ratios; the
spread is the kernel-weighted standard deviation around it, shrunk by 0.75
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
| p00 | Marvel's Wolverine | 0.3048 | 0.7436 |
| p01 | Red Dead Redemption 2 | 0.1316 | 0.2868 |
| p02 | God of War Ragnarök | 0.1182 | 0.2146 |
| p03 | Marvel's Spider-Man 2 | 0.1903 | 0.3033 |
| **mean** | | **0.1862** | **0.3871** |

Typical miss 35.0% (baseline 82.7%), 90% coverage 0.935 (baseline 0.783).
Leave-one-out cross-validation over the 18 big comparables (hour-1 ≥ 10k)
gives 0.261 vs the baseline's 0.392, so the edge is not just the four
practice cases.

## Running

```sh
MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` in the input directory and writes one `*.out` per case.
Standard library only, deterministic (two runs are byte-identical), ~0.05 s
per case — well inside the 8 s cap.
