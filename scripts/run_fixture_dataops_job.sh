#!/usr/bin/env bash
set -euo pipefail

echo "fixture_dataops_job starting: mode=FIXTURE public_read=held"
prediction-desk dataops-cycle --mode FIXTURE
echo "fixture_dataops_job completed: mode=FIXTURE public_read=held"
