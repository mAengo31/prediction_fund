from __future__ import annotations

from pathlib import Path


def test_fixture_dataops_wrapper_is_fixture_only() -> None:
    wrapper = Path("scripts/run_fixture_dataops_job.sh").read_text()

    assert "prediction-desk dataops-cycle --mode FIXTURE" in wrapper
    assert "MANUAL_PUBLIC_FETCH" not in wrapper
    assert "allow_network=true" not in wrapper
    assert "--allow-network" not in wrapper
    assert "staging_public_read_pilot" not in wrapper


def test_azure_enable_fixture_schedule_uses_wrapper_not_direct_app_args() -> None:
    script = Path("scripts/azure_enable_fixture_schedule.sh").read_text()

    assert "CONFIRM_ENABLE_FIXTURE_SCHEDULE" in script
    assert "AZURE_FIXTURE_JOB_COMMAND" in script
    assert "/app/scripts/run_fixture_dataops_job.sh" in script
    assert "REGISTRY_IDENTITY" in script
    assert "--registry-identity" in script
    assert "--mi-user-assigned" in script
    assert '--args "dataops-cycle" "--mode" "FIXTURE"' not in script
    assert "--args dataops-cycle --mode FIXTURE" not in script
    assert "MANUAL_PUBLIC_FETCH" not in script
    assert "staging_public_read_pilot" not in script


def test_azure_disable_fixture_schedule_targets_only_fixture_job() -> None:
    script = Path("scripts/azure_disable_fixture_schedule.sh").read_text()

    assert "CONFIRM_DISABLE_FIXTURE_SCHEDULE" in script
    assert "pd-fixture-dataops-job" in script
    assert "staging_public_read_pilot" not in script
    assert "MANUAL_PUBLIC_FETCH" not in script


def test_default_fixture_job_name_fits_azure_limit() -> None:
    script = Path("scripts/azure_enable_fixture_schedule.sh").read_text()

    default_name = "pd-fixture-dataops-job"
    assert default_name in script
    assert len(default_name) < 32
