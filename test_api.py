"""
End-to-End API Integration Tests for GitScrum AI
Uses FastAPI TestClient to test all REST endpoints without socket binding.
"""

from fastapi.testclient import TestClient
from app import app
import unittest

client = TestClient(app)


class TestGitScrumAPI(unittest.TestCase):
    def test_root_serves_html(self):
        """Verify GET / serves the Web Dashboard HTML."""
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("GitScrum AI", resp.text)
        self.assertIn("Daily Standup", resp.text)

    def test_rate_limit_endpoint(self):
        """Verify GET /api/rate-limit returns limit info."""
        resp = client.get("/api/rate-limit")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("limit", data)
        self.assertIn("remaining", data)

    def test_demo_endpoint(self):
        """Verify GET /api/demo returns rich realistic Sprint dataset."""
        resp = client.get("/api/demo")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        sprint = data["data"]
        self.assertIn("milestone", sprint)
        self.assertIn("metrics", sprint)
        self.assertIn("bottlenecks", sprint)
        self.assertIn("member_standup", sprint)

        # Check metrics
        metrics = sprint["metrics"]
        self.assertGreater(metrics["health_score"], 0)
        self.assertGreater(metrics["total_story_points"], 0)
        self.assertEqual(len(sprint["member_standup"]), 4)

    def test_ai_summary_heuristic_endpoint(self):
        """Verify POST /api/ai-summary with heuristic engine."""
        # First get demo data
        demo_resp = client.get("/api/demo")
        sprint_data = demo_resp.json()["data"]

        # Request heuristic summary
        payload = {
            "sprint_data": sprint_data,
            "provider": "heuristic",
        }
        resp = client.post("/api/ai-summary", json=payload)
        self.assertEqual(resp.status_code, 200)
        res_data = resp.json()
        self.assertEqual(res_data["status"], "success")
        self.assertIn("🎯 Báo cáo Scrum Master", res_data["summary"])


if __name__ == "__main__":
    unittest.main()
