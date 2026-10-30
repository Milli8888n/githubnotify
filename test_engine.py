"""
Comprehensive Automated Test Suite for GitScrum AI
Validates Story Points Regex Parsing, Agile Standup Classification,
Bottleneck Detection, AI Heuristic Summary Generation, and Webhook Formatting.
"""

from datetime import datetime, timezone, timedelta
import unittest

from agile_engine import AgileEngine
from ai_summary import AIScrumMaster
from notifier import WebhookNotifier


class TestGitScrumEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AgileEngine()
        self.now = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)

    def test_story_point_parsing(self):
        """Verify extraction of story points from various label formats and titles."""
        # 1. Label formats: sp:X, points:X, size:X
        self.assertEqual(AgileEngine.parse_story_points(["sp:3"]), 3)
        self.assertEqual(AgileEngine.parse_story_points(["points:5"]), 5)
        self.assertEqual(AgileEngine.parse_story_points(["pts:8"]), 8)
        self.assertEqual(AgileEngine.parse_story_points(["estimate:2"]), 2)
        self.assertEqual(AgileEngine.parse_story_points(["size:s"]), 2)
        self.assertEqual(AgileEngine.parse_story_points(["size:m"]), 3)
        self.assertEqual(AgileEngine.parse_story_points(["size:l"]), 5)
        self.assertEqual(AgileEngine.parse_story_points(["size:xl"]), 8)

        # 2. In title: [3sp] or (5 points)
        self.assertEqual(
            AgileEngine.parse_story_points([], title="feat: checkout stripe [5sp]"), 5
        )

        # 3. Default fallback
        self.assertEqual(AgileEngine.parse_story_points([]), 1)

    def test_standup_classification(self):
        """Verify daily standup classifies items into Done, In Progress, and Blockers."""
        milestone = {
            "number": 1,
            "title": "Sprint 1",
            "state": "open",
            "due_on": (self.now + timedelta(days=7)).isoformat(),
            "created_at": (self.now - timedelta(days=7)).isoformat(),
        }

        # PR 1: Merged 10h ago -> Done
        # PR 2: Open, created 3h ago -> In Progress
        # PR 3: Open, created 50h ago -> Blocker (age > 48h)
        pull_requests = [
            {
                "number": 101,
                "title": "Merged Feature [3sp]",
                "author": "alice",
                "author_avatar": "",
                "state": "closed",
                "merged": True,
                "labels": ["sp:3"],
                "created_at": (self.now - timedelta(hours=20)).isoformat(),
                "merged_at": (self.now - timedelta(hours=10)).isoformat(),
                "closed_at": (self.now - timedelta(hours=10)).isoformat(),
                "html_url": "https://github.com/repo/pull/101",
                "reviews": [],
            },
            {
                "number": 102,
                "title": "Active Feature [2sp]",
                "author": "bob",
                "author_avatar": "",
                "state": "open",
                "merged": False,
                "labels": ["sp:2"],
                "created_at": (self.now - timedelta(hours=3)).isoformat(),
                "html_url": "https://github.com/repo/pull/102",
                "reviews": [],
            },
            {
                "number": 103,
                "title": "Stale Feature [5sp]",
                "author": "alice",
                "author_avatar": "",
                "state": "open",
                "merged": False,
                "labels": ["sp:5"],
                "created_at": (self.now - timedelta(hours=50)).isoformat(),
                "html_url": "https://github.com/repo/pull/103",
                "reviews": [],
            },
        ]

        issues = [
            {
                "number": 201,
                "title": "Bug Fix [1sp]",
                "author": "bob",
                "author_avatar": "",
                "assignees": ["bob"],
                "state": "closed",
                "labels": ["sp:1"],
                "created_at": (self.now - timedelta(days=2)).isoformat(),
                "closed_at": (self.now - timedelta(hours=5)).isoformat(),
                "html_url": "https://github.com/repo/issues/201",
            }
        ]

        commits = [
            {
                "sha": "abc1234",
                "author": "alice",
                "message": "fix: unit test error",
                "date": (self.now - timedelta(hours=4)).isoformat(),
                "html_url": "#",
            }
        ]

        analysis = self.engine.analyze_sprint(
            milestone=milestone,
            pull_requests=pull_requests,
            issues=issues,
            commits=commits,
            now=self.now,
        )

        members = {m["username"]: m for m in analysis["member_standup"]}

        # Check Alice: has merged PR and a commit in Done, has 1 blocker (PR 103)
        self.assertIn("alice", members)
        self.assertTrue(any(d["number"] == 101 for d in members["alice"]["done"]))
        self.assertTrue(any(b["number"] == 103 for b in members["alice"]["blockers"]))

        # Check Bob: has issue in Done, PR 102 in In Progress
        self.assertIn("bob", members)
        self.assertTrue(any(d["number"] == 201 for d in members["bob"]["done"]))
        self.assertTrue(any(p["number"] == 102 for p in members["bob"]["in_progress"]))

        # Check Velocity & Story points
        # Total: 3 (PR 101) + 2 (PR 102) + 5 (PR 103) + 1 (Issue 201) = 11 SP
        # Completed: 3 (PR 101) + 1 (Issue 201) = 4 SP
        self.assertEqual(analysis["metrics"]["total_story_points"], 11)
        self.assertEqual(analysis["metrics"]["completed_story_points"], 4)

    def test_bottleneck_detection(self):
        """Verify bottleneck detection flags >24h warning and >48h critical PRs."""
        milestone = {"number": 1, "title": "Sprint Test", "state": "open"}
        pull_requests = [
            # Warning: 30 hours old
            {
                "number": 10,
                "title": "PR Thirty Hours",
                "author": "dev1",
                "state": "open",
                "created_at": (self.now - timedelta(hours=30)).isoformat(),
                "labels": [],
                "reviews": [],
                "requested_reviewers": ["reviewer1"],
                "html_url": "#",
            },
            # Critical: 55 hours old
            {
                "number": 11,
                "title": "PR Fifty-Five Hours",
                "author": "dev2",
                "state": "open",
                "created_at": (self.now - timedelta(hours=55)).isoformat(),
                "labels": [],
                "reviews": [],
                "requested_reviewers": ["reviewer2"],
                "html_url": "#",
            },
            # Changes Requested -> Critical
            {
                "number": 12,
                "title": "PR Changes Requested",
                "author": "dev3",
                "state": "open",
                "created_at": (self.now - timedelta(hours=10)).isoformat(),
                "labels": [],
                "reviews": [{"user": "lead", "state": "CHANGES_REQUESTED"}],
                "requested_reviewers": [],
                "html_url": "#",
            },
        ]

        analysis = self.engine.analyze_sprint(
            milestone=milestone,
            pull_requests=pull_requests,
            issues=[],
            commits=[],
            now=self.now,
        )

        bottlenecks = analysis["bottlenecks"]
        self.assertEqual(len(bottlenecks), 3)

        severities = {b["number"]: b["severity"] for b in bottlenecks}
        self.assertEqual(severities[10], "warning")
        self.assertEqual(severities[11], "critical")
        self.assertEqual(severities[12], "critical")

        # Health score should be deducted for critical and warning bottlenecks
        self.assertLess(analysis["metrics"]["health_score"], 80)

    def test_heuristic_ai_summary(self):
        """Verify offline heuristic AI engine generates formatted Markdown with essential sections."""
        milestone = {"title": "Sprint 5"}
        metrics = {
            "health_score": 85,
            "health_badge": "Good Progress",
            "completion_rate": 70,
            "total_story_points": 30,
            "completed_story_points": 21,
            "open_prs": 2,
            "merged_prs": 5,
            "avg_cycle_time_hours": 14.5,
            "bottlenecks_count": 1,
            "critical_bottlenecks_count": 0,
        }
        member_standup = [
            {
                "username": "alex",
                "done": [{"number": 101, "title": "Payment gateway"}],
                "in_progress": [{"number": 102, "title": "Checkout UI"}],
                "blockers": [],
            }
        ]
        sprint_data = {
            "milestone": milestone,
            "metrics": metrics,
            "bottlenecks": [],
            "member_standup": member_standup,
            "standup_window": {"hours": 24, "is_monday": False},
        }

        summary = AIScrumMaster.generate_heuristic_summary(sprint_data)
        self.assertIn("# 🎯 Báo cáo Scrum Master", summary)
        self.assertIn("## 📊 1. Tổng quan Sức khỏe & Vận tốc Sprint", summary)
        self.assertIn("## 👥 2. Tóm tắt Daily Standup", summary)
        self.assertIn("@alex", summary)
        self.assertIn("Payment gateway", summary)

    def test_webhook_standup_markdown_formatter(self):
        """Verify WebhookNotifier.format_standup_markdown produces valid clean text for Slack/Teams."""
        sprint_data = {
            "milestone": {"title": "Sprint 14"},
            "metrics": {
                "completion_rate": 80,
                "completed_story_points": 24,
                "total_story_points": 30,
                "health_score": 90,
                "health_badge": "Good Progress",
            },
            "bottlenecks": [],
            "member_standup": [
                {
                    "username": "sarah",
                    "done": [{"number": 12, "title": "Cart badge sync"}],
                    "in_progress": [],
                    "blockers": [],
                }
            ],
        }

        markdown = WebhookNotifier.format_standup_markdown(sprint_data)
        self.assertIn("*DAILY STANDUP & SPRINT UPDATE — Sprint 14*", markdown)
        self.assertIn("*sarah:*", markdown)
        self.assertIn("Cart badge sync", markdown)


if __name__ == "__main__":
    unittest.main()
