"""
Agile & Scrum Analytics Engine for GitScrum AI
Calculates Velocity, Sprint Burndown metrics, Daily Standup 3-columns, Bottleneck detection,
Story Points extraction, and Developer Contribution Matrix.
"""

from datetime import datetime, timezone, timedelta
import re
from typing import Any, Dict, List, Optional


class AgileEngine:
    SIZE_TO_POINTS = {
        "xs": 1,
        "extra-small": 1,
        "s": 2,
        "small": 2,
        "m": 3,
        "medium": 3,
        "l": 5,
        "large": 5,
        "xl": 8,
        "extra-large": 8,
    }

    @staticmethod
    def parse_story_points(labels: List[str], title: str = "", body: str = "") -> int:
        """Extract story points from issue labels, title, or body."""
        # 1. Search labels: sp:3, points:5, pts:2, 5sp, size:m
        for label in labels:
            clean = label.lower().strip()
            # sp:3, points:5, pts:2
            m = re.search(r"(?:sp|points?|pts?|estimate)\s*[:=_-]?\s*(\d+)", clean)
            if m:
                return int(m.group(1))
            # 3sp, 5pts
            m = re.search(r"^(\d+)\s*(?:sp|pts|points)$", clean)
            if m:
                return int(m.group(1))
            # size:m or size-s
            m = re.search(r"size\s*[:=_-]?\s*([a-z-]+)", clean)
            if m and m.group(1) in AgileEngine.SIZE_TO_POINTS:
                return AgileEngine.SIZE_TO_POINTS[m.group(1)]
            if clean in AgileEngine.SIZE_TO_POINTS:
                return AgileEngine.SIZE_TO_POINTS[clean]

        # 2. Search title: [3sp] or (5 points)
        text = f"{title} {body}"
        m = re.search(r"\[(?:sp|points?|pts?)?\s*(\d+)\s*(?:sp|pts)?\]", text, re.IGNORECASE)
        if m:
            return int(m.group(1))

        # Default fallback: 1 point per task if no point declared
        return 1

    @staticmethod
    def parse_iso(iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def analyze_sprint(
        self,
        milestone: Dict[str, Any],
        pull_requests: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        commits: List[Dict[str, Any]],
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive Agile/Scrum analysis on milestone data."""
        if now is None:
            now = datetime.now(timezone.utc)

        # Standup lookback window: 72h if Monday, else 24h
        is_monday = now.weekday() == 0
        standup_window_hours = 72 if is_monday else 24
        standup_cutoff = now - timedelta(hours=standup_window_hours)

        # 1. Aggregate Items & Story Points
        all_items = pull_requests + issues
        total_items = len(all_items)
        closed_items = 0
        open_items = 0

        total_story_points = 0
        completed_story_points = 0
        in_progress_story_points = 0

        for item in all_items:
            pts = self.parse_story_points(item.get("labels", []), item.get("title", ""), item.get("body", ""))
            item["story_points"] = pts
            total_story_points += pts

            if item.get("state") == "closed" or item.get("merged") is True:
                closed_items += 1
                completed_story_points += pts
            else:
                open_items += 1
                in_progress_story_points += pts

        completion_rate = (
            round((completed_story_points / total_story_points * 100), 1)
            if total_story_points > 0
            else (round((closed_items / total_items * 100), 1) if total_items > 0 else 0)
        )

        # 2. Cycle Time & Review Turnaround for PRs
        cycle_times_hours = []
        review_times_hours = []
        for pr in pull_requests:
            created_at = self.parse_iso(pr.get("created_at"))
            merged_at = self.parse_iso(pr.get("merged_at"))
            if created_at and merged_at and pr.get("merged"):
                hours = (merged_at - created_at).total_seconds() / 3600
                cycle_times_hours.append(hours)

            # Review turnaround (time to first review)
            reviews = pr.get("reviews", [])
            if created_at and reviews:
                first_rev_time = None
                for rev in reviews:
                    rev_dt = self.parse_iso(rev.get("submitted_at"))
                    if rev_dt and (first_rev_time is None or rev_dt < first_rev_time):
                        first_rev_time = rev_dt
                if first_rev_time and first_rev_time >= created_at:
                    review_times_hours.append((first_rev_time - created_at).total_seconds() / 3600)

        avg_cycle_time_hours = round(sum(cycle_times_hours) / len(cycle_times_hours), 1) if cycle_times_hours else 0.0
        avg_review_turnaround_hours = round(sum(review_times_hours) / len(review_times_hours), 1) if review_times_hours else 0.0

        # 3. Detect Bottlenecks & Stale PRs
        bottlenecks = []
        for pr in pull_requests:
            if pr.get("state") == "open" and not pr.get("draft", False):
                created_at = self.parse_iso(pr.get("created_at"))
                updated_at = self.parse_iso(pr.get("updated_at"))
                age_hours = round((now - created_at).total_seconds() / 3600, 1) if created_at else 0
                idle_hours = round((now - updated_at).total_seconds() / 3600, 1) if updated_at else age_hours

                # Check reviews for CHANGES_REQUESTED
                has_changes_requested = any(
                    r.get("state") == "CHANGES_REQUESTED" for r in pr.get("reviews", [])
                )
                is_stale_warning = age_hours >= 24
                is_stale_critical = age_hours >= 48

                is_blocked_label = any(
                    lbl.lower() in ["blocked", "blocker", "waiting", "waiting-for-review"]
                    for lbl in pr.get("labels", [])
                )

                if is_stale_warning or has_changes_requested or is_blocked_label:
                    severity = "critical" if (is_stale_critical or has_changes_requested) else "warning"
                    reason = []
                    if is_stale_critical:
                        reason.append(f"PR mở {int(age_hours)}h chưa được merge")
                    elif is_stale_warning:
                        reason.append(f"PR mở {int(age_hours)}h cần review")

                    if has_changes_requested:
                        reason.append("Reviewer đã yêu cầu sửa đổi (Changes Requested)")
                    if is_blocked_label:
                        reason.append("Gắn nhãn Blocked / Waiting")

                    bottlenecks.append({
                        "number": pr.get("number", 0),
                        "title": pr.get("title", "Untitled PR"),
                        "author": pr.get("author", "unknown"),
                        "author_avatar": pr.get("author_avatar", ""),
                        "age_hours": age_hours,
                        "idle_hours": idle_hours,
                        "severity": severity,
                        "reason": " • ".join(reason),
                        "requested_reviewers": pr.get("requested_reviewers", []),
                        "reviews_count": len(pr.get("reviews", [])),
                        "html_url": pr.get("html_url", "#"),
                    })

        # Sort bottlenecks by age desc
        bottlenecks.sort(key=lambda x: x["age_hours"], reverse=True)

        # 4. Daily Standup Matrix (By Member)
        # Columns: Done (in standup window), In Progress, Blocked
        member_standup: Dict[str, Dict[str, Any]] = {}

        def get_or_create_member(username: str, avatar: str = "") -> Dict[str, Any]:
            if username not in member_standup:
                member_standup[username] = {
                    "username": username,
                    "avatar": avatar,
                    "done": [],
                    "in_progress": [],
                    "blockers": [],
                    "stats": {
                        "merged_prs": 0,
                        "open_prs": 0,
                        "closed_issues": 0,
                        "open_issues": 0,
                        "commits": 0,
                        "story_points": 0,
                    },
                }
            if avatar and not member_standup[username]["avatar"]:
                member_standup[username]["avatar"] = avatar
            return member_standup[username]

        # Classify PRs
        for pr in pull_requests:
            author = pr.get("author", "unknown")
            member = get_or_create_member(author, pr.get("author_avatar", ""))
            pts = pr.get("story_points", 1)

            closed_at = self.parse_iso(pr.get("closed_at")) or self.parse_iso(pr.get("merged_at"))
            is_merged = pr.get("merged", False)

            if pr.get("state") == "closed":
                if is_merged:
                    member["stats"]["merged_prs"] += 1
                if closed_at and closed_at >= standup_cutoff:
                    member["done"].append({
                        "type": "pr_merged" if is_merged else "pr_closed",
                        "title": pr.get("title", ""),
                        "number": pr.get("number", 0),
                        "points": pts,
                        "url": pr.get("html_url", "#"),
                        "time": closed_at.strftime("%H:%M %d/%m"),
                    })
                    member["stats"]["story_points"] += pts
            else:
                member["stats"]["open_prs"] += 1
                # Check if it has blocker or changes requested
                has_changes_requested = any(r.get("state") == "CHANGES_REQUESTED" for r in pr.get("reviews", []))
                created_at = self.parse_iso(pr.get("created_at"))
                age = round((now - created_at).total_seconds() / 3600, 1) if created_at else 0
                
                if has_changes_requested or age >= 48:
                    member["blockers"].append({
                        "type": "pr_blocked",
                        "title": pr.get("title", ""),
                        "number": pr.get("number", 0),
                        "reason": "Changes requested" if has_changes_requested else f"Chờ review {int(age)}h",
                        "url": pr.get("html_url", "#"),
                    })
                else:
                    member["in_progress"].append({
                        "type": "pr_open",
                        "title": pr.get("title", ""),
                        "number": pr.get("number", 0),
                        "points": pts,
                        "url": pr.get("html_url", "#"),
                    })

        # Classify Issues
        for issue in issues:
            assignees = issue.get("assignees", [])
            target_users = assignees if assignees else [issue.get("author", "unassigned")]
            closed_at = self.parse_iso(issue.get("closed_at"))
            pts = issue.get("story_points", 1)

            for user in target_users:
                member = get_or_create_member(user, issue.get("author_avatar", ""))
                if issue.get("state") == "closed":
                    member["stats"]["closed_issues"] += 1
                    if closed_at and closed_at >= standup_cutoff:
                        member["done"].append({
                            "type": "issue_closed",
                            "title": issue.get("title", ""),
                            "number": issue.get("number", 0),
                            "points": pts,
                            "url": issue.get("html_url", "#"),
                            "time": closed_at.strftime("%H:%M %d/%m"),
                        })
                        member["stats"]["story_points"] += pts
                else:
                    member["stats"]["open_issues"] += 1
                    is_blocked = any(lbl.lower() in ["blocked", "blocker"] for lbl in issue.get("labels", []))
                    if is_blocked:
                        member["blockers"].append({
                            "type": "issue_blocked",
                            "title": issue.get("title", ""),
                            "number": issue.get("number", 0),
                            "reason": "Nhãn Blocked",
                            "url": issue.get("html_url", "#"),
                        })
                    else:
                        member["in_progress"].append({
                            "type": "issue_open",
                            "title": issue.get("title", ""),
                            "number": issue.get("number", 0),
                            "points": pts,
                            "url": issue.get("html_url", "#"),
                        })

        # Classify Commits
        for commit in commits:
            author = commit.get("author", "unknown")
            member = get_or_create_member(author, commit.get("author_avatar", ""))
            member["stats"]["commits"] += 1
            commit_dt = self.parse_iso(commit.get("date"))
            if commit_dt and commit_dt >= standup_cutoff:
                # Add to done if not already represented
                member["done"].append({
                    "type": "commit",
                    "title": commit.get("message", ""),
                    "number": commit.get("sha", ""),
                    "points": 0,
                    "url": commit.get("html_url", "#"),
                    "time": commit_dt.strftime("%H:%M %d/%m"),
                })

        # 5. Sprint Health Score (0 - 100)
        # Base on completion vs time, minus points for critical bottlenecks
        due_on = self.parse_iso(milestone.get("due_on"))
        created_at_ms = self.parse_iso(milestone.get("created_at"))
        
        health_score = 100
        # Deduct for bottlenecks: -10 per critical, -5 per warning
        crit_count = sum(1 for b in bottlenecks if b["severity"] == "critical")
        warn_count = sum(1 for b in bottlenecks if b["severity"] == "warning")
        health_score -= (crit_count * 12 + warn_count * 5)

        # Check due date urgency
        if due_on and created_at_ms:
            total_duration = (due_on - created_at_ms).total_seconds()
            elapsed_duration = (now - created_at_ms).total_seconds()
            if total_duration > 0:
                time_ratio = min(max(elapsed_duration / total_duration, 0.0), 1.0)
                work_ratio = completion_rate / 100.0
                # If time is 80% elapsed but work is only 30%, deduct score
                if time_ratio > work_ratio + 0.2:
                    gap_deduction = int((time_ratio - work_ratio) * 40)
                    health_score -= gap_deduction

        health_score = max(min(health_score, 100), 20)

        health_badge = "Excellent"
        if health_score < 50:
            health_badge = "Critical Risk"
        elif health_score < 75:
            health_badge = "Attention Needed"
        elif health_score < 90:
            health_badge = "Good Progress"

        return {
            "milestone": {
                "number": milestone.get("number"),
                "title": milestone.get("title"),
                "state": milestone.get("state"),
                "due_on": milestone.get("due_on"),
                "created_at": milestone.get("created_at"),
                "html_url": milestone.get("html_url"),
            },
            "metrics": {
                "health_score": health_score,
                "health_badge": health_badge,
                "total_items": total_items,
                "closed_items": closed_items,
                "open_items": open_items,
                "completion_rate": completion_rate,
                "total_story_points": total_story_points,
                "completed_story_points": completed_story_points,
                "in_progress_story_points": in_progress_story_points,
                "total_prs": len(pull_requests),
                "merged_prs": sum(1 for pr in pull_requests if pr.get("merged")),
                "open_prs": sum(1 for pr in pull_requests if pr.get("state") == "open"),
                "avg_cycle_time_hours": avg_cycle_time_hours,
                "avg_review_turnaround_hours": avg_review_turnaround_hours,
                "bottlenecks_count": len(bottlenecks),
                "critical_bottlenecks_count": crit_count,
            },
            "standup_window": {
                "hours": standup_window_hours,
                "is_monday": is_monday,
                "since": standup_cutoff.isoformat(),
            },
            "bottlenecks": bottlenecks,
            "member_standup": list(member_standup.values()),
            "raw_summary": {
                "pull_requests_count": len(pull_requests),
                "issues_count": len(issues),
                "commits_count": len(commits),
            },
        }
