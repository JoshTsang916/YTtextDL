# Project: YouTube Transcript to n8n Pipeline (YT2n8n)

## 0. 核心指導原則 (Core Directives)
- **語言模式 (Language)**：請全程使用 **繁體中文 (Traditional Chinese)** 與我溝通，包含程式碼的註解、CLI 的提示訊息 (Print outputs) 以及錯誤訊息。
- **開發策略 (Development Strategy)**：**不要重複造輪子 (Don't reinvent the wheel)**。
  - 在開始寫程式之前，請先搜尋 GitHub 是否有現成的輕量級 CLI 工具能滿足「輸入 YouTube URL -> 輸出 Transcript/Metadata -> 發送 Webhook」的需求。
  - 如果有現成的優秀專案，請優先建議使用或基於該專案修改。
  - 如果需要編寫腳本，請務必使用成熟的第三方函式庫（如 `yt-dlp` 用於抓取標題/Metadata，`youtube-transcript-api` 用於抓取字幕），將自行開發的程式碼量降到最低。

## 1. 專案目標 (Project Goal)
建置一個自動化工作流的「觸發端」，透過 CLI 接收 YouTube 網址，將影片的「標題」與「逐字稿」提取出來，並進行智慧分塊 (Chunking)，最後發送到 n8n 的 Webhook 進行後續的 AI 分析與 Obsidian 歸檔。

## 2. 功能需求詳情 (Functional Requirements)

### A. 輸入與互動 (CLI Interaction)
- 執行方式：類似 `python run.py <video_url>`。
- 介面回饋：所有的進度條、成功/失敗訊息都必須是友善的繁體中文。

### B. 資料擷取 (Extraction) - **Mandatory**
1.  **標題與 Metadata**：
    - **必須** 擷取影片標題 (Title) 與頻道名稱 (Channel Name)。
    - 建議使用 `yt-dlp` (Python library version) 來獲取這些資訊，因為它最穩定且維護最頻繁。
2.  **字幕 (Transcript)**：
    - 優先級：繁體中文 (zh-TW) > 繁中變體 (zh-Hant) > 中文 (zh) > 英文 (en)。
    - 若抓到英文，需在 Metadata 標記 `source_lang: en`，以便 n8n 後續決定是否翻譯。

### C. 智慧分塊策略 (Chunking Strategy)
- **場景**：針對 n8n 的 Loop 節點處理設計。
- **邏輯**：
  - 將長篇逐字稿切分為多個 Chunks。
  - 每個 Chunk 字數限制：約 3000-4000 tokens (或字元，視 LLM 限制而定)。
  - **切分邊界**：必須在完整的句子結尾（句號、驚嘆號等）進行切分，不可在單字中間截斷。
- **輸出結構**：回傳一個包含所有 Chunk 的 List/Array。

### D. 傳輸 (Webhook Payload)
- 將處理好的資料 POST 到 n8n。
- JSON 結構範例：
  ```json
  {
    "video_id": "dQw4w9WgXcQ",
    "url": "[https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=)...",
    "title": "影片標題必須要有",
    "channel": "頻道名稱",
    "chunks": [
      { "index": 0, "text": "第一段逐字稿內容..." },
      { "index": 1, "text": "第二段逐字稿內容..." }
    ],
    "total_chunks": 2,
    "metadata": {
      "captured_at": "2025-11-07",
      "language": "zh-TW"
    }
  }