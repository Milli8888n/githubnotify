/**
 * GitScrum AI - Client Application Logic
 * Manages GitHub API scanning, Chart.js rendering, Daily Standup 3-columns,
 * AI Scrum Master synthesis, LocalStorage persistence, and Webhook dispatch.
 */

// --- State Store ---
const AppState = {
    ghToken: localStorage.getItem("gitscrum_gh_token") || "",
    repo: localStorage.getItem("gitscrum_last_repo") || "",
    milestones: [],
    selectedMilestone: null,
    sprintData: null,
    charts: {
        statusDonut: null,
        spBar: null,
    },
    aiSettings: {
        provider: localStorage.getItem("gitscrum_ai_provider") || "heuristic",
        apiKey: localStorage.getItem("gitscrum_ai_key") || "",
        customPrompt: localStorage.getItem("gitscrum_ai_prompt") || "",
    },
    webhookSettings: {
        platform: localStorage.getItem("gitscrum_webhook_platform") || "slack",
        url: localStorage.getItem("gitscrum_webhook_url") || "",
        telegramToken: localStorage.getItem("gitscrum_telegram_token") || "",
        telegramChatId: localStorage.getItem("gitscrum_telegram_chat_id") || "",
    },
};

// --- DOM Element References ---
const DOM = {
    // Inputs & Controls
    inputRepo: document.getElementById("input-repo"),
    btnFetchMilestones: document.getElementById("btn-fetch-milestones"),
    selectMilestone: document.getElementById("select-milestone"),
    btnScanSprint: document.getElementById("btn-scan-sprint"),
    btnDemoMode: document.getElementById("btn-demo-mode"),
    btnWelcomeDemo: document.getElementById("btn-welcome-demo"),

    // Rate limit & strip
    rateLimitBadge: document.getElementById("rate-limit-badge"),
    rateLimitText: document.getElementById("rate-limit-text"),
    currentRepoInfo: document.getElementById("current-repo-info"),
    activeRepoName: document.getElementById("active-repo-name"),
    activeMilestoneName: document.getElementById("active-milestone-name"),
    welcomeBox: document.getElementById("welcome-box"),
    metricsGrid: document.getElementById("metrics-grid"),
    tabsContainer: document.getElementById("tabs-container"),

    // KPI Elements
    healthGaugeVal: document.getElementById("health-gauge-val"),
    healthBadge: document.getElementById("health-badge"),
    metricSpVal: document.getElementById("metric-sp-val"),
    metricCompletionPct: document.getElementById("metric-completion-pct"),
    metricProgressFill: document.getElementById("metric-progress-fill"),
    metricCycleTime: document.getElementById("metric-cycle-time"),
    metricMembersCount: document.getElementById("metric-members-count"),
    metricPrsMerged: document.getElementById("metric-prs-merged"),
    metricBottlenecksCount: document.getElementById("metric-bottlenecks-count"),
    metricBottleneckLabel: document.getElementById("metric-bottleneck-label"),
    tabPillBottlenecks: document.getElementById("tab-pill-bottlenecks"),

    // Tab Panels
    standupMembersGrid: document.getElementById("standup-members-grid"),
    standupWindowDesc: document.getElementById("standup-window-desc"),
    tbodyBottlenecks: document.getElementById("tbody-bottlenecks"),
    tbodyMembers: document.getElementById("tbody-members"),
    aiContentBody: document.getElementById("ai-content-body"),
    aiLoadingState: document.getElementById("ai-loading-state"),

    // Stats mini
    statTotalItems: document.getElementById("stat-total-items"),
    statTotalPrs: document.getElementById("stat-total-prs"),
    statClosedIssues: document.getElementById("stat-closed-issues"),
    statReviewTime: document.getElementById("stat-review-time"),

    // Actions
    btnCopyStandupSlack: document.getElementById("btn-copy-standup-slack"),
    btnSendStandupWebhook: document.getElementById("btn-send-standup-webhook"),
    btnRegenAI: document.getElementById("btn-regen-ai"),
    btnCopyAIMarkdown: document.getElementById("btn-copy-ai-markdown"),

    // Modals
    modalToken: document.getElementById("modal-token"),
    btnTokenModal: document.getElementById("btn-token-modal"),
    tokenStatusText: document.getElementById("token-status-text"),
    inputGhToken: document.getElementById("input-gh-token"),
    btnSaveToken: document.getElementById("btn-save-token"),
    btnClearToken: document.getElementById("btn-clear-token"),

    modalAI: document.getElementById("modal-ai"),
    btnAIModal: document.getElementById("btn-ai-modal"),
    selectAIProvider: document.getElementById("select-ai-provider"),
    groupAIKey: document.getElementById("group-ai-key"),
    inputAIKey: document.getElementById("input-ai-key"),
    inputCustomPrompt: document.getElementById("input-custom-prompt"),
    btnSaveAI: document.getElementById("btn-save-ai"),

    modalWebhook: document.getElementById("modal-webhook"),
    btnWebhookModal: document.getElementById("btn-webhook-modal"),
    selectWebhookPlatform: document.getElementById("select-webhook-platform"),
    groupWebhookUrl: document.getElementById("group-webhook-url"),
    inputWebhookUrl: document.getElementById("input-webhook-url"),
    groupTelegramFields: document.getElementById("group-telegram-fields"),
    inputTelegramToken: document.getElementById("input-telegram-token"),
    inputTelegramChatId: document.getElementById("input-telegram-chat-id"),
    webhookPreviewText: document.getElementById("webhook-preview-text"),
    btnDispatchWebhook: document.getElementById("btn-dispatch-webhook"),

    toastContainer: document.getElementById("toast-container"),
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    initSettingsUI();
    initEventListeners();
    checkRateLimit();

    // Auto-fill previous repo if stored
    if (AppState.repo) {
        DOM.inputRepo.value = AppState.repo;
    }
});

function initSettingsUI() {
    // Token badge update
    if (AppState.ghToken) {
        DOM.tokenStatusText.textContent = "Token Đã Lưu (Authed)";
        DOM.inputGhToken.value = AppState.ghToken;
    } else {
        DOM.tokenStatusText.textContent = "GitHub Token (Chưa nhập)";
    }

    // AI Settings populate
    DOM.selectAIProvider.value = AppState.aiSettings.provider;
    DOM.inputAIKey.value = AppState.aiSettings.apiKey;
    DOM.inputCustomPrompt.value = AppState.aiSettings.customPrompt;
    toggleAIKeyVisibility();

    // Webhook Settings populate
    DOM.selectWebhookPlatform.value = AppState.webhookSettings.platform;
    DOM.inputWebhookUrl.value = AppState.webhookSettings.url;
    DOM.inputTelegramToken.value = AppState.webhookSettings.telegramToken;
    DOM.inputTelegramChatId.value = AppState.webhookSettings.telegramChatId;
    toggleWebhookPlatformFields();

    // Query server .env defaults
    loadServerConfig();
}

async function loadServerConfig() {
    try {
        const res = await fetch("/api/config");
        if (res.ok) {
            const cfg = await res.json();
            if (cfg.has_github_token && !AppState.ghToken) {
                DOM.tokenStatusText.textContent = "Token Đã Cấu Hình (.env)";
            }
            if (cfg.default_repo && !DOM.inputRepo.value) {
                DOM.inputRepo.value = cfg.default_repo;
                AppState.repo = cfg.default_repo;
            }
            if (cfg.slack_webhook_url && !DOM.inputWebhookUrl.value) {
                DOM.inputWebhookUrl.value = cfg.slack_webhook_url;
            }
            if (cfg.has_gemini_key && !AppState.aiSettings.apiKey) {
                DOM.selectAIProvider.value = "gemini";
                toggleAIKeyVisibility();
            }
        }
    } catch {
        // Fallback silently if offline
    }
}

function initEventListeners() {
    // Tab switching
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetId = btn.getAttribute("data-tab");
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) targetPanel.classList.add("active");
        });
    });

    // Modal triggers
    DOM.btnTokenModal.addEventListener("click", () => openModal(DOM.modalToken));
    DOM.btnAIModal.addEventListener("click", () => openModal(DOM.modalAI));
    DOM.btnWebhookModal.addEventListener("click", () => {
        updateWebhookPreview();
        openModal(DOM.modalWebhook);
    });

    document.querySelectorAll(".modal-close").forEach(el => {
        el.addEventListener("click", () => {
            const targetId = el.getAttribute("data-close");
            const modal = document.getElementById(targetId);
            if (modal) closeModal(modal);
        });
    });

    // Close modal on click outside
    document.querySelectorAll(".modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) closeModal(overlay);
        });
    });

    // Token save/clear
    DOM.btnSaveToken.addEventListener("click", handleSaveToken);
    DOM.btnClearToken.addEventListener("click", handleClearToken);

    // AI save
    DOM.selectAIProvider.addEventListener("change", toggleAIKeyVisibility);
    DOM.btnSaveAI.addEventListener("click", handleSaveAI);

    // Webhook settings save & dispatch
    DOM.selectWebhookPlatform.addEventListener("change", () => {
        toggleWebhookPlatformFields();
        updateWebhookPreview();
    });
    DOM.btnDispatchWebhook.addEventListener("click", handleDispatchWebhook);

    // Fetch milestones
    DOM.btnFetchMilestones.addEventListener("click", handleFetchMilestones);
    DOM.inputRepo.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleFetchMilestones();
    });

    // Milestone selection change
    DOM.selectMilestone.addEventListener("change", (e) => {
        const val = e.target.value;
        DOM.btnScanSprint.disabled = !val;
    });

    // Scan Sprint
    DOM.btnScanSprint.addEventListener("click", handleScanSprint);

    // Demo triggers
    DOM.btnDemoMode.addEventListener("click", handleLoadDemo);
    DOM.btnWelcomeDemo.addEventListener("click", handleLoadDemo);

    // Copy actions
    DOM.btnCopyStandupSlack.addEventListener("click", handleCopyStandup);
    DOM.btnSendStandupWebhook.addEventListener("click", () => {
        updateWebhookPreview();
        openModal(DOM.modalWebhook);
    });
    DOM.btnRegenAI.addEventListener("click", handleRegenerateAI);
    DOM.btnCopyAIMarkdown.addEventListener("click", handleCopyAIMarkdown);
}

// --- Rate Limit Checker ---
async function checkRateLimit() {
    try {
        const url = AppState.ghToken
            ? `/api/rate-limit?token=${encodeURIComponent(AppState.ghToken)}`
            : "/api/rate-limit";
        const res = await fetch(url);
        if (res.ok) {
            const data = await res.json();
            const dot = DOM.rateLimitBadge.querySelector(".status-dot");
            const rem = data.remaining;
            const lim = data.limit;

            if (rem <= 5) {
                dot.className = "status-dot red";
            } else if (rem <= 20) {
                dot.className = "status-dot amber";
            } else {
                dot.className = "status-dot green";
            }

            DOM.rateLimitText.textContent = `GitHub API: ${rem}/${lim} còn lại (Reset: ${data.reset_time.split(" ")[1] || "UTC"})`;
        }
    } catch {
        DOM.rateLimitText.textContent = "GitHub API: Ngoại tuyến hoặc lỗi mạng";
    }
}

// --- Fetch Milestones Handler ---
async function handleFetchMilestones() {
    const rawRepo = DOM.inputRepo.value.trim().replace(/^https?:\/\/github\.com\//, "").replace(/\/$/, "");
    if (!rawRepo || !rawRepo.includes("/")) {
        showToast("Vui lòng nhập định dạng repository chuẩn 'owner/repo' (vd: facebook/react)", "error");
        return;
    }

    const [owner, repo] = rawRepo.split("/");
    AppState.repo = `${owner}/${repo}`;
    localStorage.setItem("gitscrum_last_repo", AppState.repo);

    DOM.btnFetchMilestones.disabled = true;
    DOM.btnFetchMilestones.innerHTML = `<span class="loader-spinner"></span>`;
    DOM.selectMilestone.disabled = true;
    DOM.selectMilestone.innerHTML = `<option value="">Đang tải danh sách milestones...</option>`;

    try {
        let url = `/api/milestones?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}&state=all`;
        if (AppState.ghToken) {
            url += `&token=${encodeURIComponent(AppState.ghToken)}`;
        }

        const res = await fetch(url);
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || "Không thể tải milestones.");
        }

        AppState.milestones = data.milestones || [];

        if (AppState.milestones.length === 0) {
            DOM.selectMilestone.innerHTML = `<option value="">Repo này chưa có Milestone (Sprint) nào trên GitHub</option>`;
            DOM.btnScanSprint.disabled = true;
            showToast(`Repository '${rawRepo}' hiện không có Milestone nào. Hãy tạo Milestone trên GitHub trước.`, "info");
        } else {
            let options = `<option value="">-- Chọn 1 Milestone để quét (${AppState.milestones.length} tìm thấy) --</option>`;
            AppState.milestones.forEach(m => {
                const stateEmoji = m.state === "open" ? "🟢" : "⚪";
                const totalIssues = (m.open_issues || 0) + (m.closed_issues || 0);
                const dueText = m.due_on ? `(Hạn: ${m.due_on.substring(0, 10)})` : "(Không có hạn chót)";
                options += `<option value="${m.number}">${stateEmoji} ${m.title} ${dueText} [${totalIssues} tasks]</option>`;
            });
            DOM.selectMilestone.innerHTML = options;
            DOM.selectMilestone.disabled = false;
            showToast(`Đã tìm thấy ${AppState.milestones.length} milestones cho ${rawRepo}!`, "success");
        }

        checkRateLimit();
    } catch (err) {
        DOM.selectMilestone.innerHTML = `<option value="">Lỗi: ${err.message}</option>`;
        showToast(err.message, "error");
    } finally {
        DOM.btnFetchMilestones.disabled = false;
        DOM.btnFetchMilestones.innerHTML = `<span>Tìm Milestones</span>`;
    }
}

// --- Scan Sprint Handler ---
async function handleScanSprint() {
    const milestoneNumber = parseInt(DOM.selectMilestone.value, 10);
    if (!milestoneNumber) return;

    const [owner, repo] = AppState.repo.split("/");
    const btnText = DOM.btnScanSprint.querySelector(".btn-text");
    const spinner = DOM.btnScanSprint.querySelector(".loader-spinner");

    DOM.btnScanSprint.disabled = true;
    btnText.textContent = "Đang quét...";
    spinner.style.display = "inline-block";

    try {
        const payload = {
            owner: owner,
            repo: repo,
            milestone_number: milestoneNumber,
            token: AppState.ghToken || null,
        };

        const res = await fetch("/api/scan-sprint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const result = await res.json();
        if (!res.ok) {
            throw new Error(result.detail || "Lỗi quét sprint.");
        }

        AppState.sprintData = result.data;
        populateDashboard(AppState.sprintData, `${owner}/${repo}`);
        showToast(`Quét thành công Sprint: ${AppState.sprintData.milestone.title}!`, "success");

        // Automatically trigger heuristic AI summary in background
        triggerAISummary();
        checkRateLimit();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.btnScanSprint.disabled = false;
        btnText.textContent = "Quét Sprint";
        spinner.style.display = "none";
    }
}

// --- Load Demo Handler ---
async function handleLoadDemo() {
    showToast("Đang nạp dữ liệu Sprint Demo mẫu...", "info");
    try {
        const res = await fetch("/api/demo");
        const result = await res.json();
        if (res.ok) {
            AppState.sprintData = result.data;
            populateDashboard(AppState.sprintData, result.repository);
            triggerAISummary();
            showToast("Đã nạp thành công dữ liệu mẫu Sprint 14 Checkout Overhaul!", "success");
        }
    } catch (err) {
        showToast("Không thể nạp dữ liệu demo: " + err.message, "error");
    }
}

// --- Populate Full Dashboard ---
function populateDashboard(data, repoDisplayName) {
    // Show views
    DOM.welcomeBox.style.display = "none";
    DOM.metricsGrid.style.display = "grid";
    DOM.tabsContainer.style.display = "block";
    DOM.currentRepoInfo.style.display = "block";
    DOM.activeRepoName.textContent = repoDisplayName;
    DOM.activeMilestoneName.textContent = data.milestone.title;

    // 1. Render KPIs
    const metrics = data.metrics;
    DOM.healthGaugeVal.textContent = metrics.health_score;
    DOM.healthBadge.textContent = metrics.health_badge;

    // Health color tinting
    if (metrics.health_score >= 80) {
        DOM.healthGaugeVal.style.color = "var(--accent-emerald)";
        DOM.healthBadge.className = "badge-status";
    } else if (metrics.health_score >= 55) {
        DOM.healthGaugeVal.style.color = "var(--accent-amber)";
        DOM.healthBadge.className = "badge-status";
        DOM.healthBadge.style.color = "var(--accent-amber)";
        DOM.healthBadge.style.borderColor = "var(--accent-amber)";
    } else {
        DOM.healthGaugeVal.style.color = "var(--accent-rose)";
        DOM.healthBadge.className = "badge-status";
        DOM.healthBadge.style.color = "var(--accent-rose)";
        DOM.healthBadge.style.borderColor = "var(--accent-rose)";
    }

    DOM.metricSpVal.textContent = `${metrics.completed_story_points} / ${metrics.total_story_points} SP`;
    DOM.metricCompletionPct.textContent = `${metrics.completion_rate}%`;
    DOM.metricProgressFill.style.width = `${metrics.completion_rate}%`;

    DOM.metricCycleTime.textContent = metrics.avg_cycle_time_hours > 0 ? `${metrics.avg_cycle_time_hours}h` : "N/A";
    DOM.metricMembersCount.textContent = data.member_standup.length;
    DOM.metricPrsMerged.textContent = `${metrics.merged_prs} / ${metrics.total_prs} PRs đã merge`;

    DOM.metricBottlenecksCount.textContent = metrics.bottlenecks_count;
    DOM.tabPillBottlenecks.textContent = metrics.bottlenecks_count;
    DOM.metricBottleneckLabel.textContent = metrics.critical_bottlenecks_count > 0 
        ? `${metrics.critical_bottlenecks_count} PR critical` 
        : (metrics.bottlenecks_count > 0 ? `${metrics.bottlenecks_count} PR warning` : "0 PR nghẽn");

    // Mini stats
    DOM.statTotalItems.textContent = metrics.total_items;
    DOM.statTotalPrs.textContent = metrics.total_prs;
    DOM.statClosedIssues.textContent = metrics.closed_items - metrics.merged_prs;
    DOM.statReviewTime.textContent = metrics.avg_review_turnaround_hours > 0 ? `${metrics.avg_review_turnaround_hours}h` : "N/A";

    // 2. Render Tabs
    renderStandupTab(data);
    renderOverviewCharts(data);
    renderBottlenecksTable(data.bottlenecks);
    renderMembersTable(data.member_standup);
}

// --- Tab 1: Render Daily Standup ---
function renderStandupTab(data) {
    const windowInfo = data.standup_window || {};
    DOM.standupWindowDesc.textContent = `Khung thời gian hoạt động: ${windowInfo.hours} giờ qua ${windowInfo.is_monday ? '(Gộp cuối tuần + Thứ 6)' : ''}`;

    const members = data.member_standup || [];
    if (members.length === 0) {
        DOM.standupMembersGrid.innerHTML = `
            <div class="glass-inner text-center py-5 text-muted">
                Chưa ghi nhận hoạt động nào của thành viên trong Milestone này.
            </div>`;
        return;
    }

    let html = "";
    members.forEach(m => {
        const avatarHtml = m.avatar 
            ? `<img src="${m.avatar}" class="member-avatar" alt="${m.username}">`
            : `<div class="member-avatar-placeholder">${m.username.substring(0, 2).toUpperCase()}</div>`;

        // Column 1: Done
        let doneHtml = "";
        if (m.done && m.done.length > 0) {
            doneHtml = `<ul class="item-list">` + m.done.map(item => `
                <li>
                    <span class="item-badge ${item.points > 0 ? 'badge-pts' : ''}">${item.points > 0 ? item.points + 'SP' : '#' + item.number}</span>
                    <a href="${item.url || '#'}" target="_blank" class="item-link">${escapeHtml(item.title)}</a>
                </li>
            `).join("") + `</ul>`;
        } else {
            doneHtml = `<div class="empty-col-text">Chưa có PR/Issue nào đóng trong 24h qua</div>`;
        }

        // Column 2: In Progress
        let inProgHtml = "";
        if (m.in_progress && m.in_progress.length > 0) {
            inProgHtml = `<ul class="item-list">` + m.in_progress.map(item => `
                <li>
                    <span class="item-badge ${item.points > 0 ? 'badge-pts' : ''}">${item.points > 0 ? item.points + 'SP' : '#' + item.number}</span>
                    <a href="${item.url || '#'}" target="_blank" class="item-link">${escapeHtml(item.title)}</a>
                </li>
            `).join("") + `</ul>`;
        } else {
            inProgHtml = `<div class="empty-col-text">Hiện không có task nào đang mở</div>`;
        }

        // Column 3: Blockers
        let blockersHtml = "";
        if (m.blockers && m.blockers.length > 0) {
            blockersHtml = `<ul class="item-list">` + m.blockers.map(item => `
                <li>
                    <span class="item-badge" style="background: rgba(244, 63, 94, 0.2); color: var(--accent-rose);">#${item.number}</span>
                    <a href="${item.url || '#'}" target="_blank" class="item-link" style="color: var(--accent-rose);">${escapeHtml(item.title)}</a>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">⚠️ ${escapeHtml(item.reason)}</div>
                </li>
            `).join("") + `</ul>`;
        } else {
            blockersHtml = `<div class="empty-col-text" style="color: var(--accent-emerald);">Không có vướng mắc</div>`;
        }

        html += `
        <div class="standup-member-card">
            <div class="member-header">
                <div class="member-profile">
                    ${avatarHtml}
                    <div class="member-username">@${escapeHtml(m.username)}</div>
                </div>
                <div class="member-meta-stats">
                    <span>${m.stats.merged_prs} PRs Merged</span>
                    <span>•</span>
                    <span>${m.stats.open_prs} PRs Mở</span>
                    <span>•</span>
                    <span>${m.stats.commits} Commits</span>
                    <span>•</span>
                    <span style="color: var(--accent-emerald); font-weight: 700;">${m.stats.story_points} SP</span>
                </div>
            </div>
            <div class="standup-columns-3">
                <div class="column-box">
                    <div class="column-title done">✅ Đã Xong (${m.done.length})</div>
                    ${doneHtml}
                </div>
                <div class="column-box">
                    <div class="column-title in-prog">⚡ Đang Làm (${m.in_progress.length})</div>
                    ${inProgHtml}
                </div>
                <div class="column-box">
                    <div class="column-title blockers">🚨 Vướng Mắc (${m.blockers.length})</div>
                    ${blockersHtml}
                </div>
            </div>
        </div>`;
    });

    DOM.standupMembersGrid.innerHTML = html;
}

// --- Tab 2: Render Overview Charts ---
function renderOverviewCharts(data) {
    const metrics = data.metrics;

    // Destroy prior charts
    if (AppState.charts.statusDonut) AppState.charts.statusDonut.destroy();
    if (AppState.charts.spBar) AppState.charts.spBar.destroy();

    // 1. Donut Chart
    const ctxDonut = document.getElementById("chart-status-donut").getContext("2d");
    AppState.charts.statusDonut = new Chart(ctxDonut, {
        type: "doughnut",
        data: {
            labels: ["PR Merged", "PR Đang Mở", "Issues Đã Đóng", "Issues Đang Mở"],
            datasets: [{
                data: [
                    metrics.merged_prs,
                    metrics.open_prs,
                    Math.max(metrics.closed_items - metrics.merged_prs, 0),
                    Math.max(metrics.open_items - metrics.open_prs, 0),
                ],
                backgroundColor: [
                    "#10b981", // Emerald
                    "#38bdf8", // Cyan
                    "#6366f1", // Indigo
                    "#f59e0b", // Amber
                ],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#94a3b8", font: { family: "Inter", size: 12 } }
                }
            },
            cutout: "70%",
        }
    });

    // 2. Story Points Bar Chart
    const ctxBar = document.getElementById("chart-sp-bar").getContext("2d");
    AppState.charts.spBar = new Chart(ctxBar, {
        type: "bar",
        data: {
            labels: ["Hoàn thành (Done)", "Đang thực hiện (In Progress)", "Tổng kế hoạch"],
            datasets: [{
                label: "Story Points",
                data: [
                    metrics.completed_story_points,
                    metrics.in_progress_story_points,
                    metrics.total_story_points,
                ],
                backgroundColor: [
                    "#10b981",
                    "#38bdf8",
                    "rgba(255, 255, 255, 0.15)",
                ],
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94a3b8", font: { family: "JetBrains Mono" } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#94a3b8", font: { family: "Inter", size: 11 } }
                }
            }
        }
    });
}

// --- Tab 3: Render Bottlenecks Table ---
function renderBottlenecksTable(bottlenecks) {
    if (!bottlenecks || bottlenecks.length === 0) {
        DOM.tbodyBottlenecks.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4" style="color: var(--accent-emerald);">
                    🎉 Tuyệt vời! Không phát hiện PR nào bị nghẽn (>24h) hoặc bị Changes Requested.
                </td>
            </tr>`;
        return;
    }

    let html = "";
    bottlenecks.forEach(b => {
        const pillClass = b.severity === "critical" ? "pill-critical" : "pill-warning";
        const pillText = b.severity === "critical" ? "Critical (>48h)" : "Warning (>24h)";
        const reviewers = b.requested_reviewers && b.requested_reviewers.length > 0
            ? b.requested_reviewers.map(r => `<span class="item-badge">@${escapeHtml(r)}</span>`).join(" ")
            : `<span class="text-muted" style="font-size: 11px;">Chưa phân công</span>`;

        html += `
        <tr>
            <td><span class="${pillClass}">${pillText}</span></td>
            <td>
                <a href="${b.html_url}" target="_blank" class="item-link" style="font-weight: 600;">
                    #${b.number} ${escapeHtml(b.title)}
                </a>
            </td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${b.author_avatar ? `<img src="${b.author_avatar}" style="width: 20px; height: 20px; border-radius: 50%;">` : ''}
                    <span>@${escapeHtml(b.author)}</span>
                </div>
            </td>
            <td><strong>${Math.round(b.age_hours)} giờ</strong></td>
            <td><span style="color: ${b.severity === 'critical' ? 'var(--accent-rose)' : 'var(--accent-amber)'};">${escapeHtml(b.reason)}</span></td>
            <td>${reviewers}</td>
        </tr>`;
    });

    DOM.tbodyBottlenecks.innerHTML = html;
}

// --- Tab 4: Render Members Table ---
function renderMembersTable(members) {
    if (!members || members.length === 0) {
        DOM.tbodyMembers.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">Chưa có dữ liệu.</td></tr>`;
        return;
    }

    let html = "";
    members.forEach(m => {
        html += `
        <tr>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${m.avatar ? `<img src="${m.avatar}" style="width: 24px; height: 24px; border-radius: 50%;">` : ''}
                    <strong>@${escapeHtml(m.username)}</strong>
                </div>
            </td>
            <td><span style="color: var(--accent-emerald); font-weight: 700;">${m.stats.merged_prs}</span></td>
            <td><span>${m.stats.open_prs}</span></td>
            <td><span style="font-family: var(--font-mono);">${m.stats.commits}</span></td>
            <td><span style="color: var(--primary-cyan); font-weight: 700;">${m.stats.story_points} SP</span></td>
            <td>${m.done.length} việc đóng</td>
            <td>${m.blockers.length > 0 ? `<span style="color: var(--accent-rose); font-weight: 700;">${m.blockers.length} vướng</span>` : '<span style="color: var(--text-dim);">0</span>'}</td>
        </tr>`;
    });

    DOM.tbodyMembers.innerHTML = html;
}

// --- Tab 5: Trigger AI Scrum Master Summary ---
async function triggerAISummary() {
    if (!AppState.sprintData) return;

    DOM.aiLoadingState.style.display = "flex";
    DOM.aiContentBody.innerHTML = "";

    try {
        const payload = {
            sprint_data: AppState.sprintData,
            provider: AppState.aiSettings.provider,
            api_key: AppState.aiSettings.apiKey || null,
            custom_prompt: AppState.aiSettings.customPrompt || null,
        };

        const res = await fetch("/api/ai-summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const result = await res.json();
        if (res.ok && result.summary) {
            DOM.aiContentBody.innerHTML = marked.parse(result.summary);
            AppState.lastAISummary = result.summary;
        } else {
            DOM.aiContentBody.innerHTML = `<p class="text-muted">Không thể tạo nhận xét: ${result.detail || 'Lỗi không xác định'}</p>`;
        }
    } catch (err) {
        DOM.aiContentBody.innerHTML = `<p class="text-muted">Lỗi gọi AI: ${err.message}</p>`;
    } finally {
        DOM.aiLoadingState.style.display = "none";
    }
}

function handleRegenerateAI() {
    showToast("Đang tái tạo báo cáo AI Scrum Master...", "info");
    triggerAISummary();
}

// --- Copy Actions ---
function handleCopyStandup() {
    if (!AppState.sprintData) {
        showToast("Chưa có dữ liệu để copy.", "error");
        return;
    }
    const markdown = formatStandupForClipboard(AppState.sprintData);
    navigator.clipboard.writeText(markdown).then(() => {
        showToast("Đã copy báo cáo Daily Standup định dạng Slack/Discord vào clipboard!", "success");
    }).catch(err => {
        showToast("Lỗi copy: " + err.message, "error");
    });
}

function handleCopyAIMarkdown() {
    if (!AppState.lastAISummary) {
        showToast("Chưa có báo cáo AI để copy.", "error");
        return;
    }
    navigator.clipboard.writeText(AppState.lastAISummary).then(() => {
        showToast("Đã copy toàn bộ báo cáo AI Scrum Master (Markdown)!", "success");
    }).catch(err => {
        showToast("Lỗi copy: " + err.message, "error");
    });
}

function formatStandupForClipboard(data) {
    const lines = [];
    lines.push(`*DAILY STANDUP — ${data.milestone.title}*`);
    lines.push(`Tiến độ: ${data.metrics.completion_rate}% (${data.metrics.completed_story_points}/${data.metrics.total_story_points} SP) | Sức khỏe: ${data.metrics.health_score}/100 (${data.metrics.health_badge})`);
    lines.push("");

    if (data.bottlenecks && data.bottlenecks.length > 0) {
        lines.push(`*🚨 CẢNH BÁO NGHẼN:*`);
        data.bottlenecks.slice(0, 3).forEach(b => {
            lines.push(`• PR #${b.number} (${b.title}) chờ ${Math.round(b.age_hours)}h — ${b.reason}`);
        });
        lines.push("");
    }

    lines.push(`*👥 THÀNH VIÊN:*`);
    data.member_standup.forEach(m => {
        lines.push(`*@${m.username}:*`);
        const doneStr = m.done.length > 0 ? m.done.map(d => `#${d.number} ${d.title}`).slice(0, 2).join(", ") : "Không có task đóng";
        const inProgStr = m.in_progress.length > 0 ? m.in_progress.map(p => `#${p.number} ${p.title}`).slice(0, 2).join(", ") : "Đang chờ task";
        lines.push(`  • Xong: ${doneStr}`);
        lines.push(`  • Đang làm: ${inProgStr}`);
        if (m.blockers && m.blockers.length > 0) {
            lines.push(`  • ⚠️ Blocker: ${m.blockers.map(bl => '#' + bl.number + ' ' + bl.reason).join(", ")}`);
        }
        lines.push("");
    });

    return lines.join("\n");
}

// --- Webhook Dispatch ---
function updateWebhookPreview() {
    if (!AppState.sprintData) {
        DOM.webhookPreviewText.textContent = "Chưa có dữ liệu sprint. Vui lòng quét repo hoặc bấm 'Nạp Dữ Liệu Demo' trước.";
        return;
    }
    DOM.webhookPreviewText.textContent = formatStandupForClipboard(AppState.sprintData);
}

async function handleDispatchWebhook() {
    if (!AppState.sprintData) {
        showToast("Chưa có dữ liệu sprint để gửi.", "error");
        return;
    }

    const platform = DOM.selectWebhookPlatform.value;
    const webhookUrl = DOM.inputWebhookUrl.value.trim();
    const tgToken = DOM.inputTelegramToken.value.trim();
    const tgChat = DOM.inputTelegramChatId.value.trim();

    if (platform !== "telegram" && !webhookUrl) {
        showToast("Vui lòng nhập Webhook URL.", "error");
        return;
    }
    if (platform === "telegram" && (!tgToken || !tgChat)) {
        showToast("Vui lòng nhập Telegram Bot Token và Chat ID.", "error");
        return;
    }

    // Persist settings
    AppState.webhookSettings = { platform, url: webhookUrl, telegramToken: tgToken, telegramChatId: tgChat };
    localStorage.setItem("gitscrum_webhook_platform", platform);
    localStorage.setItem("gitscrum_webhook_url", webhookUrl);
    localStorage.setItem("gitscrum_telegram_token", tgToken);
    localStorage.setItem("gitscrum_telegram_chat_id", tgChat);

    DOM.btnDispatchWebhook.disabled = true;
    DOM.btnDispatchWebhook.innerHTML = `<span class="loader-spinner"></span> Đang gửi...`;

    try {
        const payload = {
            platform: platform,
            webhook_url: webhookUrl || null,
            telegram_token: tgToken || null,
            telegram_chat_id: tgChat || null,
            sprint_data: AppState.sprintData,
        };

        const res = await fetch("/api/send-webhook", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const result = await res.json();
        if (res.ok) {
            showToast(`Gửi báo cáo tới ${platform.toUpperCase()} thành công!`, "success");
            closeModal(DOM.modalWebhook);
        } else {
            throw new Error(result.detail || "Gửi webhook thất bại.");
        }
    } catch (err) {
        showToast("Lỗi gửi webhook: " + err.message, "error");
    } finally {
        DOM.btnDispatchWebhook.disabled = false;
        DOM.btnDispatchWebhook.innerHTML = `<span>🚀 Bắn Báo Cáo Ngay</span>`;
    }
}

// --- Settings Modals Logic ---
function handleSaveToken() {
    const token = DOM.inputGhToken.value.trim();
    AppState.ghToken = token;
    if (token) {
        localStorage.setItem("gitscrum_gh_token", token);
        DOM.tokenStatusText.textContent = "Token Đã Lưu (Authed)";
        showToast("Đã lưu token! Đang kiểm tra lại giới hạn rate limit...", "success");
    } else {
        localStorage.removeItem("gitscrum_gh_token");
        DOM.tokenStatusText.textContent = "GitHub Token (Chưa nhập)";
        showToast("Đã xóa token cá nhân.", "info");
    }
    checkRateLimit();
    closeModal(DOM.modalToken);
}

function handleClearToken() {
    DOM.inputGhToken.value = "";
    handleSaveToken();
}

function toggleAIKeyVisibility() {
    const prov = DOM.selectAIProvider.value;
    DOM.groupAIKey.style.display = prov === "heuristic" ? "none" : "block";
}

function handleSaveAI() {
    AppState.aiSettings.provider = DOM.selectAIProvider.value;
    AppState.aiSettings.apiKey = DOM.inputAIKey.value.trim();
    AppState.aiSettings.customPrompt = DOM.inputCustomPrompt.value.trim();

    localStorage.setItem("gitscrum_ai_provider", AppState.aiSettings.provider);
    localStorage.setItem("gitscrum_ai_key", AppState.aiSettings.apiKey);
    localStorage.setItem("gitscrum_ai_prompt", AppState.aiSettings.customPrompt);

    showToast("Đã lưu cấu hình AI!", "success");
    closeModal(DOM.modalAI);

    if (AppState.sprintData) {
        triggerAISummary();
    }
}

function toggleWebhookPlatformFields() {
    const platform = DOM.selectWebhookPlatform.value;
    if (platform === "telegram") {
        DOM.groupWebhookUrl.style.display = "none";
        DOM.groupTelegramFields.style.display = "block";
    } else {
        DOM.groupWebhookUrl.style.display = "block";
        DOM.groupTelegramFields.style.display = "none";
    }
}

function openModal(modalEl) {
    if (modalEl) modalEl.style.display = "flex";
}

function closeModal(modalEl) {
    if (modalEl) modalEl.style.display = "none";
}

// --- Toast Notification Helper ---
function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icon = type === "success" ? "✅" : (type === "error" ? "❌" : "ℹ️");
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(20px)";
        toast.style.transition = "all 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
