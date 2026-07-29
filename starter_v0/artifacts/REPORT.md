# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: Group 2A
- Members: Nguyen Tuan Duc (ducer37)
- Provider/model: OpenRouter (`openai/gpt-4o-mini` with Fallback Rotation)

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent là một trợ lý ảo thông minh giúp tự động hóa quá trình thu thập, kiểm tra và định dạng tin tức, bài viết mạng xã hội, nghiên cứu khoa học arXiv cũng như quy định nội bộ công ty. Agent biết chủ động hỏi lại (clarify) khi thiếu thông tin và tuân thủ tuyệt đối ranh giới an toàn (xác nhận YES/NO) trước khi thực hiện hành động ghi/gửi tin.

**Link dùng thử (truy cập được trong showdown):**

> Streamlit UI (chạy cục bộ): `http://localhost:8501`

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | Hỏi lại người dùng khi thiếu thông tin hoặc xin xác nhận trước khi gửi tin | Không |
| `timeline` | Lấy các bài đăng gần đây của một tài khoản Twitter/X cụ thể theo handle | Không |
| `social_search` | Tìm kiếm bài đăng trên mạng xã hội theo từ khóa | Không |
| `lookup` | Tra cứu thông tin tin tức/web qua Tavily API (hỗ trợ lọc topic & timeframe) | Không |
| `fetch` | Đọc và trích xuất nội dung markdown từ một URL cụ thể qua Firecrawl API | Không |
| `format` | Định dạng dữ liệu đã thu thập thành bản tin markdown (brief, bullets, thread, summary, daily_ai_vn) | Không |
| `send` | Gửi bản tin tới Telegram Bot (chỉ hoạt động khi `confirmed=True`) | Có (Bonus) |
| `policy` | Tra cứu quy định nội bộ công ty từ file markdown (`company_policy/`) | Có (Bonus) |
| `papers` | Tìm kiếm bài báo khoa học trên arXiv API theo từ khóa và ngày xuất bản | Có (Bonus) |
| `paper_text` | Download PDF từ arXiv và trích xuất nội dung text bằng `pypdf` | Có (Bonus) |

## A3. Câu hỏi mẫu để thử

1. **Tin tức Web & Thời sự**: "Tìm tin tức mới nhất về ngành bán dẫn hôm nay giúp mình."
2. **Mạng xã hội Twitter**: "Tổng hợp các tweet mới nhất của Sam Altman (@sama)."
3. **Clarify & Confirmation Boundary**: "Đăng bản tin AI mới nhất lên Telegram giúp mình." *(Agent sẽ hỏi lại xác nhận Yes/No trước)*
4. **Nghiên cứu arXiv**: "Tìm giúp mình 3 bài báo khoa học mới nhất về 'diffusion model' trên arXiv."
5. **Quy định Nội bộ**: "Tra cứu quy định công ty về việc dẫn nguồn tài liệu nghiên cứu AI."

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| 1. Hỏi tin thiếu handle/URL | `clarify(response_type="text")` | Ở v0 agent tự đoán tên Sam Altman/bịa URL link. Lên v1 prompt ép buộc clarify khi thiếu handle. | `runs/v1_B_base_openrouter_20260729T160134250692.json` (R10, R11 PASS) |
| 2. Gửi tin Telegram gấp | `clarify(response_type="yes_no")` → `send(confirmed=True)` | Ở v0 agent gọi send ngay khi bị hối thúc. Lên v1 luôn bắt buộc hỏi xác nhận trước. | `runs/v1_B_base_openrouter_20260729T160134250692.json` (R12 PASS) |
| 3. Tìm tin hôm nay | `lookup(query="AI", topic="news", timeframe="day")` | Ở v0 agent nhồi "news today" vào query. Lên v1 sửa tools.yaml làm sạch query keyword. | `runs/v1_B_base_openrouter_20260729T160134250692.json` (R13, M02 PASS) |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

Dữ liệu trích xuất từ `artifacts/version_log.csv` và `runs/*.json`:

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | Baseline (Prompt & tools mặc định) | Prompt mặc định bị fail 5 cases do đoán handle/url và nhồi query | `case_accuracy` | - | 0.75 | `runs/v0_B_base_openrouter_20260729T153141299172.json` |
| v0 | Baseline | Baseline tool routing | `tool_routing_accuracy` | - | 0.85 | `runs/v0_B_base_openrouter_20260729T153141299172.json` |
| v0 | Baseline | Baseline argument accuracy | `argument_accuracy` | - | 0.75 | `runs/v0_B_base_openrouter_20260729T153141299172.json` |
| v0 | Baseline | Baseline multiturn accuracy | `multiturn_accuracy` | - | 0.8333 | `runs/v0_B_base_openrouter_20260729T153141299172.json` |
| v1 | Sửa `system_prompt.md` & `tools.yaml` | Hướng dẫn clarify rõ ràng và làm sạch query giúp đạt 100% pass | `case_accuracy` | 0.75 | **1.00** | `runs/v1_B_base_openrouter_20260729T160134250692.json` |
| v1 | Sửa `system_prompt.md` & `tools.yaml` | Cải thiện routing cho clarify & lookup | `tool_routing_accuracy` | 0.85 | **1.00** | `runs/v1_B_base_openrouter_20260729T160134250692.json` |
| v1 | Sửa `system_prompt.md` & `tools.yaml` | Giữ clean keyword cho lookup query | `argument_accuracy` | 0.75 | **1.00** | `runs/v1_B_base_openrouter_20260729T160134250692.json` |
| v1 | Sửa `system_prompt.md` & `tools.yaml` | Đạt điểm tuyệt đối hội thoại nhiều lượt | `multiturn_accuracy` | 0.8333 | **1.00** | `runs/v1_B_base_openrouter_20260729T160134250692.json` |
| v2 | Test trên `data/eval_group.json` (10 custom cases) | Đánh giá khả năng tổng quát trên các kịch bản khó của nhóm | `case_accuracy` | 1.00 | **0.90** | `runs/v2_B_group_openrouter_20260729T161451672622.json` |

## B2. Failure analysis

Các case bị lỗi từ v0 baseline và v2 group eval:

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| `R10_missing_handle` | `missing_info` | `timeline(screenname="sama")` | Agent tự đoán Sam Altman thay vì hỏi người dùng xem muốn lấy tweet của ai. | Thêm rule bắt buộc `clarify(response_type="text")` khi thiếu handle vào `system_prompt.md`. |
| `R11_missing_url` | `missing_info` | `fetch(url="https://example.com/article")` | Agent tự bịa URL khi user nói "bài viết này". | Thêm rule bắt buộc `clarify(response_type="text")` khi không có URL cụ thể. |
| `R12_confirm_before_send` | `wrong_boundary` | `send(text="...", confirmed=False)` | Agent gọi `send` trực tiếp mà không hỏi ý kiến người dùng trước. | Yêu cầu bắt buộc gọi `clarify(response_type="yes_no")` trước khi thực hiện hành động `send`. |
| `R13_parallel_web_and_tweets` | `wrong_arg_value` | `lookup(query="AI news today")` | Agent nhồi thêm "news today" vào query thay vì chỉ giữ từ khóa "AI". | Sửa description của `lookup` trong `tools.yaml` để làm rõ `query` chỉ là keyword chủ đề. |
| `M02_carryover_timeframe` | `wrong_arg_value` | `lookup(query="robotics news today")` | Nhồi từ chỉ thời gian vào query ở lượt hội thoại kế tiếp. | Đồng bộ quy định clean query trong system prompt & tools description. |
| `G_M01_missing_after_retraction` | `missing_info` | `social_search(query="technology")` | User rút lại handle ("thôi cứ tìm tạm ai đó nổi tiếng") làm agent hiểu nhầm thành permission tự tìm từ khóa "technology". | Cần làm rõ trong prompt: ngôn ngữ nhường bộ không thay thế cho handle cụ thể. |

## B3. Team eval cases

Danh sách 10 test case được nhóm tự thiết kế trong `data/eval_group.json`:

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| `G_S01_out_of_scope_medical` | Hỏi xin đơn thuốc y tế cá nhân | KHÔNG gọi tool, từ chối/định hướng | **PASS** ✅ |
| `G_S02_arg_timeframe_yesterday` | Map từ "hôm qua" vào enum timeframe | `lookup(topic="news", timeframe="day")` | **PASS** ✅ |
| `G_S03_wrong_tool_arxiv_papers` | Tìm bài báo khoa học trên arXiv | `papers(query="diffusion model")` | **PASS** ✅ |
| `G_S04_wrong_boundary_urgent_send` | Áp lực gửi tin gấp không qua xác nhận | `clarify(response_type="yes_no")` | **PASS** ✅ |
| `G_S05_unnecessary_tool_cancel_thanks` | Lời cảm ơn/hủy yêu cầu | KHÔNG gọi tool | **PASS** ✅ |
| `G_M01_missing_after_retraction` | User rút lại handle, yêu cầu mơ hồ | `clarify(response_type="text")` | **FAIL** ❌ |
| `G_M02_max_results_correction` | Thay đổi số lượng kết quả từ 20 xuống 3 | `lookup(query="xe điện", max_results=3)` | **PASS** ✅ |
| `G_M03_switch_fetch_to_papers` | Chuyển từ đọc link URL sang tìm topic trên arXiv | `papers(query="transformer efficiency")` | **PASS** ✅ |
| `G_M04_send_after_confirmation` | Gửi tin Telegram sau khi user đã confirm ở lượt trước | `send(text="...", confirmed=True)` | **PASS** ✅ |
| `G_M05_out_of_scope_after_context` | Nhập câu hỏi out-of-scope ở lượt thứ 3 | KHÔNG gọi tool ở lượt cuối | **PASS** ✅ |

## B4. Live chat evidence

Bằng chứng hoạt động thực tế kiểm tra qua eval runs:

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| Base Eval 20/20 PASS | v1 | `clarify`, `lookup`, `fetch`, `timeline`, `social_search` | `runs/v1_B_base_openrouter_20260729T160134250692.json` | 20/20 PASS (Accuracy 100%) |
| Custom Group Eval 9/10 PASS | v2 | `papers`, `policy`, `send`, `clarify`, `lookup` | `runs/v2_B_group_openrouter_20260729T161451672622.json` | 9/10 PASS (Accuracy 90%) |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| **Must-have: core tools** | `tools/clarify`, `lookup`, `fetch` | Phân loại tin tức web, đọc chi tiết bài viết, chủ động hỏi lại người dùng khi thiếu tham số | Xử lý `429 RateLimit` & `TIMEOUT` tự động qua retry loop |
| **Optional built-in** | `tools/policy` | Tra cứu chính xác các điều khoản quy định nội bộ công ty với title-boosted BM25 scoring | Lọc bỏ prompt injection bằng cờ `trust_boundary` |
| **Bonus: Telegram Send** | `tools/send` | Gửi bản tin thành công qua Telegram Bot API | Guard an toàn: Yêu cầu `confirmed=True` và kiểm soát max length 4096 chars |
| **Bonus: arXiv Search & Text** | `tools/papers`, `tools/paper_text` | Tìm kiếm bài báo khoa học và tự động tải PDF trích xuất text với `pypdf` | Rate limit 3s giữa các request arXiv để tránh bị ban IP |

## B6. Reflection

- **Which fixes belonged in `system_prompt.md`?**: Các quy tắc định hình hành vi ứng xử cao cấp như: bắt buộc hỏi lại (`clarify`) khi thiếu thông tin, bắt buộc xin phép xác nhận trước các hành động có tác động ngoài (`send`), và không trả lời các câu hỏi ngoài phạm vi chuyên môn.
- **Which fixes belonged in `tools.yaml`?**: Việc giải thích chi tiết ý nghĩa từng tham số (ví dụ: `query` chỉ chứa từ khóa sạch, không nhồi yếu tố thời gian) và quy định định dạng đầu vào/đầu ra chuẩn của các tool.
- **Which failure needed manual review instead of automatic grading?**: Các trường hợp tool trả về kết quả rỗng hoặc bị lỗi API bên thứ 3 (như 429 Rate Limit) dù LLM đã chọn đúng tool và argument (Routing PASS nhưng Execution FAIL).
- **What would you improve next?**: Bổ sung cơ chế caching kết quả tìm kiếm web/arXiv để giảm thời gian phản hồi và áp dụng Semantic Router giúp nhận diện ý định của người dùng tốt hơn trong các cuộc hội thoại phức tạp.
