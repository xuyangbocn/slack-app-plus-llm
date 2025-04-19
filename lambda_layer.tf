# Lambda layer for slack-sdk
data "archive_file" "slack_sdk" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_layer/py_slack_sdk/"
  output_path = "${path.module}/files/py_slack_sdk.zip"
}

resource "aws_lambda_layer_version" "slack_sdk" {
  layer_name               = "py-slack-sdk"
  description              = "Include slack-sdk"
  compatible_architectures = ["x86_64", "arm64"]
  compatible_runtimes      = ["python3.10", "python3.11", "python3.12", "python3.13"]

  filename         = data.archive_file.slack_sdk.output_path
  source_code_hash = data.archive_file.slack_sdk.output_base64sha256
}

# Lambda layer for openai-sdk
data "archive_file" "openai_sdk" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_layer/py_openai_sdk/"
  output_path = "${path.module}/files/py_openai_sdk.zip"
}

resource "aws_lambda_layer_version" "openai_sdk" {
  layer_name               = "py-openai-sdk"
  description              = "Include openai-sdk"
  compatible_architectures = ["x86_64", "arm64"]
  compatible_runtimes      = ["python3.10", "python3.11", "python3.12", "python3.13"]

  filename         = data.archive_file.openai_sdk.output_path
  source_code_hash = data.archive_file.openai_sdk.output_base64sha256
}

# Lambda layer for gitlab-sdk
data "archive_file" "gitlab_sdk" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_layer/py_gitlab_sdk/"
  output_path = "${path.module}/files/py_gitlab_sdk.zip"
}

resource "aws_lambda_layer_version" "gitlab_sdk" {
  layer_name               = "py-gitlab-sdk"
  description              = "Include gitlab-sdk"
  compatible_architectures = ["x86_64", "arm64"]
  compatible_runtimes      = ["python3.10", "python3.11", "python3.12", "python3.13"]

  filename         = data.archive_file.gitlab_sdk.output_path
  source_code_hash = data.archive_file.gitlab_sdk.output_base64sha256
}

# Lambda layer for jira-sdk
data "archive_file" "jira_sdk" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_layer/py_jira_sdk/"
  output_path = "${path.module}/files/py_jira_sdk.zip"
}

resource "aws_lambda_layer_version" "jira_sdk" {
  layer_name               = "py-jira-sdk"
  description              = "Include jira-sdk"
  compatible_architectures = ["x86_64", "arm64"]
  compatible_runtimes      = ["python3.10", "python3.11", "python3.12", "python3.13"]

  filename         = data.archive_file.jira_sdk.output_path
  source_code_hash = data.archive_file.jira_sdk.output_base64sha256
}
