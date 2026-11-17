#!/usr/bin/env python3
"""Launch Shape Matcher -- forecast a big game launch's Twitch viewers, hour by hour.

Idea
----
A launch day on Twitch has a shape, not a level: viewers dip in the small
hours, jump when the US East Coast unlocks, sag around midday, then climb to
an evening peak as the US wakes up and Europe settles in for the night.  The
shape depends mostly on how much of the audience is already watching in
hour 1: when hour 1 is already huge, the day stays flat (the peak is barely
above hour 1); when hour 1 is small, the day climbs many-fold to its peak.
Across 26 clean past launches the log of the peak ratio correlates -0.94
with the log of the hour-1 print.

So, for each hour h = 2..24, we take the log-ratio log(viewers_h / viewers_1)
of every comparable past launch, and combine them with a Gaussian kernel
centred on this case's hour-1 print (bandwidth 0.75 in log space): launches
whose hour-1 print was close to ours count most.  The forecast median is
the kernel-weighted median of the log-ratios; the spread is the
kernel-weighted standard deviation around it, shrunk by 0.75 (the raw
cross-launch spread overstates how uncertain a matched launch is) with a
floor of 0.25 in log space.  Quantiles are the normal quantiles of that
log-scale distribution, exponentiated and scaled by the hour-1 print.

Only comparables marked "Tier: comparable" are used: early-access
contaminated launches (their peak came days before release day), weak
analogues and the target game's own pre-release history are left out.
If too few clean comparables are present, we fall back to every
comparable that is not early-access, weak or the target's own history;
with no usable comparables at all we fall back to a flat forecast
(median = hour-1 print, spread widening as 0.15 * sqrt(h - 1)).

The program is deterministic, uses only the standard library, and reads
every *.in file in the input directory, writing one *.out per case.
"""

import json
import math
import os
import sys

# Standard normal quantiles for the levels 0.05, 0.25, 0.5, 0.75, 0.95.
Z = (-1.6448536269514722, -0.6744897501960817, 0.0,
     0.6744897501960817, 1.6448536269514722)

KERNEL_BANDWIDTH = 0.75   # in log space, on log(hour-1 viewers)
SPREAD_SHRINK = 0.75      # kernel sd overstates matched-launch uncertainty
SPREAD_FLOOR = 0.25       # minimum log-scale spread
MIN_CLEAN = 5             # need at least this many clean comparables
BASELINE_SIGMA = 0.15     # fallback spread: 0.15 * sqrt(h - 1)
MAX_VIEWERS = 1_000_000_000


def parse_time(text):
    """Parse an ISO 8601 UTC timestamp into seconds since the epoch."""
    # fromisoformat in 3.11+ handles 'Z'; be defensive for older builds.
    try:
        from datetime import datetime
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def release_day_hours(comp):
    """Map hour 1..24 of the comparable's release day to its viewer count."""
    day_start = parse_time(comp.get("day_start", ""))
    if day_start is None:
        return {}
    hours = {}
    for row in comp.get("hourly") or []:
        start = parse_time(row.get("from", ""))
        viewers = row.get("viewers")
        if start is None or viewers is None:
            continue
        hour = int((start - day_start) // 3600) + 1
        if 1 <= hour <= 24 and viewers > 0:
            hours[hour] = viewers
    return hours


def is_clean_launch(comp):
    return "Tier: comparable" in (comp.get("unlock") or "")


def is_usable_fallback(comp):
    unlock = comp.get("unlock") or ""
    return ("early-access-contaminated" not in unlock
            and "Tier: weak" not in unlock
            and "Not a launch:" not in unlock)


def collect_library(case):
    """Return a list of (hour1_viewers, {hour: viewers}) for usable launches."""
    comparables = case.get("comparables") or []
    clean = [c for c in comparables if is_clean_launch(c)]
    pool = clean if len(clean) >= MIN_CLEAN else [c for c in comparables
                                                  if is_usable_fallback(c)]
    library = []
    for comp in pool:
        hours = release_day_hours(comp)
        hour1 = hours.get(1)
        if hour1 and hour1 > 0:
            library.append((hour1, hours))
    return library


def weighted_median(pairs):
    """Weighted median of (value, weight) pairs; pairs need not be sorted."""
    total = sum(w for _, w in pairs)
    if total <= 0:
        return None
    ordered = sorted(pairs)
    acc = 0.0
    for value, weight in ordered:
        acc += weight
        if acc >= total / 2:
            return value
    return ordered[-1][0]


def forecast_hour(hour1, library, hour):
    """Five quantiles for one hour, as viewer counts."""
    log_hour1 = math.log(hour1)
    pairs = []
    for comp_hour1, hours in library:
        viewers = hours.get(hour)
        if viewers is None:
            continue
        weight = math.exp(-0.5 * ((math.log(comp_hour1) - log_hour1)
                                  / KERNEL_BANDWIDTH) ** 2)
        pairs.append((math.log(viewers / comp_hour1), weight))
    if not pairs:
        return None
    median = weighted_median(pairs)
    total = sum(w for _, w in pairs)
    variance = sum(w * (v - median) ** 2 for v, w in pairs) / total
    spread = max(math.sqrt(variance) * SPREAD_SHRINK, SPREAD_FLOOR)
    quantiles = [hour1 * math.exp(median + z * spread) for z in Z]
    return quantiles


def flat_forecast(hour1):
    """Fallback: every hour stays at the hour-1 print, spread widening."""
    out = {}
    for hour in range(2, 25):
        spread = BASELINE_SIGMA * math.sqrt(hour - 1)
        out[hour] = [hour1 * math.exp(z * spread) for z in Z]
    return out


def forecast_case(case):
    known = case.get("known") or []
    hour1 = None
    if known:
        hour1 = known[0].get("viewers")
    if not hour1 or hour1 <= 0:
        # No hour-1 print: use the last known hourly point, else 1.
        hourly = case.get("history_hourly") or []
        if hourly:
            hour1 = hourly[-1].get("viewers") or 1
        else:
            hour1 = 1
    hour1 = max(float(hour1), 1.0)

    library = collect_library(case)
    if not library:
        rows = flat_forecast(hour1)
    else:
        rows = {}
        for hour in range(2, 25):
            quantiles = forecast_hour(hour1, library, hour)
            if quantiles is None:
                quantiles = flat_forecast(hour1)[hour]
            rows[hour] = quantiles

    hours = []
    for hour in range(2, 25):
        # Round to 2 decimals, clamp to (0, 1e9], keep non-decreasing.
        qs = [round(min(max(q, 0.01), MAX_VIEWERS), 2) for q in rows[hour]]
        for i in range(1, 5):
            if qs[i] < qs[i - 1]:
                qs[i] = qs[i - 1]
        hours.append({"hour": hour, "q": qs})
    return {"hours": hours}


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(output_dir, exist_ok=True)
    names = sorted(n for n in os.listdir(input_dir) if n.endswith(".in"))
    for name in names:
        case_id = name[:-3]
        with open(os.path.join(input_dir, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        forecast = forecast_case(case)
        out_path = os.path.join(output_dir, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(forecast, fh, separators=(",", ":"))
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
