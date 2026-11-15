import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

import engine
from engine import (
    OllamaEmbeddingFunction,
    _format_cited_output,
    _generate_answer,
    _relevant_sources,
    complete_daily_checkin,
    compute_demo_readiness,
    effective_latest_state,
    environment_constraints,
    evaluate_health_systems,
    get_gamification_stats,
    get_vitals_history,
    load_scenario_to_db,
    log_vitals,
    seed_scenario,
    simulate_countermeasure_projection,
    validate_telemetry_plausibility,
)


class ScenarioFixtureTests(unittest.TestCase):
    def test_scenario_values_and_evidence_status_are_explicit(self):
        scenarios = {item["scenario_id"]: item for item in seed_scenario()}

        iss = scenarios["iss_leo_baseline"]["measurements"]
        self.assertEqual(iss["neutron_radiation_msv"]["value"], 0.15)
        self.assertEqual(
            iss["neutron_radiation_msv"]["evidence_status"],
            "csa_radi_n2_empirical",
        )
        self.assertIsNone(iss["radiation_dose_rate_msv_day"]["value"])
        self.assertEqual(
            iss["cabin_co2_partial_pressure_mmhg"]["value"], 2.8
        )
        self.assertIn(
            "Synthetic fixture",
            iss["cabin_co2_partial_pressure_mmhg"]["note"],
        )

        artemis = scenarios["artemis_lunar_spe"]["measurements"]
        self.assertEqual(artemis["radiation_spike_msv_day"]["value"], 18.5)
        self.assertEqual(
            artemis["radiation_spike_msv_day"]["particle_components"],
            ["neutron", "proton"],
        )
        self.assertIn(
            "Project stress test (synthetic)",
            artemis["radiation_spike_msv_day"]["note"],
        )

        mars = scenarios["mars_surface_day_210"]["measurements"]
        self.assertEqual(
            scenarios["mars_surface_day_210"]["name"],
            "Day 210 Mars Transit Extrapolation",
        )
        self.assertEqual(mars["cumulative_bmd_change_percent"]["value"], -8.4)
        self.assertEqual(
            mars["cumulative_bmd_change_percent"]["start_value"], -7.8
        )
        self.assertEqual(mars["cabin_co2_partial_pressure_mmhg"]["value"], 4.3)
        self.assertEqual(
            mars["plasma_volume_shift_percent_range"]["value"], [10, 15]
        )
        self.assertTrue(
            all(
                measure["evidence_status"]
                in {
                    "synthetic_assumption",
                    "synthetic_extrapolation",
                    "csa_radi_n2_empirical",
                    "not_available",
                }
                for scenario in scenarios.values()
                for measure in scenario["measurements"].values()
            )
        )

    def test_all_project_risk_tags_are_present(self):
        tags = {
            tag
            for scenario in seed_scenario()
            for tag in scenario["risk_tags"]
        }
        self.assertEqual(
            tags,
            {
                "HRP-RED-SANS",
                "HRP-RED-BONE",
                "HRP-RED-BHPC",
                "HRP-RED-RAD",
                "HRP-MOD-CARDIO",
            },
        )


class CitationOutputTests(unittest.TestCase):
    def test_osdr_accession_selects_matching_record_and_hrp_context(self):
        sources = [
            {
                "title": "OSD-817 metadata",
                "url": "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/",
            },
            {
                "title": "OSD-979 metadata",
                "url": "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-979/",
            },
            {
                "title": "Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)",
                "url": "https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/",
            },
        ]
        selected = _relevant_sources(
            "OSD-817 is an ex-vivo ground study of optic-nerve SANS pathogenesis.",
            sources,
        )
        selected_urls = {source["url"] for source in selected}
        self.assertIn(sources[0]["url"], selected_urls)
        self.assertIn(sources[2]["url"], selected_urls)
        self.assertNotIn(sources[1]["url"], selected_urls)

    def test_retrieved_claim_has_source_url_in_output(self):
        source = {
            "title": "Canadian Space Agency — Radi-N2 neutron dose",
            "url": "https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp",
        }
        output = _format_cited_output(
            "CSA reports neutron radiation results.",
            [
                {
                    "document": "CSA reported about 150 µSv/day neutron dose.",
                    "metadata": {
                        "source_file": "knowledge_base/csa_radiation_monitoring.md",
                        "section": "Radi-N2",
                    },
                    "sources": [source],
                }
            ],
        )
        self.assertIn("150 µSv/day neutron dose", output)
        self.assertIn("[S1]", output)
        self.assertIn(source["url"], output)

    def test_osdr_accession_citation_is_preserved(self):
        source = {
            "title": "NASA OSDR — OSD-817 metadata",
            "url": "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/",
        }
        hrp_source = {
            "title": "Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)",
            "url": engine._PROJECT_TAG_SOURCE_URLS["HRP-RED-SANS"],
        }
        output = _format_cited_output(
            "OSD-817 is an ex-vivo ground study.",
            [
                {
                    "document": (
                        "OSD-817 is a ground study using ex-vivo optic-nerve "
                        "material to study Spaceflight Associated Neuro-ocular "
                        "Syndrome (SANS). Related project tag: HRP-RED-SANS."
                    ),
                    "metadata": {
                        "source_file": "knowledge_base/nasa_osdr_datasets.md",
                        "section": "OSDR study records verified",
                    },
                    "sources": [source, hrp_source],
                }
            ],
        )
        self.assertIn("OSD-817", output)
        self.assertIn(source["url"], output)
        self.assertIn("HRP-RED-SANS", output)
        self.assertIn(hrp_source["url"], output)
        self.assertIn("not NASA-issued risk IDs", output)


class OfflineFallbackTests(unittest.TestCase):
    def test_embeddings_fall_back_to_deterministic_local_hash_vectors(self):
        embedder = OllamaEmbeddingFunction(base_url="http://offline.invalid")
        with patch("engine.urlopen", side_effect=URLError("offline")):
            first = embedder(["same text", "another text"])
            self.assertEqual(embedder.last_backend, "local-hash-384-v1")
            second = embedder(["same text", "another text"])
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 384)

    def test_answer_falls_back_to_cited_retrieval_summary(self):
        source = {
            "title": "NASA OSDR — OSD-817 metadata",
            "url": "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/",
        }
        retrieved = [
            {
                "document": "OSD-817 is an ex-vivo ground study of SANS.",
                "metadata": {
                    "source_file": "knowledge_base/nasa_osdr_datasets.md",
                    "section": "OSDR study records verified",
                },
                "sources": [source],
            }
        ]
        with patch("engine.urlopen", side_effect=URLError("offline")):
            answer = _generate_answer(
                "What is OSD-817?",
                retrieved,
                "llama3.2:latest",
                "http://offline.invalid",
            )
        self.assertIn("Offline evidence summary", answer)
        self.assertIn(source["url"], answer)
        self.assertIn("not a clinical assessment", answer)

    def test_embedding_dimension_mismatch_rebuilds_index_once_and_retries(self):
        source = {
            "title": "NASA OSDR — OSD-817 metadata",
            "url": "https://visualization.osdr.nasa.gov/biodata/api/v2/dataset/OSD-817/",
        }
        collection = Mock()
        collection.count.return_value = 1
        collection.metadata = {
            "embedding_backend": "local-hash-384-v1",
            "embedding_dimension": 384,
        }
        collection.query.side_effect = [
            RuntimeError("Embedding dimension mismatch: expected 384, got 768"),
            {
                "documents": [["OSD-817 is a ground ex-vivo optic-nerve study."]],
                "metadatas": [[
                    {
                        "source_file": "knowledge_base/nasa_osdr_datasets.md",
                        "section": "OSDR study records verified",
                        "citations_json": json.dumps([source]),
                    }
                ]],
                "distances": [[0.1]],
            },
        ]
        with (
            patch("engine._collection", return_value=collection),
            patch("ingest_rag.ingest") as rebuild,
            patch("engine._generate_answer", return_value="Retrieved OSD-817 evidence."),
        ):
            result = engine.query_flight_surgeon_copilot("What is OSD-817?")
        rebuild.assert_called_once_with()
        self.assertEqual(collection.query.call_count, 2)
        self.assertIn(source["url"], result)


class TelemetryAndProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "mission_telemetry.db"
        self.path_patcher = patch.object(
            engine, "TELEMETRY_DB_PATH", self.database_path
        )
        self.path_patcher.start()

    def tearDown(self):
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def test_existing_database_migrates_metric_provenance_column(self):
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                """
                CREATE TABLE mission_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT NOT NULL DEFAULT 'manual',
                    mission_day INTEGER NOT NULL,
                    environment TEXT NOT NULL,
                    heart_rate REAL, bp_sys REAL, bp_dia REAL,
                    blood_glucose REAL, body_temp REAL, sleep_hours REAL,
                    mood_score REAL, neutron_radiation_msv REAL,
                    radiation_dose_rate_msv_day REAL, bone_bmd_delta REAL,
                    cabin_co2 REAL, status_overall TEXT NOT NULL,
                    evidence_status TEXT NOT NULL DEFAULT 'user_entered_unverified',
                    radiation_metric_note TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()
        finally:
            connection.close()
        self.assertEqual(load_scenario_to_db("iss_leo_baseline"), 14)
        history = get_vitals_history(1, "iss_leo_baseline")
        self.assertEqual(
            json.loads(history[0]["metric_evidence_json"])[
                "neutron_radiation_msv"
            ],
            "csa_radi_n2_empirical",
        )

    def test_scenario_loader_preserves_fixture_endpoints_and_marks_synthetic(self):
        self.assertEqual(load_scenario_to_db("iss_leo_baseline"), 14)
        iss_history = get_vitals_history(14, "iss_leo_baseline")
        self.assertTrue(
            all(row["radiation_dose_rate_msv_day"] is None for row in iss_history)
        )
        self.assertTrue(
            all(row["neutron_radiation_msv"] == 0.15 for row in iss_history)
        )
        self.assertTrue(
            all(
                json.loads(row["metric_evidence_json"])[
                    "neutron_radiation_msv"
                ]
                == "csa_radi_n2_empirical"
                for row in iss_history
            )
        )
        iss_state = effective_latest_state(iss_history)
        self.assertEqual(
            iss_state["metric_evidence_status"]["neutron_radiation_msv"],
            "csa_radi_n2_empirical",
        )
        self.assertEqual(
            iss_state["metric_evidence_status"]["cabin_co2"],
            "synthetic_assumption",
        )
        self.assertTrue(all(row["cabin_co2"] == 2.8 for row in iss_history))

        self.assertEqual(load_scenario_to_db("artemis_lunar_spe"), 14)
        artemis_history = get_vitals_history(14, "artemis_lunar_spe")
        self.assertIsNone(artemis_history[-2]["radiation_dose_rate_msv_day"])
        self.assertEqual(artemis_history[-1]["radiation_dose_rate_msv_day"], 18.5)
        self.assertIsNone(artemis_history[-1]["neutron_radiation_msv"])
        self.assertIn("Project stress test (synthetic)", artemis_history[-1]["radiation_metric_note"])

        self.assertEqual(load_scenario_to_db("mars_surface_day_210"), 14)
        history = get_vitals_history(14, "mars_surface_day_210")
        self.assertEqual(len(history), 14)
        self.assertEqual(
            (history[0]["mission_day"], history[-1]["mission_day"]),
            (197, 210),
        )
        self.assertEqual(history[0]["bone_bmd_delta"], -7.8)
        self.assertEqual(history[-1]["bone_bmd_delta"], -8.4)
        self.assertEqual(
            [row["bone_bmd_delta"] for row in history],
            [round(-7.8 - (index * 0.6 / 13), 2) for index in range(14)],
        )
        self.assertEqual(history[-1]["cabin_co2"], 4.3)
        self.assertEqual(
            history[-1]["evidence_status"], "synthetic_design_fixture"
        )
        self.assertIsNone(history[-1]["neutron_radiation_msv"])
        self.assertEqual(
            json.loads(history[0]["metric_evidence_json"])["bone_bmd_delta"],
            "synthetic_extrapolation",
        )

    def test_vitals_history_and_daily_checkin(self):
        row_id = log_vitals(
            mission_day=3,
            environment="ISS LEO",
            heart_rate=72,
            bp_sys=118,
            bp_dia=76,
            sleep_hours=7.2,
            mood_score=8,
            evidence_status="synthetic_test",
        )
        self.assertGreater(row_id, 0)
        self.assertEqual(get_vitals_history(1)[0]["mission_day"], 3)
        stats = complete_daily_checkin(readiness_score=82)
        self.assertEqual(stats["readiness_score"], 82)
        self.assertEqual(stats["streak_days"], 1)
        self.assertEqual(get_gamification_stats()["completed_tasks"], 1)

    def test_health_systems_and_projection_are_non_operational(self):
        systems = evaluate_health_systems(
            {
                "sleep_hours": 5.2,
                "mood_score": 5,
                "heart_rate": 75,
                "bp_sys": 120,
                "bp_dia": 80,
                "bone_bmd_delta": -2,
                "radiation_dose_rate_msv_day": 0.5,
                "cabin_co2": 3.2,
            }
        )
        self.assertEqual(
            set(systems),
            {
                "neuro_ocular_behavioral",
                "cardiovascular",
                "skeletal_bone",
                "immune_radiation",
            },
        )
        self.assertTrue(
            all(system["classification_note"] for system in systems.values())
        )
        self.assertTrue(systems["cardiovascular"]["compounding_alerts"])

        neutron_only = evaluate_health_systems(
            {
                "neutron_radiation_msv": 1.0,
                "cabin_co2": 4.3,
                "sleep_hours": 5.2,
                "mood_score": 5,
            }
        )
        self.assertEqual(neutron_only["immune_radiation"]["status"], "Amber")
        self.assertIsNone(
            neutron_only["immune_radiation"]["key_metrics"][
                "radiation_dose_rate_msv_day"
            ]
        )
        self.assertTrue(
            neutron_only["neuro_ocular_behavioral"]["compounding_alerts"]
        )

        projection = simulate_countermeasure_projection(
            {
                "heart_rate": 75,
                "bp_sys": 120,
                "bp_dia": 80,
                "sleep_hours": 6,
                "mood_score": 7,
                "radiation_dose_rate_msv_day": 0.5,
                "bone_bmd_delta": -1,
            },
            ["Water-Wall Shelter (design concept)"],
        )
        self.assertEqual(len(projection), 14)
        self.assertEqual(
            set(projection["scenario"]),
            {
                "No Action (Baseline Drift)",
                "With Selected Countermeasures",
            },
        )
        self.assertEqual(
            set(projection["evidence_status"]),
            {"synthetic_non_operational_projection"},
        )
        self.assertIn("not validated efficacy estimates", projection.attrs["disclaimer"])
        baseline_day_one = projection[
            (projection["scenario"] == "No Action (Baseline Drift)")
            & (projection["day_ahead"] == 1)
        ].iloc[0]
        self.assertAlmostEqual(baseline_day_one["bone_bmd_delta"], -1.04)
        self.assertIn(
            "Offsets half of the demo daily BMD drift",
            projection.attrs["countermeasure_assumptions"][
                "ARED Resistance Protocol (+30 min)"
            ],
        )
        ared_projection = simulate_countermeasure_projection(
            {"bone_bmd_delta": -1},
            ["ARED Resistance Protocol (+30 min)"],
        )
        selected_day_one = ared_projection[
            (ared_projection["scenario"] == "With Selected Countermeasures")
            & (ared_projection["day_ahead"] == 1)
        ].iloc[0]
        self.assertAlmostEqual(selected_day_one["bone_bmd_delta"], -1.02)

        neutron_only_projection = simulate_countermeasure_projection(
            {"neutron_radiation_msv": 1.0}, []
        )
        self.assertTrue(
            neutron_only_projection["radiation_risk_index"].notna().all()
        )

    def test_telemetry_plausibility_bounds_and_missing_values(self):
        warnings = validate_telemetry_plausibility(
            {
                "heart_rate": 24,
                "bp_sys": 260,
                "blood_glucose": 601,
                "body_temp": float("nan"),
                "cabin_co2": None,
                "bone_bmd_delta": -40,
            }
        )
        self.assertEqual(len(warnings), 3)
        self.assertTrue(all("Likely sensor error" in warning for warning in warnings))
        self.assertEqual(validate_telemetry_plausibility({"heart_rate": 25}), [])
        valid_boundaries = {
            "heart_rate": 240,
            "bp_sys": 50,
            "bp_dia": 160,
            "blood_glucose": 30,
            "body_temp": 43.0,
            "cabin_co2": 30.0,
            "radiation_dose_rate_msv_day": 500,
            "bone_bmd_delta": 20,
        }
        self.assertEqual(validate_telemetry_plausibility(valid_boundaries), [])
        invalid_boundaries = {
            "heart_rate": 241,
            "bp_sys": 49,
            "bp_dia": 161,
            "blood_glucose": 29,
            "body_temp": 31.9,
            "cabin_co2": 0.09,
            "radiation_dose_rate_msv_day": 501,
            "bone_bmd_delta": 20.1,
        }
        self.assertEqual(
            len(validate_telemetry_plausibility(invalid_boundaries)), 8
        )

    def test_effective_latest_state_merges_history_and_scenario_fixtures(self):
        history = [
            {
                "scenario_id": "mars_surface_day_210",
                "mission_day": 209,
                "heart_rate": 71,
                "bone_bmd_delta": -8.1,
                "cabin_co2": 4.2,
            },
            {
                "scenario_id": "mars_surface_day_210",
                "mission_day": 210,
                "heart_rate": None,
                "bone_bmd_delta": None,
                "cabin_co2": None,
                "evidence_status": "user_entered_unverified",
            },
        ]
        state = effective_latest_state(history)
        self.assertEqual(state["mission_day"], 210)
        self.assertEqual(state["heart_rate"], 71)
        self.assertEqual(state["bone_bmd_delta"], -8.1)
        self.assertEqual(state["cabin_co2"], 4.2)
        self.assertEqual(state["evidence_status"], "user_entered_unverified")
        self.assertIsNone(state["neutron_radiation_msv"])

    def test_cabin_co2_glucose_and_temperature_status_bands(self):
        def systems_for(**values):
            return evaluate_health_systems(
                {
                    "sleep_hours": 8,
                    "mood_score": 8,
                    "radiation_dose_rate_msv_day": 0.1,
                    **values,
                }
            )

        self.assertEqual(
            systems_for(cabin_co2=3.1)["neuro_ocular_behavioral"]["status"],
            "Amber",
        )
        self.assertEqual(
            systems_for(cabin_co2=5.1)["neuro_ocular_behavioral"]["status"],
            "Red",
        )
        self.assertEqual(
            systems_for(blood_glucose=60)["immune_radiation"]["status"],
            "Amber",
        )
        self.assertEqual(
            systems_for(blood_glucose=54)["immune_radiation"]["status"],
            "Red",
        )
        self.assertEqual(
            systems_for(body_temp=37.8)["immune_radiation"]["status"],
            "Amber",
        )
        self.assertEqual(
            systems_for(body_temp=38.5)["immune_radiation"]["status"],
            "Red",
        )

    def test_missing_telemetry_uses_no_data_unless_present_metric_alerts(self):
        self.assertEqual(engine._classify(missing=True), "No Data")
        self.assertEqual(engine._classify(missing=True, amber=True), "Amber")
        self.assertEqual(engine._classify(missing=True, red=True), "Red")
        systems = evaluate_health_systems({})
        self.assertTrue(
            all(system["status"] == "No Data" for system in systems.values())
        )
        systems_with_red = evaluate_health_systems(
            {
                "heart_rate": 190,
                "bp_sys": 180,
                "bp_dia": 120,
            }
        )
        self.assertEqual(systems_with_red["cardiovascular"]["status"], "Red")
        self.assertEqual(
            engine._overall_status(
                {"unknown": {"status": "No Data"}, "known": {"status": "Green"}}
            ),
            "Green",
        )

    def test_radiation_classification_uses_available_radiation_observation(self):
        def status(**values):
            return evaluate_health_systems(
                {
                    "blood_glucose": 90,
                    "body_temp": 36.5,
                    **values,
                }
            )["immune_radiation"]["status"]

        self.assertEqual(status(neutron_radiation_msv=0.15), "Green")
        self.assertEqual(status(neutron_radiation_msv=0.5), "Amber")
        self.assertEqual(status(neutron_radiation_msv=10), "Red")
        self.assertEqual(
            status(
                radiation_dose_rate_msv_day=0.1,
                neutron_radiation_msv=10,
            ),
            "Green",
        )
        self.assertEqual(
            status(
                radiation_dose_rate_msv_day=10,
                neutron_radiation_msv=0.1,
            ),
            "Red",
        )
        self.assertEqual(status(), "No Data")

    def test_environment_constraints_are_defined_for_all_profiles(self):
        iss = environment_constraints("ISS (LEO - 0.5s Latency)")
        lunar = environment_constraints(
            "Artemis Lunar Transit (~1.3s One-Way / ~2.6s Round-Trip)"
        )
        mars = environment_constraints(
            "Mars Surface Base (Up to ~22-Min One-Way / ~44-Min Round-Trip)"
        )
        for profile in (iss, lunar, mars):
            self.assertEqual(
                set(profile),
                {"latency_label", "comms_state", "measurement_feasibility"},
            )
            self.assertTrue(all(isinstance(value, str) for value in profile.values()))
        self.assertIn("0.5s", iss["latency_label"])
        self.assertEqual(
            lunar["latency_label"],
            "Artemis Lunar Transit (~1.3s One-Way / ~2.6s Round-Trip)",
        )
        self.assertEqual(
            mars["latency_label"],
            "Mars Surface Base (Up to ~22-Min One-Way / ~44-Min Round-Trip)",
        )
        self.assertIn("cabin CO2 monitoring", iss["measurement_feasibility"])
        self.assertNotIn("CDRA monitor", iss["measurement_feasibility"])
        self.assertTrue(
            all(
                profile["measurement_feasibility"].count("Illustrative") <= 1
                for profile in (iss, lunar, mars)
            )
        )
        self.assertIn("Radi-N2", iss["measurement_feasibility"])
        self.assertIn("Amsler", lunar["measurement_feasibility"])
        self.assertIn("ultrasound/tonometer", mars["measurement_feasibility"])
        with self.assertRaises(ValueError):
            environment_constraints("unrecognized")

    def test_live_demo_readiness_weights_statuses_and_ignores_no_data(self):
        systems = {
            "nominal": {"status": "Green"},
            "watch": {"status": "Amber"},
            "priority": {"status": "Red"},
            "missing": {"status": "No Data"},
        }
        self.assertEqual(compute_demo_readiness(systems), 30.0)
        self.assertEqual(
            compute_demo_readiness({"red": {"status": "Red"}}),
            50.0,
        )
        self.assertEqual(compute_demo_readiness({}), 100.0)


if __name__ == "__main__":
    unittest.main()
