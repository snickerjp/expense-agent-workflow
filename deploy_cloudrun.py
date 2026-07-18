"""Cloud Run deployment script for Expense Agent Workflow.

Usage:
    1. Create .env file with GOOGLE_CLOUD_PROJECT=your-project-id
    2. Run: python deploy_cloudrun.py

Based on: https://raw.githubusercontent.com/haren-bh/codelabs/main/adk_visual_builder/deploycloudrun.py
"""

import os
import subprocess

from dotenv import load_dotenv


def run_command(command, error_msg, capture=True):
    """Utility to run shell commands."""
    try:
        result = subprocess.run(
            command, check=True, text=True, capture_output=capture
        )
        return result.stdout.strip() if capture else True
    except subprocess.CalledProcessError as e:
        print(f"❌ {error_msg}")
        if capture:
            print(f"Error details: {e.stderr}")
        return None


def setup_service_account(project_id):
    """Ensures the service account exists and has the necessary roles."""
    sa_name = "expense-agent"
    sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"

    # 1. Check if Service Account exists
    print(f"🔍 Checking if service account {sa_email} exists...")
    check_cmd = [
        "gcloud",
        "iam",
        "service-accounts",
        "describe",
        sa_email,
        f"--project={project_id}",
        "--format=json",
    ]
    if (
        run_command(
            check_cmd,
            "Service account not found, attempting to create...",
            capture=True,
        )
        is None
    ):
        print(f"🛠️ Creating service account: {sa_name}...")
        create_cmd = [
            "gcloud",
            "iam",
            "service-accounts",
            "create",
            sa_name,
            "--display-name=Expense Agent Service Account",
            f"--project={project_id}",
        ]
        run_command(create_cmd, "Failed to create service account.")
    else:
        print(f"✅ Service account {sa_name} already exists.")

    # 2. Define roles to assign
    roles = [
        "roles/cloudbuild.builds.builder",
        "roles/iam.serviceAccountUser",
        "roles/storage.admin",
        "roles/aiplatform.user",  # Vertex AI - Gemini calls
        "roles/run.admin",  # Cloud Run management
        "roles/logging.logWriter",  # Cloud Logging
        "roles/artifactregistry.writer",  # Container Registry
        "roles/drive.metadata.reader",  # Google Drive metadata
        "roles/drive.readonly",  # Drive file download
    ]

    print(f"🔐 Assigning IAM roles to {sa_email}...")
    for role in roles:
        bind_cmd = [
            "gcloud",
            "projects",
            "add-iam-policy-binding",
            project_id,
            f"--member=serviceAccount:{sa_email}",
            f"--role={role}",
            "--quiet",
        ]
        run_command(bind_cmd, f"Failed to assign role {role}")

    return sa_email


def deploy_agent():
    """Deploy the expense agent to Cloud Run."""
    # 1. Load configuration
    load_dotenv()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        print("❌ Error: GOOGLE_CLOUD_PROJECT not found in .env file.")
        print(
            "   Create a .env file with: GOOGLE_CLOUD_PROJECT=your-project-id"
        )
        return

    # Configuration values
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-northeast1")
    agent_path = "./src/agents"
    service_name = "expense-agent"
    app_name = "expense-agent"

    # Optional env vars for production mode
    drive_rules_file_id = os.getenv("DRIVE_RULES_FILE_ID", "")
    drive_receipts_folder_id = os.getenv("DRIVE_RECEIPTS_FOLDER_ID", "")
    sheets_form_responses_id = os.getenv("SHEETS_FORM_RESPONSES_ID", "")

    # 2. Setup Service Account and Permissions
    sa_email = setup_service_account(project_id)
    if not sa_email:
        return

    # 3. Execute Deployment Command
    command = [
        "adk",
        "deploy",
        "cloud_run",
        f"--project={project_id}",
        f"--region={location}",
        f"--service_name={service_name}",
        f"--app_name={app_name}",
        "--artifact_service_uri=memory://",
        "--with_ui",
        agent_path,
        "--",
        f"--service-account={sa_email}",
        f"--build-service-account=projects/{project_id}/serviceAccounts/{sa_email}",
        f"--set-env-vars=EXPENSE_MODE=production"
        f",GOOGLE_CLOUD_PROJECT={project_id}"
        f",GOOGLE_CLOUD_LOCATION={location}"
        f",DRIVE_RULES_FILE_ID={drive_rules_file_id}"
        f",DRIVE_RECEIPTS_FOLDER_ID={drive_receipts_folder_id}"
        f",SHEETS_FORM_RESPONSES_ID={sheets_form_responses_id}",
    ]

    print(
        f"\n🚀 Deploying '{app_name}' to Cloud Run in {project_id} ({location})"
    )
    print(f"   Service Account: {sa_email}")
    print("   Mode: production (Vertex AI + Drive + Sheets)")
    print()

    # capture_output=False shows real-time logs
    run_command(command, "Deployment failed. Check logs above.", capture=False)


if __name__ == "__main__":
    deploy_agent()
