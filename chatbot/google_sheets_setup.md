# Hướng Dẫn Kết Nối Google Sheets

## Bước 1 — Tạo Service Account trên Google Cloud

1. Truy cập [console.cloud.google.com](https://console.cloud.google.com)
2. Tạo project mới (hoặc chọn project có sẵn)
3. Vào **APIs & Services → Library**, tìm và bật:
   - **Google Sheets API**
   - **Google Drive API**
4. Vào **APIs & Services → Credentials**
5. Nhấn **Create Credentials → Service Account**
6. Đặt tên (ví dụ: `chatbot-service`), nhấn **Done**
7. Click vào Service Account vừa tạo → tab **Keys**
8. Nhấn **Add Key → Create new key → JSON**
9. File JSON sẽ tự động tải về — **đổi tên thành `credentials.json`**
10. Đặt file vào thư mục gốc của project (cùng cấp với `app/`)

```
chatbot/
├── credentials.json   ← đặt ở đây
├── app/
└── ...
```

> ⚠️ **QUAN TRỌNG**: Thêm `credentials.json` vào `.gitignore` — KHÔNG commit file này lên Git!

---

## Bước 2 — Chia sẻ Google Sheet với Service Account

1. Mở file `credentials.json`, tìm trường `"client_email"`:
   ```
   "client_email": "chatbot-service@your-project.iam.gserviceaccount.com"
   ```
2. Mở Google Sheet của bạn
3. Nhấn nút **Share** (Chia sẻ)
4. Paste email service account vào ô email
5. Đặt quyền **Viewer** (chỉ đọc) hoặc **Editor** (nếu cần ghi)
6. Nhấn **Send**

---

## Bước 3 — Lấy Sheet ID

Mở Google Sheet, nhìn vào URL:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                      Đây là SHEET_ID
```

Điền vào file `.env`:
```env
SHEET_CUSTOMERS_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
SHEET_PRODUCTS_ID=...
SHEET_FAQ_ID=...
```

---

## Bước 4 — Định dạng Sheet khuyến nghị

### Sheet Khách Hàng
| Tên | Email | Số điện thoại | Địa chỉ | Ghi chú |
|-----|-------|--------------|---------|---------|
| Nguyễn Văn A | a@email.com | 0901234567 | Hà Nội | VIP |

### Sheet Sản Phẩm / Dịch Vụ
| Tên sản phẩm | Mô tả | Giá | Danh mục | Tình trạng |
|-------------|-------|-----|---------|-----------|
| Gói Basic | Hỗ trợ 24/7 | 500,000 | Dịch vụ | Còn hàng |

### Sheet FAQ
| Câu hỏi | Trả lời |
|---------|---------|
| Giờ làm việc? | 8:00 - 17:30, Thứ 2 - Thứ 6 |
| Chính sách đổi trả? | Trong vòng 30 ngày... |

> Row đầu tiên **phải là header** (tên cột). Chatbot sẽ tự đọc tất cả các cột.

---

## Kiểm tra kết nối

Sau khi cài đặt xong, chạy server và gọi API:

```bash
# Kiem tra ket noi va sync
curl -X POST http://localhost:8000/api/v1/sheets/sync

# Xem du lieu khach hang
curl http://localhost:8000/api/v1/sheets/customers

# Xem FAQ
curl http://localhost:8000/api/v1/sheets/faq
```

Hoặc vào giao diện web: `http://localhost:8000` → nhấn nút **🔄 Sync**
