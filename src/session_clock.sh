#!/usr/bin/env bash
# 17 Nov (DK 06:48 "Create a system that actually works"): GitHub's cron fires late or not at all, so the daily books' times
# can't depend on it. The live session is running round the clock (hand-over chain), so it keeps the clock: at each daily-book
# time it starts DK's ig-daily-live workflow itself. The daily books' own "already ran today" tag stops any double if a cron
# also fires. DK's IG_DAILY_LIVE_ENABLED still gates every run of that workflow; with it off, the dispatch does nothing.
# Usage: session_clock.sh <repo>   (needs GH_TOKEN with actions:write). Runs until killed.
REPO="$1"; WF="${2:-ig-daily-live.yml}"; LOGF="${3:-runs/ig_live/clock.log}"   # 23 Nov: the demo chain keeps the demo daily books' clock too (ig-daily.yml)
# job  zone              target   (dispatched 4 min early: the job takes ~2 min to install and log in)
TARGETS="eu_open|Europe/London|08:05 us_open|America/New_York|09:35 eu_close|Europe/London|16:10 us_close|America/New_York|15:40"
SENT=""
while true; do
  DOW=$(date -u +%u)
  if [ "$DOW" -le 5 ]; then
    for t in $TARGETS; do
      IFS='|' read -r JOB TZN T <<< "$t"
      TAG="$JOB:$(TZ=$TZN date +%F)"
      case " $SENT " in *" $TAG "*) continue;; esac
      D=$(( $(TZ=$TZN date -d "today $T" +%s) - $(date -u +%s) ))
      if [ "$D" -le 240 ] && [ "$D" -gt -600 ]; then
        if gh workflow run "$WF" -R "$REPO" -f job="$JOB" -f dry=false; then
          echo "$(date -u +%FT%TZ) clock: started daily books $JOB (target $T $TZN)" | tee -a "$LOGF"
        else
          echo "$(date -u +%FT%TZ) clock: FAILED to start daily books $JOB" | tee -a "$LOGF"
        fi
        SENT="$SENT $TAG"
      fi
    done
  fi
  sleep 30
done
