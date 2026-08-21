"""Experiment Engine (Milestone D) — controlled before/after comparisons.

An experiment answers a question ("did the FMIC lower charge temps?") by comparing a
baseline arm vs a changed arm. The engine reports the delta AND explicitly warns when
the comparison is **poorly controlled** — e.g. the two arms ran at materially different
ambient temperature — so a confounded result is never presented as clean.
"""
from __future__ import annotations

from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from .engmodels import ARMS, Experiment, ExperimentRun
from .models import Vehicle
from .obsmodels import EnvironmentSnapshot

# A comparison is flagged confounded if the arms' mean ambient temperature differs by
# more than this (°C) — enough to move charge-air / cooling / jetting results.
AMBIENT_CONFOUND_C = 5.0


def open_experiment(session: Session, vehicle: Vehicle, question: str, *, metric: str | None = None,
                    unit: str | None = None, code: str | None = None) -> Experiment:
    exp = Experiment(vehicle_id=vehicle.id, question=question, metric=metric, unit=unit, code=code)
    session.add(exp)
    session.flush()
    return exp


def add_run(session: Session, experiment: Experiment, arm: str, value: float, *,
            unit: str | None = None, environment_id: int | None = None,
            session_id: int | None = None, note: str | None = None) -> ExperimentRun:
    if arm not in ARMS:
        raise ValueError(f"invalid arm '{arm}' (baseline|changed)")
    row = ExperimentRun(experiment_id=experiment.id, arm=arm, value=value, unit=unit,
                        environment_id=environment_id, session_id=session_id, note=note)
    session.add(row)
    session.flush()
    return row


def _ambient(session: Session, env_id: int | None) -> float | None:
    if env_id is None:
        return None
    env = session.get(EnvironmentSnapshot, env_id)
    return env.ambient_c if env else None


def compare(session: Session, experiment_id: int) -> dict:
    """Compare the baseline vs changed arms, with a confounder assessment."""
    exp = session.get(Experiment, experiment_id)
    if exp is None:
        return {}
    runs = session.scalars(select(ExperimentRun).where(
        ExperimentRun.experiment_id == experiment_id)).all()
    base = [r for r in runs if r.arm == "baseline" and r.value is not None]
    chg = [r for r in runs if r.arm == "changed" and r.value is not None]

    warnings: list[str] = []
    if not base or not chg:
        warnings.append("Incomplete: need at least one baseline and one changed run.")

    base_mean = mean([r.value for r in base]) if base else None
    chg_mean = mean([r.value for r in chg]) if chg else None
    delta = (chg_mean - base_mean) if (base_mean is not None and chg_mean is not None) else None

    # Confounder check: ambient temperature difference between the arms.
    base_amb = [a for a in (_ambient(session, r.environment_id) for r in base) if a is not None]
    chg_amb = [a for a in (_ambient(session, r.environment_id) for r in chg) if a is not None]
    controlled = True
    if base_amb and chg_amb:
        amb_gap = abs(mean(base_amb) - mean(chg_amb))
        if amb_gap > AMBIENT_CONFOUND_C:
            controlled = False
            warnings.append(f"Poorly controlled: ambient differs by {amb_gap:.1f}°C between arms "
                            f"(> {AMBIENT_CONFOUND_C:g}°C) — the result may be confounded.")
    else:
        warnings.append("Ambient not recorded for both arms — control cannot be assessed.")

    return {
        "experiment_id": experiment_id, "question": exp.question, "metric": exp.metric,
        "unit": exp.unit, "baseline_mean": base_mean, "changed_mean": chg_mean, "delta": delta,
        "n_baseline": len(base), "n_changed": len(chg),
        "controlled": controlled, "warnings": warnings,
    }
