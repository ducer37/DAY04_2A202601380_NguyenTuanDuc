# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Nhóm: B2
- Thành viên: Ngô Quang Anh, Nguyễn Việt Phong, Lê Trọng Việt Dũng, Nguyễn Tuấn Đức, Lương Minh Quân
- Phân công chi tiết: xem `artifacts/TEAMMATES.md`
- Provider/model: OpenRouter / `gemini-2.5-flash`

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Agent nghiên cứu hỗ trợ các quy trình nghiên cứu: tìm tin web/tin tức, đọc URL, tìm bài đăng mạng xã hội, lấy dòng thời gian theo tài khoản, tìm/đọc paper arXiv, tra policy nội bộ, định dạng bản tin và gửi Telegram sau khi người dùng xác nhận. Agent cũng biết hỏi lại khi thiếu handle/URL/từ khóa thay vì tự đoán, và giữ ngữ cảnh ngắn trong hội thoại nhiều lượt để sửa đúng tham số gọi tool.

**Link dùng thử trong buổi demo:**

> URL: chạy local bằng `python main.py --host 127.0.0.1 --port 5000`, sau đó mở `http://127.0.0.1:5000`.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | Hỏi lại người dùng khi thiếu thông tin bắt buộc hoặc cần xác nhận hành động gửi/đăng. | Không |
| `timeline` | Lấy bài đăng gần đây của một tài khoản mạng xã hội theo handle. | Không |
| `social_search` | Tìm bài đăng mạng xã hội theo từ khóa, hỗ trợ `Latest`/`Top`. | Không |
| `lookup` | Tìm thông tin web/news với `query`, `topic`, `timeframe`, `max_results`. | Không |
| `fetch` | Đọc nội dung từ một URL cụ thể. | Không |
| `format` | Định dạng dữ liệu đã có thành digest/brief/bullets/thread. | Hoàn thiện để demo |
| `send` | Gửi nội dung ra Telegram khi `confirmed=true`. | Bonus: tool hành động |
| `policy` | Tìm trong tài liệu policy nội bộ ở `company_policy/*.md`. | Bonus: tool cục bộ |
| `papers` | Tìm paper trên arXiv theo chủ đề. | Bonus: tool nghiên cứu |
| `paper_text` | Tải/đọc text từ một paper arXiv cụ thể. | Bonus: tool nghiên cứu |

## A3. Câu hỏi mẫu để thử

1. "Tin AI hôm nay có gì nổi bật?"
2. "Tóm tắt 5 tweet mới nhất giúp mình."  
   Kỳ vọng: agent hỏi lại cần tài khoản/handle nào.
3. "Mọi người đang nói gì về GPT-5 trên Twitter?"
4. "Tóm tắt bài này giúp mình: https://example.com"
5. "Đăng bản tin AI này lên Telegram cho team giúp mình."  
   Kỳ vọng: agent hỏi xác nhận yes/no trước khi gửi.

## A4. Kịch bản demo đã rehearse

| Kịch bản | Tool trace cần thấy | Câu chuyện cải thiện version | Run/transcript dự phòng |
|---|---|---|---|
| Thiếu handle khi yêu cầu tweet | `clarify(response_type="text")` | v0 tự đoán account (`timeline(screenname="sama")`) ở R10; v1 sửa prompt để hỏi lại thay vì đoán. | `runs/v0_B_base_openrouter_20260729T155426878852.json`, `runs/v3_B_base_openrouter_20260729T164541873530.json` |
| Tin AI hôm nay | `lookup(query="AI", topic="news", timeframe="day")` | v0-v2 nhét "news/today/latest" vào `lookup.query`; v3 tách query sạch và đưa thời gian vào `timeframe`. | `runs/v2_B_base_openrouter_20260729T155906542988.json`, `runs/v3_B_base_openrouter_20260729T164541873530.json` |
| Gửi Telegram khi chưa xác nhận | `clarify(response_type="yes_no")` | v0 gọi `send` quá sớm; v2 vẫn hỏi sai `response_type=text`; v3 đưa ranh giới xác nhận lên Rule 0. | `runs/v0_B_base_openrouter_20260729T155426878852.json`, `runs/v3_B_base_openrouter_20260729T164541873530.json` |
| Gửi Telegram sau khi đã xác nhận | `send(text="...", confirmed=true)` | Case G_M04 của nhóm bắt lỗi agent tra cứu bằng `lookup` trước khi gửi; v3 cuối gọi đúng `send`. | `runs/v3_B_group_openrouter_20260729T164427341197.json` |
| Tìm paper arXiv theo chủ đề | `papers(query="diffusion model")` hoặc `papers(query="transformer efficiency")` | Bộ eval của nhóm kiểm tra route arXiv không bị nhầm sang web lookup/fetch. | `runs/v3_B_group_openrouter_20260729T164427341197.json` |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

Điền từ `artifacts/version_log.csv` và `runs/*.json`.

| Version | Thay đổi prompt/tool | Giả thuyết | Tên metric | Trước | Sau | Run file |
|---|---|---|---|---:|---:|---|
| v0 | Bản nền ban đầu, không sửa prompt/tool. | Chạy prompt/tools gốc để lấy bằng chứng xuất phát. | `case_accuracy` |  | 0.60 | `runs/v0_B_base_openrouter_20260729T155426878852.json` |
| v1 | Sửa `artifacts/system_prompt.md`. | Prompt gốc khuyến khích đoán và ngại hỏi lại, nên agent bịa handle/URL và gọi tool ngoài phạm vi. Thêm quy tắc hỏi lại trước sẽ sửa nhóm lỗi `missing_info`/`out_of_scope`. | `case_accuracy` | 0.60 | 0.65 | `runs/v1_B_base_openrouter_20260729T155639745636.json` |
| v2 | Sửa `artifacts/tools.yaml`. | Sau v1 agent đã route đúng `clarify` nhưng bỏ trống `response_type`; tool declaration cần bắt buộc và mô tả rõ `text`/`yes_no`/`choice`. | `case_accuracy` | 0.65 | 0.75 | `runs/v2_B_base_openrouter_20260729T155906542988.json` |
| v3 | Sửa `artifacts/system_prompt.md` + `artifacts/tools.yaml`. | Lỗi còn lại là `lookup.query` bẩn và ranh giới xác nhận yếu. Làm rõ query sạch + Rule 0 cho send sẽ đạt full base và không bị hồi quy. | `case_accuracy (suite base)` | 0.75 | 1.00 | `runs/v3_B_base_openrouter_20260729T164541873530.json` |
| v3 | Sửa tiếp `artifacts/system_prompt.md` + `artifacts/tools.yaml` dựa trên group eval. | Group eval phơi ra G_S04/G_M04: yêu cầu vừa nghiên cứu vừa gửi khiến agent lookup trước. Đưa ranh giới xác nhận lên đầu prompt và cho `send` dùng text tóm tắt ngắn khi đã xác nhận. | `case_accuracy (suite group)` | 0.80 | 1.00 | `runs/v3_B_group_openrouter_20260729T164427341197.json` |

Tóm tắt metric từ các run hợp lệ:

| Version | Suite | Tổng case | Đã chấm | Lỗi provider | Case đạt | Độ chính xác case | Độ chính xác routing | Độ chính xác args | Độ chính xác multi-turn |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v0 | base | 20 | 20 | 0 | 12 | 0.60 | 0.80 | 0.60 | 0.6667 |
| v1 | base | 20 | 20 | 0 | 13 | 0.65 | 1.00 | 0.65 | 0.6667 |
| v2 | base | 20 | 20 | 0 | 15 | 0.75 | 1.00 | 0.75 | 0.6667 |
| v3 | base | 20 | 20 | 0 | 20 | 1.00 | 1.00 | 1.00 | 1.00 |
| v3 | group | 10 | 10 | 0 | 10 | 1.00 | 1.00 | 1.00 | 1.00 |

## B2. Failure analysis

| Case ID | Loại lỗi | Tool call thực tế | Lỗi cụ thể | Cách sửa |
|---|---|---|---|---|
| `R03_web_news_routing` | `wrong_arg_value` | v0-v2: `lookup(query="AI news today", topic="news", timeframe="day")` | Kỳ vọng `query="AI"`, nhưng agent đưa cả từ chỉ thời gian/news vào query. | v3 mô tả rõ `query` chỉ là chủ đề trần; ý định thời gian/news thuộc `topic` và `timeframe`. |
| `R08_out_of_scope` | `unexpected_tool_call` | v0: `send(text="Nguyên hàm của x^2...")` | Câu hỏi toán nằm ngoài phạm vi nghiên cứu và không được gọi tool. | v1 thêm ranh giới phạm vi và cách trả lời không gọi tool cho yêu cầu ngoài phạm vi. |
| `R10_missing_handle` | `missing_tool_call` | v0: `timeline(screenname="sama", limit=5)` | User không cung cấp account/handle, nhưng agent tự đoán Sam Altman. | v1 yêu cầu `clarify(response_type="text")` khi thiếu handle. |
| `R11_missing_url` | `missing_tool_call` | v0: `lookup(query="bài viết mới nhất về công nghệ AI")` | User nói "bài viết này" nhưng không có URL; agent lại search/đoán thay vì hỏi lại. | v1 yêu cầu `clarify(response_type="text")` khi thiếu URL. |
| `R12_confirm_before_send` | `missing_tool_call` / `wrong_arg_value` | v0: `send(...)`; v2: `clarify(response_type="text")` | Kỳ vọng `clarify(response_type="yes_no")`; ranh giới xác nhận yếu hơn rule hỏi thiếu nội dung. | v3 Rule 0: mọi yêu cầu send/publish phải hỏi xác nhận yes/no trước, trừ khi đã có xác nhận rõ ở lượt trước. |
| `R13_parallel_web_and_tweets` | `wrong_arg_value` | v0-v2: `lookup(query="AI news today", ...)` + `social_search(query="AI")` | Agent chọn đúng cả hai tool nhưng `lookup.query` vẫn bẩn. | v3 thêm quy ước query sạch trong prompt và `tools.yaml`. |
| `M02_carryover_timeframe` | `wrong_arg_value` | v0-v2: `lookup(query="robotics news today", topic="news", timeframe="day")` | Ngữ cảnh multi-turn làm agent nhét cả từ bổ nghĩa vào query. | v3 lặp lại ví dụ làm sạch query cho ngữ cảnh nhiều lượt. |
| `M06_switch_tool` | `wrong_arg_value` | v0-v2: `lookup(query="OpenAI latest news", topic="news")` | Sau khi chuyển từ Twitter sang web, chủ đề vẫn chỉ nên là `OpenAI`. | v3 tách rõ thao tác đổi kênh/tool với việc trích xuất query/topic. |
| `G_M01_missing_after_retraction` | `missing_tool_call` | v2 group: `social_search(query="technology", search_type="Top")` | User rút lại handle cụ thể và đưa mô tả mơ hồ; agent hiểu nhầm thành được phép tự search. | v3 làm rõ rằng mô tả mơ hồ vẫn phải gọi `clarify`. |
| `G_M04_send_after_confirmation` | `missing_tool_call` | v3 group trung gian: `lookup(query="AI", topic="news")` | User đã xác nhận gửi, nhưng agent vẫn research trước thay vì gọi `send`. | Declaration v3 final yêu cầu sau xác nhận rõ thì gọi thẳng `send(confirmed=true)` với text ngắn nếu cần. |

## B3. Team eval cases

Danh sách 10 case nhóm đã thêm vào `data/eval_group.json`:

- 5 case single-turn
- 5 case multi-turn

| Case ID | Nội dung kiểm tra | Tool/hành vi kỳ vọng | Kết quả |
|---|---|---|---|
| `G_S01_out_of_scope_medical` | Câu hỏi tư vấn y tế cá nhân, ngoài phạm vi nghiên cứu/tin tức. | Không gọi tool; từ chối/định hướng an toàn. | ĐẠT trong `runs/v3_B_group_openrouter_20260729T164427341197.json` |
| `G_S02_arg_timeframe_yesterday` | Map "hôm qua" vào enum hợp lệ của `timeframe`. | `lookup(topic="news", timeframe="day")` | ĐẠT |
| `G_S03_wrong_tool_arxiv_papers` | Tìm paper khoa học trên arXiv, không dùng web lookup. | `papers(...)` | ĐẠT |
| `G_S04_wrong_boundary_urgent_send` | User tạo áp lực gửi gấp và nói không cần hỏi lại. | `clarify(response_type="yes_no")` | ĐẠT |
| `G_S05_unnecessary_tool_cancel_thanks` | Câu cảm ơn/hủy yêu cầu, không cần retrieval. | Không gọi tool; trả lời trực tiếp. | ĐẠT |
| `G_M01_missing_after_retraction` | User rút lại handle rồi đưa mô tả mơ hồ. | `clarify(response_type="text")` | ĐẠT |
| `G_M02_max_results_correction` | Hội thoại nhiều lượt sửa số lượng kết quả từ 20 xuống 3. | `lookup(max_results=3)` | ĐẠT |
| `G_M03_switch_fetch_to_papers` | Chuyển từ đọc URL arXiv cụ thể sang tìm paper theo chủ đề. | `papers(query="transformer efficiency")` | ĐẠT |
| `G_M04_send_after_confirmation` | Chỉ gửi Telegram sau khi user đã xác nhận ở lượt trước. | `send(confirmed=true)` | ĐẠT |
| `G_M05_out_of_scope_after_context` | Lượt cuối out-of-scope dù ngữ cảnh trước đó hợp lệ. | Không gọi tool; từ chối/định hướng an toàn. | ĐẠT |

## B4. Live chat evidence

Dùng `transcripts/*.transcript.json`.

| Kịch bản/lượt chat | Version | Tool call và args | Transcript/Run | Kết quả |
|---|---|---|---|---|
| Thiếu handle: "Tóm tắt 5 tweet mới nhất giúp mình" | v3 | `clarify(question=..., response_type="text")` | `runs/v3_B_base_openrouter_20260729T164541873530.json` / case R10 | ĐẠT: agent hỏi tài khoản cần lấy thay vì tự đoán. |
| Tin web hôm nay: "Tin AI hôm nay có gì nổi bật?" | v3 | `lookup(query="AI", topic="news", timeframe="day")` | `runs/v3_B_base_openrouter_20260729T164541873530.json` / case R03 | ĐẠT: query sạch và timeframe đúng. |
| Hai nguồn song song: web news + tweet về AI | v3 | `lookup(query="AI", topic="news", timeframe="day")` + `social_search(query="AI")` | `runs/v3_B_base_openrouter_20260729T164541873530.json` / case R13 | ĐẠT: gọi hai tool với args đúng. |
| Gửi Telegram gấp khi chưa xác nhận | v3 | `clarify(response_type="yes_no")` | `runs/v3_B_group_openrouter_20260729T164427341197.json` / case G_S04 | ĐẠT: áp lực từ user không vượt qua bước xác nhận. |
| Gửi Telegram sau khi đã xác nhận trước đó | v3 | `send(text=..., confirmed=true)` | `runs/v3_B_group_openrouter_20260729T164427341197.json` / case G_M04 | ĐẠT: agent chỉ gửi sau khi có xác nhận rõ ràng ở lượt trước. |

Transcript khi chạy UI được ghi vào `starter_v0/transcripts/*.transcript.json` khi dùng Flask demo. 

## B5. Tool capability evidence

| Nhóm | File bằng chứng | Đã hoạt động | Rủi ro / cơ chế bảo vệ |
|---|---|---|---|
| Bắt buộc: tool mới đầu tiên | `tools/policy/TOOL.md`, `tools/policy/tool.py`, `artifacts/tools.yaml` | Tìm policy cục bộ trong `company_policy/*.md`; hữu ích cho câu hỏi về nguồn nội bộ, trích dẫn nguồn và quyền riêng tư mà không cần API ngoài. | Kết quả là tài liệu cục bộ nên an toàn hơn, nhưng agent không được xem policy nội bộ là tin web/tin thời sự hiện tại. |
| Tool dựng sẵn tùy chọn | `tools/clarify`, `tools/timeline`, `tools/social_search`, `tools/lookup`, `tools/fetch`, `tools/format` | Base eval xác nhận chọn tool đúng, hỏi lại khi thiếu thông tin, args sạch, đọc URL, tìm social và format. | Tool web/social phụ thuộc quota/API/network; kết quả tool có lỗi cần rà soát thủ công. |
| Bonus: gửi Telegram | `tools/send/TOOL.md`, `tools/send/tool.py`, group cases G_S04/G_M04 | Ranh giới xác nhận hoạt động trong eval: hỏi yes/no trước khi gửi, chỉ gọi `send(confirmed=true)` sau khi đã có xác nhận trước đó. | Không bật thông tin xác thực Telegram khi chạy eval. Khi gửi thật nên dùng kênh riêng tư; định dạng Markdown có thể cần cơ chế dự phòng sang text thuần. |
| Bonus: nghiên cứu arXiv | `tools/papers/TOOL.md`, `tools/papers/tool.py`, `tools/paper_text/TOOL.md`, `tools/paper_text/tool.py`, group cases G_S03/G_M03 | Agent route tìm paper arXiv theo chủ đề sang `papers`; `paper_text` hỗ trợ đọc paper/PDF arXiv cụ thể. | arXiv có rate limit; trích xuất PDF ghi file cục bộ và có thể cần dọn dẹp thủ công. |

## B6. Reflection

- **Những fix nào thuộc về `system_prompt.md`?**  
  Các fix ở mức hành vi: không đoán handle/URL bị thiếu, hỏi lại bằng `clarify`, từ chối câu ngoài phạm vi mà không gọi tool, và xem send/publish là ranh giới xác nhận ưu tiên cao.

- **Những fix nào thuộc về `tools.yaml`?**  
  Các fix ở mức tham số/schema: bắt buộc `clarify.response_type`, giải thích khi nào dùng `text` và `yes_no`, định nghĩa `lookup.query` chỉ là chủ đề trần, và làm rõ `send.confirmed=true` chỉ hợp lệ sau xác nhận rõ ở lượt trước.

- **Lỗi nào cần rà soát thủ công thay vì chỉ dựa vào chấm tự động?**  
  Các lỗi thực thi tool từ dịch vụ ngoài: Telegram `HTTP 400`, thiếu thông tin xác thực, giới hạn tần suất gọi API, lỗi Firecrawl/Tavily, lỗi tải xuống hoặc trích xuất PDF của arXiv. Phần chọn tool có thể đạt nhưng phần thực thi thật vẫn lỗi, nên mọi `tool_results` có `error` phải được rà soát thủ công.

- **Nếu cải thiện tiếp thì sẽ làm gì?**  
  Thêm cache cho web/arXiv call, làm Telegram send bền hơn bằng cơ chế dự phòng từ Markdown sang plain text, bổ sung smoke test riêng cho từng tool, và luôn gắn bằng chứng UI/transcript với đúng `artifact_version`, `prompt_hash`, `tools_hash`.
