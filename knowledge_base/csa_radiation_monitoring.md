# CSA neutron-radiation monitoring on the International Space Station

## Scope and limits

This reference distinguishes what Canadian Space Agency (CSA) public material says from design assumptions. The instruments described below measure neutron radiation; they do not replace the mission radiation-protection system, dosimetry, solar monitoring, or instructions from the Space Radiation Analysis Group (SRAG) / mission control.

No public CSA source cited here establishes universal **mission-dose (mSv)** thresholds, acute SPE neutron-spike thresholds, or a standard ISS module-by-module “water-wall versus unshielded” shelter map. Do not invent such limits. Numeric trigger levels, alarm rules, dose allocations, and shelter locations must come from the applicable vehicle and mission radiation-protection plan and be approved by the responsible radiation and medical authorities.

## Radi-N2 bubble detectors (CSA experiment)

Radi-N2 measured neutron radiation with small passive bubble detectors. Each tube contains a polymer gel with liquid droplets; an interacting neutron vaporizes a droplet and leaves a visible bubble. Detectors were read before and after deployment, positioned at selected ISS locations (including a crew-worn detector and one in sleeping quarters), left in place for about a week, then collected and read. The measurements provide an integrated neutron-dose result for the deployment interval; they are not a real-time SPE alarm.

CSA reports early Radi-N2 results of about **150 microsieverts (0.15 mSv) of neutron dose per day** for ISS astronauts. CSA also reports only minor differences among the seven U.S. segment modules in the study and typically lower neutron doses in sleeping quarters than in other daily-activity locations. These are reported experiment findings, not a guaranteed dose rate for every crew member, time, module, or mission, and not a dose limit.

The study's purpose included measuring crew neutron exposure and helping identify locations that could offer protection during a major solar event. Its results support characterization and research; they do not, on their own, designate a current storm shelter or prove a specific shielding configuration safe.

## Canadian Active Neutron Spectrometer (CANS)

CSA describes CANS as a Canadian-developed **future technology** intended to improve on earlier neutron-measurement experiments by collecting continuous, time-stamped data autonomously. The CSA description says an astronaut places the instrument at a selected station location; a plastic scintillator emits light when a neutron interacts, and the instrument stores data for later transmission to Earth. The aim is to characterize neutron radiation at different ISS locations and support shielding strategies.

The CSA page characterizes CANS as future technology; it does not publish an operational flight status, validated alarm algorithm, clinical action limit, or SPE spike threshold. It should therefore not be represented as a currently available operational alarm or as an instrument that independently instructs crew to shelter.

## Dose thresholds and acute SPE spikes

| Quantity | What is publicly established by the sources below | Operational interpretation |
|---|---|---|
| Cumulative mission neutron dose (mSv) | Radi-N2 published an early average of roughly 0.15 mSv/day. This is an observed rate, not a threshold. | **No generic CSA mission-dose threshold is specified here.** Track measured dose using the approved mission dose allocation, dosimeter, uncertainty treatment, and radiation-protection rules. A career limit, where applicable, is not interchangeable with a per-mission or neutron-only alert. |
| Acute SPE neutron spike | Radi-N2's week-long passive deployments cannot resolve an acute event in real time. CSA's CANS description is continuous/time-stamped but gives no public trigger level or alarm logic. | **No public numeric spike threshold is specified here.** Use the mission's authorized SPE alerts, active radiation instrumentation, and prebriefed response criteria. Do not wait for passive detector results during an event. |

Do not convert the 150 µSv/day experiment result into a mission limit. It is neither an allowance nor a forecast, and neutron dose is only one part of the radiation environment. A valid operational dose assessment requires the approved quantity (e.g. organ/effective dose as defined by the mission), instrument calibration and uncertainty, crew-specific constraints, time history, and the current mission radiation plan.

## Shielding-location map: measured evidence versus planning overlay

- **Measured CSA finding:** Radi-N2 reported lower neutron dose in sleeping quarters than elsewhere in the measured activity locations, and only minor differences among the seven U.S. segment modules in its study.
- **Not established by that finding:** the statement does not identify every sleep station as a certified storm shelter, establish the presence or thickness of a “water wall,” rank named unshielded nodes, or give dose reduction factors for a future vehicle.
- **Safe way to represent a map:** label site values with their instrument, measurement interval, uncertainty, location, and vehicle configuration. Mark unmeasured locations as “unknown,” not “unshielded.” Treat “water-wall sleep station” and “unshielded node” as design labels only if that specific vehicle's radiation engineering documentation confirms the geometry and measurements.
- **Shielding caveat:** Hydrogen-rich materials such as water can be useful in shielding design, but neutron fields and secondary particles depend on energy, material, geometry, and surrounding structure. A label or material alone does not establish a safe shelter; use mission-specific radiation transport analysis and measurements.

## Crew response and communications blackout

An SPE response is driven by official mission alerts and the spacecraft's approved procedure, not a self-invented neutron count or mSv threshold. When directed by the mission plan, promptly stop or defer exposed activities such as EVA, move by the prescribed route to the designated shelter, secure mission-critical tasks as instructed, and remain there until the authorized all-clear or updated instruction. Do not delay sheltering to collect optional measurements.

If communications are unavailable during a suspected event, execute the stored SPE contingency: use the vehicle's approved alerting and radiation-monitoring equipment, go to the preassigned shelter if the onboard alert or prebriefed criteria call for it, account for crew, note event timing and available readings, and retry approved communication paths. The actual triggers, shelter location, allowable activities, and all-clear authority must be supplied in the mission-specific plan. This document does not establish them.

## Public sources

- Canadian Space Agency, [Radi-N2: Tracking space radiation and its risks](https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp)
- Canadian Space Agency, [Canadian Active Neutron Spectrometer: Detecting space radiation in real time](https://www.asc-csa.gc.ca/eng/iss/cans.asp)
- Canadian Space Agency, [Testing technologies](https://www.asc-csa.gc.ca/eng/iss/testing-technologies.asp) (lists CANS as future technology)
- NASA HRP, [Hazard: Space Radiation](https://www.nasa.gov/hrp/hazard-space-radiation/)
- NASA Human Health and Performance, [Space Radiation](https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/) (describes monitoring support and notes uncertainty in exposure-limit recommendations for long-duration missions)
