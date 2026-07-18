# 経費精算マルチエージェントシステム

Google ADK + FastAPI + Docker による経費精算の自動審査APIシステム。
Cloud Run へのデプロイに最適化。マルチモーダル対応（領収書画像読み取り）。

## 動作モード

| モード | 環境変数 `EXPENSE_MODE` | LLM | 料金 (per 1M tokens) |
|---|---|---|---|
| **demo** | `demo`（デフォルト） | gemini-3.5-flash | Input $1.50 / Output $1.50 |
| **production** | `production` | gemini-3.1-flash-lite | Input $0.25 / Output $1.50 |

- demo: ハードコードルール、APIキー認証、画像読み取りなし
- production: Drive/Sheets連携、Vertex AI (location=global)、サービスアカウント認証、領収書画像OCR

## アーキテクチャ

```mermaid
graph TB
    subgraph "Google Workspace"
        GF[Google Form] -->|回答保存| GS[Google Sheets]
        GF -->|領収書アップロード| GD_R[Google Drive: 領収書]
        GD_K[Google Drive: 社内規程ドキュメント]
    end

    subgraph "Cloud Run (asia-northeast1)"
        API[FastAPI<br>POST /api/expense-check]
        CFG[Config<br>EXPENSE_MODE切替]

        subgraph "SequentialAgent: expense_router"
            direction LR
            RF[RuleFinder Agent]
            EC[ExpenseChecker Agent<br>マルチモーダル]
            RF --> EC
        end

        subgraph "Services"
            DS[DriveService]
            SS[SheetsService]
        end
    end

    subgraph "Vertex AI (location=global)"
        GEMINI[Gemini 3.1 Flash-Lite<br>マルチモーダル対応]
    end

    GS -->|Sheets API| SS
    GD_K -->|Drive API| DS
    GD_R -->|Drive API| DS

    API --> CFG
    CFG --> RF
    RF -.->|規程テキスト取得| DS
    EC -.->|領収書画像取得| DS
    RF -.->|LLM Call| GEMINI
    EC -.->|テキスト+画像| GEMINI
```

## エージェント処理フロー

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Runner as ADK InMemoryRunner
    participant RF as RuleFinder
    participant EC as ExpenseChecker
    participant Drive as Google Drive
    participant LLM as Gemini (global)

    Client->>FastAPI: POST /api/expense-check
    FastAPI->>Runner: run_async(申請データ + 画像)

    Note over Runner: Sequential実行開始

    Runner->>RF: Step 1: ルール抽出
    alt Production Mode
        RF->>Drive: 社内規程ドキュメント取得
        Drive-->>RF: テキストデータ
    end
    RF->>LLM: 申請種別 + 社内規程テキスト
    LLM-->>RF: 適用ルール(上限額, 必須項目, 禁止事項)
    RF-->>Runner: output_key: "extracted_rules"

    Runner->>EC: Step 2: 審査判定
    alt 領収書画像あり
        EC->>Drive: 領収書画像ダウンロード
        Drive-->>EC: 画像バイナリ
    end
    EC->>LLM: {extracted_rules} + 申請データ + 領収書画像
    LLM-->>EC: JSON(status, confidence_score, details)
    EC-->>Runner: output_key: "check_result"

    Note over Runner: Sequential実行完了

    Runner-->>FastAPI: ExpenseCheckResponse
    FastAPI-->>Client: 200 OK (JSON)
```

## ディレクトリ構成

```
expense-agent-workflow/
├── compose.yaml
├── docker/
│   ├── dev.Dockerfile
│   └── prod.Dockerfile
├── deploy_cloudrun.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .editorconfig
├── .env.example
├── src/
│   ├── config.py
│   ├── main.py
│   ├── schemas.py
│   ├── agents/
│   │   ├── rule_finder.py
│   │   ├── expense_checker.py
│   │   └── router.py
│   └── services/
│       ├── drive.py
│       └── sheets.py
├── tests/
│   ├── test_config.py
│   ├── test_schemas.py
│   ├── test_rule_finder.py
│   ├── test_expense_checker.py
│   ├── test_router.py
│   ├── test_main.py
│   ├── test_drive.py
│   └── test_sheets.py
├── gas/
│   ├── form_trigger.gs
│   └── README.md
└── .kiro/
    ├── agents/expense-agent.json
    └── hooks/lint-and-format.sh
```

## セットアップ

### 前提条件

- Docker & Docker Compose
- **demo モード:** Google API Key
- **production モード:** GCP プロジェクト + サービスアカウント

### ローカル開発（demo モード）

```bash
cp .env.example .env
# .env の GOOGLE_API_KEY を設定

docker compose up
```

### Production モード設定

```bash
# .env を編集
EXPENSE_MODE=production
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=asia-northeast1
GEMINI_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
DRIVE_RULES_FILE_ID=your-rules-doc-file-id
DRIVE_RECEIPTS_FOLDER_ID=your-receipts-folder-id
SHEETS_FORM_RESPONSES_ID=your-spreadsheet-id

docker compose up
```

### テスト実行

```bash
pytest tests/ -v
```

### Lint / Format（Google Python Style Guide準拠）

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## 環境変数一覧

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `EXPENSE_MODE` | - | `demo` | 動作モード (`demo` / `production`) |
| `GOOGLE_API_KEY` | demo時 | - | Gemini API キー |
| `GOOGLE_GENAI_USE_VERTEXAI` | production時 | `false` | Vertex AI使用フラグ |
| `GOOGLE_CLOUD_PROJECT` | production時 | - | GCPプロジェクトID |
| `GOOGLE_CLOUD_LOCATION` | - | `asia-northeast1` | Cloud Runデプロイリージョン |
| `GEMINI_LOCATION` | - | `global` | Vertex AIモデル呼び出しリージョン |
| `DRIVE_RULES_FILE_ID` | - | - | 社内規程ドキュメントのDriveファイルID |
| `DRIVE_RECEIPTS_FOLDER_ID` | - | - | 領収書フォルダのDrive ID |
| `SHEETS_FORM_RESPONSES_ID` | - | - | Formの回答スプレッドシートID |
| `GOOGLE_APPLICATION_CREDENTIALS` | production時(ローカル) | - | サービスアカウントJSONパス |

## API仕様

### POST /api/expense-check

**リクエスト:**

```json
{
  "type": "社内懇親会",
  "amount": 24000,
  "count": 6,
  "participants_raw": "田中太郎、山田花子、佐藤一郎、鈴木次郎、高橋三郎、伊藤四郎",
  "purpose": "チームビルディング",
  "receipt_url": "https://drive.google.com/file/d/FILE_ID/view"
}
```

**レスポンス:**

```json
{
  "status": "承認",
  "confidence_score": 4.5,
  "details": {
    "per_person_amount": 4000,
    "limit_amount": 5000,
    "required_items_check": "全員の氏名あり",
    "prohibition_check": "該当なし",
    "receipt_check": "宛名: 株式会社テスト、金額一致"
  },
  "rejection_reason": null
}
```

## 社内規程（demo モードの組み込みルール）

| カテゴリ | 1人あたり上限 | 必須項目 |
|---|---|---|
| 社内懇親会 | 5,000円 | 全員の氏名 |
| 社外接待 | 10,000円（役員同席時15,000円） | 取引先名、目的 |

**禁止事項:** 領収書の宛名「上様」は一切不可

## Cloud Run デプロイ

### デプロイスクリプト（推奨）

```bash
cp .env.example .env
# .env にプロジェクトID等を設定

python deploy_cloudrun.py
```

デプロイスクリプトが自動で行うこと:
1. サービスアカウント `expense-agent@PROJECT_ID.iam.gserviceaccount.com` を作成
2. 必要なIAMロールを付与（Vertex AI, Drive, Cloud Run等）
3. `adk deploy cloud_run` でCloud Runにデプロイ

### 手動デプロイ（Dockerイメージ）

```bash
docker build -f docker/prod.Dockerfile -t expense-agent .

gcloud run deploy expense-agent \
  --image gcr.io/PROJECT_ID/expense-agent \
  --platform managed \
  --region asia-northeast1 \
  --set-env-vars "EXPENSE_MODE=production,GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=PROJECT_ID,GEMINI_LOCATION=global" \
  --service-account expense-agent@PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 技術スタック

| 項目 | 技術 |
|---|---|
| フレームワーク | FastAPI (lifespan pattern) |
| AIエージェント | Google ADK 1.5 (SequentialAgent + InMemoryRunner) |
| LLM (demo) | Gemini 3.5 Flash (Gemini API) |
| LLM (production) | Gemini 3.1 Flash-Lite (Vertex AI, global) |
| バリデーション | Pydantic 2.11 |
| 設定管理 | pydantic-settings |
| Google API | google-api-python-client (Drive, Sheets) |
| 認証 | google-auth（サービスアカウント / APIキー） |
| サーバー | Uvicorn |
| コンテナ | Docker (python:3.13-slim) |
| デプロイ先 | Google Cloud Run |
| Linter/Formatter | Ruff (Google Python Style Guide準拠, 80文字) |
| テスト | pytest + pytest-asyncio + httpx |
| GAS連携 | Google Apps Script (Form → API → Sheets) |
