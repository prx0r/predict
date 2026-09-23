#!/usr/bin/env bash
# Clone all third_party recipe repos (shallow). Skips dead upstream (404s,
# see docs/TRADERS.md) and anything already present. No keys needed.
# Usage: bash scripts/clone_third_party.sh
set -u
cd "$(dirname "$0")/../third_party" || exit 1
clone() { [ -d "$2" ] && echo "SKIP(exists) $2" || { git clone -q --depth 1 "https://github.com/$1.git" "$2" && echo "OK $2"; }; }
# trader trackers (live recipes)
clone EricSpencer00/polymarket-whale-tracker polywhale
clone 0xsteve-00/polymarket-tracker polytrack
clone nerdyvinny/prediction-market-copy-bot pmbot
clone anthowave/polymarket-copy-trading-bot anthowave
clone SnipeRun/polymarket-copy-trading-bot sniperun
clone ArslanKamchybekov/copy-trading copy-sim
clone ryanfrigo/kalshi-ai-trading-bot kalshi-ai
clone OctagonAI/kalshi-trading-bot-cli kalshi-cli
clone OctagonAI/kalshi-deep-trading-bot kalshi-deep
clone ImMike/polymarket-arbitrage pm-arb
# prediction-market infra
clone qoery-com/pmxt pmxt
# congress pipelines
clone seralifatih/congress-trading-pipeline congress-pipe
clone DMulajkar/Quantgress quantgress
clone crnicholson/capitol-api capitol-api
# gov data + MCP recipes
clone lzinga/us-gov-open-data-mcp us-gov-mcp
clone btopn/OpenInsider-MCP openinsider-mcp
# thesis repos
clone prx0r/unignorant unignorant
clone prx0r/cg cg
# DEAD upstream (do not re-add): stackpathLab/polymarket-copy-trading-bot,
# ScouterInfinite/*, ethuncledealer/*, kalkiai-trade/*, Cortex-Trading-Systems/*
echo DONE
