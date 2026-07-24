output "service_url" {
  description = "Cloud RunサービスのURL"
  value       = google_cloud_run_v2_service.expense_agent.uri
}

output "service_account_email" {
  description = "ランタイムサービスアカウントのメールアドレス"
  value       = google_service_account.expense_agent.email
}

output "artifact_registry_repository" {
  description = "コンテナイメージ格納先のArtifact Registryリポジトリパス"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}"
}
