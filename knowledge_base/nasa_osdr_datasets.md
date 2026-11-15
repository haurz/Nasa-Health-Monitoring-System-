# NASA OSDR and environmental data references for Offline Astro-Twin

## Scope and evidence limits

NASA's Open Science Data Repository (OSDR) provides open biological and physical science datasets from spaceflight and ground studies. NASA describes its OSDR/ALSDA holdings as including physiological, phenotypic, behavioral, bioimaging, and environmental data. These records are research data, not operational medical procedures, validated alert thresholds, or automatic calibration coefficients for this demo.

The study records below were checked against NASA's Biological Data API on **November 14, 2026**. The study type, organism/material, and scope matter: ground analogs, animal studies, and ex-vivo tissue experiments can support research context, but they are not direct astronaut measurements. Do not describe a study as validating a numerical scenario value unless its NASA metadata and measured data actually support that value.

## ISS environmental telemetry

NASA's Environmental Data App (EDA) provides ISS cabin and hardware environmental telemetry alongside radiation data gathered from spaceflight missions. Its Mission Dashboard describes temperature, carbon dioxide (CO₂), relative-humidity, and radiation-dose measurements for the ISS cabin and ground control over mission timelines; temperature and relative-humidity readings are also collected from flight and ground hardware units. Raw and summary data are available through the app's Data Tables.

EDA is a NASA OSDR visualization resource, not a single OSD study accession titled “ISS Environmental Monitoring Data.” Its existence does **not** establish any specific baseline such as 0.5 mSv/day, 2.8 mmHg CO₂, or a particular cabin temperature. Those values must be derived from a selected mission, sensor, sampling interval, units, and data table, with quality and calibration details retained.

## OSDR study records verified

| Accession | NASA metadata title and study scope | Relevance, project tag, and limits |
|---|---|---|
| [OSD-817](https://osdr.nasa.gov/bio/repo/data/studies/OSD-817) | “The ex vivo human translaminar autonomous system to study spaceflight associated neuro-ocular syndrome pathogenesis (Optic Nerve, Histology and Microscopy).” NASA metadata identifies a ground study, human optic-nerve/posterior-eye material, and an ex-vivo translaminar autonomous system. [NASA API metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/) | Relevant to SANS and optic-nerve pathogenesis research; contextual project tag: `HRP-RED-SANS`. It uses ex-vivo donor tissue in a ground model, not an in-flight astronaut cohort or a measured SANS incidence/risk estimate. |
| [OSD-979](https://osdr.nasa.gov/bio/repo/data/studies/OSD-979) | “Small changes in thermoregulation influence cancellous bone turnover balance in distal femur metaphysis in growing female mice.” NASA metadata identifies a ground study in *Mus musculus*, with housing temperature and housing condition factors and bone-microstructure assays. [NASA API metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-979/) | Relevant to cancellous bone and thermoregulation research; contextual project tag: `HRP-RED-BONE`. It is not a microgravity or spaceflight-induced bone-loss dataset. Do not cite it as direct evidence for astronaut BMD-loss rates. |
| [OSD-981](https://osdr.nasa.gov/bio/repo/data/studies/OSD-981) | “Bone Marrow Adipose Tissue Is Not Required for Reconstitution of the Immune System Following Irradiation in Male Mice.” NASA metadata identifies a ground mouse study involving irradiation and immune reconstitution; assays include bone microstructure. The study description reports few differences in bone parameters between the groups. [NASA API metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-981/) | Relevant to an animal irradiation/immune-reconstitution model and bone measurements; contextual project tags: `HRP-RED-BONE` and `HRP-RED-RAD`. It is not a spaceflight bone-loss study and does not substantiate a claim of bone microstructure loss. |
| [OSD-1018](https://osdr.nasa.gov/bio/repo/data/studies/OSD-1018) | “Differential Impact of Social Isolation and Space Radiation on Behavior and Motor Learning in Rats.” NASA metadata identifies a ground study of rats, social-isolation conditions, simulated radiation exposure, and behavior/motor-learning assays. [NASA API metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-1018/) | Relevant to interaction research on isolation, radiation, and behavior; contextual project tags: `HRP-RED-BHPC` and `HRP-RED-RAD`. It is an animal ground study, not a human behavioral-health outcome or an astronaut performance threshold. |

The HRP tag values in this table are **project-defined retrieval labels only**. NASA OSDR does not assign these HRP tags to study records, and the tags do not indicate that a study rated the corresponding risk.

### Dataset families without verified accessions in this reference

“Commercial astronaut and microgravity bed-rest phenotypic datasets” is a broad search description, not a verified NASA accession or one identified dataset title. NASA confirms that OSDR/ALSDA contains physiological and phenotypic research data, but no specific commercial-astronaut or bed-rest accession was established here to support the requested cardiovascular-fluid-shift or immune-marker claims. Treat these phrases as **catalog search leads**, not dataset citations or calibration evidence, until exact study accessions and metadata are checked.

## Use in scenario and copilot outputs

- The IDs `HRP-RED-SANS`, `HRP-RED-BONE`, `HRP-RED-BHPC`, `HRP-RED-RAD`, and `HRP-MOD-CARDIO` remain project-defined tags, not NASA-issued identifiers or NASA severity classifications.
- Cite an OSDR accession only when its title/topic is relevant to the retrieved claim. Preserve its model and study type (for example, ex-vivo, mouse, rat, ground, or in-flight) in summaries.
- NASA HRP risk descriptions provide risk context; OSDR experimental records provide study-specific methods/results; CSA Radi-N2 and CANS describe neutron-measurement research/technology. These sources are not interchangeable, and none by itself supplies the synthetic scenario values or mission-specific operational limits.
- For ISS radiation context, CSA Radi-N2 reports an early neutron-only result of about **150 µSv/day (0.15 mSv/day)**, not total ISS dose or an operational threshold. CANS is described by CSA as a technology for continuous, time-stamped neutron data; that description does not define an alarm threshold.

## Public sources

- NASA, [Biological and Physical Sciences Data](https://science.nasa.gov/biological-physical/data/) — OSDR and related data repositories.
- NASA, [OSDR](https://science.nasa.gov/biological-physical/data/osdr/) — repository scope, ALSDA holdings, and related data visualization resources.
- NASA, [Environmental Data App](https://visualization.osdr.nasa.gov/eda/) — ISS cabin/hardware environment and radiation telemetry description.
- NASA OSDR, [Biological Data API](https://visualization.osdr.nasa.gov/biodata/api/) — public metadata/query API.
- NASA OSDR, [OSD-817 metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/).
- NASA OSDR, [OSD-979 metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-979/).
- NASA OSDR, [OSD-981 metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-981/).
- NASA OSDR, [OSD-1018 metadata](https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-1018/).
- NASA HRP, [Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/).
- NASA HRP, [Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/).
- NASA HRP, [Risk of Spaceflight-Induced Bone Changes](https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/).
- NASA, [Behavioral Health Risk](https://www.nasa.gov/directorates/esdmd/hhp/behavioral-health-risk/).
- NASA, [Risk of Cardiovascular Adaptations](https://www.nasa.gov/directorates/esdmd/hhp/cv-risk/).
- NASA, [Space Radiation](https://www.nasa.gov/directorates/esdmd/hhp/space-radiation/).
- Canadian Space Agency, [Radi-N2: Tracking space radiation and its risks](https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp).
- Canadian Space Agency, [Canadian Active Neutron Spectrometer (CANS)](https://www.asc-csa.gc.ca/eng/iss/cans.asp).
