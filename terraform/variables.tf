variable "project_id" {
  description = "デプロイ先のGCPプロジェクトID"
  type        = string
}

variable "region" {
  description = "Cloud Run / Artifact Registryのリージョン"
  type        = string
  default     = "asia-northeast1"
}

variable "service_name" {
  description = "Cloud Runサービス名"
  type        = string
  default     = "expense-agent"
}

variable "repository_id" {
  description = "Artifact Registryリポジトリ名"
  type        = string
  default     = "expense-agent"
}

variable "image_tag" {
  description = <<-EOT
    Cloud Runにデプロイするコンテナイメージの完全なタグ。
    未指定の場合はプレースホルダイメージを使用し、後段の
    `docker build && docker push` 完了後に再applyして更新する想定。
  EOT
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "allow_unauthenticated" {
  description = "未認証アクセスを許可するか（課題提出用の一時デモではtrue）"
  type        = bool
  default     = true
}
