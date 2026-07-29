---
name: send
track: bonus
kind: action
provider: Telegram Bot API
requires_env: [TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]
inputs: [text, confirmed]
outputs: [status, chars_sent, preview]
side_effect: true
---
# send

Gửi văn bản/bản tin lên kênh Telegram. Tool có side-effect thật — chỉ gửi khi `confirmed=True`.

### Luồng xác nhận BẮT BUỘC:
1. Agent nhận yêu cầu gửi/đăng → gọi `clarify(question="...", response_type="yes_no")`
2. User đồng ý → Agent gọi `send(text="...", confirmed=True)`
3. User từ chối → DỪNG, không gọi `send`

### Behavior khi `confirmed=False`:
- Tool trả về `status: needs_confirmation` và **KHÔNG gửi tin** — đây là guard an toàn.
- Không bao giờ gọi `send(confirmed=False)` — vô nghĩa và không có tác dụng.

### Constraints:
- Cần `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` trong `.env`
- Hỗ trợ Markdown trong `text` (parse_mode="Markdown")
- Max 4096 ký tự mỗi tin — tool sẽ tự truncate nếu vượt giới hạn
- Rate limit Telegram: 30 tin/giây

### Ví dụ:
```python
# ✅ Đúng: đã có xác nhận từ user
send(text="AI Daily: ...", confirmed=True)

# ❌ Sai: gọi trực tiếp không qua clarify trước
send(text="...", confirmed=False)  # sẽ không gửi
```
