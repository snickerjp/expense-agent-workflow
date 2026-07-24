# Terraform (Cloud Run デプロイ用IaC)

サービスアカウント・Artifact Registry・Cloud Runサービスを IaC で管理する。
`terraform apply` / `terraform destroy` で作成・破棄を繰り返せる。

## 使い方

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars の project_id を編集

terraform init
terraform apply   # 1回目: SA / Artifact Registry / Cloud Run(プレースホルダイメージ) を作成
```

Artifact Registryリポジトリ作成後、アプリのイメージをbuild & pushする（Terraformはイメージのbuildを行わない）。

```bash
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
docker build -f ../docker/prod.Dockerfile -t asia-northeast1-docker.pkg.dev/PROJECT_ID/expense-agent/expense-agent:latest ..
docker push asia-northeast1-docker.pkg.dev/PROJECT_ID/expense-agent/expense-agent:latest
```

再度applyしてCloud Runのイメージを実イメージに更新する。

```bash
terraform apply -var="image_tag=asia-northeast1-docker.pkg.dev/PROJECT_ID/expense-agent/expense-agent:latest"
```

## 破棄

```bash
terraform destroy
```

## 注意

- `GOOGLE_API_KEY` はTerraformでは管理しない（productionモードはVertex AI認証のため不要）。
- Drive/Sheets連携用の環境変数（`DRIVE_RULES_FILE_ID`等）は未設定でも動作する
  （`rule_finder`はハードコードルールにフォールバックし、`receipt_url`なしのリクエストなら画像取得も走らない）。
  連携する場合は `cloud_run.tf` の `env` ブロックに追加する。
