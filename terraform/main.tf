# 経費精算エージェント用ランタイムサービスアカウント
# Cloud Runコンテナが実行時に使用する（Vertex AI呼び出し + ログ書き込みのみ）。
resource "google_service_account" "expense_agent" {
  account_id   = "expense-agent"
  display_name = "Expense Agent Service Account"
  project      = var.project_id
}

# 実行時に必要な最小限のIAMロール。
# イメージのbuild/pushは実行者本人の認証情報で行うため、
# デプロイ用の広範なロール（cloudbuild.builds.builder等）はここでは付与しない。
resource "google_project_iam_member" "expense_agent_roles" {
  for_each = toset([
    "roles/aiplatform.user",   # Vertex AI (Gemini) 呼び出し
    "roles/logging.logWriter", # Cloud Logging書き込み
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.expense_agent.email}"
}

# コンテナイメージ格納用のArtifact Registryリポジトリ
resource "google_artifact_registry_repository" "expense_agent" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "経費精算エージェントのコンテナイメージ"
}
