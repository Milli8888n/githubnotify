"""
Notification & Webhook Dispatcher Module for GitScrum AI
Formats and sends Agile/Scrum reports to Slack, Discord, Telegram, and Microsoft Teams.
"""

from typing import Any, Dict, List, Optional
import httpx


class WebhookNotifier:
    @staticmethod
    def format_standup_markdown(sprint_data: Dict[str, Any]) -> str:
        """Format sprint and daily standup data into clean Markdown for Slack/Teams clipboard copy."""
        milestone = sprint_data.get("milestone", {})
        metrics = sprint_data.get("metrics", {})
        bottlenecks = sprint_data.get("bottlenecks", [])
        member_standup = sprint_data.get("member_standup", [])

        lines = []
        lines.append(f"☀️ *DAILY STANDUP & SPRINT UPDATE — {milestone.get('title', 'Sprint')}*")
        lines.append(f"📊 *Tiến độ:* {metrics.get('completion_rate', 0)}% ({metrics.get('completed_story_points', 0)}/{metrics.get('total_story_points', 0)} SP) | *Sức khỏe:* {metrics.get('health_badge', 'N/A')} ({metrics.get('health_score', 100)}/100)")
        lines.append("")

        if bottlenecks:
            lines.append("🚨 *CẢNH BÁO NGHẼN (Bottlenecks):*")
            for b in bottlenecks[:3]:
                reviewers = ", ".join(f"@{r}" for r in b.get("requested_reviewers", [])) or "chưa gán"
                lines.append(f"• PR #{b['number']} ({b['title']}) chờ {int(b['age_hours'])}h — {b['reason']} [Reviewer: {reviewers}]")
            lines.append("")

        lines.append("👥 *BÁO CÁO THÀNH VIÊN (24h qua & Hôm nay):*")
        for member in member_standup:
            uname = member.get("username")
            done = member.get("done", [])
            in_prog = member.get("in_progress", [])
            blockers = member.get("blockers", [])

            lines.append(f"*{uname}:*")
            if done:
                done_str = ", ".join(f"#{d['number']} {d['title'][:30]}" for d in done[:2])
                lines.append(f"  • *Hôm qua:* {done_str}")
            else:
                lines.append("  • *Hôm qua:* Không có task đóng")

            if in_prog:
                prog_str = ", ".join(f"#{p['number']} {p['title'][:30]}" for p in in_prog[:2])
                lines.append(f"  • *Hôm nay:* {prog_str}")
            else:
                lines.append("  • *Hôm nay:* Đang nhận task mới")

            if blockers:
                block_str = ", ".join(f"#{bl['number']} ({bl['reason']})" for bl in blockers)
                lines.append(f"  • ⚠️ *Blocker:* {block_str}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    async def send_slack_webhook(webhook_url: str, sprint_data: Dict[str, Any], custom_message: Optional[str] = None) -> Dict[str, Any]:
        """Send rich notification to a Slack incoming webhook."""
        text_content = custom_message or WebhookNotifier.format_standup_markdown(sprint_data)
        metrics = sprint_data.get("metrics", {})
        milestone = sprint_data.get("milestone", {})

        payload = {
            "text": f"Daily Standup & Sprint Update: {milestone.get('title')}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🎯 GitScrum: {milestone.get('title', 'Sprint Update')}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Tiến độ:*\n{metrics.get('completion_rate', 0)}% ({metrics.get('completed_story_points')}/{metrics.get('total_story_points')} SP)"},
                        {"type": "mrkdwn", "text": f"*Sức khỏe Sprint:*\n{metrics.get('health_score')}/100 ({metrics.get('health_badge')})"},
                        {"type": "mrkdwn", "text": f"*PR Merged:*\n{metrics.get('merged_prs')}/{metrics.get('total_prs')}"},
                        {"type": "mrkdwn", "text": f"*PR Nghẽn (>24h):*\n{metrics.get('bottlenecks_count')} PRs"},
                    ],
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text_content[:2900],  # Slack text block limit safe guard
                    },
                },
            ],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Slack webhook failed ({resp.status_code}): {resp.text}")
            return {"status": "success", "platform": "slack"}

    @staticmethod
    async def send_discord_webhook(webhook_url: str, sprint_data: Dict[str, Any], custom_message: Optional[str] = None) -> Dict[str, Any]:
        """Send rich embed notification to a Discord webhook."""
        milestone = sprint_data.get("milestone", {})
        metrics = sprint_data.get("metrics", {})
        bottlenecks = sprint_data.get("bottlenecks", [])

        health_score = metrics.get("health_score", 100)
        # Discord color (decimal integer): Green=3066993, Amber=15844367, Red=15158332
        embed_color = 3066993 if health_score >= 80 else (15844367 if health_score >= 55 else 15158332)

        standup_text = custom_message or WebhookNotifier.format_standup_markdown(sprint_data)

        embed = {
            "title": f"🎯 GitScrum Report: {milestone.get('title', 'Sprint Update')}",
            "description": f"Báo cáo tiến độ và tổng hợp Daily Standup từ GitHub",
            "color": embed_color,
            "fields": [
                {
                    "name": "📊 Tiến độ Sprint",
                    "value": f"{metrics.get('completion_rate', 0)}% ({metrics.get('completed_story_points')}/{metrics.get('total_story_points')} SP)",
                    "inline": True,
                },
                {
                    "name": "❤️ Sức khỏe",
                    "value": f"{health_score}/100 ({metrics.get('health_badge')})",
                    "inline": True,
                },
                {
                    "name": "⏱️ Chu kỳ merge",
                    "value": f"{metrics.get('avg_cycle_time_hours')} giờ",
                    "inline": True,
                },
            ],
            "footer": {"text": "GitScrum AI Reporter • Automated Agile Pulse"},
        }

        if bottlenecks:
            bottleneck_lines = [
                f"• **PR #{b['number']}** ({b['title'][:25]}...) chờ {int(b['age_hours'])}h — {b['reason']}"
                for b in bottlenecks[:3]
            ]
            embed["fields"].append({
                "name": "🚨 Cảnh báo nghẽn (Bottlenecks)",
                "value": "\n".join(bottleneck_lines),
                "inline": False,
            })

        payload = {
            "username": "GitScrum AI Bot",
            "avatar_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            "content": f"📢 **Daily Standup & Sprint Update** cho `{milestone.get('title')}`:\n```markdown\n{standup_text[:1500]}\n```",
            "embeds": [embed],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code not in [200, 204]:
                raise ValueError(f"Discord webhook failed ({resp.status_code}): {resp.text}")
            return {"status": "success", "platform": "discord"}

    @staticmethod
    async def send_telegram_message(bot_token: str, chat_id: str, message: str) -> Dict[str, Any]:
        """Send message via Telegram Bot API."""
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Telegram API failed ({resp.status_code}): {resp.text}")
            return {"status": "success", "platform": "telegram"}
