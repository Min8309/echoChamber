"""Selected evidence bundles, fair speaker turns and privacy over the real API."""

import unittest
import json
from unittest.mock import patch
import requests
from test_protection import LiveServer
from test_datasets import KEY, OTHER, payload


class DiscussionTests(unittest.TestCase):
    def test_bundle_rules_four_people_snapshot_coverage_and_private_comparison(self):
        with LiveServer() as server:
            data = server.post("/api/datasets", payload(), headers=KEY).json()
            ids = [row["row_id"] for row in data["rows"][:2]]
            body = dict(
                dataset_id=data["dataset_id"],
                dataset_row_ids=ids[::-1],
                participant_count=4,
                steps=8,
                seed=1,
            )
            response = server.post("/api/runs", body, headers=KEY)
            self.assertEqual(response.status_code, 201, response.text)
            run = response.json()
            self.assertEqual(len(run["agents"]), 4)
            self.assertEqual(len({row["speaker_id"] for row in run["events"]}), 4)
            self.assertEqual(
                [row["row_id"] for row in run["source_data"]["rows"]], ids[::-1]
            )
            self.assertEqual(
                {id for row in run["events"] for id in row["source_row_ids"]}, set(ids)
            )
            self.assertTrue(
                all(
                    row["analysis"] is None and row["discussion_stage"]
                    for row in run["events"]
                )
            )
            self.assertEqual(server.units(), 0)
            self.assertEqual(len(server.get("/api/agents").json()), 3)
            self.assertEqual(server.get("/api/runs/" + run["run_id"]).status_code, 404)
            self.assertEqual(
                requests.get(
                    server.base + "/api/runs/" + run["run_id"], headers=OTHER
                ).status_code,
                404,
            )
            comparison = requests.get(
                server.base
                + f"/api/datasets/{data['dataset_id']}/compare?run_id={run['run_id']}",
                headers=KEY,
            ).json()
            self.assertEqual(comparison["basic"]["real"]["count"], 2)
            self.assertEqual(comparison["basic"]["virtual"]["count"], 8)
            self.assertFalse(comparison["ai"]["comparable"])
            for invalid in [
                dict(body, dataset_row_ids=ids + ids),
                dict(body, dataset_row_ids=["missing"]),
                dict(body, participant_count=2),
                dict(body, steps=2),
                dict(body, dataset_row_id=ids[0]),
            ]:
                self.assertIn(
                    server.post("/api/runs", invalid, headers=KEY).status_code,
                    [404, 422],
                )

    def test_ai_receives_all_evidence_and_recent_dialogue(self):
        from app.routers.workbench import RunRequest, generate_run
        from app.services.storage import load_agents
        from fake_provider import FakeOpenAI

        roster = list(
            {agent.name: agent.model_dump() for agent in load_agents()}.values()
        )[:3]
        request = RunRequest(
            dataset_id="private",
            dataset_row_ids=["one", "two"],
            steps=3,
            engine="openai",
        )
        source = {
            "dataset_id": "private",
            "text": "첫 자료",
            "discussion": True,
            "rows": [
                {"row_id": "one", "number": 1, "text": "첫 자료"},
                {"row_id": "two", "number": 2, "text": "다른 관점의 자료"},
            ],
        }
        client = FakeOpenAI()
        with (
            patch.object(
                client.responses, "create", wraps=client.responses.create
            ) as generate,
            patch("app.routers.workbench.datasets.load"),
            patch("app.routers.workbench.runs.save_run"),
        ):
            result = list(
                generate_run(request, roster, client, source=source, owner="owner")
            )
        self.assertEqual(generate.call_count, 3)
        first = json.loads(generate.call_args_list[0].kwargs["input"])
        last = json.loads(generate.call_args_list[-1].kwargs["input"])
        self.assertEqual(
            [row["text"] for row in first["materials"]], ["첫 자료", "다른 관점의 자료"]
        )
        self.assertEqual(first["recent_dialogue"], [])
        self.assertEqual(len(last["recent_dialogue"]), 2)
        self.assertEqual(result[-1][0], "complete")

    def test_ai_bundle_stream_charges_each_generation_and_analysis(self):
        with LiveServer(OPENAI_API_KEY="test-only-key") as server:
            data = server.post("/api/datasets", payload(), headers=KEY).json()
            body = dict(
                dataset_id=data["dataset_id"],
                dataset_row_ids=[row["row_id"] for row in data["rows"]],
                participant_count=3,
                steps=3,
                engine="openai",
            )
            response = server.post("/api/runs", body, headers=KEY)
            self.assertEqual(response.status_code, 201, response.text)
            run = response.json()
            self.assertEqual(server.units(), 6)
            self.assertEqual(len({event["speaker_id"] for event in run["events"]}), 3)
            self.assertTrue(all(event["analysis"] for event in run["events"]))


if __name__ == "__main__":
    unittest.main()
