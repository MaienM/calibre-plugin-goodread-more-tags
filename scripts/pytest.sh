#!/usr/bin/env bash

./scripts/kill-and-run.sh

echo "===== Pytest ====="
MIN_TESTS_PER_PROC=2
(
	set -e

	numtests="$(pytest --collect-only "$@" | grep -Ex 'collected [0-9]+ items?' | cut -d' ' -f2)"
	numprocs="$(grep -c '^processor' /proc/cpuinfo)"
	useprocs="$((numtests / MIN_TESTS_PER_PROC))"
	[ "$useprocs" -le "$numprocs" ] || useprocs="$numprocs"
	[ "$useprocs" -gt 0 ] || useprocs=1

	pytest -vv --numprocesses="$useprocs" --randomly-seed="$RANDOM" "$@"
)
