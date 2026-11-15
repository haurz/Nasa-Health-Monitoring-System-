"""Mission-control dashboard for the non-operational Offline Astro-Twin demo."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import chromadb
import streamlit.components.v1 as components
from plotly.subplots import make_subplots

from engine import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    compute_demo_readiness,
    complete_daily_checkin,
    effective_latest_state,
    environment_constraints,
    evaluate_health_systems,
    get_gamification_stats,
    get_vitals_history,
    load_scenario_to_db,
    log_vitals,
    query_flight_surgeon_copilot,
    simulate_countermeasure_projection,
    validate_telemetry_plausibility,
)
from ingest_rag import ingest


st.set_page_config(
    page_title="Offline Astro-Twin | Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROJECT_ROOT = Path(__file__).resolve().parent
SELF_EXAM_PATH = PROJECT_ROOT / "knowledge_base" / "astronaut_self_exam_protocols.md"

ENVIRONMENT_OPTIONS = (
    "ISS (LEO - 0.5s Latency)",
    "Artemis Lunar Transit (~1.3s One-Way / ~2.6s Round-Trip)",
    "Mars Surface Base (Up to ~22-Min One-Way / ~44-Min Round-Trip)",
)
SCENARIO_OPTIONS = {
    "Nominal Day 45 (ISS)": "iss_leo_baseline",
    "Solar Particle Event (Lunar)": "artemis_lunar_spe",
    "Day 210 Mars Transit Extrapolation": "mars_surface_day_210",
}
SCENARIO_LABELS = {value: key for key, value in SCENARIO_OPTIONS.items()}
SCENARIO_ENVIRONMENTS = {
    "iss_leo_baseline": ENVIRONMENT_OPTIONS[0],
    "artemis_lunar_spe": ENVIRONMENT_OPTIONS[1],
    "mars_surface_day_210": ENVIRONMENT_OPTIONS[2],
}
SYSTEM_LABELS = {
    "neuro_ocular_behavioral": "Brain / Eyes",
    "cardiovascular": "Cardiovascular",
    "skeletal_bone": "Skeletal / Bone",
    "immune_radiation": "Immune / Radiation",
}
SYSTEM_METRICS = {
    "neuro_ocular_behavioral": ("sleep_hours", "mood_score", "cabin_co2"),
    "cardiovascular": ("heart_rate", "bp_sys", "bp_dia"),
    "skeletal_bone": ("bone_bmd_delta",),
    "immune_radiation": (
        "radiation_dose_rate_msv_day",
        "neutron_radiation_msv",
        "blood_glucose",
        "body_temp",
    ),
}
# Synthetic/demo cadence only; these intervals are not mission medical schedules.
DEMO_MEASUREMENT_CADENCE_DAYS = {
    "sleep_hours": 1,
    "mood_score": 1,
    "cabin_co2": 1,
    "heart_rate": 1,
    "bp_sys": 1,
    "bp_dia": 1,
    "bone_bmd_delta": 30,
    "radiation_dose_rate_msv_day": 1,
    "neutron_radiation_msv": 7,
    "blood_glucose": 1,
    "body_temp": 1,
}
METRIC_LABELS = {
    "sleep_hours": "Sleep (h)",
    "mood_score": "Mood (project score)",
    "cabin_co2": "Cabin CO2 (mmHg)",
    "heart_rate": "Heart rate (bpm)",
    "bp_sys": "Systolic BP (mmHg)",
    "bp_dia": "Diastolic BP (mmHg)",
    "bone_bmd_delta": "BMD delta (%)",
    "radiation_dose_rate_msv_day": "Radiation fixture (mSv/day)",
    "neutron_radiation_msv": "Neutron dose reference (mSv/day)",
    "blood_glucose": "Blood glucose (mg/dL)",
    "body_temp": "Body temperature (°C)",
}
COUNTERMEASURES = [
    "Water-Wall Shelter (design concept)",
    "ARED Resistance Protocol (+30 min)",
    "Thigh Cuff & Fluid Load",
    "Circadian Blue-Light Reset",
]
EXAM_HEADINGS = {
    "neuro_ocular_behavioral": "## B. SANS visual and neurologic observation",
    "cardiovascular": "## A. Cardiovascular and orthostatic observation",
    "skeletal_bone": "## C. Bone and musculoskeletal observation",
    "immune_radiation": "## D. Immune and metabolic observation",
}
STATUS_SYMBOLS = {"No Data": "○", "Green": "●", "Amber": "▲", "Red": "■"}
QUICK_REFERENCE = {
    "neuro_ocular_behavioral": (
        "Amsler grid (one eye at a time), reported sleep hours, approved mood scale, and cabin CO2 partial pressure (mmHg).",
        "The grid records central-vision distortions; sleep and mood logs track changes in rest and wellbeing.",
        "Microgravity-related headward fluid shifts are associated with SANS; isolation and altered light/dark schedules can disrupt sleep and behavior.",
        "Project-only display triggers: cabin CO2 >3.0 mmHg (Amber), >5.0 (Red); sleep <7 h (Amber), <5 h (Red); mood <=6 (Amber), <=3 (Red). New or sudden visual/neurologic symptoms require mission medical assessment regardless of these demo bands.",
        "Use the same approved Amsler grid conditions and record changes; follow the assigned sleep/light schedule and ECLSS instructions.",
    ),
    "cardiovascular": (
        "Resting pulse (bpm), cuff systolic/diastolic blood pressure (mmHg), and recorded symptoms/posture.",
        "These readings describe the measured pulse and pressure at the recorded time and position; they do not diagnose orthostatic intolerance.",
        "Microgravity fluid redistribution and cardiovascular deconditioning can affect regulation during gravity transitions.",
        "Project-only display triggers: pulse <50 or >100 bpm (Amber), <40 or >120 (Red); systolic <90 or >139 mmHg (Amber), <80 or >=180 (Red); diastolic <60 or >89 (Amber), <50 or >=120 (Red). Symptoms and approved mission criteria take priority.",
        "Use the assigned cuff/pulse device as trained; follow the prescribed ARED/exercise and hydration plan without changing it based on this dashboard.",
    ),
    "skeletal_bone": (
        "The approved comparable BMD measurement when scheduled, plus ARED session/load logs and reported pain; exercise logs are not BMD measurements.",
        "BMD quantifies bone mineral density; exercise records only document participation and equipment load.",
        "Reduced mechanical loading in microgravity is associated with bone changes; NASA's 1.0–1.5%/month figure is a population average, not an individual threshold.",
        "Project-only display triggers: BMD delta below 0% (Amber) or below -5% (Red); these are invented UI bands, not clinical or NASA limits. Report injury or persistent focal pain through mission medical channels.",
        "Complete only the prescribed ARED plan and nutrition guidance; do not increase load to compensate for missed sessions.",
    ),
    "immune_radiation": (
        "Personal dosimeter reading with dose quantity/time window, assigned thermometer (site recorded), glucometer (mg/dL, time/context), and any mission-approved immune assay.",
        "Dosimetry estimates measured radiation exposure; temperature and glucose record specific metabolic/illness observations. They do not measure immune function.",
        "Solar particle events can rapidly increase radiation exposure; spaceflight stressors can alter immune responses. A glucose or temperature reading alone does not establish immune status.",
        "Project-only display triggers: radiation observation >=0.5 mSv/day (Amber), >=10 (Red); glucose <70 or >180 mg/dL (Amber), <55 or >250 (Red); temperature <36.0 or >=37.8°C (Amber), <35.0 or >=38.5 (Red). These are not mission limits; follow official alerts and medical rules.",
        "Check mission SPE alert status; if alerted, defer EVA, relocate to the preassigned storm shelter until all-clear, log shelter entry/exit times and personal dosimeter readings, and if comms are delayed/down, execute the stored SPE contingency and queue the handover report.",
    ),
}
QUICK_REFERENCE_KB_SOURCES = {
    "neuro_ocular_behavioral": (
        "knowledge_base/nasa_hrp_5_hazards.md; "
        "knowledge_base/astronaut_self_exam_protocols.md"
    ),
    "cardiovascular": (
        "knowledge_base/nasa_hrp_5_hazards.md; "
        "knowledge_base/astronaut_self_exam_protocols.md"
    ),
    "skeletal_bone": (
        "knowledge_base/nasa_hrp_5_hazards.md; "
        "knowledge_base/astronaut_self_exam_protocols.md"
    ),
    "immune_radiation": (
        "knowledge_base/nasa_hrp_5_hazards.md; "
        "knowledge_base/csa_radiation_monitoring.md; "
        "knowledge_base/astronaut_self_exam_protocols.md"
    ),
}
SYSTEM_ACTION_GUIDANCE = {
    "neuro_ocular_behavioral": (
        "1. Complete the assigned Amsler grid one eye at a time and log any distortion. "
        "2. Record sleep opportunity and actual sleep, plus the approved mood scale. "
        "3. If the cabin CO2 monitor alarms or a trend is flagged, check the vehicle "
        "ECLSS procedure and report scrubber/airflow indications—do not adjust equipment.",
        "New or worsening vision or neurologic symptoms; or the demo-only thresholds "
        "listed in the Quick Reference. Vehicle alarms and the approved medical plan govern.",
    ),
    "cardiovascular": (
        "1. Measure resting pulse and cuff pressure with the assigned devices and log "
        "time, posture, and symptoms. 2. Repeat only when the device procedure directs "
        "and it is safe. 3. Continue the prescribed ARED/exercise, hydration, and nutrition plan.",
        "Chest pain, collapse, severe dizziness/breathlessness, or the demo-only bands "
        "in Quick Reference; follow the onboard medical procedure.",
    ),
    "skeletal_bone": (
        "1. Log prescribed ARED exercise, sets, loads, and interruptions. 2. Use only "
        "scheduled, approved comparable BMD measurements. 3. Follow mission nutrition "
        "guidance; do not increase loads after missed sessions.",
        "Injury, persistent localized bone/joint pain, or a concerning scheduled "
        "measurement; demo BMD bands are not clinical thresholds.",
    ),
    "immune_radiation": (
        "1. Check mission SPE alert status before EVA; if alerted, defer EVA. "
        "2. Relocate to the preassigned storm shelter until all-clear. "
        "3. Log shelter entry/exit times and personal dosimeter readings. "
        "4. If comms are delayed/down, execute the stored SPE contingency and "
        "queue the handover report.",
        "An official SPE alert or onboard radiation alarm; or severe/worsening illness "
        "symptoms. Do not wait for a demo numeric band or communications reply.",
    ),
}
SYSTEM_ACTION_KB_SOURCES = {
    "neuro_ocular_behavioral": (
        "knowledge_base/astronaut_self_exam_protocols.md (§B, §E); "
        "knowledge_base/nasa_hrp_5_hazards.md"
    ),
    "cardiovascular": (
        "knowledge_base/astronaut_self_exam_protocols.md (§A); "
        "knowledge_base/nasa_hrp_5_hazards.md"
    ),
    "skeletal_bone": (
        "knowledge_base/astronaut_self_exam_protocols.md (§C); "
        "knowledge_base/nasa_hrp_5_hazards.md"
    ),
    "immune_radiation": (
        "knowledge_base/nasa_hrp_5_hazards.md; "
        "knowledge_base/csa_radiation_monitoring.md; "
        "knowledge_base/astronaut_self_exam_protocols.md (§D)"
    ),
}
HANDOVER_CHECKLISTS = {
    ENVIRONMENT_OPTIONS[0]: (
        "Confirm cabin CO₂ monitoring trend/alarms and CDRA status, Radi-N2 "
        "detector placement/integration interval (passive, not real-time), ARED "
        "session log, cuff readings, and personal dosimeter record."
    ),
    ENVIRONMENT_OPTIONS[1]: (
        "Confirm portable dosimeter record, cuff/finger pulse-ox readings, Amsler "
        "grid observations, vehicle environmental alarms, and SPE contingency status."
    ),
    ENVIRONMENT_OPTIONS[2]: (
        "Confirm habitat environmental-loop alarms, portable ultrasound/tonometer "
        "availability and readings if mission-approved, dosimeter record, EVA/shelter "
        "status, symptom timeline, and queued communications attempts."
    ),
}


def _initialize_demo() -> None:
    st.session_state.setdefault("active_scenario", "iss_leo_baseline")
    current_scenario = st.session_state["active_scenario"]
    if current_scenario not in SCENARIO_ENVIRONMENTS:
        current_scenario = "iss_leo_baseline"
        st.session_state["active_scenario"] = current_scenario
    st.session_state.setdefault(
        "environment_mode", SCENARIO_ENVIRONMENTS[current_scenario]
    )
    st.session_state.setdefault("selected_system", "neuro_ocular_behavioral")

    scenario_id = st.session_state.get("active_scenario", "iss_leo_baseline")
    if not st.session_state.get("_astro_twin_initialized"):
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        if collection.count() == 0:
            with st.spinner("Building the local NASA/CSA knowledge index..."):
                ingest()

        latest = get_vitals_history(1)
        if not latest:
            load_scenario_to_db("iss_leo_baseline")
            latest = get_vitals_history(1)

        scenario_id = (
            latest[0].get("scenario_id")
            if latest and latest[0].get("scenario_id") in SCENARIO_LABELS
            else "iss_leo_baseline"
        )
        st.session_state["_astro_twin_initialized"] = True

    scenario_id = st.session_state.get("active_scenario", scenario_id)
    if scenario_id not in SCENARIO_ENVIRONMENTS:
        scenario_id = "iss_leo_baseline"
        st.session_state["active_scenario"] = scenario_id
    if st.session_state.get("environment_mode") not in ENVIRONMENT_OPTIONS:
        st.session_state["environment_mode"] = SCENARIO_ENVIRONMENTS[scenario_id]
    scenario_history = get_vitals_history(14, scenario_id=scenario_id)
    legacy_synthetic_seed = bool(scenario_history) and all(
        row.get("evidence_status") == "synthetic_design_fixture"
        and not row.get("metric_evidence_json")
        for row in scenario_history
    )
    if not scenario_history or legacy_synthetic_seed:
        load_scenario_to_db(scenario_id)


def _load_preset(scenario_id: str) -> None:
    load_scenario_to_db(scenario_id)
    st.session_state["active_scenario"] = scenario_id
    st.session_state["environment_mode"] = SCENARIO_ENVIRONMENTS[scenario_id]


def _extract_guide(section_heading: str) -> str:
    if not SELF_EXAM_PATH.is_file():
        return "The local self-check reference is not available."
    text = SELF_EXAM_PATH.read_text(encoding="utf-8")
    start = text.find(section_heading)
    if start < 0:
        return "The requested self-check section was not found."
    following = re.search(r"^## ", text[start + len(section_heading) :], re.MULTILINE)
    end = (
        start + len(section_heading) + following.start()
        if following
        else len(text)
    )
    return text[start:end].strip()


def _latest_for(scenario_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    history = get_vitals_history(limit=14, scenario_id=scenario_id)
    if not history:
        return [], {}
    return history, history[-1]


def _due_metrics_for_system(
    history: list[dict[str, Any]],
    system_id: str,
    effective_latest: dict[str, Any],
) -> list[str]:
    latest_day = effective_latest.get("mission_day")
    if latest_day is None:
        return []
    latest_day = int(latest_day)
    due = []
    radiation_metric = (
        "neutron_radiation_msv"
        if effective_latest.get("neutron_radiation_msv") is not None
        else "radiation_dose_rate_msv_day"
    )
    for metric in SYSTEM_METRICS[system_id]:
        if metric in {"radiation_dose_rate_msv_day", "neutron_radiation_msv"}:
            continue
        cadence = DEMO_MEASUREMENT_CADENCE_DAYS[metric]
        observed_days = [
            int(row["mission_day"])
            for row in history
            if row.get(metric) is not None and row.get("mission_day") is not None
        ]
        label = METRIC_LABELS.get(metric, metric)
        if not observed_days:
            due.append(f"{label}: no recorded reading (demo cadence {cadence}d)")
            continue
        age_days = max(0, latest_day - max(observed_days))
        if age_days >= cadence:
            due.append(
                f"{label}: {age_days} mission day(s) since last reading "
                f"(demo cadence {cadence}d)"
            )
    if system_id == "immune_radiation":
        cadence = DEMO_MEASUREMENT_CADENCE_DAYS[radiation_metric]
        observed_days = [
            int(row["mission_day"])
            for row in history
            if row.get(radiation_metric) is not None
            and row.get("mission_day") is not None
        ]
        if not observed_days:
            due.append(
                f"Radiation observation: no recorded reading (demo cadence {cadence}d)"
            )
        else:
            age_days = max(0, latest_day - max(observed_days))
            if age_days >= cadence:
                due.append(
                    f"Radiation observation: {age_days} mission day(s) since "
                    f"last reading (demo cadence {cadence}d)"
                )
    return due


def _ground_handover_report(
    scenario_id: str,
    environment_mode: str,
    systems: dict[str, dict[str, Any]],
    latest: dict[str, Any],
) -> str:
    constraints = environment_constraints(environment_mode)
    checklist = HANDOVER_CHECKLISTS[environment_mode]
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metric_names = (
        "heart_rate",
        "bp_sys",
        "bp_dia",
        "blood_glucose",
        "body_temp",
        "sleep_hours",
        "mood_score",
        "radiation_dose_rate_msv_day",
        "neutron_radiation_msv",
        "bone_bmd_delta",
        "cabin_co2",
    )
    lines = [
        "# Offline Astro-Twin — Ground Handover",
        "",
        f"- Generated (UTC): {timestamp}",
        f"- Active scenario: {SCENARIO_LABELS.get(scenario_id, scenario_id)} (`{scenario_id}`)",
        f"- Environment mode: {environment_mode}",
        f"- Comms delay window: {constraints['latency_label']}",
        f"- Communications state: {constraints['comms_state']}",
        f"- Measurement feasibility: {constraints['measurement_feasibility']}",
        "",
        "## Environment-specific queued checklist",
        f"- {checklist}",
        "- Safety: educational demo report; telemetry may be synthetic or unverified.",
        "",
        "## Effective telemetry",
    ]
    lines.extend(
        f"- {name}: {_format_value(latest.get(name))}" for name in metric_names
    )
    provenance = latest.get("metric_evidence_status", {})
    if provenance:
        lines.extend(["", "## Per-metric provenance"])
        lines.extend(f"- {metric}: {status}" for metric, status in provenance.items())
    lines.extend(["", "## System status"])
    active_alerts = []
    for system_id, system in systems.items():
        symbol = STATUS_SYMBOLS[system["status"]]
        lines.append(
            f"- {SYSTEM_LABELS[system_id]}: {symbol} {system['status']}"
        )
        if system["status"] != "Green":
            active_alerts.append(
                f"{SYSTEM_LABELS[system_id]}: {system['status']}"
            )
        active_alerts.extend(system["compounding_alerts"])
    lines.extend(["", "## Active alerts"])
    lines.extend(f"- {alert}" for alert in active_alerts)
    if not active_alerts:
        lines.append("- No non-Green demo statuses or configured co-occurrence alerts.")
    plausibility_warnings = validate_telemetry_plausibility(latest)
    if plausibility_warnings:
        lines.extend(["", "## Sensor plausibility warnings"])
        lines.extend(f"- {warning}" for warning in plausibility_warnings)
    lines.append("")
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if value is None:
        return "No data"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _metric_provenance(
    metric: str, latest: dict[str, Any], scenario_id: str
) -> tuple[str, str]:
    if latest.get(metric) is None:
        return "No data recorded", "No value is present for this metric."
    source_status = latest.get("metric_evidence_status", {}).get(metric)
    if source_status == "user_entered_unverified":
        return "Unverified manual entry", "User-entered value; not independently verified."
    if metric == "neutron_radiation_msv" and source_status == "csa_radi_n2_empirical":
        return (
            "Real: neutron dose 0.15 mSv/day (CSA Radi-N2)",
            "CSA-reported measurement value repeated here as a scenario reference; not 14 daily measurements or total dose.",
        )
    if metric == "bone_bmd_delta" and source_status == "synthetic_extrapolation":
        return (
            "Extrapolated: BMD (HRP 1.0–1.5%/mo rate)",
            "Synthetic interpolation using published population-average context; not a NASA-derived daily trajectory.",
        )
    if metric == "radiation_dose_rate_msv_day" and scenario_id == "artemis_lunar_spe":
        return (
            "Project stress test (synthetic)",
            "Mixed neutron/proton endpoint scenario value; not an Artemis measurement or dose limit.",
        )
    if metric == "cabin_co2" and scenario_id == "mars_surface_day_210":
        return (
            "Project stress test (synthetic)",
            "4.3 mmHg Day 210 scenario input; not a measured Mars habitat baseline.",
        )
    if metric == "cabin_co2" and scenario_id == "iss_leo_baseline":
        return (
            "Synthetic: cabin CO₂ fixture",
            "2.8 mmHg is not an EDA empirical baseline.",
        )
    labels = {
        "sleep_hours": "Synthetic: sleep fixture",
        "mood_score": "Synthetic: mood fixture",
        "cabin_co2": "Synthetic: cabin CO₂ fixture",
        "heart_rate": "Synthetic: heart rate fixture",
        "bp_sys": "Synthetic: blood pressure fixture",
        "bp_dia": "Synthetic: blood pressure fixture",
        "blood_glucose": "Synthetic: blood glucose fixture",
        "body_temp": "Synthetic: temperature fixture",
    }
    if metric in labels:
        return labels[metric], "Scenario fixture value; not an individual crew measurement."
    return (
        "Project stress test (synthetic)"
        if source_status == "synthetic_assumption"
        else "Synthetic scenario fixture",
        "Scenario fixture value; not an individual crew measurement.",
    )


def _data_core_pills(latest: dict[str, Any]) -> str:
    evidence = latest.get("metric_evidence_status", {})
    pills = ["LOCAL SQLITE", "LOCAL CHROMA"]
    if "csa_radi_n2_empirical" in evidence.values():
        pills.append("REAL · CSA RADI-N2")
    if "synthetic_extrapolation" in evidence.values():
        pills.append("EXTRAPOLATED · BMD")
    if any(
        status in {"synthetic_assumption", "synthetic_design_fixture"}
        for status in evidence.values()
    ):
        pills.append("SYNTHETIC SCENARIO")
    if "user_entered_unverified" in evidence.values():
        pills.append("UNVERIFIED MANUAL")
    return (
        '<div class="data-core"><strong>DATA CORE</strong>'
        + "".join(
            f'<span class="data-pill">{html.escape(pill)}</span>'
            for pill in pills
        )
        + "</div>"
    )


def _render_astro_svg(
    systems: dict[str, dict[str, Any]], selected_system: str
) -> str:
    hotspot_specs = (
        (
            "neuro_ocular_behavioral",
            "BRAIN / EYES",
            170,
            57,
            ("sleep_hours", "mood_score", "cabin_co2"),
        ),
        (
            "cardiovascular",
            "CARDIO",
            170,
            139,
            ("heart_rate", "bp_sys", "bp_dia"),
        ),
        ("skeletal_bone", "SKELETAL", 171, 253, ("bone_bmd_delta",)),
        (
            "immune_radiation",
            "RADIATION",
            224,
            182,
            ("radiation_dose_rate_msv_day", "neutron_radiation_msv"),
        ),
    )
    hotspots = []
    for system_id, label, x, y, metric_keys in hotspot_specs:
        system = systems[system_id]
        color = html.escape(str(system["color"]), quote=True)
        status = html.escape(str(system["status"]))
        primary_metric = next(
            (
                f"{key.replace('_', ' ')}: {_format_value(system['key_metrics'].get(key))}"
                for key in metric_keys
                if system["key_metrics"].get(key) is not None
            ),
            "Primary metric: No data",
        )
        tooltip = html.escape(
            f"{SYSTEM_LABELS[system_id]} — {STATUS_SYMBOLS[status]} {status.upper()}; {primary_metric}"
        )
        active_class = " active" if system_id == selected_system else ""
        status_class = status.lower()
        pulse_duration = "1.1s" if status == "Red" else "2.4s"
        pulse_delay = "-0.55s" if status == "Red" else "-1.2s"
        label_x = 268 if label == "RADIATION" else 218
        line_end_x = label_x - 4
        label_y = 108 if label == "CARDIO" else y + 4
        if label == "CARDIO":
            leader = (
                f'<path d="M{x + 9} {y} H214 V104" fill="none" '
                'stroke="#8aa7b8" stroke-width="1" opacity=".8"/>'
            )
        else:
            leader = (
                f'<line x1="{x + 9}" y1="{y}" x2="{line_end_x}" y2="{y}" '
                'stroke="#8aa7b8" stroke-width="1" opacity=".8"/>'
            )
        hotspots.append(
            f'<a class="hotspot {status_class}{active_class}" '
            f'href="?system={system_id}" target="_top" '
            f'style="--pulse-duration:{pulse_duration};--pulse-delay:{pulse_delay};text-decoration:none;cursor:pointer;">'
            f'<title>{tooltip}</title>'
            f'{leader}'
            f'<circle class="target-reticle" cx="{x}" cy="{y}" r="19" '
            'fill="none" stroke="#8ff5ff" stroke-width="1.5" '
            'stroke-dasharray="4 3"/>'
            f'<circle class="radar-ring" cx="{x}" cy="{y}" r="8" '
            f'fill="none" stroke="{color}" stroke-width="2"/>'
            f'<circle class="radar-ring second" cx="{x}" cy="{y}" r="8" '
            f'fill="none" stroke="{color}" stroke-width="1.5"/>'
            f'<circle class="hotspot-node" cx="{x}" cy="{y}" r="8" '
            f'fill="{color}" stroke="#fff" stroke-width="2"/>'
            f'<text class="hotspot-label{active_class}" x="{label_x}" '
            f'y="{label_y}" fill="#d9e8ef">{label}</text></a>'
        )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:transparent;overflow:hidden;}}
svg{{width:100%;height:auto;max-height:460px;display:block;}}
.suit{{fill:url(#suit);stroke:#77a6bf;stroke-width:3;stroke-linejoin:round;}}
.hotspot{{cursor:pointer;transform-box:fill-box;transform-origin:center;transition:transform .2s ease,filter .2s ease;}}
.hotspot:hover{{transform:scale(1.12);filter:drop-shadow(0 0 8px #42eaff);}}
.hotspot-label{{font:12px system-ui,sans-serif;fill:#d9e8ef;paint-order:stroke;stroke:#07111b;stroke-width:2px;stroke-linejoin:round;}}
.hotspot-label.active{{font-weight:800;fill:#8ff5ff;}}
.radar-ring{{transform-box:fill-box;transform-origin:center;animation:radar-pulse var(--pulse-duration) ease-out infinite;}}
.radar-ring.second{{animation-delay:var(--pulse-delay);}}
.hotspot.red .radar-ring{{animation-duration:1.1s;}}
.hotspot.red .radar-ring.second{{animation-duration:1.1s;animation-delay:-.55s;}}
.target-reticle{{opacity:0;transform-box:fill-box;transform-origin:center;}}
.hotspot.active .target-reticle{{opacity:1;animation:reticle-rotate 8s linear infinite;}}
.scanline{{opacity:.22;animation:scan-sweep 5s linear infinite;}}
@keyframes radar-pulse{{0%{{transform:scale(.55);opacity:.8;}}100%{{transform:scale(2.7);opacity:0;}}}}
@keyframes reticle-rotate{{to{{transform:rotate(360deg);}}}}
@keyframes scan-sweep{{0%{{transform:translateY(0);}}100%{{transform:translateY(410px);}}}}
@media(prefers-reduced-motion:reduce){{.hotspot,.radar-ring,.target-reticle,.scanline{{animation:none!important;transition:none!important;}}}}
</style></head><body><svg viewBox="0 0 380 450" role="img" aria-label="Astronaut silhouette with four color-coded health-system hotspots" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="suit" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="#183448"/><stop offset="100%" stop-color="#0b1825"/></linearGradient><linearGradient id="scan-gradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#4deaff" stop-opacity="0"/><stop offset="48%" stop-color="#4deaff" stop-opacity="1"/><stop offset="100%" stop-color="#4deaff" stop-opacity="0"/></linearGradient></defs>
<g class="suit"><circle cx="170" cy="58" r="36"/><path d="M139 101 Q170 88 201 101 L220 193 Q198 208 170 208 Q142 208 120 193 Z"/><path d="M137 111 L98 130 L79 217 Q77 228 88 231 Q99 234 104 222 L133 160"/><path d="M203 111 L242 130 L261 217 Q263 228 252 231 Q241 234 236 222 L207 160"/><path d="M143 202 L139 303 L125 389 Q123 402 137 404 Q150 405 154 392 L171 311 L187 392 Q191 405 204 404 Q218 402 216 389 L201 303 L197 202"/><path d="M146 128 Q170 142 194 128 M150 177 L190 177" fill="none"/><rect x="151" y="146" width="38" height="22" rx="5" fill="#102535"/></g>
<rect class="scanline" x="76" y="18" width="188" height="4" fill="url(#scan-gradient)" opacity="0.22"/>
<g>{''.join(hotspots)}</g></svg></body></html>"""


def _historical_figure(
    history: list[dict[str, Any]], system_id: str
) -> go.Figure | None:
    data = pd.DataFrame(history)
    metrics = [
        metric
        for metric in SYSTEM_METRICS[system_id]
        if metric in data and data[metric].notna().any()
    ]
    if data.empty or not metrics:
        return None
    if "cabin_co2" in metrics:
        data["cabin_co2"] = data["cabin_co2"].ffill().bfill()

    figure = make_subplots(
        rows=len(metrics),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=[METRIC_LABELS[item] for item in metrics],
    )
    axis_ranges = {
        "heart_rate": [50, 110],
        "bp_sys": [85, 160],
        "bp_dia": [50, 100],
        "sleep_hours": [4.5, 9.5],
        "mood_score": [1, 10],
        "cabin_co2": [0, 6.5],
        "bone_bmd_delta": [-12, 1],
        "radiation_dose_rate_msv_day": [0, 22],
        "neutron_radiation_msv": [0, 22],
    }
    for row_index, metric in enumerate(metrics, start=1):
        clean = data[["mission_day", metric]].dropna()
        figure.add_trace(
            go.Scatter(
                x=clean["mission_day"],
                y=clean[metric],
                mode="lines+markers",
                name=METRIC_LABELS[metric],
                line={"color": "#38d9ff", "width": 2},
                marker={"size": 6},
                showlegend=False,
                hovertemplate="%{x}<br>%{y}<extra></extra>",
            ),
            row=row_index,
            col=1,
        )
        figure.update_yaxes(
            title_text=METRIC_LABELS[metric],
            range=axis_ranges.get(metric),
            row=row_index,
            col=1,
        )
    figure.update_xaxes(title_text="Mission day", row=len(metrics), col=1)
    figure.update_layout(
        height=max(250, 190 * len(metrics)),
        margin={"l": 8, "r": 8, "t": 38, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#d9e8ef"},
        hovermode="x unified",
    )
    return figure


def _projection_figure(
    projection: pd.DataFrame,
) -> tuple[go.Figure, list[str]]:
    indicators = (
        "radiation_risk_index",
        "bone_bmd_delta",
        "cardio_stability_score",
        "neuro_readiness_score",
    )
    labels = {
        "radiation_risk_index": "Radiation risk index",
        "bone_bmd_delta": "BMD change per day (synthetic %/day)",
        "cardio_stability_score": "Cardio stability (demo score)",
        "neuro_readiness_score": "Neuro readiness (demo score)",
    }
    y_axis_labels = {
        "radiation_risk_index": "Index",
        "bone_bmd_delta": "%/day",
        "cardio_stability_score": "Score",
        "neuro_readiness_score": "Score",
    }
    scenarios = (
        ("No Action (Baseline Drift)", "#8b9aaa"),
        ("With Selected Countermeasures", "#38d9ff"),
    )
    omission_notes = {
        "radiation_risk_index": (
            "Radiation projection omitted: no baseline radiation measurement "
            "in this scenario."
        ),
        "bone_bmd_delta": (
            "BMD projection omitted: no baseline BMD measurement in this scenario."
        ),
        "cardio_stability_score": (
            "Cardio projection omitted: no baseline cardiovascular measurements "
            "in this scenario."
        ),
        "neuro_readiness_score": (
            "Neuro projection omitted: no baseline sleep/mood measurements "
            "in this scenario."
        ),
    }
    active_indicators = [
        indicator
        for indicator in indicators
        if indicator in projection and projection[indicator].notna().any()
    ]
    skipped_indicators = [
        indicator for indicator in indicators if indicator not in active_indicators
    ]
    omitted_notes = [omission_notes[item] for item in skipped_indicators]
    if not active_indicators:
        figure = go.Figure()
        figure.update_layout(
            height=150,
            margin={"l": 8, "r": 8, "t": 12, "b": 8},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#d9e8ef"},
        )
        return figure, omitted_notes

    figure = make_subplots(
        rows=len(active_indicators),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.13,
        subplot_titles=[labels[item] for item in active_indicators],
    )
    for row_index, indicator in enumerate(active_indicators, start=1):
        for scenario, color in scenarios:
            rows = projection[projection["scenario"] == scenario]
            baseline_line = (
                {"color": "#cbd5e1", "width": 2, "dash": "dot"}
                if scenario == "No Action (Baseline Drift)"
                else {"color": color, "width": 2}
            )
            y_values = rows[indicator]
            if (
                indicator == "bone_bmd_delta"
                and "starting_bone_bmd_delta" in rows
            ):
                ordered = rows.sort_values("day_ahead")
                if ordered[indicator].notna().any():
                    y_values = ordered[indicator].diff()
                    if ordered["starting_bone_bmd_delta"].notna().any():
                        y_values = y_values.fillna(
                            ordered[indicator].iloc[0]
                            - ordered["starting_bone_bmd_delta"].iloc[0]
                        )
                else:
                    y_values = pd.Series(
                        float("nan"), index=ordered.index
                    )
            figure.add_trace(
                go.Scatter(
                    x=rows["day_ahead"],
                    y=y_values,
                    mode="lines+markers",
                    name=scenario,
                    legendgroup=scenario,
                    showlegend=(row_index == 1),
                    line=baseline_line,
                    marker={"size": 5},
                    connectgaps=False,
                ),
                row=row_index,
                col=1,
            )
        figure.update_yaxes(
            title_text=y_axis_labels[indicator], row=row_index, col=1
        )
        if indicator == "bone_bmd_delta":
            figure.add_hrect(
                y0=-0.05,
                y1=-0.033,
                row=row_index,
                col=1,
                fillcolor="rgba(255, 171, 0, 0.14)",
                line_width=0,
                annotation_text=(
                    "NASA HRP population-average context: 1.0–1.5%/month "
                    "(~0.033–0.05% loss/day); not a target or daily trajectory"
                ),
                annotation_position="top left",
                annotation_font={"color": "#ffd166", "size": 9},
            )
    figure.update_xaxes(
        title_text="Days ahead", row=len(active_indicators), col=1
    )
    figure.update_layout(
        height=max(300, 180 * len(active_indicators)),
        margin={"l": 8, "r": 8, "t": 64, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#d9e8ef"},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    return figure, omitted_notes


def _enriched_question(
    question: str, mode: str, scenario_id: str, latest: dict[str, Any]
) -> str:
    field_names = (
        "heart_rate",
        "bp_sys",
        "bp_dia",
        "blood_glucose",
        "body_temp",
        "sleep_hours",
        "mood_score",
        "radiation_dose_rate_msv_day",
        "neutron_radiation_msv",
        "bone_bmd_delta",
        "cabin_co2",
    )
    summary = ", ".join(
        f"{name}={_format_value(latest.get(name))}"
        for name in field_names
        if latest.get(name) is not None
    ) or "No telemetry values are recorded."
    return (
        f"{question}\n\n"
        "Dashboard context (demo telemetry, not a medical assessment):\n"
        f"- Environment mode: {mode}\n"
        f"- Scenario: {scenario_id}\n"
        f"- Latest telemetry: {summary}\n"
        "Treat measurements as synthetic or unverified unless their record "
        "explicitly establishes otherwise. Scenario fixture fallback values "
        "are not current sensor readings."
    )


st.markdown(
    """
    <style>
    :root {
      color-scheme: dark;
      --background-color: #07111b;
      --secondary-background-color: #0b1825;
      --text-color: #e6f2f7;
      --primary-color: #38d9ff;
    }
    .stApp {
      background:
        radial-gradient(ellipse at 18% 0%, rgba(18, 83, 112, .22), transparent 34%),
        linear-gradient(160deg, #07111b 0%, #091522 54%, #07101a 100%);
      color: #e6f2f7;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stApp p, .stApp label, .stApp [data-testid="stWidgetLabel"] {
      color: #e6f2f7;
    }
    .stApp [data-testid="stCaptionContainer"] { color: #93aab8; }
    .stApp [data-testid="stMetricLabel"],
    .stApp [data-testid="stMetricValue"],
    .stApp [data-testid="stMetricDelta"] { color: #e6f2f7; }
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #0b1825 0%, #0a1420 100%);
      border-right: 1px solid rgba(88, 174, 207, .18);
    }
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .mission-kicker {
      color: #62d9ff; letter-spacing: .18em; font-size: .75rem;
      font-weight: 700; text-transform: uppercase;
    }
    .mission-subtitle { color: #91a9b8; margin-top: -.6rem; }
    .comms-banner {
      border: 1px solid #ffab00; background: rgba(255, 171, 0, .12);
      color: #ffd166; padding: .8rem 1rem; border-radius: .6rem;
      font-weight: 800; letter-spacing: .04em; margin: .6rem 0 1rem;
      box-shadow: 0 0 24px rgba(255, 171, 0, .12);
    }
    .status-chip {
      display: inline-block; border: 1px solid currentColor; border-radius: 999px;
      padding: .24rem .65rem; font-size: .82rem; font-weight: 800;
      letter-spacing: .04em; margin: .15rem 0 .45rem;
    }
    .provenance-chip {
      display: inline-block; margin: .15rem 0 .45rem; padding: .12rem .45rem;
      border: 1px solid rgba(147,170,184,.35); border-radius: 999px;
      color: #b7c9d3; font-size: .72rem;
    }
    .data-core {
      display: flex; flex-wrap: wrap; align-items: center; gap: .4rem;
      min-height: 3.2rem; padding: .55rem .7rem;
      background: rgba(17, 34, 49, .72);
      border: 1px solid rgba(88,174,207,.18); border-radius: .65rem;
    }
    .data-pill {
      padding: .14rem .42rem; border: 1px solid rgba(56,217,255,.3);
      border-radius: 999px; color: #bdefff; font-size: .68rem;
      letter-spacing: .02em; white-space: nowrap;
    }
    .due-now {
      display: inline-block; margin-left: .4rem; padding: .12rem .42rem;
      border: 1px solid #ffab00; border-radius: .35rem; color: #ffd166;
      font-size: .72rem; font-weight: 800; letter-spacing: .04em;
    }
    .small-muted { color: #93aab8; font-size: .85rem; }
    div[data-testid="stMetric"] {
      background: rgba(17, 34, 49, .72); border: 1px solid rgba(88,174,207,.18);
      border-radius: .65rem; padding: .7rem .85rem;
    }
    div[data-testid="stButton"] > button {
      border: 1px solid rgba(56,217,255,.32); border-radius: .55rem;
      background: rgba(20, 54, 72, .62); color: #e6f8ff;
    }
    div[data-testid="stButton"] > button:hover {
      border-color: #38d9ff; color: #fff; background: rgba(23, 86, 112, .72);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_initialize_demo()
st.session_state.setdefault("handover_outbox", [])
if "selected_countermeasures" in st.session_state:
    previous_countermeasures = st.session_state["selected_countermeasures"]
    if isinstance(previous_countermeasures, list):
        st.session_state["selected_countermeasures"] = [
            "Water-Wall Shelter (design concept)"
            if item == "Water-Wall Shelter Relocation"
            else item
            for item in previous_countermeasures
        ]
active_scenario = st.session_state["active_scenario"]

with st.sidebar:
    st.markdown('<div class="mission-kicker">Mission workspace</div>', unsafe_allow_html=True)
    present_mode = st.toggle(
        "Present mode (30s Demo)",
        key="present_mode",
        help="Hide secondary captions and expanders for a cleaner screen recording.",
    )
    with st.expander("Demo Script (30s)", expanded=False):
        st.markdown(
            "1. Select a mission scenario.\n"
            "2. Point out the astronaut systems, status symbols, and DATA CORE provenance.\n"
            "3. Open one action card and distinguish demo bands from medical limits.\n"
            "4. Select a countermeasure concept and show the synthetic projection.\n"
            "5. Show offline cited retrieval or queue a delayed ground handover."
        )
    st.subheader("Demo scenarios")
    st.caption(
        "Preset trajectories are synthetic fixtures. Selecting one replaces "
        "that scenario's demo rows."
    )
    for label, scenario_id in SCENARIO_OPTIONS.items():
        is_active = scenario_id == active_scenario
        if st.button(
            f"▶ {label}" if is_active else label,
            key=f"preset_{scenario_id}",
            width="stretch",
            type="primary" if is_active else "secondary",
        ):
            _load_preset(scenario_id)
            st.rerun()

    st.divider()
    st.subheader("Manual telemetry")
    _, scenario_latest = _latest_for(active_scenario)
    suggested_day = (
        int(scenario_latest["mission_day"]) + 1 if scenario_latest else 1
    )
    with st.expander("Enter an optional telemetry point", expanded=False):
        with st.form("manual_telemetry_form"):
            st.caption(
                "Enter only readings from an approved device/procedure. "
                "Blank inputs stay null; entries are unverified."
            )
            st.caption(f"Next stored mission day: {suggested_day}")
            heart_rate = st.number_input(
                "Heart rate (bpm)", min_value=0.0, value=None, step=1.0
            )
            bp_sys = st.number_input(
                "Systolic blood pressure (mmHg)",
                min_value=0.0,
                value=None,
                step=1.0,
            )
            bp_dia = st.number_input(
                "Diastolic blood pressure (mmHg)",
                min_value=0.0,
                value=None,
                step=1.0,
            )
            blood_glucose = st.number_input(
                "Blood glucose (mg/dL)",
                min_value=0.0,
                value=None,
                step=1.0,
            )
            body_temp = st.number_input(
                "Body temperature (°C)",
                min_value=0.0,
                value=None,
                step=0.1,
                format="%.1f",
            )
            sleep_hours = st.number_input(
                "Sleep (hours)",
                min_value=0.0,
                value=None,
                step=0.5,
                format="%.1f",
            )
            mood_score = st.number_input(
                "Mood score (project scale 1–10)",
                min_value=1.0,
                max_value=10.0,
                value=None,
                step=1.0,
            )
            radiation_rate = st.number_input(
                "Radiation dose rate (mSv/day; quantity must be specified)",
                min_value=0.0,
                value=None,
                step=0.1,
                format="%.2f",
            )
            bone_delta = st.number_input(
                "BMD delta (%)",
                value=None,
                step=0.1,
                format="%.2f",
            )
            cabin_co2 = st.number_input(
                "Cabin CO2 partial pressure (mmHg)",
                min_value=0.0,
                value=None,
                step=0.1,
                format="%.2f",
            )
            override_sensor_plausibility = st.checkbox(
                "Override sensor plausibility check"
            )
            submitted = st.form_submit_button(
                "Save telemetry point", width="stretch"
            )
        if submitted:
            entered = {
                "heart_rate": heart_rate,
                "bp_sys": bp_sys,
                "bp_dia": bp_dia,
                "blood_glucose": blood_glucose,
                "body_temp": body_temp,
                "sleep_hours": sleep_hours,
                "mood_score": mood_score,
                "radiation_dose_rate_msv_day": radiation_rate,
                "bone_bmd_delta": bone_delta,
                "cabin_co2": cabin_co2,
            }
            if all(value is None for value in entered.values()):
                st.warning("Enter at least one measurement before saving.")
            else:
                plausibility_warnings = validate_telemetry_plausibility(entered)
                if plausibility_warnings and not override_sensor_plausibility:
                    st.error(
                        "Telemetry was not saved. Review these checks or select "
                        "the override checkbox:\n\n"
                        + "\n".join(f"- {item}" for item in plausibility_warnings)
                    )
                else:
                    if plausibility_warnings:
                        st.warning(
                            "Saving despite plausibility warnings; the record "
                            "remains unverified."
                        )
                    log_vitals(
                        mission_day=suggested_day,
                        environment=st.session_state.get(
                            "environment_mode",
                            SCENARIO_ENVIRONMENTS[active_scenario],
                        ),
                        scenario_id=active_scenario,
                        evidence_status="user_entered_unverified",
                        **entered,
                    )
                    st.session_state["_telemetry_saved"] = True
                    st.rerun()

if present_mode:
    st.markdown(
        """
        <style>
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stExpander"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

if st.session_state.pop("_telemetry_saved", False):
    st.toast("Telemetry point saved as unverified demo data.")

active_scenario = st.session_state["active_scenario"]
history, latest_row = _latest_for(active_scenario)
if not history:
    load_scenario_to_db(active_scenario)
    history, latest_row = _latest_for(active_scenario)
effective_latest = effective_latest_state(history)
systems = evaluate_health_systems(effective_latest)
stats = get_gamification_stats()
environment_mode = st.session_state.get(
    "environment_mode", SCENARIO_ENVIRONMENTS[active_scenario]
)

st.title("Mission Control")
st.markdown(
    '<div class="mission-subtitle">Local demo telemetry, evidence-linked knowledge, and non-operational visualizations.</div>',
    unsafe_allow_html=True,
)

header_cols = st.columns([1.7, 1.0, 2.4], gap="small")
with header_cols[0]:
    st.selectbox(
        "Environment mode",
        ENVIRONMENT_OPTIONS,
        key="environment_mode",
        help="Comms profiles are interface scenarios, not measured link performance.",
    )
    environment_mode = st.session_state["environment_mode"]
    environment_profile = environment_constraints(environment_mode)
with header_cols[1]:
    st.metric(
        "Demo readiness (synthetic)",
        f"{compute_demo_readiness(systems):.0f}/100",
        help=(
            "Computed from this scenario's illustrative system bands: "
            "20 points per Amber, 50 per Red; No Data is ignored. "
            "Not a medical fitness-for-duty assessment."
        ),
    )
with header_cols[2]:
    st.markdown(_data_core_pills(effective_latest), unsafe_allow_html=True)

st.subheader("Crew systems overview")
body_col, trend_col = st.columns([0.95, 1.35], gap="large")

with body_col:
    st.markdown("#### Interactive human-body status")
    qp_system = st.query_params.get("system")
    if qp_system in SYSTEM_LABELS:
        st.session_state["selected_system"] = qp_system
        del st.query_params["system"]
    selected_for_svg = st.session_state.get(
        "selected_system", "neuro_ocular_behavioral"
    )
    components.html(
        _render_astro_svg(systems, selected_for_svg),
        height=465,
        scrolling=False,
    )
    selected_system = st.radio(
        "Select a system",
        options=list(SYSTEM_LABELS),
        format_func=lambda value: SYSTEM_LABELS[value],
        horizontal=True,
        key="selected_system",
    )
    system = systems[selected_system]
    st.markdown(
        f'<span class="status-chip" style="color:{system["color"]}">'
        f'{STATUS_SYMBOLS[system["status"]]} {system["status"].upper()}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("**Project tags:** " + " · ".join(f"`{tag}`" for tag in system["project_tag"]))
    st.caption(system["classification_note"])
    st.caption(system["system_note"])

    due_metrics = _due_metrics_for_system(
        history, selected_system, effective_latest
    )
    if due_metrics:
        st.markdown(
            '<span class="due-now">DUE NOW</span> '
            + " · ".join(html.escape(metric) for metric in due_metrics),
            unsafe_allow_html=True,
        )
        st.caption(
            "Synthetic/demo cadence only; not a mission schedule or medical alert."
        )

    metric_cols = st.columns(2)
    for index, (name, value) in enumerate(system["key_metrics"].items()):
        label = METRIC_LABELS.get(name, name.replace("_", " ").title())
        provenance_label, provenance_note = _metric_provenance(
            name, effective_latest, active_scenario
        )
        metric_cols[index % 2].metric(
            label, _format_value(value), help=provenance_note
        )
        metric_cols[index % 2].markdown(
            f'<span class="provenance-chip">{html.escape(provenance_label)}</span>',
            unsafe_allow_html=True,
        )
    if system["compounding_alerts"]:
        for alert in system["compounding_alerts"]:
            st.warning(alert)
    else:
        st.caption("No configured demo co-occurrence alert is present.")

    action_text, escalation_text = SYSTEM_ACTION_GUIDANCE[selected_system]
    with st.expander("What You Can Do Now (General Countermeasures)"):
        st.markdown(action_text)
        st.markdown(
            f"**Knowledge base:** {SYSTEM_ACTION_KB_SOURCES[selected_system]}"
        )
        st.markdown(f"**Escalate when...** {escalation_text}")

    with st.expander(
        "How to Perform Self-Exam",
        expanded=(system["status"] != "Green"),
    ):
        st.markdown(
            _extract_guide(EXAM_HEADINGS[selected_system])
        )
        st.caption(
            "Educational reference only. Follow approved onboard medical "
            "procedures; this guide is not an authorized flight protocol."
        )
    with st.expander("Astronaut Quick Reference (5 Core Questions)"):
        questions = (
            "1. Space measurement:",
            "2. Physiological purpose:",
            "3. Spaceflight hazard mechanism:",
            "4. Numeric escalation trigger:",
            "5. Concrete preventive countermeasure:",
        )
        for question, answer in zip(questions, QUICK_REFERENCE[selected_system]):
            st.markdown(
                f"**{question}** {answer} "
                f"*(KB: {QUICK_REFERENCE_KB_SOURCES[selected_system]})*"
            )
        st.caption(
            "Follow approved onboard procedures. This plain-language reference "
            "is educational and does not provide diagnosis or treatment."
        )

with trend_col:
    st.markdown("#### Historical trend · 14 mission days")
    st.caption("Trend values come from the selected local scenario; fixture data may be synthetic.")
    historical_figure = _historical_figure(history, selected_system)
    if historical_figure is None:
        st.info("No non-null history is available for this system in the active scenario.")
    else:
        st.plotly_chart(
            historical_figure,
            width="stretch",
            config={"displayModeBar": False},
        )

    st.markdown("#### Seven-day countermeasure simulator")
    st.caption(
        "All projected drift and countermeasure effects are synthetic, "
        "non-operational UI assumptions."
    )
    selected_countermeasures = st.multiselect(
        "Select countermeasure concepts",
        options=COUNTERMEASURES,
        default=[],
        key="selected_countermeasures",
    )
    projection = simulate_countermeasure_projection(
        effective_latest, selected_countermeasures
    )
    projection_figure, omitted_indicators = _projection_figure(projection)
    st.plotly_chart(
        projection_figure,
        width="stretch",
        config={"displayModeBar": False},
    )
    if omitted_indicators:
        st.caption(" ".join(omitted_indicators))
    st.caption(projection.attrs["disclaimer"])
    st.caption(
        "BMD reference context: NASA HRP, "
        "[Risk of Spaceflight-Induced Bone Changes]"
        "(https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/). "
        "The shaded population-average rate is not a target, daily prediction, "
        "or individual risk estimate."
    )

with st.expander("Mission Routine & Ground Link", expanded=False):
    st.markdown("#### Crew Check-In & Gamification")
    checkin_cols = st.columns(2)
    checkin_cols[0].metric("Check-in streak", f"{stats['streak_days']} days")
    checkin_cols[1].metric("Completed check-ins", stats["completed_tasks"])
    protocols = st.columns(3)
    with protocols[0]:
        st.checkbox("👁️ Vision Grid Check (SANS)", key="protocol_amsler")
    with protocols[1]:
        st.checkbox("🦴 ARED Resistance & Hydration Protocol", key="protocol_ared")
    with protocols[2]:
        st.checkbox("☢️ Dosimeter & Cabin CO2 Verification", key="protocol_dosimeter")
    protocol_count = sum(
        bool(st.session_state.get(key, False))
        for key in ("protocol_amsler", "protocol_ared", "protocol_dosimeter")
    )
    st.progress(
        protocol_count / 3,
        text=f"Daily protocol completion: {protocol_count}/3",
    )

    completed_tasks = int(stats.get("completed_tasks", 0))
    streak_days = int(stats.get("streak_days", 0))
    if completed_tasks >= 30 and streak_days >= 7:
        crew_rank = "Deep-Space Commander"
    elif completed_tasks >= 7 or streak_days >= 3:
        crew_rank = "Orbital Specialist"
    else:
        crew_rank = "Cadet"
    st.markdown(f"**Crew Rank:** `{crew_rank}`")
    if st.button(
        "Complete Daily Self-Check",
        type="primary",
        width="stretch",
    ):
        complete_daily_checkin()
        st.session_state["_celebrate_checkin"] = protocol_count == 3
        st.rerun()
    st.caption("Records a local demo check-in; checklist is for engagement only.")
    if st.session_state.pop("_celebrate_checkin", False):
        if protocol_count == 3:
            st.balloons()
            st.toast("All three daily protocols complete. Check-in logged!")
        else:
            st.toast(
                "Daily check-in logged. Complete all 3 protocols for the full "
                "check-in celebration."
            )

    if environment_mode != ENVIRONMENT_OPTIONS[0]:
        st.markdown(
            '<div class="comms-banner">AIR-GAPPED AUTONOMOUS MODE ACTIVE — '
            "Ground Flight Surgeon Unreachable</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "Connected-mode profile selected. This demo does not verify "
            "connectivity or contact a flight surgeon."
        )
    st.markdown(
        "**Onboard instrument profile (demo; availability unverified):** "
        f"{environment_profile['measurement_feasibility']}"
    )
    st.caption(
        f"Comms profile: {environment_profile['latency_label']} · "
        f"{environment_profile['comms_state']}"
    )

    report = _ground_handover_report(
        active_scenario, environment_mode, systems, effective_latest
    )
    report_file_name = (
        "offline_astro_twin_handover_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
    )
    if environment_mode == ENVIRONMENT_OPTIONS[1]:
        simulated_eta = "T+2.6s"
    else:
        simulated_eta = "T+44m"

    if environment_mode == ENVIRONMENT_OPTIONS[0]:
        st.download_button(
            "Download Ground Handover Report",
            data=report,
            file_name=report_file_name,
            mime="text/markdown",
            help="Downloads a local report; it is not transmitted to ground.",
        )
    else:
        queue_col, download_col, contact_col = st.columns([1.2, 1.15, 1.0])
        queue_clicked = queue_col.button(
            "Queue Ground Handover Report",
            width="stretch",
            help="Adds a local demo outbox entry; no report is transmitted.",
        )
        download_col.download_button(
            "Download Markdown",
            data=report,
            file_name=report_file_name,
            mime="text/markdown",
            width="stretch",
        )
        outbox = st.session_state["handover_outbox"]
        contact_clicked = contact_col.button(
            "Mark Contact Established",
            width="stretch",
            disabled=not outbox or bool(outbox[-1]["contact_established"]),
            help="Marks the latest simulated handover as acknowledged locally.",
        )
        if queue_clicked:
            outbox.append(
                {
                    "report": report,
                    "environment": environment_mode,
                    "queued_at": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    "simulated_reply_eta": simulated_eta,
                    "contact_established": False,
                }
            )
        if contact_clicked:
            outbox[-1]["contact_established"] = True
            outbox[-1]["contact_established_at"] = datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds")
        if outbox:
            latest_handover = outbox[-1]
            contact_state = (
                "contact marked established"
                if latest_handover["contact_established"]
                else f"simulated reply ETA {latest_handover['simulated_reply_eta']}"
            )
            st.info(
                f"Local outbox: {contact_state}. No communications are sent."
            )

    st.caption(
        f"Active scenario: **{SCENARIO_LABELS.get(active_scenario, active_scenario)}** "
        f"({active_scenario}) · Latest stored mission day: "
        f"{latest_row.get('mission_day', '—')}. Status colors and fixture values "
        "are non-operational."
    )

st.divider()
st.subheader("Offline NASA / CSA Flight Surgeon Copilot")
st.caption(
    "Local retrieval only; answers cite retrieved sources and do not replace "
    "crew medical procedures or ground consultation."
)

quick_actions = {
    "Triage Current Anomalies": (
        "Summarize the current demo telemetry and identify which values need "
        "verification against approved procedures. Do not diagnose or prescribe."
    ),
    "Radiation Shelter Guidance": (
        "Summarize the retrieved NASA/CSA radiation and shelter evidence. "
        "Distinguish measurements, project assumptions, and mission-specific guidance."
    ),
    "Explain Risk Factors & OSDR Evidence": (
        "Explain relevant HRP risks and NASA OSDR studies, preserving exact "
        "study IDs and whether each study is ground, animal, ex-vivo, or in-flight."
    ),
}

def _run_copilot(user_question: str) -> None:
    enriched = _enriched_question(
        user_question,
        st.session_state["environment_mode"],
        st.session_state["active_scenario"],
        effective_latest,
    )
    try:
        with st.spinner("Searching the local NASA/CSA knowledge base..."):
            result = query_flight_surgeon_copilot(enriched, top_k=5)
        st.session_state["copilot_answer"] = result
        st.session_state["copilot_question"] = user_question
    except RuntimeError as exc:
        st.error(f"Copilot query failed: {exc}")


action_cols = st.columns(3)
for column, (label, question) in zip(action_cols, quick_actions.items()):
    with column:
        if st.button(label, width="stretch"):
            _run_copilot(question)

with st.form("copilot_question_form"):
    custom_question = st.text_input(
        "Ask a question",
        placeholder="Ask about a risk, scenario, or cited study...",
    )
    ask = st.form_submit_button("Ask Copilot", type="primary")
if ask:
    if custom_question.strip():
        _run_copilot(custom_question.strip())
    else:
        st.warning("Enter a question first.")

if st.session_state.get("copilot_answer"):
    st.markdown(f"**Question:** {st.session_state['copilot_question']}")
    st.markdown(st.session_state["copilot_answer"])
