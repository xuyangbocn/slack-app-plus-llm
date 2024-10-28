# Lambda IAM Role
data "aws_iam_policy_document" "lmbd_role_policy_msg_handler" {
  statement {
    sid    = "AllowCreateLog"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:${local.account_id}:*",
      "${aws_cloudwatch_log_group.tool_call_audit.arn}:*",
    ]
  }

  statement {
    sid    = "AllowConsumeSqsMsg"
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ReceiveMessage",
      "sqs:GetQueueUrl",
    ]
    resources = [aws_sqs_queue.msg_receiver.arn]
  }

  statement {
    sid       = "AllowAccessSqsKms"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.msg_receiver.arn]
  }

  statement {
    sid    = "AllowReadWriteAsstThreadAndChatCompletionDDB"
    effect = "Allow"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.asst_thread.arn,
      aws_dynamodb_table.chat_completion.arn
    ]
  }

  statement {
    sid    = "AllowAssumeCrossAccountRole"
    effect = "Allow"
    actions = [
      "sts:AssumeRole"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "msg_handler" {
  name               = local.msg_handler.iam_role
  assume_role_policy = data.aws_iam_policy_document.lmbd_assume_policy.json
}

resource "aws_iam_role_policy" "lmbd_role_policy_msg_handler" {
  name   = local.msg_handler.iam_role
  role   = aws_iam_role.msg_handler.id
  policy = data.aws_iam_policy_document.lmbd_role_policy_msg_handler.json
}

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
  compatible_runtimes      = ["python3.9", "python3.10", "python3.11", "python3.12"]

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
  compatible_runtimes      = ["python3.9", "python3.10", "python3.11", "python3.12"]

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
  compatible_runtimes      = ["python3.9", "python3.10", "python3.11", "python3.12"]

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
  compatible_runtimes      = ["python3.9", "python3.10", "python3.11", "python3.12"]

  filename         = data.archive_file.jira_sdk.output_path
  source_code_hash = data.archive_file.jira_sdk.output_base64sha256
}

# Lambda source code
data "archive_file" "msg_handler" {
  type             = "zip"
  source_dir       = "${path.module}/lambda_msg_handler/"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_msg_handler.zip"
}

# Lambda setup
resource "aws_lambda_function" "msg_handler" {
  function_name    = local.msg_handler.lambda
  runtime          = "python3.12"
  filename         = data.archive_file.msg_handler.output_path
  source_code_hash = data.archive_file.msg_handler.output_base64sha256
  role             = aws_iam_role.msg_handler.arn
  memory_size      = local.msg_handler.lambda_mem
  timeout          = local.msg_handler.lambda_timeout
  handler          = "lambda_function.lambda_handler"
  layers = [
    aws_lambda_layer_version.slack_sdk.arn,
    aws_lambda_layer_version.openai_sdk.arn,
    aws_lambda_layer_version.gitlab_sdk.arn,
    aws_lambda_layer_version.jira_sdk.arn,
  ]

  environment {
    variables = {
      sqs_url                     = aws_sqs_queue.msg_receiver.url
      slack_oauth_token           = local.slack_oauth_token
      ddb_asst_thread             = local.msg_handler.ddb_asst_thread
      ddb_chat_completion         = local.msg_handler.ddb_chat_completion
      cwlg_tool_call_audit        = local.msg_handler.cwlg_tool_call_audit
      cwls_func_call_audit        = local.msg_handler.cwls_func_call_audit
      openai_api_key              = var.openai_handler_vars.api_key
      openai_gpt_model            = var.openai_handler_vars.model
      openai_asst_instructions    = var.openai_handler_vars.asst_instructions
      az_openai_endpoint          = var.az_openai_handler_vars.endpoint
      az_openai_api_key           = var.az_openai_handler_vars.api_key
      az_openai_api_version       = var.az_openai_handler_vars.api_version
      az_openai_deployment_name   = var.az_openai_handler_vars.deployment_name
      az_openai_asst_instructions = var.az_openai_handler_vars.asst_instructions
      az_data_source              = jsonencode(var.az_openai_handler_vars.az_data_source)
      llm_tools_vars              = jsonencode(var.llm_tools_vars)
    }
  }
}

resource "aws_lambda_function_event_invoke_config" "msg_handler" {
  function_name                = aws_lambda_function.msg_handler.function_name
  maximum_event_age_in_seconds = 1200
  maximum_retry_attempts       = 0
}

# SQS to trigger msg handler lambda
resource "aws_lambda_event_source_mapping" "msg_handler" {
  event_source_arn = aws_sqs_queue.msg_receiver.arn
  function_name    = aws_lambda_function.msg_handler.arn
  enabled          = true
}

# Allow SQS to invoke lambda
resource "aws_lambda_permission" "msg_handler" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.msg_receiver.arn
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.msg_receiver.arn
}

