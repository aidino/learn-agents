
### **Bản Thiết Kế Hệ Thống AI Code Reviewer (Phiên bản 1.0)**

**1. Tổng quan (Overview)**

* **Mục tiêu:** Xây dựng một hệ thống multi-agent có khả năng phân tích và review code theo yêu cầu, tập trung vào các vấn đề về bảo mật (Security) và kiến trúc (Architecture) để nâng cao chất lượng mã nguồn.
* **Triết lý thiết kế:**
    * **Đơn giản là trên hết:** Tối giản hóa các tính năng, luồng hoạt động và kiến trúc để dễ dàng triển khai và bảo trì.
    * **Bảo mật làm trọng tâm (Security by Design):** Sử dụng mô hình xác thực hiện đại (GitHub App) để không bao giờ xử lý hay lưu trữ thông tin nhạy cảm của người dùng (Personal Access Token).
    * **Tập trung vào giá trị cốt lõi:** Chỉ thực hiện các tính năng review mang lại giá trị cao mà các công cụ linting thông thường bỏ qua.
* **Phạm vi Phiên bản 1 (MVP Scope):**
    * **Trong phạm vi:**
        * Xác thực qua GitHub App.
        * Kích hoạt thủ công qua giao diện chat (`adk web`).
        * Phân tích Security, Architecture (deadlock...).
        * Phân tích dựa trên `diff` của PR.
        * Trả kết quả dưới dạng bình luận trên Pull Request của GitHub.
    * **Ngoài phạm vi:**
        * Cơ chế trigger tự động qua webhook.
        * Hệ thống thu thập phản hồi của người dùng (`👍 Hữu ích` / `👎 Không chính xác`).
        * Giao diện web (FE/Dashboard) chuyên dụng.

**2. Kiến trúc hệ thống (System Architecture)**

* **Mô hình tổng thể:** Hệ thống sẽ hoạt động theo mô hình **"Hybrid Pull Model"** – kết hợp sự an toàn của GitHub App với việc kích hoạt thủ công từ người dùng.
* **Các thành phần chính (Key Components):**
    * **Agent Điều Phối (Orchestrator Agent):** "Bộ não" của hệ thống, nhận lệnh từ người dùng, điều phối các agent khác và tổng hợp kết quả.
    * **Git Agent (`github-mcp-server`):** Chịu trách nhiệm tương tác với GitHub API để lấy thông tin PR.
    * **Security Agent (`Semgrep MCP`):** Phân tích mã nguồn để tìm kiếm lỗ hổng bảo mật.
    * **Architecture Agent (`Serena MCP` & Custom Logic):** Phân tích các vấn đề về kiến trúc, rủi ro deadlock, và xây dựng đồ thị tác động.
* **Công nghệ sử dụng (Technology Stack):**
    * **Agent Framework:** Google Agent Development Kit (ADK)
    * **Authentication:** Công cụ ADK Authentication
    * **Security Analysis:** Semgrep MCP
    * **Code Intelligence:** Serena MCP
    * **Git Interaction:** github-mcp-server

**3. Luồng hoạt động chi tiết (Detailed Workflow)**

Đây là luồng hoàn chỉnh từ đầu đến cuối.

**Giai đoạn 0: Cài đặt (Làm 1 lần)**
1.  **Người dùng** truy cập trang GitHub Marketplace và nhấn **"Install"** để cài đặt GitHub App của hệ thống vào repository hoặc organization của họ.
2.  Hệ thống (sử dụng **ADK Authentication**) xử lý quá trình xác thực và lưu lại `installation_id` tương ứng với repository đó.

**Giai đoạn 1: Tương tác người dùng (Kích hoạt thủ công)**
1.  **Người dùng** muốn review một PR, họ mở terminal và chạy lệnh `adk web` để khởi động giao diện chat.
2.  **Agent Điều Phối** chào và hỏi: *"Vui lòng cung cấp cho tôi URL của Pull Request mà bạn muốn phân tích."*
3.  **Người dùng** dán URL của PR vào (ví dụ: `https://github.com/org/repo/pull/123`).

**Giai đoạn 2: Xử lý Backend (Tự động)**
1.  **Agent Điều Phối** nhận URL, phân tích để lấy ra `tên repository` và `PR number`.
2.  Dùng `tên repository` để tra cứu `installation_id` đã lưu.
    * *Nếu không có:* Báo cho người dùng cần cài đặt GitHub App.
    * *Nếu có:* Tiếp tục.
3.  **Agent Điều Phối** yêu cầu **ADK Authentication** sử dụng `installation_id` để tạo ra một **token truy cập tạm thời (temporary installation access token)**.
4.  **Agent Điều Phối** giao nhiệm vụ cho các agent con, kèm theo token tạm thời:
    * Gửi `PR number` cho **Git Agent** để lấy `diff` của PR.
    * Gửi `diff` và mã nguồn liên quan cho **Security Agent** và **Architecture Agent** để phân tích.

**Giai đoạn 3: Báo cáo kết quả**
1.  Các agent con trả kết quả phân tích về cho **Agent Điều Phối**.
2.  **Agent Điều Phối** tổng hợp tất cả thông tin thành một báo cáo duy nhất, định dạng bằng Markdown.
3.  **Agent Điều Phối** sử dụng **Git Agent** (với token tạm thời) để đăng báo cáo đó dưới dạng một bình luận duy nhất lên PR trên GitHub.
    * Báo cáo sẽ được định dạng gọn gàng bằng thẻ `<details>` để người dùng có thể mở rộng xem chi tiết.
4.  Cuối cùng, **Agent Điều Phối** phản hồi trên giao diện chat: *"Xong! Tôi đã đăng kết quả review vào PR #123. Bạn có thể xem ngay trên GitHub."*

**4. Thiết kế Chi tiết Giao diện (Interface Design)**

* **Giao diện Đầu vào (Input):** Cửa sổ chat của `adk web`. Tương tác tối giản, chỉ yêu cầu 1 thông tin đầu vào là URL của Pull Request.
* **Giao diện Đầu ra (Output):** Bình luận trên GitHub Pull Request.
    * **Cấu trúc:**
        * Dòng tóm tắt tổng quan.
        * Các mục chi tiết có thể thu gọn cho từng loại phân tích (Bảo mật, Kiến trúc, Đồ thị Tác động).
        * Trong mỗi mục, liệt kê rõ ràng vị trí (file, dòng code) và mô tả vấn đề/gợi ý.

