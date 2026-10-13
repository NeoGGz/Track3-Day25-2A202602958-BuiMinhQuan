# Lab 25B — Report

**Họ tên / nhóm:** Bui Minh Quan — **MSV:** 2A202602958  
**Commit:** a3f9ce7078c14d183ed1e95d311a2df59bc86855  
**Điểm tự động:** 84.0 / 88; đã đạt toàn bộ 84 điểm công khai.

Commit trên là snapshot code và dữ liệu đã kiểm chứng; báo cáo được lưu trong commit tiếp theo để tránh
tự tham chiếu hash. 4 điểm SLO ẩn và 12 điểm báo cáo do giảng viên chấm, chưa tự nhận là đạt.
Tên repo giữ `Track3-Day25-2A202602958-BuiMinhQuan` theo lựa chọn của chủ repo, khác cách nối tên bằng dấu gạch
ngang trong README. Các file cấm sửa được giữ nguyên. Không dùng API key, Docker hay đồng hồ thật trong client.

Số liệu bảng chính dùng seed 25. `scoreboard.json` kiểm tra cả seed 25, 26, 27: G1–G6, C1, workflow đều PASS.
85/85 test đạt (82 test có sẵn + 3 regression bổ sung); các nhóm test được grader tính điểm có 76/76 test đạt.
Regression kiểm tra đúng ngưỡng burn-rate, budget vừa hết và answer cũ về sau webhook. Availability biểu diễn 0–1;
cost là đơn vị chi phí mô phỏng; N/A nghĩa là không có mốc restore tương ứng.

## 1. Kết quả Game Day (naive vs resilient)

| Băng | Client | availability | p95 (s) | amplification | retry_ratio | cost/turn | recovery (s) | Kết quả |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | naive | 0.7194 | 7.157 | 7.738 | 6.738 | 2.163 | 4.0 | FAIL |
| G1 | resilient | 1.0 | 4.817 | 1.06 | 0.001 | 2.094 | 0.0 | PASS |
| G2 | naive | 0.456 | 15.034 | 9.904 | 8.904 | 4.627 | 155.0 | FAIL |
| G2 | resilient | 1.0 | 10.781 | 1.038 | 0.005 | 2.116 | 0.0 | PASS |
| G3 | naive | 1.0 | 4.768 | 1.164 | 0.164 | 2.328 | 0.0 | FAIL |
| G3 | resilient | 1.0 | 4.718 | 1.065 | 0.035 | 2.146 | 0.0 | PASS |
| G4 | naive | 1.0 | 13.764 | 1.004 | 0.004 | 2.008 | 0.0 | FAIL |
| G4 | resilient | 1.0 | 5.684 | 1.013 | 0.002 | 2.069 | 0.0 | PASS |
| G5 | naive | 0.3699 | 5.359 | 17.03 | 16.03 | 2.124 | N/A | FAIL |
| G5 | resilient | 0.8179 | 5.482 | 1.003 | 0.002 | 2.504 | N/A | PASS |
| G6 | naive | 0.517 | 4.836 | 12.344 | 11.344 | 2.009 | 0.0 | FAIL |
| G6 | resilient | 1.0 | 6.225 | 1.067 | 0.027 | 2.164 | 0.0 | PASS |

Client mới có 0 vi phạm retry-after trên cả 6 băng, 0 retry lỗi 400, 0 route không tương thích và
0 failover không cần thiết. G2, G3, G4, G6 có primary share sau restore = 100%; G1 = 93,5% vì rate limit
12 rps còn áp dụng. Recovery = 0 s là kết quả theo cửa sổ thành công của simulator: fallback duy trì dịch vụ,
không có nghĩa là alpha không bị sự cố.

## 2. Cấu hình client và lý do

Giữ các giá trị client starter sau khi kiểm chứng, thay các giá trị cache chưa phù hợp. Chính sách phản ứng
lỗi và state machine mới là thay đổi chính; không hard-code tên băng, thời điểm hoặc state simulator.

| Tham số | Giá trị | Lý do và bằng chứng |
|---|---|---|
| attempt_timeout_s | 8 | G6 availability 100%; timeout 30 s giảm còn 94,88%. Còn thời gian cho fallback trong deadline 30 s. |
| max_attempts_per_provider | 2 | Tối đa một retry transient; G2 amplification 1,038, G3 retry_ratio 0,035. |
| min_time_left_s | 1 | Không đặt attempt khi không còn thời gian hữu ích; mọi timeout được cap theo deadline. |
| backoff_base_s / cap_s | 0,25 / 4 | Full jitter giảm đồng bộ; G1 có 0 vi phạm retry-after. Delay có header = retry-after + jitter. |
| retry_budget_ratio / min_per_s / max_tokens | 0,1 / 0,5 / 20 | Bucket chung giới hạn retries, cho phép burst nhỏ; G3 retry_ratio 3,5% dưới ngưỡng 10%. Floor theo thời gian và bucket ban đầu khiến 10% là giới hạn xấp xỉ dài hạn. |
| quota_cooldown_s | 300 | Hết credit không tự chữa bằng retry; G5 availability 81,79%, không retry 400 hay failover vô ích. |
| breaker.window_size / min_calls | 20 / 10 | Cửa sổ hữu hạn bắt thay đổi, tránh trip do một lỗi đơn lẻ; G2 recovery 0 s nhờ fallback. |
| breaker.failure_rate_threshold | 0,5 | Trip khi ít nhất nửa cửa sổ lỗi; G2/G6 availability 100%, không biến 400/quota thành lỗi sức khỏe. |
| breaker.slow_call_s / slow_rate_threshold | 5 / 0,6 | Nhận diện thành công chậm; G4 p95 5,684 s so với naive 13,764 s. |
| breaker.open_duration_s | 10 | Giảm tải rồi thăm dò định kỳ; traffic quay về alpha 100% trên G2/G4/G6. |
| half_open_max_probes / successes | 2 / 2 | Chỉ hai probe đang bay, cần hai thành công nhanh; cả 13 test breaker PASS, gồm concurrency và generation cũ. |

| Loại lỗi | Breaker | Retry cùng provider | Failover / cooldown |
|---|---|---|---|
| 400 và lỗi client khác | release, không ghi sức khỏe | không | GiveUp ngay, không failover |
| 429 insufficient_quota | release | không | cooldown 300 s rồi failover ngay |
| 429 rate_limit_exceeded | release | không retry ngay | cooldown theo retry-after, spillover ngay |
| 529 / 503 / 5xx khác / timeout | ghi failure | chỉ khi breaker cho phép, còn lượt, budget và deadline | hết điều kiện thì failover |
| thành công chậm | ghi slow success | không | breaker có thể OPEN cho các call tiếp theo |

Nếu mọi provider tạm hết rate limit, có thể chờ cooldown ngắn tối đa 5 s cộng jitter nếu còn deadline.
Không chờ quota. Ladder giữ thứ tự alpha → alpha-eu → beta → gamma-mini, loại gamma-mini cho task tool.
HALF-OPEN cấp Permit; chuyển state tăng generation, bỏ kết quả cũ, hủy attempt giải phóng probe.

## 3. Ba thí nghiệm

Chạy `python scripts/run_experiments.py`; cấu hình ablation nằm trong bản copy trong bộ nhớ, không thay
client/config nộp bài. Dữ liệu đầy đủ ở `reports/experiments.json`.

### 3.1. Retry budget khi breaker cấu hình sai

Đặt min_calls = 1.000.000.000, max_attempts_per_provider = 5. Khi tắt budget dùng ratio = 100,
max_tokens = 1e9, min_per_s = 1e6 đúng hướng dẫn README.

| Băng | Budget | availability | amplification | retry_ratio | recovery (s) | p95 (s) |
| --- | --- | --- | --- | --- | --- | --- |
| G2 | bật | 0.9983 | 1.378 | 0.058 | 0.0 | 19.254 |
| G3 | bật | 1.0 | 1.136 | 0.068 | 0.0 | 4.55 |
| G2 | tắt | 0.967 | 1.597 | 0.4 | 32.0 | 21.508 |
| G3 | tắt | 1.0 | 1.162 | 0.158 | 0.0 | 4.661 |

Trên G2, tắt budget tăng retry_ratio từ 0,058 lên 0,400, giảm availability từ 99,83% xuống 96,70%,
và recovery từ 0 lên 32 s. Trên G3, retry_ratio 0,158 khi tắt budget vượt yêu cầu 0,10 dù user vẫn thành công;
budget giữ còn 0,068. Khi breaker đúng, G2 amplification chỉ 1,038 thay vì 1,378 với breaker hỏng + budget.
Cần cả hai: breaker ngắt nguồn không khỏe, budget chặn retries trước khi đủ min_calls và khi lỗi rải rác
chưa chạm ngưỡng trip, hoặc cấu hình breaker bị sai.

### 3.2. Timeout 30 s và survivorship bias

| Băng | Timeout (s) | availability | p95 (s) | give_up_reasons |
| --- | --- | --- | --- | --- |
| G6 | 8 | 1.0 | 6.225 | {} |
| G6 | 30 | 0.9488 | 5.445 | {"deadline": 103, "no_provider_available": 19} |
| G4 | 8 | 1.0 | 5.684 | {} |
| G4 | 30 | 1.0 | 5.608 | {} |

G6 có 103 GiveUp vì deadline và 19 vì không còn provider, trong khi timeout 8 s không có GiveUp.
p95 giảm từ 6,225 xuống 5,445 s khi timeout dài, nhưng đó là p95 của các lượt sống sót: các lượt bị treo
và thất bại không nằm trong tập đo. G4 gần như không đổi (availability 100%, p95 5,684 → 5,608 s) vì
slow-call breaker vẫn phát hiện độ trễ và ngắt alpha trước khi cần timeout 30 s.
Chọn timeout dựa trên phân phối độ trễ khỏe mạnh của từng deployment, deadline tổng và phần thời gian
phải dành cho retry/fallback; không lấy p95 có điều kiện trong sự cố làm thước đo duy nhất.

### 3.3. Bỏ lọc tool calling

G6 phát sinh 244 route không tương thích,
availability giảm từ 100% xuống 89.77%.
Với người quản lý sản phẩm: model dự phòng trả lời hội thoại được nhưng không tạo lệnh tool cần để xử lý
hoàn tiền; có phản hồi từ model chưa đồng nghĩa hoàn thành yêu cầu khách hàng. Fallback phải giữ capability
của từng bước trước khi tối ưu chi phí hoặc độ trễ.

## 4. Workflow hoàn tiền

| Executor | completion | crashes | duplicate refunds | duplicate emails | lost refunds | overpaid (cent) | wasted LLM/crash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| naive | 1.0 | 81 | 128 | 81 | 0 | 1496700 | 1.123 |
| yours | 1.0 | 66 | 0 | 0 | 0 | 0 | 0.303 |

Client workflow mới hoàn tất 500/500 phiên, qua 66 worker crash, 0 hoàn tiền/email trùng và 0 hoàn tiền mất.
Key ổn định theo session + step (JSON tuple có namespace) được gửi cho payment/email. Checkpoint chỉ ghi
sau khi bước thành công; worker mới tải kết quả và bỏ qua bước hoàn thành. Chỉ bắt ServiceError và
ServiceTimeout, không bắt WorkerCrash.

Idempotency đơn lẻ giữ side effect một lần nhưng vẫn tính lại LLM và lookup sau crash, làm tốn tiền.
Checkpoint đơn lẻ không xử lý được khoảng trống payment đã commit nhưng worker chết trước khi ghi kết quả:
chạy lại sẽ trả tiền hai lần nếu thiếu key. Ghi checkpoint trước payment có thể đánh dấu thành công trong
khi tiền chưa chuyển, khiến resume bỏ qua và mất hoàn tiền. DurableStore và sự khử trùng lặp của dịch vụ
là giả định độ bền của lab; không khẳng định exactly-once transport.

## 5. Alerting & error budget

| Sự cố | Mong đợi | Naive | Độ trễ naive (phút) | Burn-rate | Độ trễ burn-rate (phút) |
| --- | --- | --- | --- | --- | --- |
| checkout_bug | page | phát hiện | 1 | phát hiện | 27 |
| provider_outage | page | phát hiện | 0 | phát hiện | 4 |
| deploy_blip | none | false page | N/A | không page | N/A |
| slow_leak | ticket | bỏ sót | N/A | phát hiện | 1337 |
| degraded_evening | page | phát hiện | 214 | phát hiện | 291 |
| night_spike | none | false page | N/A | không page | N/A |
| small_bump | none | false page | N/A | không page | N/A |

Naive có 7 page, 3 false page và bỏ sót slow_leak; burn-rate có 3 page, 1 ticket, 0 false page, mọi sự cố
được phát hiện trong thời hạn public. Dùng prefix sum, tổng cửa sổ O(1), toàn bộ scan O(số phút × số rule).
Mỗi rule cần đồng thời cửa sổ dài và ngắn: 14,4× (60 & 5 phút), 6× (360 & 30 phút), ticket 1× (4320 & 360 phút).

30 ngày có 25.901.755 requests, 55.618 bad; budget cho phép 129.508,8 bad ở SLO 99,5%.
Đã tiêu **42,95%**, còn **57,05%**, availability **99,7853%**; **không đóng băng release**.
small_bump kéo dài 20 phút ở 12% lỗi: 20 × 0,12 = 2,4 phút lỗi tương đương khi traffic không đổi,
burn 6 h = 2,4/360/0,005 = 1,33×; burn 1 h = 8×.
Cả hai dưới ngưỡng page (6× và 14,4×) dù cửa sổ ngắn xấu, nên không đánh thức on-call.
Tính thực tế dùng request-weighted sums, không lấy trung bình tỷ lệ theo phút khi traffic biến động.

## 6. Postmortem — G2 với client naive (blameless)

ShopAgent chịu mất 75% năng lực alpha trong khoảng t=120–300 s. Cơ chế retry ba tầng làm amplification
lên 9,904, khiến availability còn 45,60% và tiếp tục gián đoạn sau khi provider khôi phục.
Client mới giữ availability 100%, amplification 1,038 và đạt cửa sổ hồi phục ngay tại mốc restore nhờ fallback.

![So sánh retry storm và client chịu lỗi](gameday/G2_overload_storm.png)

**Ảnh hưởng:** 1.285/2.362 lượt user thất bại (54,40%); 34.475 attempt cho 3.481 logical call;
26.298 lỗi rate limit, 2.737 timeout, 3.194 overload; 28.381 vi phạm retry-after.
Provider giảm năng lực 180 s, cửa sổ hồi phục 95% bắt đầu t=455 s: tổng 335 s từ trigger, kéo thêm 155 s
sau restore. Một số lượt vẫn thành công lúc đầu nên không gọi toàn bộ 335 s là outage 100%.
Giả sử 30 ngày chỉ có sự cố này, traffic user bình thường 4 lượt/s, mẫu số tháng = 10.368.000 lượt,
budget 0,5% = 51.840 lượt: tiêu 1.285/51.840 = **2,48% budget tháng**, còn 97,52%, chưa vượt budget tháng.
Trong riêng mẫu G2, budget 11,81 lượt bị vượt: tiêu khoảng 108,81 lần budget cửa sổ đó.

Timeline tính trực tiếp từ CSV naive; các khoảng là [start, end), tỷ lệ call = tổng calls_ok / calls_done.

| t / khoảng (s) | Sự kiện | Bằng chứng từ CSV |
|---|---|---|
| 110–120 | trước trigger | 9,1 attempt/s; 92/92 call thành công = 100% |
| 120–130 | alpha mất 75% GPU tại t=120 | 6,2 attempt/s; 32/32 call hoàn tất thành công; backlog chưa phản ánh hết vào completion |
| 140–150 | retry storm hình thành | 214,2 attempt/s; 0/47 call thành công = 0% |
| 290–300 | cuối khoảng provider suy giảm | 146,1 attempt/s; 0/41 call thành công |
| 300–310 | GPU đã hồi phục tại t=300 | 38,8 attempt/s; 0/18 call thành công, dịch vụ chưa hồi phục |
| 390–400 | failure tiếp tục tự duy trì | 85,0 attempt/s; 0/50 call thành công |
| 445–455 | bắt đầu thoát backlog | 13,8 attempt/s; 8/40 call thành công = 20% |
| 455–485 | cửa sổ hồi phục theo metric | 10,87 attempt/s; 352/368 call thành công = 95,65% |

**Trigger:** giảm GPU của alpha. **Root cause:** retry app × gateway × SDK, tối đa 36 attempt/call,
delay cố định, thiếu jitter/budget/breaker/fallback và không tôn trọng retry-after. Đây là khoảng trống
trong thiết kế và kiểm chứng khả năng chịu lỗi của hệ thống, không phải lỗi của một cá nhân.

**Vòng lặp metastable:** timeout không hủy xử lý trên server → hàng đợi tiếp tục chứa request mà client
đã bỏ → client retry bổ sung tải → hàng đợi dài hơn, tiếp tục timeout/529/429 → lại retry.
Tại t=300 năng lực phục hồi nhưng tải retry và backlog tồn tại; năng lực khỏe mạnh chưa đủ để ngay lập tức
rút hàng đợi. Rate limit và deadline cuối cùng giúp chặn bớt tải, nhưng fixed delay đồng bộ retries và
retry-after bị bỏ qua làm tình hình tệ hơn. Trong bản sửa, OPEN breaker, cooldown và fallback giảm tải alpha;
probe có giới hạn cho phép đưa traffic quay về an toàn.

| # | Hành động | Loại | Owner (vai trò) | Cách kiểm chứng |
|---|---|---|---|---|
| 1 | Một tầng retry transient, full jitter, budget chung; tắt retry trùng ở gateway/SDK | prevent | Maintainer ShopAgent | CI seeds 25–27: G2 amplification ≤ 1,6, G3 retry_ratio ≤ 0,10, 0 retry 400 |
| 2 | Dashboard attempt/logical call, queue/timeout, breaker transition và burn-rate | detect | On-call/SRE | Replay G2 thấy tải 214,2 attempt/s so với 9,1 trước sự cố; public SLO 0 false page |
| 3 | Sliding-window slow/failure breaker, hai probe, fallback kiểm tra tools | mitigate | Platform reliability | G2 recovery ≤ 30 s, primary share ≥ 80%; G4 p95 ≤ 10 s; G6 incompatible_routes = 0 |
| 4 | Game Day nhiều seed và kiểm thử crash/payment trong CI | prevent | QA reliability | G1–G6/C1 PASS cả ba seed, workflow 0 duplicate/lost refund và completion ≥ 99% |

Các owner là vai trò đề xuất cho follow-up, không khẳng định đã phân công một người thực tế.

## 7. Một điểm yếu còn lại

G2 p95 vẫn 10,781 s, p99 15,610 s do các request đang bay trước khi breaker đủ kết quả hoặc probe
gặp hàng đợi. Nếu mọi provider cùng chậm/sập, fallback không tạo thêm năng lực; cache chỉ cứu FAQ
chia sẻ được, nên C1 availability tổng chỉ 91,17% dù FAQ đạt 96,34%.
Bước tiếp theo là deadline phân bổ theo từng deployment, bulkhead giới hạn concurrency, admission control
và chỉ dùng cancellation khi provider thực sự hỗ trợ. Cần đo tradeoff timeout/failover/cost trước khi giảm
timeout; tuyệt đối không hedge side effect hoàn tiền khi chưa đảm bảo idempotency.

## 8. Cache (Part G)

| Client | availability | faq_availability | cache_hit_ratio | stale_served | wrong_answers | outdated_answers | cost/turn | Kết quả |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| resilient | 0.8373 | 0.8424 | 0.0 | 0 | 0 | 0 | 1.386 | FAIL |
| cached | 0.9117 | 0.9634 | 0.591 | 190 | 0 | 2 | 0.956 | PASS |

| Tham số | Giá trị | Bằng chứng lựa chọn |
|---|---|---|
| similarity_threshold | 0,90 | 0 wrong_answers, hit 59,1%; 0,80 tạo 183 wrong_answers; 0,97 hit 49,8% dưới yêu cầu 50%. |
| ttl_s | 30 | Chỉ 2 outdated_answers ở seed 25, dưới 15; TTL 300 tạo 95. Chọn 30 thay vì 60 để dành biên khi cường độ băng ẩn thay đổi. |
| max_stale_s | 180 | Vượt sự cố 120 s với khoảng dự phòng; FAQ 96,34%, 190 stale served; tắt stale chỉ đạt 85,29%. |
| max_entries | 500 | LRU hữu hạn, không nhân bản entry cho các paraphrase gần nhau; test eviction PASS. |

Cache chỉ lưu FAQ không personal; prompt_version là scope, chọn cosine cao nhất đủ ngưỡng,
không đổi stored_at khi hit. Age ≤ TTL là fresh; sau TTL chỉ được Serve nếu inner GiveUp và còn trong
cửa sổ TTL + max_stale. Lookup lại lúc GiveUp bảo đảm webhook có thể vô hiệu entry trong lúc provider
đang xử lý. Webhook xóa mọi entry chứa source, provider thành công mới refresh entry.

### 8.1. Ngưỡng similarity

| Ngưỡng | hit ratio | wrong_answers | cost/turn |
| --- | --- | --- | --- |
| 0.8 | 0.609 | 183 | 1.018 |
| 0.9 | 0.591 | 0 | 0.956 |
| 0.97 | 0.498 | 0 | 1.018 |

Ở 0,80, wrong_answers_by_reason = {"other_question": 183}; hit cao hơn không có ích khi trả sai ý định.
Catalog có các cặp gần nghĩa nhưng khác câu trả lời: điều kiện hoàn tiền / thời gian nhận tiền hoàn,
đổi size / đổi màu, phí ship nội thành / ngoại tỉnh, phương thức thanh toán / COD. Metric chỉ cho tổng
183 theo lý do, không đủ để khẳng định số lỗi riêng của từng cặp. 0,90 loại các near miss trong public tapes;
0,97 làm rớt nhiều paraphrase hợp lệ, tăng cost/turn từ 0,956 lên 1,018.

### 8.2. TTL

| TTL (s) | hit ratio | outdated_answers | FAQ availability | cost/turn |
| --- | --- | --- | --- | --- |
| 30 | 0.591 | 2 | 0.9634 | 0.956 |
| 60 | 0.652 | 3 | 0.964 | 0.916 |
| 300 | 0.731 | 95 | 0.964 | 0.863 |

Webhook hữu ích cho đổi chính sách hoàn tiền ở t=150, nhưng thay phí ship t=480 không được thông báo,
nên cache không có tín hiệu invalidate. TTL giới hạn thời gian dùng answer fresh cũ: 30/60/300 s tương
ứng 2/3/95 outdated_answers. TTL 300 giảm cost nhưng vi phạm ngưỡng 15; TTL 30 giữ hit trên 50% và
biên an toàn tốt hơn. Khi provider cũng lỗi, stale có thể kéo dài tuổi answer thêm max_stale_s;
không khẳng định TTL một mình bảo đảm freshness tuyệt đối khi có stale-if-error.

### 8.3. Tắt stale-if-error

max_stale_s = 0 giảm FAQ availability từ 96,34% xuống 85,29%, hit từ 59,1% xuống 48,1%,
stale served từ 190 xuống 0; tổng availability từ 91,17% xuống 84,40%. Stale là bước cứu cuối khi
mọi provider không trả lời, không thay cho refresh khi provider khỏe. Scope và invalidation vẫn được
áp dụng cho stale: không trả prompt cũ, nguồn bị webhook đổi, hoặc dữ liệu cá nhân.

**Vì sao không cache câu hỏi cá nhân kể cả theo user?** Trạng thái đơn hàng, hoàn tiền, điểm có thể đổi
bất kỳ lúc nào và cần dữ liệu hệ thống cùng authorization hiện tại. Scope theo user chỉ tránh lộ chéo user,
không chứng minh freshness hay quyền truy cập; lab loại toàn bộ personal khỏi allowlist.

**Alert khi cache làm dashboard xanh:** giữ SLI user-visible và provider-attempt SLI riêng, theo dõi error/timeout
rate theo provider, breaker OPEN, tỷ lệ stale, tuổi stale và cache miss thất bại. Page theo burn-rate của
đường live và tác động miss/personal, ticket/page phù hợp khi stale tăng kéo dài hoặc sắp hết cửa sổ.
Không dùng availability FAQ có cache làm bằng chứng provider khỏe.

## 9. Tái lập và nộp bài

Trên Windows đã tạo `.venv`, cài editable `.[dev,plot]`, dùng Python 3.13.15. Trên máy sạch chạy:

```bash
python -m pip install -e ".[dev,plot]"
python -m pytest -q tests tests_extra
python scripts/run_gameday.py --client both
python scripts/run_gameday.py --scenarios configs/scenarios_cache.yaml --client resilient,cached --out reports/cache
python scripts/run_workflows.py --executor both
python scripts/run_slo.py --alerter both
python scripts/run_experiments.py
python scripts/plot_timeseries.py --scenario G2_overload_storm
python scripts/grade.py --seeds 25,26,27
python scripts/write_report.py
ruff check src tests tests_extra scripts
```

Source data đi kèm JSON, CSV và hình trong `reports/`; không chỉnh simulator, tests hay scenario.
Hidden tapes / hidden SLO không có trong repo và chưa được kiểm chứng. Repo public:
https://github.com/NeoGGz/Track3-Day25-2A202602958-BuiMinhQuan — nộp URL này cùng commit phù hợp lên kênh lớp.
