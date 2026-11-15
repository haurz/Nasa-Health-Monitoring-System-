# Offline Astro-Twin

**2026 NASA Space Apps Challenge — Create Health Monitoring Software for Astronauts on Space Missions**

Offline Astro-Twin is an educational prototype for exploring how a locally available crew-health dashboard and evidence-linked reference assistant could work during deep-space missions. It combines synthetic mission scenarios, locally stored telemetry, a small retrieval-augmented knowledge base, and transparent, non-operational visualizations.

> **Safety and evidence notice:** This project is not a medical device, NASA/CSA system, flight procedure, validated clinical decision-support system, or replacement for mission medical authority. Project-defined `HRP-RED-*` and `HRP-MOD-*` strings are organizational tags—not NASA risk IDs or severity classifications. Scenario values, telemetry trajectories, status colors/bands, readiness scores, and projected countermeasure effects are synthetic design assumptions unless explicitly cited otherwise.

## Project overview and problem statement

On deep-space missions, crew medical support cannot assume continuous contact with Earth. Artemis lunar transit introduces communication delay, while Mars surface operations may face up to **22 minutes one-way communication delay**—and therefore periods when a real-time ground response is unavailable. A cloud-dependent health application may also be unusable when connectivity is interrupted.

Offline Astro-Twin explores an **air-gapped-first** design: keep the current demo telemetry, local knowledge index, and retrieval interface on the local machine so the interface can still run when Ollama or a network service is unreachable. The goal is to support review of observations and retrieval of cited public background material—not to diagnose, prescribe, set alert thresholds, or autonomously make crew-care decisions. Mission-specific procedures and the crew medical officer remain authoritative.

The Mars and lunar environment labels and latency descriptions in this prototype are interface scenarios, not measurements of a deployed NASA system or guaranteed communications performance.

## Challenge requirements alignment

This table is the team's interpretation of the Space Apps challenge, not a claim that the prototype satisfies flight or clinical requirements.

| Challenge need | Offline Astro-Twin implementation | Boundary |
|---|---|---|
| Monitor crew health across mission conditions | Four-system dashboard, manual telemetry entry, scenario histories, and status visualization | Demo fixtures and display bands are synthetic; this is not a medical monitor. |
| Support missions with limited Earth connectivity | Local SQLite telemetry, persistent Chroma index, deterministic local embedding fallback, and extractive answer fallback | The handover outbox is simulated; no report is transmitted or acknowledged by ground. |
| Make health information understandable to crew | Interactive astronaut overview, plain-language action cards, and five-question references | Guidance is educational and does not replace onboard procedures or medical authority. |
| Provide evidence for displayed context | Knowledge-base retrieval returns citations to NASA/CSA public material | A citation provides context; it does not validate the project's scenario values or thresholds. |
| Preserve data provenance and uncertainty | Real-reference, extrapolated, synthetic, and unverified-manual labels | No individual astronaut or validated mission telemetry is included. |

## System architecture

| Layer | Module / data | Responsibility |
|---|---|---|
| Mission-control UI | [`app.py`](app.py) | Streamlit dashboard with environment selector, optional comms-blackout banner, scenario and manual telemetry controls, interactive SVG astronaut silhouette, four-system status details, 14-day Plotly history, seven-day projection, and a cited copilot panel. |
| Local data and demo logic | [`engine.py`](engine.py) | SQLite telemetry and gamification helpers; illustrative neuro/ocular/behavioral, cardiovascular, skeletal/bone, and immune/radiation groupings; synthetic countermeasure projections; local retrieval and answer generation. |
| Knowledge indexer | [`ingest_rag.py`](ingest_rag.py) | Splits Markdown knowledge-base documents into cited chunks and indexes them in a persistent ChromaDB collection. It uses Ollama embeddings when available and deterministic 384-dimensional local hash embeddings when Ollama cannot be reached. |
| Evidence corpus | [`knowledge_base/`](knowledge_base/) | NASA HRP risk context, NASA OSDR/Environmental Data App scope and study metadata, CSA neutron-monitoring context, and educational self-exam notes with limits and source links. |

The local database is written to `data/mission_telemetry.db`; ChromaDB persists its index in `chroma_db/`. Both folders are retained in the project so a fresh clone has the demo's local data and knowledge index available without a network download.

### Offline behavior

If Ollama is unavailable, the embedding function falls back to deterministic local hash vectors, and answer generation produces an extractive summary of retrieved passages. The Chroma collection is rebuilt when its embedding backend or vector dimension changes. The dashboard can retrieve from the local index without requiring a cloud inference provider; initial ingestion still needs either an available Ollama embedding endpoint or the built-in hash-vector fallback.

## NASA and space-agency partner data

The knowledge base is a curated reference set, not a claim that every cited dataset calibrates or validates the prototype. The table maps mission-health needs to relevant public resources and explains the prototype's intended use and limitations.

| Problem / research context | Public resource | Offline Astro-Twin use and evidence limits |
|---|---|---|
| Interacting human-spaceflight hazards and broad HRP risk context | NASA HRP [5 Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/) and [Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/); NASA [Human System Risks](https://www.nasa.gov/hhp/human-system-risks/) | Background taxonomy for the knowledge base. The project’s colored status groupings and tag strings are not NASA classifications. |
| SANS and optic-nerve research | NASA HRP [Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/) and NASA [Risk of Spaceflight Associated Neuro-ocular Syndrome](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-spaceflight-associated-neuro-ocular-syndrome/); NASA OSDR [OSD-817 study page](https://osdr.nasa.gov/bio/repo/data/studies/OSD-817) and [OSD-817 metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/) | OSD-817 is a ground, ex-vivo human optic-nerve/posterior-eye model relevant to SANS pathogenesis research—not an in-flight astronaut cohort or a SANS risk estimate. |
| Bone changes and bone-related research | NASA HRP [Risk of Spaceflight-Induced Bone Changes](https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/) and NASA [Risk of Bone Fracture due to Spaceflight-induced Changes to Bone](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-bone-fracture-due-to-spaceflight-induced-changes-to-bone/); NASA OSDR [OSD-979 study page](https://osdr.nasa.gov/bio/repo/data/studies/OSD-979) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-979/); [OSD-981 study page](https://osdr.nasa.gov/bio/repo/data/studies/OSD-981) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-981/) | OSD-979 is a ground study in growing female mice on thermoregulation and cancellous-bone turnover. OSD-981 is a ground male-mouse irradiation/immune-reconstitution study with bone assays; it does not report a spaceflight bone-loss result. Neither validates the demo’s astronaut BMD trajectory. |
| Social isolation, simulated radiation, and behavior | NASA OSDR [OSD-1018 study page](https://osdr.nasa.gov/bio/repo/data/studies/OSD-1018) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-1018/); NASA [Behavioral Health Risk](https://www.nasa.gov/directorates/esdmd/hhp/behavioral-health-risk/) | OSD-1018 is a ground rat study of social isolation, simulated radiation, and behavior/motor learning—not a human behavioral-health outcome or astronaut performance threshold. |
| Cardiovascular adaptation and orthostatic intolerance | NASA [Risk of Cardiovascular Adaptations](https://www.nasa.gov/directorates/esdmd/hhp/cv-risk/) and NASA HRP [Risk of Cardiovascular Adaptations](https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/) | Provides risk context only. A 10–15% plasma-volume shift in the project scenario is unverified and is retained only as a synthetic assumption. |
| Immune changes and sleep/circadian context | NASA HRP [Risk of Altered Immune System Responses](https://www.nasa.gov/reference/risk-of-altered-immune-system-responses/) and [Risk from Inadequate Sleep and Irregular Schedules](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/) | Public research context; the prototype does not measure immune markers or infer clinical immune status from symptoms or sleep. |
| Radiation hazard and space environment | NASA HRP [Hazard: Space Radiation](https://www.nasa.gov/hrp/hazard-space-radiation/) and NASA Human Health and Performance [Space Radiation](https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/); NASA [CO₂ Risk](https://www.nasa.gov/directorates/esdmd/hhp/carbon-dioxide-risk/) | Supports hazard background only. Synthetic scenario inputs are not dose limits, environmental baselines, or crew action criteria. |
| Isolation, distance, gravity, and closed environments | NASA HRP [Hazard: Isolation and Confinement](https://www.nasa.gov/hrp/hazard-isolation-and-confinement/), [Hazard: Distance from Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/), [Hazard: Gravity Fields](https://www.nasa.gov/hrp/hazard-gravity-fields/), and [Hazard: Hostile/Closed Environments](https://www.nasa.gov/hrp/hazard-hostile-closed-environments/) | Provides framing for interacting mission hazards and autonomy constraints; it does not endorse this dashboard’s response logic. |
| ISS cabin/hardware environment and radiation telemetry | NASA [Biological and Physical Sciences Data](https://science.nasa.gov/biological-physical/data/), [OSDR overview](https://science.nasa.gov/biological-physical/data/osdr/), and [Environmental Data App (EDA)](https://visualization.osdr.nasa.gov/eda/); NASA OSDR [Biological Data API](https://visualization.osdr.nasa.gov/biodata/api/) | EDA describes ISS environmental and radiation telemetry, including temperature, CO₂, humidity, and radiation data. It is not a single “ISS Environmental Monitoring Data” accession and does not by itself establish the prototype’s numerical values. |
| Neutron-radiation monitoring and measurement technology | CSA [Radi-N2: Tracking space radiation and its risks](https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp), [Canadian Active Neutron Spectrometer (CANS)](https://www.asc-csa.gc.ca/eng/iss/cans.asp), and [Testing technologies](https://www.asc-csa.gc.ca/eng/iss/testing-technologies.asp) | Radi-N2 is a passive bubble-detector experiment with a reported neutron-only result; CANS is described as technology for continuous, time-stamped neutron data. These references do not provide a generic mission threshold or a vehicle-specific shelter map. |

### Real vs. extrapolated vs. synthetic provenance

| Label | What it means in this prototype | Example and limit |
|---|---|---|
| Real source reference | A value or fact reported by a public source, displayed with its dose/measurement scope | CSA Radi-N2 reported approximately 150 µSv/day (0.15 mSv/day) of neutron dose. The demo repeats this as a scenario reference; it is not 14 dated measurements, total ISS dose, or an operational limit. |
| Extrapolated | A project-generated trajectory informed by a cited research context | The Mars BMD fixture interpolates a 14-day window using the NASA HRP population-average 1.0–1.5%/month context. NASA did not measure this Mars trajectory or validate its daily points. |
| Synthetic | A project fixture, display band, score, or projection rather than an observed crew measurement | ISS CO₂ 2.8 mmHg; lunar event 18.5 mSv/day; Mars Day 210 BMD −8.4% and CO₂ 4.3 mmHg; scenario vital signs, UI thresholds, readiness, countermeasure effects, and simulated handover acknowledgements. |
| Unverified manual entry | A value entered by a user, stored locally without independent verification | Not a confirmed sensor observation unless independently confirmed through mission-approved systems. |

**Future work:** Evaluate a properly scoped, timestamp-aligned integration with NASA RadLab resources and NASA OSDR Inspiration4 time-series datasets. The current prototype does not download, calibrate against, or validate itself with these datasets. Any future integration must verify the exact accession, variables, units, licensing/data-use conditions, missingness, and whether the measurements are comparable to the demo signals before using them.

The NASA self-exam reference [`astronaut_self_exam_protocols.md`](knowledge_base/astronaut_self_exam_protocols.md) is also educational and not an approved NASA/CSA or vehicle medical procedure.

## Quickstart

Run these commands from the project root with Python installed:

```bash
pip install -r requirements.txt
python ingest_rag.py
python -m unittest test_engine.py
streamlit run app.py
```

On Windows PowerShell, use the same commands after changing to the project folder:

```powershell
Set-Location "C:\Users\hibaz\OneDrive\Desktop\NASA Health monitoring sysem"
python -m pip install -r requirements.txt
python ingest_rag.py
python -m unittest test_engine.py
python -m streamlit run app.py
```

The ingestion step attempts to use the configured local Ollama embedding model (`nomic-embed-text:latest` by default) at `http://localhost:11434`; if Ollama is unreachable, the indexer uses its deterministic local hash-vector fallback. For local answer generation when Ollama is available, the app defaults to `llama3.2:latest`. Model names and service URL can be overridden with `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_MODEL`, and `OLLAMA_BASE_URL`. No cloud inference service is required by these modules.

## Complete references for submission

The following public sources are cited in the knowledge base and project context. NASA/CSA pages provide research or instrument context; they do not endorse this software, its alert tags, thresholds, or synthetic scenario values.

### NASA Human Research Program and human-system risks

- NASA HRP, [5 Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)
- NASA HRP, [Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
- NASA, [Human System Risks](https://www.nasa.gov/hhp/human-system-risks/)
- NASA, [Behavioral Health Risk](https://www.nasa.gov/directorates/esdmd/hhp/behavioral-health-risk/)
- NASA, [Risk of Cardiovascular Adaptations](https://www.nasa.gov/directorates/esdmd/hhp/cv-risk/)
- NASA HRP, [Risk of Cardiovascular Adaptations](https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/)
- NASA, [Risk of Spaceflight-induced Bone Fracture](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-bone-fracture-due-to-spaceflight-induced-changes-to-bone/)
- NASA HRP, [Risk of Spaceflight-Induced Bone Changes](https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/)
- NASA, [Risk of Spaceflight Associated Neuro-ocular Syndrome](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-spaceflight-associated-neuro-ocular-syndrome/)
- NASA HRP, [Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/)
- NASA HRP, [Risk of Altered Immune System Responses](https://www.nasa.gov/reference/risk-of-altered-immune-system-responses/)
- NASA HRP, [Risk from Inadequate Sleep and Irregular Schedules](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/)
- NASA, [CO₂ Risk](https://www.nasa.gov/directorates/esdmd/hhp/carbon-dioxide-risk/)
- NASA, [Space Radiation](https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/)
- NASA HRP, [Hazard: Isolation and Confinement](https://www.nasa.gov/hrp/hazard-isolation-and-confinement/)
- NASA HRP, [Hazard: Distance from Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/)
- NASA HRP, [Hazard: Gravity Fields](https://www.nasa.gov/hrp/hazard-gravity-fields/)
- NASA HRP, [Hazard: Hostile/Closed Environments](https://www.nasa.gov/hrp/hazard-hostile-closed-environments/)

### NASA Open Science Data Repository and environmental data

- NASA, [Biological and Physical Sciences Data](https://science.nasa.gov/biological-physical/data/)
- NASA, [Open Science Data Repository](https://science.nasa.gov/biological-physical/data/osdr/)
- NASA, [Environmental Data App](https://visualization.osdr.nasa.gov/eda/)
- NASA OSDR, [Biological Data API](https://visualization.osdr.nasa.gov/biodata/api/)
- NASA OSDR, [OSD-817 study](https://osdr.nasa.gov/bio/repo/data/studies/OSD-817) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/)
- NASA OSDR, [OSD-979 study](https://osdr.nasa.gov/bio/repo/data/studies/OSD-979) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-979/)
- NASA OSDR, [OSD-981 study](https://osdr.nasa.gov/bio/repo/data/studies/OSD-981) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-981/)
- NASA OSDR, [OSD-1018 study](https://osdr.nasa.gov/bio/repo/data/studies/OSD-1018) and [metadata API](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-1018/)

### Canadian Space Agency

- CSA, [Radi-N2: Tracking space radiation and its risks](https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp)
- CSA, [Canadian Active Neutron Spectrometer (CANS)](https://www.asc-csa.gc.ca/eng/iss/cans.asp)
- CSA, [Testing technologies](https://www.asc-csa.gc.ca/eng/iss/testing-technologies.asp)

## AI assistance disclosure

- **Tool:** GitHub Copilot, an AI coding assistant.
- **Assistance:** Code scaffolding, debugging, focused test authoring, and documentation drafting.
- **Human responsibility:** Project contributors must review and approve AI-assisted changes and verify sources before submission or use.
- **Limitations:** AI-generated content is not scientific evidence, a medical recommendation, or a substitute for checking source metadata and mission procedures. The project does not claim autonomous medical capability or “super intelligence.”

## AI / Super Intelligence (SI) transparency and safety

GitHub Copilot was used to accelerate code scaffolding and the focused unit tests. The Flight Surgeon Copilot panel is a local retrieval-augmented feature: when configured Ollama models are available, local Ollama generates embeddings and an answer from retrieved passages; when Ollama is unreachable, deterministic local hash-vector embeddings and an extractive, source-grounded answer fallback are used. Responses include retrieved evidence and source links, but retrieval does not establish that a source validates a synthetic scenario.

This prototype does not claim artificial general intelligence or autonomous medical capability. All scenario fixtures, generated telemetry, status bands, “readiness” gamification, and countermeasure projection coefficients are non-operational educational demonstrations. They are not validated medical recommendations, treatment effects, alert thresholds, individual predictions, radiation limits, or mission procedures. Use only mission-approved clinical and operations guidance for real crew decisions.
