

### **Kế hoạch triển khai chi tiết: AI Code Reviewer v1.0**

**Tổng thời gian dự kiến: 4-6 tuần**

-----

### **Giai đoạn 0: Thiết lập Nền tảng (Foundation Setup)**

  * **Thời gian dự kiến:** 2-3 ngày
  * **Yêu cầu:** Chuẩn bị môi trường, dự án và các tài sản cần thiết để bắt đầu code.

| Task | Yêu cầu | Cách làm | Các thư viện/công cụ cần thiết |
| :--- | :--- | :--- | :--- |
| **0.1: Tạo GitHub App** | Có một GitHub App đã được đăng ký và nhận được App ID, Private Key. | 1. Truy cập **Settings \> Developer settings \> GitHub Apps** trên tài khoản GitHub của bạn.\<br\>2. Nhấn "New GitHub App".\<br\>3. Cấu hình các quyền cần thiết (Permissions): `Contents: Read-only`, `Pull requests: Read & write`.\<br\>4. Tạo và tải Private Key (.pem file) về máy. Lưu lại App ID. | GitHub Account |
| **0.2: Khởi tạo dự án ADK** | Cấu trúc thư mục dự án được tạo ra bởi ADK. | 1. Cài đặt ADK: `pip install adk`.\<br\>2. Chạy lệnh `adk init my-code-reviewer` để tạo dự án.\<br\>3. `cd my-code-reviewer`. | Google ADK |
| **0.3: Cấu hình Môi trường** | Quản lý an toàn các biến môi trường (App ID, Private Key). | 1. Tạo file `.env` ở thư mục gốc của dự án.\<br\>2. Thêm các biến: `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` (nội dung của file .pem).\<br\>3. Cài đặt thư viện `python-dotenv` để load các biến này vào ứng dụng. | `python-dotenv` |

-----

### **Giai đoạn 1: Xác thực và Tương tác Git (Authentication & Git Interaction)**

  * **Thời gian dự kiến:** 1 tuần
  * **Yêu cầu:** Hệ thống có khả năng nhận lệnh từ người dùng, xác thực với GitHub thông qua App và lấy được thông tin của một Pull Request.

| Task | Yêu cầu | Cách làm | Các thư viện/công cụ cần thiết |
| :--- | :--- | :--- | :--- |
| **1.1: Xử lý Input từ User** | Agent chính có thể nhận và phân tích URL của Pull Request từ giao diện chat `adk web`. | 1. Mở file `main.py` do ADK tạo ra.\<br\>2. Chỉnh sửa hàm xử lý message để nhận vào một chuỗi là URL.\<br\>3. Sử dụng regex hoặc `urllib.parse` để bóc tách `owner`, `repo`, và `pr_number` từ URL. | `re`, `urllib` |
| **1.2: Tích hợp ADK Auth** | Lấy được token truy cập tạm thời (installation access token) để tương tác với API của GitHub. | 1. Tạo một module/file quản lý việc xác thực, ví dụ: `auth_manager.py`.\<br\>2. Viết hàm `get_installation_token(owner, repo)` sử dụng các biến môi trường.\<br\>3. Logic này sẽ cần tạo JWT và gọi API của GitHub để đổi lấy token tạm thời. (Bạn có thể tham khảo doc của ADK Auth hoặc doc của GitHub API).\<br\>4. Lưu `installation_id` vào một file JSON đơn giản (`installations.json`) sau khi app được cài lần đầu. | `google-auth` (nếu ADK Auth dùng nó), `PyJWT`, `requests` |
| **1.3: Phát triển Git Agent** | Agent có khả năng lấy thông tin `diff` của một PR. | 1. Tạo agent mới: `adk new-agent git_agent`.\<br\>2. Viết một hàm trong agent này, ví dụ: `get_pr_diff(owner, repo, pr_number, token)`.\<br\>3. Bên trong hàm, sử dụng thư viện `requests` để gọi đến GitHub API endpoint: `GET /repos/{owner}/{repo}/pulls/{pull_number}`. Header `Accept` cần có `application/vnd.github.v3.diff` để lấy diff. | `requests` |

-----

### **Giai đoạn 2: Phân tích Đơn agent (Single-Agent Analysis)**

  * **Thời gian dự kiến:** 1 tuần
  * **Yêu cầu:** Tích hợp thành công một agent phân tích (Security Agent) để xử lý dữ liệu code lấy về từ Giai đoạn 1.

| Task | Yêu cầu | Cách làm | Các thư viện/công cụ cần thiết |
| :--- | :--- | :--- | :--- |
| **2.1: Phát triển Security Agent** | Agent có khả năng nhận một đoạn code (diff) và trả về các lỗ hổng bảo mật. | 1. Tạo agent mới: `adk new-agent security_agent`.\<br\>2. Viết hàm `analyze_code(diff_content)`. | Semgrep (cài đặt trên máy) |
| **2.2: Tích hợp Semgrep** | Gọi Semgrep từ code Python và nhận lại kết quả. | 1. Trong hàm `analyze_code`, lưu `diff_content` vào một file tạm thời.\<br\>2. Sử dụng thư viện `subprocess` để chạy lệnh Semgrep trên file tạm đó với output là JSON: `semgrep scan --json /path/to/temp/file.py`.\<br\>3. Đọc và parse file JSON kết quả để lấy ra các thông tin cần thiết (vị trí lỗi, mô tả).\<br\>4. Xóa file tạm sau khi hoàn tất. | `subprocess`, `json`, `tempfile` |

-----

### **Giai đoạn 3: Phân tích Đa agent & Điều phối (Multi-Agent & Orchestration)**

  * **Thời gian dự kiến:** 1-2 tuần
  * **Yêu cầu:** Agent Điều Phối có thể quản lý luồng làm việc của nhiều agent, tích hợp thêm Architecture Agent.

| Task | Yêu cầu | Cách làm | Các thư viện/công cụ cần thiết |
| :--- | :--- | :--- | :--- |
| **3.1: Xây dựng Agent Điều Phối** | Agent chính (trong `main.py`) có thể gọi tuần tự các agent khác (Git -\> Security -\> Architecture) và thu thập kết quả. | 1. Trong hàm xử lý chính, sau khi nhận URL, hãy thực hiện chuỗi hành động:\<br\> a. Gọi `auth_manager` để lấy token.\<br\> b. Gọi `git_agent.get_pr_diff(...)`.\<br\> c. Gửi `diff` cho `security_agent.analyze_code(...)`.\<br\> d. Gửi `diff` cho `architecture_agent.analyze_code(...)`.\<br\> e. Lưu kết quả từ các agent vào một dictionary. | - |
| **3.2: Phát triển Architecture Agent (MVP)** | Agent có khả năng phát hiện các mẫu code đơn giản có thể dẫn đến deadlock. | 1. Tạo agent mới: `adk new-agent architecture_agent`.\<br\>2. Viết hàm `analyze_code(diff_content)`.\<br\>3. **Cách làm đơn giản cho MVP:** Dùng regex để tìm kiếm các từ khóa như `lock.acquire()`, `mutex`, `synchronized` trong `diff_content` và cảnh báo người dùng cần review kỹ các đoạn này. Chưa cần phân tích AST phức tạp. | `re` |

-----

### **Giai đoạn 4: Hoàn thiện Báo cáo & Tích hợp (Reporting & Final Integration)**

  * **Thời gian dự kiến:** 1 tuần
  * **Yêu cầu:** Tổng hợp kết quả từ các agent, định dạng thành báo cáo và đăng lên GitHub PR.

| Task | Yêu cầu | Cách làm | Các thư viện/công cụ cần thiết |
| :--- | :--- | :--- | :--- |
| **4.1: Định dạng Báo cáo** | Tạo một chuỗi Markdown đẹp mắt từ kết quả phân tích. | 1. Viết một hàm `format_report(analysis_results)` trong Agent Điều Phối.\<br\>2. Hàm này sẽ duyệt qua kết quả và xây dựng một chuỗi string, sử dụng các thẻ `<details>` và `<summary>` của Markdown để tạo các mục có thể thu gọn. | - |
| **4.2: Đăng bình luận lên PR** | Hệ thống có thể đăng báo cáo đã định dạng lên đúng PR. | 1. Thêm một hàm `post_comment(owner, repo, pr_number, report, token)` vào **Git Agent**.\<br\>2. Bên trong hàm, sử dụng `requests` để gọi API của GitHub: `POST /repos/{owner}/{repo}/issues/{pr_number}/comments` với body là chuỗi Markdown của báo cáo. | `requests` |
| **4.3: Hoàn thiện luồng** | Kết nối tất cả các bước lại với nhau. | 1. Sau khi `format_report`, Agent Điều Phối gọi `git_agent.post_comment`.\<br\>2. Cuối cùng, phản hồi lại trên giao diện chat cho người dùng biết là đã hoàn thành. | - |

-----

### **Giai đoạn 5: Tinh chỉnh và Kiểm thử**

  * **Thời gian dự kiến:** 1 tuần
  * **Yêu cầu:** Đảm bảo hệ thống chạy ổn định, xử lý lỗi và có tài liệu hướng dẫn cơ bản.

| Task | Yêu cầu | Cách làm | Các thư viện/công cụ cần thiết |
| :--- | :--- | :--- | :--- |
| **5.1: Xử lý Lỗi** | Hệ thống không bị crash khi có lỗi (ví dụ: URL sai, token hết hạn, API GitHub lỗi). | 1. Thêm các khối `try...except` vào các đoạn code gọi API, xử lý file...\<br\>2. Khi có lỗi, agent cần trả về một thông báo thân thiện cho người dùng. | - |
| **5.2: Kiểm thử End-to-End** | Xác minh toàn bộ luồng hoạt động trơn tru. | 1. Tạo một repository test trên GitHub.\<br\>2. Tạo một PR có chứa các đoạn code "cố tình" có lỗi bảo mật hoặc kiến trúc.\<br\>3. Chạy hệ thống và kiểm tra xem bình luận được đăng lên có chính xác không. | - |