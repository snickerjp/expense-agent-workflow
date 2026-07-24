resource "google_cloud_run_v2_service" "expense_agent" {
  name     = var.service_name
  project  = var.project_id
  location = var.region

  # 作成・破棄を繰り返す運用のため保護を無効化
  deletion_protection = false

  template {
    service_account = google_service_account.expense_agent.email

    containers {
      image = var.image_tag

      env {
        name  = "EXPENSE_MODE"
        value = "production"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "1"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
    }
  }

  # docker push後の再applyで image_tag のみ更新する運用のため、
  # Terraform管理外のクライアント側変更（トラフィック分割等）は無視しない。
  depends_on = [
    google_artifact_registry_repository.expense_agent,
    google_project_iam_member.expense_agent_roles,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.expense_agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
