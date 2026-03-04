# 📓 Lessons Learned — Nhật Ký Cải Tiến

> Ghi lại những thay đổi, bài học, và quyết định kỹ thuật theo từng ngày.
> Format: `## YYYY-MM-DD — Tiêu đề`

---

## 2026-03-03 — Khởi tạo dự án

### ✅ Đã làm
- Khởi tạo cấu trúc project FastAPI theo layered architecture (`api`, `core`, `services`, `models`, `utils`)
- Tích hợp Claude API qua `anthropic` SDK, hỗ trợ cả REST và WebSocket streaming
- Thay Redis bằng **SQLite + aiosqlite** — đơn giản hơn, không cần cài thêm service
- Thay Chroma server bằng **Chroma PersistentClient** — lưu file local, không cần Docker
- Tích hợp **Google Sheets** làm nguồn dữ liệu chính (khách hàng, sản phẩm, FAQ)
- Tự động sync Sheets → vector DB mỗi 5 phút qua background task
- Xây dựng **Web UI** (`app/static/index.html`) với streaming, quick replies, nút Sync

### 🧠 Bài học
- Chroma `PersistentClient` thay thế hoàn toàn `HttpClient` cho môi trường single-server — đơn giản hơn nhiều
- `aiosqlite` + SQLAlchemy async hoạt động tốt với FastAPI, không cần PostgreSQL cho quy mô nhỏ/vừa
- Nên dùng `upsert` thay `add` trong Chroma để tránh lỗi duplicate khi sync lại

### ⚠️ Cần theo dõi
- Chroma local chưa hỗ trợ tốt multi-process — nếu scale lên nhiều worker cần chuyển sang Chroma server
- Google Sheets API có giới hạn 300 requests/phút — cần cache kỹ nếu traffic cao

---

## Template cho ngày tiếp theo

```
## YYYY-MM-DD — Tiêu đề thay đổi

### ✅ Đã làm
-

### 🧠 Bài học
-

### 🐛 Bug đã fix
-

### ⚠️ Cần theo dõi
-

### 💡 Ý tưởng tiếp theo
-
```

---

*Cập nhật file này mỗi ngày cuối buổi làm việc.*
