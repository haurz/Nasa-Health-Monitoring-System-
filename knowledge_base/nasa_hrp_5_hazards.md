# NASA HRP: five hazards and associated health risks

## Scope and safety

This is an educational, offline reference for the Offline Astro-Twin challenge concept. It summarizes public NASA Human Research Program (HRP) material; it is **not** a NASA procedure, a clinical decision aid, or a substitute for evaluation by the mission medical team. NASA's public risk descriptions explain research risks, not universal in-flight diagnostic cutoffs.

The colored bands below are **illustrative triage placeholders only**. They are not NASA/CSA limits, astronaut medical standards, or instructions to treat. They are pending review and approval by the flight surgeon and mission medical/operations authority. The crew member's approved personal baseline, measurement method, vehicle constraints, and mission-specific procedure supersede every example here. An onboard vehicle alarm or a red-flag symptom warrants action under the approved emergency procedure regardless of a number in this table.

## NASA's five hazards of human spaceflight

NASA HRP groups interacting spaceflight conditions into five hazards. A single event can involve several at once; they should not be treated as isolated causes.

1. **Space radiation.** Galactic cosmic rays and solar particle events (SPEs) expose crews to ionizing radiation. Potential concerns include cancer, degenerative tissue effects, central nervous system effects, and acute radiation effects. Radiation cannot be sensed directly by a person; environmental monitoring and dosimetry are essential.
2. **Isolation and confinement.** Small living volume, separation from family and ordinary social supports, team dynamics, workload, and limited privacy can affect mood, behavior, sleep, and performance.
3. **Distance from Earth.** Communication delay or loss, limited resupply, and reduced access to ground-based medical expertise make autonomy and preplanned contingencies increasingly important.
4. **Gravity fields.** Microgravity and transitions between gravity levels affect fluid distribution, cardiovascular regulation, balance, sensorimotor function, muscle, and weight-bearing bone. Headward fluid shifts are also associated with eye and brain changes.
5. **Hostile/closed environments.** A spacecraft is a constrained ecosystem: atmosphere, temperature, pressure, lighting, noise, microbes, and limited space can influence health and performance. Exposure and equipment status require vehicle-specific monitoring.

## HRP health risks relevant to monitoring

- **Cardiovascular adaptations (`HRP-MOD-CARDIO`, project tag):** Weightlessness redistributes body fluids and changes cardiovascular loading and regulation. NASA identifies orthostatic intolerance during acceleration as a primary in-mission cardiovascular risk, particularly for LEO and lunar surface operations. A 10–15% plasma-volume shift was not verified in the NASA sources reviewed for this update; do not present that figure as an HRP baseline. A resting heart rate or cuff reading alone cannot diagnose these conditions.
- **Spaceflight-induced bone changes (`HRP-RED-BONE`, project tag):** NASA reports average bone mineral density (BMD) losses of **1–1.5% per month** in weight-bearing bones during four-to-six-month missions. This is a population-level research finding, not an individual prediction, diagnostic threshold, or safe/unsafe cutoff. NASA notes that bone-loss persistence on longer missions remains uncertain.
- **Spaceflight Associated Neuro-ocular Syndrome (SANS) (`HRP-RED-SANS`, project tag):** Headward fluid shifts in chronic weightlessness are associated with optic-nerve swelling, retinal folds, flattening of the back of the eye, and other eye/brain structural changes. NASA identifies SANS as a research priority for future Mars missions; mechanisms and long-term outcomes remain under study. New visual or neurologic symptoms merit medical evaluation.
- **Altered immune system responses:** Spaceflight stressors can alter immune responses; NASA reports reactivation of latent viruses (including herpes-family viruses), as well as reported rashes, atypical allergies, and infections. A symptom log can help identify change but cannot measure immune function or rule out infection.
- **Behavioral health and performance (`HRP-RED-BHPC`, project tag):** Isolation, workload, irregular schedules, and disrupted light-dark cues may impair sleep, circadian alignment, mood, and performance. NASA says exploration missions beyond LEO will have constrained resources that limit validated countermeasures; feasible and acceptable countermeasures for exploration missions have not yet been developed and validated. Sleep quantity alone does not establish alertness or fitness for duty.
- **Space radiation (`HRP-RED-RAD`, project tag):** NASA identifies radiation exposure as a major human-spaceflight risk and describes continuous environmental monitoring and dosimetry support. Do not treat any single dose-rate number as an individual limit, warning threshold, or mission-wide prediction; use mission-specific radiation protection rules.

### Project alert-tag and scenario-data provenance

The strings `HRP-RED-SANS`, `HRP-RED-BONE`, `HRP-RED-BHPC`, `HRP-RED-RAD`, and `HRP-MOD-CARDIO` are **project-defined labels**, not NASA-issued risk IDs. NASA's public HRP pages identify the corresponding human-system risks but do not assign these IDs or certify these `RED`/`MOD` groupings as NASA severity classifications. They are organizational tags only, not medical alerts, probabilities, risk ratings, or action thresholds.

The following values may be used only as **synthetic scenario-fixture inputs** unless a mission-specific, authoritative source is supplied. The cited primary sources establish context or report different measurements; they do not substantiate the fixture values:

| Scenario value | Evidence status and safe interpretation |
|---|---|
| ISS/LEO radiation, approximately **0.5 mSv/day** | Not verified as an ISS total-dose empirical baseline in the NASA/CSA sources reviewed here. CSA's Radi-N2 reported an early result of about **150 µSv/day (0.15 mSv/day) of neutron dose**, a neutron-only experiment result, not a total-dose rate or limit. Keep 0.5 mSv/day labeled synthetic unless a directly applicable source and dose quantity are cited. |
| ISS cabin CO₂, **2.8 mmHg** | Not verified as an empirical ISS cabin baseline by the NASA sources reviewed here. Treat as a synthetic fixture value, not a nominal level, limit, or alert threshold. NASA's CO₂ risk page describes the hazard and control systems, not this measurement. |
| Artemis lunar solar-particle-event spike, **18.5 mSv/day** neutron/proton | Not verified as an Artemis measurement or NASA/CSA event baseline. Treat the number and particle characterization as synthetic; it is not an SPE forecast, dose limit, alarm threshold, or crew action criterion. |
| Mars Surface Day 210 cumulative BMD change, **−8.4%** | No crewed Mars surface observation establishes a day-210 BMD result. Treat this value as a synthetic model/fixture assumption, not measured Mars data or an individual prediction. NASA's 1–1.5% monthly finding is for typical four-to-six-month spaceflight missions and does not validate this Mars extrapolation. |
| Mars Surface Day 210 cabin CO₂, **4.3 mmHg** | Not verified as a measured Mars habitat value. Treat as a synthetic fixture value, not an empirical environmental baseline, exposure limit, or action threshold. |
| Cardiovascular plasma-volume shift, **10–15%** | Not verified as an empirical value in the NASA sources reviewed here. Do not attach this range to the NASA cardiovascular risk or represent it as a NASA HRP baseline without a precise supporting source. |

When presenting these fixture inputs, preserve the scenario label and cite them as **synthetic assumptions**; do not attach a NASA citation in a way that implies NASA measured or endorsed the values. Cite NASA/CSA sources separately for the contextual risk claim. NASA/CSA operational limits, dose quantities, and environmental control procedures are mission- and vehicle-specific.

## Illustrative monitoring bands — not operational limits

These example bands are included only to illustrate how a future interface might organize observations. Except for the cited scientific findings (such as average bone loss), these numbers are **not NASA/CSA-approved limits** and are not validated for astronauts, microgravity, or this project. They must not be used to clear someone for duty, diagnose illness, or delay escalation. Repeat a questionable reading only if doing so is safe and consistent with the approved procedure.

| Measure | Green (illustrative) | Amber (illustrative) | Red (illustrative) |
|---|---|---|---|
| Resting heart rate (bpm) | 50–100 | 40–49 or 101–120 | <40 or >120; or any rate with fainting, chest pain, severe breathlessness, or marked weakness |
| Blood pressure (mmHg) | Systolic 90–139 **and** diastolic 60–89 | Systolic 80–89 or 140–179; or diastolic 50–59 or 90–119 | Systolic <80 or ≥180; diastolic <50 or ≥120; or any reading with collapse, chest pain, confusion, or severe symptoms |
| Blood glucose (mg/dL) | 70–180 | 54–69 or 181–250 | <54 or >250, especially with confusion, vomiting, severe weakness, or symptoms of low/high glucose |
| Body temperature (°C) | 36.0–37.9 | 35.0–35.9 or 38.0–38.9 | <35.0 or ≥39.0, or temperature change with severe illness signs |
| Daily sleep (hours actually asleep, 24-hour period) | ≥7 | 5 to <7 | <5, repeated inability to sleep, or sleepiness that creates an immediate task-safety concern |
| Mood score (1–10; 10 = best, 1 = worst) | 7–10 | 4–6 | 1–3, or any thoughts of self-harm / inability to remain safe regardless of score |
| Bone-density “T-score drift (%)” | Not defined | Not defined | Not defined — a T-score is a standard-deviation score, **not a percentage**; do not calculate percent drift from it |
| Cabin CO₂ partial pressure (mmHg) | <2.0 | 2.0–3.0 | >3.0 or any vehicle CO₂ alarm / symptoms; follow the vehicle's approved environmental-control procedure |

These bands are intentionally conservative examples, not standards. Heart rate and blood pressure depend on the crewmember's baseline, posture, timing, device, and vehicle; glucose depends on meal timing, instrument, and clinical context; temperature depends on measurement site and device. An individual may be healthy outside these ranges or unwell inside them.

For bone monitoring, use only a clinician-approved, comparable instrument and site. A T-score is expressed in standard deviations from a reference population. It is not a percent-valued longitudinal measure. NASA's reported 1–1.5% monthly BMD loss is a research average, not a percent “T-score drift” action threshold. No public NASA/CSA individual in-flight BMD percentage alert band is specified here.

For cabin CO₂, vehicle sensors, published vehicle limits, and onboard alarms govern; the values above are merely illustrative placeholders and must not replace environmental-control-system procedures.

## Demo telemetry and countermeasure projections

The optional SQLite demo trajectory is generated, not astronaut telemetry. It fills non-fixture vital fields with deterministic synthetic values; exact fixture inputs such as 0.5 mSv/day, 2.8 mmHg, 18.5 mSv/day, −8.4% BMD, and 4.3 mmHg retain their synthetic evidence labels. The Artemis value is stored as a mixed neutron/proton scenario value, never as a neutron-only measurement. Missing measurements remain null rather than being represented as zero.

Health-system colors and compounding alerts are non-operational UI groupings. They use illustrative display bands, including project-defined BMD and radiation groupings; they are not NASA severity ratings, dose limits, diagnostic criteria, or evidence of causation. The neuro/behavioral grouping has no SANS-specific eye examination, and the immune/radiation grouping contains no immune biomarker.

The seven-day “No Action” and “With Selected Countermeasures” projection is a synthetic visualization only. Its baseline drift and the assumed effects of Water-Wall Shelter Relocation, ARED Resistance Protocol (+30 min), Thigh Cuff & Fluid Load, and Circadian Blue-Light Reset are invented interface coefficients, not measured efficacy estimates or medical recommendations. Do not use the generated scores or trajectory for mission planning, treatment, or crew decisions.

## Red flags and communications-loss contingency

Use the mission's prebriefed emergency and medical decision procedures. Do not wait for a scheduled check-in or for a measurement to enter a colored band when there is chest pain, collapse, severe breathing difficulty, new one-sided weakness or speech difficulty, seizure, confusion, sudden severe headache, acute vision loss, serious injury, or rapidly worsening symptoms. Thoughts of self-harm or inability to keep oneself safe also require immediate escalation through the approved crew-support route.

If communication with Earth is unavailable: follow the onboard emergency checklist and assigned crew roles; use the designated onboard medical resources and locally stored mission guidance; record symptoms, onset, trend, and measurements; use alternate approved communication paths and retry on the prebriefed schedule. Preserve the crew member's safety and do not improvise medication or procedures from this reference. Resume ground consultation as soon as the approved communications route is available.

## Public sources

- NASA HRP, [5 Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)
- NASA HRP, [Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
- NASA, [Human System Risks](https://www.nasa.gov/hhp/human-system-risks/) (risk descriptions; does not define the project alert IDs above)
- NASA, [Behavioral Health Risk](https://www.nasa.gov/directorates/esdmd/hhp/behavioral-health-risk/)
- NASA, [Risk of Cardiovascular Adaptations](https://www.nasa.gov/directorates/esdmd/hhp/cv-risk/)
- NASA HRP, [Risk of Cardiovascular Adaptations](https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/)
- NASA, [Space Radiation](https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/)
- NASA, [CO₂ Risk](https://www.nasa.gov/directorates/esdmd/hhp/carbon-dioxide-risk/)
- NASA, [Risk of Bone Fracture due to Spaceflight-induced Changes to Bone](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-bone-fracture-due-to-spaceflight-induced-changes-to-bone/)
- NASA, [Risk of Spaceflight Associated Neuro-ocular Syndrome](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-spaceflight-associated-neuro-ocular-syndrome/)
- NASA HRP, [Risk of Spaceflight-Induced Bone Changes](https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/)
- NASA HRP, [Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/)
- NASA HRP, [Risk of Altered Immune System Responses](https://www.nasa.gov/reference/risk-of-altered-immune-system-responses/)
- NASA HRP, [Risk from Inadequate Sleep and Irregular Schedules](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/)
- NASA HRP, [Hazard: Isolation and Confinement](https://www.nasa.gov/hrp/hazard-isolation-and-confinement/)
- NASA HRP, [Hazard: Distance from Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/)
- NASA HRP, [Hazard: Gravity Fields](https://www.nasa.gov/hrp/hazard-gravity-fields/)
- NASA HRP, [Hazard: Hostile/Closed Environments](https://www.nasa.gov/hrp/hazard-hostile-closed-environments/)
- NASA Human Health and Performance, [Space Radiation](https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/)
- Canadian Space Agency, [Radi-N2: Tracking space radiation and its risks](https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp) (neutron-dose result; not total ISS dose or an operational threshold)
