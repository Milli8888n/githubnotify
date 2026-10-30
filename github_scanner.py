"""
GitHub API Scanner Module for GitScrum AI
Fetches milestones, pull requests, issues, reviews, and commits with pagination and rate limit handling.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx


class GitHubScanner:
    def __init__(self, token: Optional[str] = None):
        self.token = token.strip() if token and token.strip() else None
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitScrum-AI-Reporter/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_rate_limit(self) -> Dict[str, Any]:
        """Fetch current rate limit status from GitHub."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/rate_limit", headers=self._get_headers()
            )
            if resp.status_code == 200:
                data = resp.json().get("resources", {}).get("core", {})
                reset_time = datetime.fromtimestamp(
                    data.get("reset", 0), tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
                return {
                    "limit": data.get("limit", 60),
                    "remaining": data.get("remaining", 0),
                    "reset_time": reset_time,
                    "authenticated": bool(self.token),
                }
            return {
                "limit": 60 if not self.token else 5000,
                "remaining": "Unknown",
                "reset_time": "Unknown",
                "authenticated": bool(self.token),
            }

    async def verify_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Verify repository exists and user has access."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}", headers=self._get_headers()
            )
            if resp.status_code == 404:
                raise ValueError(
                    f"Repository '{owner}/{repo}' not found. Check repository name or token permissions."
                )
            if resp.status_code == 401:
                raise ValueError(
                    "Invalid GitHub Personal Access Token. Please verify token permissions."
                )
            if resp.status_code == 403:
                rate_remaining = resp.headers.get("x-ratelimit-remaining", "0")
                if rate_remaining == "0":
                    reset_epoch = int(resp.headers.get("x-ratelimit-reset", "0"))
                    reset_str = datetime.fromtimestamp(
                        reset_epoch, tz=timezone.utc
                    ).strftime("%H:%M:%S UTC")
                    raise ValueError(
                        f"GitHub API rate limit exceeded. Resets at {reset_str}. Provide a GitHub Token to get 5,000 requests/hr."
                    )
                raise ValueError(f"Access forbidden: {resp.text}")
            if resp.status_code != 200:
                raise ValueError(
                    f"GitHub API error ({resp.status_code}): {resp.text}"
                )

            data = resp.json()
            return {
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "default_branch": data.get("default_branch", "main"),
                "private": data.get("private", False),
                "open_issues_count": data.get("open_issues_count", 0),
            }

    async def get_milestones(
        self, owner: str, repo: str, state: str = "all"
    ) -> List[Dict[str, Any]]:
        """Fetch milestones (Sprints) for the repository."""
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/milestones",
                params={"state": state, "per_page": 50, "sort": "due_on", "direction": "desc"},
                headers=self._get_headers(),
            )
            if resp.status_code != 200:
                raise ValueError(
                    f"Failed to fetch milestones ({resp.status_code}): {resp.text}"
                )

            milestones = resp.json()
            results = []
            for m in milestones:
                results.append(
                    {
                        "number": m.get("number"),
                        "title": m.get("title"),
                        "description": m.get("description") or "",
                        "state": m.get("state"),
                        "open_issues": m.get("open_issues", 0),
                        "closed_issues": m.get("closed_issues", 0),
                        "created_at": m.get("created_at"),
                        "updated_at": m.get("updated_at"),
                        "due_on": m.get("due_on"),
                        "closed_at": m.get("closed_at"),
                        "html_url": m.get("html_url"),
                    }
                )
            return results

    async def get_milestone_items(
        self, owner: str, repo: str, milestone_number: int
    ) -> Dict[str, Any]:
        """Fetch all issues and pull requests attached to a specific milestone."""
        items: List[Dict[str, Any]] = []
        page = 1
        per_page = 100

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/issues",
                    params={
                        "milestone": milestone_number,
                        "state": "all",
                        "per_page": per_page,
                        "page": page,
                    },
                    headers=self._get_headers(),
                )
                if resp.status_code != 200:
                    raise ValueError(
                        f"Failed to fetch milestone items ({resp.status_code}): {resp.text}"
                    )

                data = resp.json()
                if not data:
                    break
                items.extend(data)
                if len(data) < per_page or page >= 5:  # Cap at 500 items for safety
                    break
                page += 1

            # Separate PRs and Issues
            pull_requests: List[Dict[str, Any]] = []
            pure_issues: List[Dict[str, Any]] = []

            for item in items:
                labels = [label["name"] for label in item.get("labels", [])]
                assignees = [a["login"] for a in item.get("assignees", [])]
                author = item.get("user", {}).get("login", "unknown")

                base_item = {
                    "id": item.get("id"),
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "author": author,
                    "author_avatar": item.get("user", {}).get("avatar_url", ""),
                    "assignees": assignees,
                    "labels": labels,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "closed_at": item.get("closed_at"),
                    "html_url": item.get("html_url"),
                    "comments_count": item.get("comments", 0),
                    "body": item.get("body") or "",
                }

                if "pull_request" in item:
                    # It is a Pull Request, let's fetch deeper PR metadata
                    pr_num = item["number"]
                    pr_detail_resp = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_num}",
                        headers=self._get_headers(),
                    )
                    pr_detail = (
                        pr_detail_resp.json()
                        if pr_detail_resp.status_code == 200
                        else {}
                    )

                    # Fetch reviews for bottleneck analysis
                    reviews_resp = await client.get(
                        f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_num}/reviews",
                        headers=self._get_headers(),
                    )
                    reviews_data = (
                        reviews_resp.json()
                        if reviews_resp.status_code == 200
                        else []
                    )

                    requested_reviewers = [
                        r.get("login")
                        for r in pr_detail.get("requested_reviewers", [])
                    ]

                    # Parse latest review status per reviewer
                    reviews_summary = []
                    for rev in reviews_data:
                        reviews_summary.append(
                            {
                                "user": rev.get("user", {}).get("login"),
                                "state": rev.get("state"),  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
                                "submitted_at": rev.get("submitted_at"),
                            }
                        )

                    merged_at = pr_detail.get("merged_at")
                    is_merged = bool(merged_at)
                    draft = pr_detail.get("draft", False)

                    base_item.update(
                        {
                            "is_pr": True,
                            "draft": draft,
                            "merged": is_merged,
                            "merged_at": merged_at,
                            "merged_by": pr_detail.get("merged_by", {}).get(
                                "login"
                            )
                            if is_merged and pr_detail.get("merged_by")
                            else None,
                            "requested_reviewers": requested_reviewers,
                            "reviews": reviews_summary,
                            "additions": pr_detail.get("additions", 0),
                            "deletions": pr_detail.get("deletions", 0),
                            "changed_files": pr_detail.get("changed_files", 0),
                        }
                    )
                    pull_requests.append(base_item)
                else:
                    base_item["is_pr"] = False
                    pure_issues.append(base_item)

            # Fetch recent commits within milestone window (if created_at is known)
            commits = await self.get_repo_commits(owner, repo, client, limit=100)

            return {
                "pull_requests": pull_requests,
                "issues": pure_issues,
                "commits": commits,
            }

    async def get_repo_commits(
        self,
        owner: str,
        repo: str,
        client: httpx.AsyncClient,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch recent repository commits."""
        params: Dict[str, Any] = {"per_page": min(limit, 100)}
        if since:
            params["since"] = since

        resp = await client.get(
            f"{self.base_url}/repos/{owner}/{repo}/commits",
            params=params,
            headers=self._get_headers(),
        )
        if resp.status_code != 200:
            return []

        commits_data = resp.json()
        parsed_commits = []
        for c in commits_data:
            commit_obj = c.get("commit", {})
            author_obj = c.get("author") or {}
            committer_name = (
                author_obj.get("login")
                or commit_obj.get("author", {}).get("name")
                or "Unknown"
            )
            parsed_commits.append(
                {
                    "sha": c.get("sha", "")[:7],
                    "author": committer_name,
                    "author_avatar": author_obj.get("avatar_url", ""),
                    "message": commit_obj.get("message", "").split("\n")[0],
                    "date": commit_obj.get("author", {}).get("date"),
                    "html_url": c.get("html_url"),
                }
            )
        return parsed_commits
