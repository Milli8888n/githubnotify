"""
AI Scrum Master Module for GitScrum AI
Provides intelligent heuristic synthesis (offline, zero-cost, instant)
and optional LLM integrations (Google Gemini & OpenAI) for natural Scrum Master commentary.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx


class AIScrumMaster:
    @staticmethod
    def generate_heuristic_summary(
        sprint_data: Dict[str, Any],
        tone: str = "balanced"  # balanced, encouraging, strict
    ) -> str:
        """
        Synthesizes a structured, high-insight Scrum Master Markdown report
        completely offline without requiring an external AI API key.
        """
        milestone = sprint_data.get("milestone", {})
        metrics = sprint_data.get("metrics", {})
        bottlenecks = sprint_data.get("bottlenecks", [])
        member_standup = sprint_data.get("member_standup", [])
        standup_window = sprint_data.get("standup_window", {})

        title = milestone.get("title", "Sprint Current")
        health_score = metrics.get("health_score", 100)
        health_badge = metrics.get("health_badge", "Good Progress")
        completion_rate = metrics.get("completion_rate", 0)
        total_sp = metrics.get("total_story_points", 0)
        completed_sp = metrics.get("completed_story_points", 0)
        open_prs = metrics.get("open_prs", 0)
        merged_prs = metrics.get("merged_prs", 0)
        cycle_time = metrics.get("avg_cycle_time_hours", 0)
        crit_bottlenecks = metrics.get("critical_bottlenecks_count", 0)

        window_hours = standup_window.get("hours", 24)
        is_monday = standup_window.get("is_monday", False)
        window_text = f"{window_hours}h qua" + (" (cuối tuần + Thứ 6)" if is_monday else "")

        # Status emoji
        health_icon = "🟢" if health_score >= 80 else ("🟡" if health_score >= 55 else "🔴")

        # 1. Executive Summary
        report = []
        report.append(f"# 🎯 Báo cáo Scrum Master: {title}")
        report.append(f"> **Tình trạng Sprint:** {health_icon} **{health_score}/100** ({health_badge}) | **Tiến độ:** {completion_rate}% ({completed_sp}/{total_sp} SP) | **Thời gian quét:** {datetime.now(timezone.utc).strftime('%H:%M - %d/%m/%Y UTC')}\n")

        # 2. Key Observations
        report.append("## 📊 1. Tổng quan Sức khỏe & Vận tốc Sprint")
        observations = []
        if completion_rate >= 75:
            observations.append(f"- ✅ **Tiến độ xuất sắc:** Đã hoàn thành {completed_sp}/{total_sp} Story Points ({completion_rate}%). Khả năng cao đạt mục tiêu Sprint.")
        elif completion_rate >= 40:
            observations.append(f"- ⚠️ **Tiến độ trung bình:** Đạt {completion_rate}% khối lượng công việc. Cần đẩy nhanh các PR đang mở.")
        else:
            observations.append(f"- 🚨 **Báo động tiến độ:** Mới hoàn thành {completion_rate}%. Cần rà soát lại phạm vi công việc và hỗ trợ các đầu việc tồn đọng.")

        if cycle_time > 0:
            if cycle_time <= 12:
                observations.append(f"- ⚡ **Chu kỳ review nhanh:** Thời gian merge trung bình chỉ **{cycle_time} giờ**, luồng code flow rất mượt.")
            elif cycle_time <= 36:
                observations.append(f"- ⏱️ **Chu kỳ review ổn định:** Thời gian merge trung bình là **{cycle_time} giờ**.")
            else:
                observations.append(f"- 🐢 **Nghẽn review:** Thời gian merge trung bình lên tới **{cycle_time} giờ** (>36h), các PR đang bị ngâm quá lâu.")

        if crit_bottlenecks > 0:
            observations.append(f"- 🚨 **Phát hiện {crit_bottlenecks} PR nghẽn nghiêm trọng:** Cần can thiệp gỡ vướng ngay trong buổi standup hôm nay.")
        else:
            observations.append("- 🎉 **Không có PR nào bị ngâm quá 48h:** Tinh thần review của team rất tốt.")

        report.extend(observations)
        report.append("")

        # 3. Daily Standup Bulletin (By Member)
        report.append(f"## 👥 2. Tóm tắt Daily Standup ({window_text})")
        if not member_standup:
            report.append("_Chưa ghi nhận hoạt động nào của thành viên trong mốc thời gian này._\n")
        else:
            for member in member_standup:
                uname = member.get("username", "Unknown")
                done = member.get("done", [])
                in_prog = member.get("in_progress", [])
                blockers = member.get("blockers", [])

                report.append(f"### 👤 @{uname}")
                if done:
                    done_titles = [f"• #{item.get('number')} {item.get('title')}" for item in done[:3]]
                    report.append(f"- **Đã xong:** {len(done)} việc\n  " + "\n  ".join(done_titles))
                else:
                    report.append("- **Đã xong:** _Chưa có PR/Issue nào đóng trong 24h qua_")

                if in_prog:
                    prog_titles = [f"• #{item.get('number')} {item.get('title')}" for item in in_prog[:3]]
                    report.append(f"- **Đang làm:** {len(in_prog)} việc\n  " + "\n  ".join(prog_titles))
                else:
                    report.append("- **Đang làm:** _Hiện không có PR hay issue mở_")

                if blockers:
                    block_titles = [f"• #{item.get('number')} {item.get('title')} ({item.get('reason')})" for item in blockers]
                    report.append(f"- ⚠️ **Vướng mắc (Blocker):**\n  " + "\n  ".join(block_titles))
                report.append("")

        # 4. Critical Bottlenecks
        if bottlenecks:
            report.append("## 🚨 3. Điểm nghẽn cần ưu tiên xử lý (Bottleneck Radar)")
            report.append("| PR | Tác giả | Thời gian chờ | Lý do | Reviewer phân công |")
            report.append("| :--- | :--- | :--- | :--- | :--- |")
            for b in bottlenecks[:5]:
                pr_link = f"[#{b['number']} {b['title'][:35]}...]({b['html_url']})"
                reviewers = ", ".join(f"@{r}" for r in b.get("requested_reviewers", [])) or "_Chưa gán_"
                age_str = f"**{int(b['age_hours'])}h**"
                report.append(f"| {pr_link} | @{b['author']} | {age_str} | {b['reason']} | {reviewers} |")
            report.append("")

        # 5. Scrum Master Recommendations
        report.append("## 💡 4. Khuyến nghị cho phiên họp Standup hôm nay")
        recommendations = []
        if crit_bottlenecks > 0:
            recommendations.append("1. **Gỡ tắc nghẽn trước:** Dành 5 phút đầu buổi standup để chốt review cho các PR bị ngâm >48h.")
        if open_prs > merged_prs + 3:
            recommendations.append("2. **Hạn chế mở thêm việc mới (WIP Limit):** Tập trung review và merge các PR đang dở dang trước khi pick issue mới.")
        if completion_rate < 50:
            recommendations.append("3. **Rà soát Scope:** Đánh giá lại độ ưu tiên các User Story trong Milestone, cân nhắc chuyển các việc P2/P3 sang Sprint sau nếu thiếu thời gian.")
        recommendations.append("4. **Đồng bộ tiến độ:** Khuyến khích các dev tag reviewer trực tiếp trên kênh chat để rút ngắn chu kỳ phản hồi.")

        report.extend(recommendations)
        return "\n".join(report)

    @staticmethod
    async def generate_llm_summary(
        sprint_data: Dict[str, Any],
        provider: str,  # "gemini" or "openai"
        api_key: str,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Call external LLM API (Google Gemini or OpenAI) to generate a customized Scrum Master narrative."""
        if not api_key:
            return AIScrumMaster.generate_heuristic_summary(sprint_data)

        # Prepare context payload
        milestone = sprint_data.get("milestone", {})
        metrics = sprint_data.get("metrics", {})
        bottlenecks = sprint_data.get("bottlenecks", [])
        member_standup = sprint_data.get("member_standup", [])

        prompt_context = f"""
Bạn là một Senior Scrum Master dày dạn kinh nghiệm. Dưới đây là dữ liệu thực tế được quét từ GitHub Repository của Sprint hiện tại:
- Sprint / Milestone: {milestone.get('title')} (Trạng thái: {milestone.get('state')})
- Điểm sức khỏe Sprint: {metrics.get('health_score')}/100 ({metrics.get('health_badge')})
- Khối lượng: {metrics.get('completed_story_points')}/{metrics.get('total_story_points')} Story Points hoàn thành ({metrics.get('completion_rate')}%)
- Tổng số PR: {metrics.get('total_prs')} (Đã merge: {metrics.get('merged_prs')}, Đang mở: {metrics.get('open_prs')})
- Chu kỳ merge trung bình (Cycle time): {metrics.get('avg_cycle_time_hours')} giờ
- Số điểm nghẽn PR tồn đọng: {metrics.get('bottlenecks_count')}

Danh sách PR nghẽn (chờ review lâu hoặc có Changes Requested):
{bottlenecks[:5]}

Chi tiết hoạt động của các thành viên trong 24h qua (Standup):
{member_standup}

Nhiệm vụ của bạn:
Hãy viết một bản Báo cáo Tóm tắt Daily Standup & Đánh giá Sprint theo đúng văn phong Scrum Master chuyên nghiệp, sắc bén và xây dựng:
1. Đánh giá tốc độ và sức khỏe Sprint hiện tại (khen ngợi thành tích, chỉ rõ rủi ro).
2. Tóm tắt ai đã làm gì hôm qua, ai đang làm gì, ai đang bị nghẽn (nêu đích danh @username).
3. Nêu rõ các PR nghẽn và reviewer cần được nhắc nhở.
4. Đưa ra 3-4 lời khuyên hành động thiết thực cho team trong ngày hôm nay.

{f'Yêu cầu bổ sung từ người dùng: {custom_instructions}' if custom_instructions else ''}
Định dạng xuất ra: Markdown chuẩn có icon, tiêu đề rõ ràng, bảng biểu nếu cần.
"""

        try:
            if provider.lower() == "gemini":
                # Google Gemini API
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_context}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048},
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            return candidates[0]["content"]["parts"][0]["text"]
                    raise ValueError(f"Gemini API returned error {resp.status_code}: {resp.text}")

            elif provider.lower() == "openai":
                # OpenAI API
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an elite Agile Scrum Master."},
                        {"role": "user", "content": prompt_context},
                    ],
                    "temperature": 0.4,
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    raise ValueError(f"OpenAI API returned error {resp.status_code}: {resp.text}")

        except Exception as e:
            # Fallback seamlessly to Heuristic Engine with note
            fallback = AIScrumMaster.generate_heuristic_summary(sprint_data)
            return f"> ⚠️ *Không thể kết nối đến AI API ({str(e)}). Tự động chuyển sang AI Heuristic Engine nội bộ:*\n\n{fallback}"

        return AIScrumMaster.generate_heuristic_summary(sprint_data)
