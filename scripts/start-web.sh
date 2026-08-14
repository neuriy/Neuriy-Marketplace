#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="${DOTNET_ROOT}:${DOTNET_ROOT}/tools:${PATH}"
cd "${ROOT}/src/NeuriyMarketplace.Web"
exec dotnet run --urls "http://127.0.0.1:5011"
