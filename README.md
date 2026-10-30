# ⚡ GitScrum AI

> **Công cụ quét lịch sử hoạt động GitHub theo Sprint (Milestone) để tự động hóa báo cáo Daily Standup, đo lường Velocity và cảnh báo điểm nghẽn Pull Request cho các đội ngũ Agile / Scrum.**

![GitScrum AI Dashboard](https://img.shields.io/badge/Agile-Scrum-38bdf8?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-10b981?style=for-the-badge)
![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

---

## 🌟 Các Tính Năng Cốt Lõi

### 1. ☀️ Tự Động Hóa Daily Standup (3 Cột Chuẩn Scrum)
- Tự động quét và phân loại hoạt động trong **24 giờ qua** (hoặc **72 giờ** nếu chạy vào Thứ Hai để gộp cả hoạt động cuối tuần).
- Nhóm thông tin theo từng thành viên trong team:
  - **✅ Đã Xong Hôm Qua:** Các Pull Request đã merge, Issue đã đóng, Commit đã push.
  - **⚡ Đang Làm Hôm Nay:** Các PR đang mở, Issue được phân công.
  - **🚨 Vướng Mắc (Blockers):** PR bị tồn đọng >48h chưa ai review, PR có trạng thái *Changes Requested*, hoặc Issue có nhãn `blocked`.
- **1-Click Copy:** Sao chép nội dung đã định dạng chuẩn Markdown để dán ngay vào kênh chat của team (Slack, Discord, MS Teams).

### 2. 🚨 Bottleneck Radar (Radar Cảnh Báo Điểm Nghẽn)
- Phát hiện các PR bị "ngâm" quá lâu trong hàng đợi review:
  - 🟡 **Warning:** PR mở > 24 giờ chưa được review / merge.
  - 🔴 **Critical:** PR mở > 48 giờ (kèm hiệu ứng cảnh báo nhấp nháy).
  - ⚠️ **Changes Requested:** Đã có reviewer yêu cầu sửa đổi nhưng chưa được cập nhật.
- Liệt kê cụ thể reviewer được phân công để Scrum Master dễ dàng nhắc nhở.

### 3. 📈 Đo Lường Velocity & Vận Tốc Sprint
- Trích xuất **Story Points** tự động từ nhãn Issue/PR:
  - Hỗ trợ định dạng số: `sp:3`, `points:5`, `pts:8`, `estimate:2`.
  - Hỗ trợ T-shirt size: `size:s` (2 SP), `size:m` (3 SP), `size:l` (5 SP), `size:xl` (8 SP).
  - Hỗ trợ cú pháp trong tiêu đề: `[5sp]` hoặc `[3 points]`.
- Tính toán **PR Cycle Time**: Đo thời gian trung bình từ lúc mở PR đến khi được merge.
- Tính toán **Sprint Health Score (0 - 100)**: Đánh giá độ rủi ro sprint dựa trên tiến độ so với thời gian và số lượng blocker.

### 4. 🤖 AI Scrum Master (Hybrid Engine)
- **Heuristic Engine (Mặc định):** Phân tích thuật toán thông minh, chạy **100% offline, miễn phí, tức thì**, không cần token bên ngoài.
- **LLM Engine Tùy Chọn:** Cho phép cắm API Key của **Google Gemini** (`gemini-1.5-flash`) hoặc **OpenAI** (`gpt-4o-mini`) để tạo nhận xét sâu sắc theo văn phong Scrum Master chuyên nghiệp.

### 5. 🔔 Gửi Báo Cáo Trực Tiếp Qua Webhook
- Hỗ trợ bắn báo cáo Daily Standup và Sprint Update tới:
  - **Slack:** Định dạng Block Kit với thanh trạng thái màu sắc.
  - **Discord:** Định dạng Embed sang trọng.
  - **Telegram:** Gửi trực tiếp vào nhóm qua Telegram Bot API.

### 6. 🎨 Giao Diện Glassmorphism Cao Cấp
- Thiết kế Dark Theme hiện đại, phong cách bảng điều khiển công nghệ cao (`#060911` kết hợp neon cyan, emerald, amber, rose).
- Biểu đồ tương tác thời gian thực với **Chart.js** (Phân bổ công việc Donut, Tiến độ Story Points Bar chart).
- Lưu trữ cấu hình (Token, Webhook, Repo) an toàn trong `localStorage` trình duyệt.

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### Yêu Cầu
- Python 3.9 trở lên
- Trình duyệt web hiện đại (Chrome, Edge, Firefox, Safari)

### Bước 1: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 2: Khởi chạy ứng dụng
Chạy script khởi động 1-click (tự động kiểm tra gói và mở trình duyệt):
```bash
python run.py
```
Hoặc khởi chạy trực tiếp bằng Uvicorn:
```bash
uvicorn app:app --port 8000 --reload
```

Sau khi khởi chạy, truy cập vào giao diện web tại: **`http://localhost:8000`**

---

## 🎮 Thử Nghiệm Ngay Với Chế Độ Demo

Nếu chưa có GitHub Token hoặc chưa tạo Milestone trên GitHub:
1. Mở trang web `http://localhost:8000`.
2. Bấm nút **🎮 Nạp Dữ Liệu Demo** ở góc phải hoặc trên banner chào mừng.
3. Toàn bộ KPI, biểu đồ tiến độ, ma trận thành viên và báo cáo AI Scrum Master sẽ hiển thị ngay lập tức với dữ liệu mô phỏng thực tế.

---

## 📖 Cách Sử Dụng Với Repo GitHub Thực Tế

1. **Nhập Tên Repo:** Nhập định dạng `owner/repo` (ví dụ: `facebook/react`, `fastapi/tiangolo` hoặc repo nội bộ của công ty).
2. **Tìm Milestones:** Bấm nút **Tìm Milestones**. Hệ thống sẽ tải danh sách các Milestone tương ứng với các Sprint.
3. **Cấu Hình GitHub Token (Khuyến khích):**
   - Mặc định, GitHub giới hạn 60 yêu cầu/giờ cho tài khoản ẩn danh.
   - Bấm vào nút **🔑 GitHub Token** ở thanh trên cùng và dán token cá nhân của bạn (Classic PAT hoặc Fine-grained PAT) để tăng giới hạn lên **5,000 yêu cầu/giờ** và quét được cả **Private Repo**.
   - *Lưu ý: Token chỉ được lưu trong LocalStorage trên trình duyệt của bạn, không gửi về bất kỳ máy chủ bên thứ ba nào.*
4. **Quét Sprint:** Chọn Milestone mong muốn và bấm **🚀 Quét Sprint**.
5. **Chia Sẻ Báo Cáo:**
   - Bấm **📋 Copy cho Slack / Discord** để lấy văn bản dán vào nhóm chat.
   - Hoặc bấm **📤 Gửi Webhook** để bắn tự động vào kênh của team.

---

## 🧪 Chạy Kiểm Thử Tự Động (Unit Tests)

Dự án đi kèm bộ test toàn diện kiểm tra giải thuật trích xuất Story Points, phân loại Standup, phát hiện điểm nghẽn và định dạng Webhook:

```bash
python test_engine.py
```

Kết quả mong đợi:
```
.....
----------------------------------------------------------------------
Ran 5 tests in 0.012s

OK
```

---

## 📂 Cấu Trúc Dự Án

```
githubnotify/
├── app.py                 # FastAPI backend server & REST API routes
├── github_scanner.py      # Module quét GitHub REST API (Milestones, PRs, Issues, Commits)
├── agile_engine.py        # Engine tính toán Agile/Scrum (Standup, Velocity, Bottlenecks, Health Score)
├── ai_summary.py          # AI Scrum Master (Heuristic Engine & LLM Gemini/OpenAI)
├── notifier.py            # Module định dạng và bắn thông báo Webhook (Slack, Discord, Telegram)
├── test_engine.py         # Bộ kiểm thử tự động toàn diện
├── run.py                 # Script khởi chạy 1-click
├── requirements.txt       # Danh sách thư viện phụ thuộc
├── static/
│   ├── index.html         # Giao diện Web Dashboard (HTML5 semantic)
│   ├── style.css          # Hệ thống giao diện Glassmorphism Dark Theme
│   └── app.js             # Logic xử lý giao diện, Chart.js & LocalStorage
└── README.md              # Tài liệu hướng dẫn sử dụng
```

---

## 📄 Quy Ước Nhãn Đề Xuất Cho Team (Best Practices)

Để GitScrum AI hoạt động hiệu quả nhất, khuyến khích team áp dụng các quy ước sau trên GitHub:
- **Tạo Milestone cho mỗi Sprint:** Đặt tên dạng `Sprint 24 (20/10 - 03/11)` và gán hạn chót `due_on`.
- **Gán nhãn Story Points vào Issue / PR:** Ví dụ nhãn `sp:1`, `sp:2`, `sp:3`, `sp:5`, `sp:8` hoặc viết `[3sp]` trong tiêu đề.
- **Gán nhãn khi bị tắc:** Sử dụng nhãn `blocked` hoặc `waiting` cho các task đang chờ bên thứ ba hoặc phụ thuộc team khác.

---

*Phát triển với tinh thần Agile & Tự động hóa quy trình phát triển phần mềm.*
