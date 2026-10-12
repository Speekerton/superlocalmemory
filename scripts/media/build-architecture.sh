#!/usr/bin/env bash
# Rebuild docs/assets/slm-architecture.{png,svg} from slm-architecture.mmd.
# Needs mmdc (npm i -g @mermaid-js/mermaid-cli) and a Chrome; edit pp.json for its path.
set -euo pipefail
cd "$(dirname "$0")/../.."
mmdc -i docs/assets/slm-architecture.mmd -o docs/assets/slm-architecture.png -p scripts/media/pp.json -b transparent -s 2 -C scripts/media/mmdc.css
mmdc -i docs/assets/slm-architecture.mmd -o docs/assets/slm-architecture.svg -p scripts/media/pp.json -b transparent -C scripts/media/mmdc.css
