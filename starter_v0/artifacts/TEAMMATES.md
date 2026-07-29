# Thành viên nhóm

| Thành viên | Mã sinh viên | Vai trò | Phần việc chính |
|---|---|---|---|
| Ngô Quang Anh | 2A202601106 | QA | Kiểm tra test case, rà soát log eval và verify kết quả v0-v3. |
| Nguyễn Việt Phong | 2A202601975 | Prompt | Cải tiến `system_prompt.md`, phân tích lỗi prompt qua từng version. |
| Lê Trọng Việt Dũng | 2A202601746 | Tool | Hoàn thiện tool/schema, kiểm tra routing và argument của tool. |
| Nguyễn Tuấn Đức | 2A202601380 | Product Architect | Điều phối kiến trúc agent, tổng hợp version, report và demo flow. |
| Lương Minh Quân | 2A202601308 | UI | Xây dựng giao diện demo, trực quan hóa case, chat history, memory và reasoning log. |

## Cách chia việc

- QA: chạy/đối chiếu eval base và group, kiểm tra log thật, phát hiện regression.
- Prompt: tối ưu prompt cho clarify, clean query, confirmation boundary và chống gọi tool sai phạm vi.
- Tool: bổ sung/hoàn thiện policy, arXiv, Telegram và đảm bảo khai báo tool khớp yêu cầu eval.
- UI: làm demo HTML/Flask hiển thị chat, test case, token, latency, cost và trace.
- Product Architect: giữ tổng thể bài lab nhất quán, chuẩn hóa báo cáo và chuẩn bị luồng demo cuối.
