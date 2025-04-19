resource "random_string" "x" {
  length    = 5
  min_lower = 5
  special   = false
}

locals {
  region     = var.region
  account_id = data.aws_caller_identity.current.account_id

  slack_app_ids     = [for k, v in var.slack_app : k]
  slack_app_tokens  = [for k, v in var.slack_app : v]
  slack_oauth_token = var.slack_oauth_token

  kms = "kms-${var.name}-${random_string.x.id}"

  msg_receiver = {
    iam_role = "iamr-receiver-${var.name}-${random_string.x.id}"
    lambda   = "lmbd-receiver-${var.name}-${random_string.x.id}"
    sqs      = "sqs-event-${var.name}-${random_string.x.id}"
  }

  msg_handler = {
    iam_role             = "iamr-handler-${var.name}-${random_string.x.id}"
    lambda               = "lmbd-handler-${var.name}-${random_string.x.id}"
    lambda_mem           = var.lambda_msg_handler_mem
    lambda_timeout       = var.lambda_msg_handler_timeout
    ddb_asst_thread      = "ddb-asst-thread-${var.name}-${random_string.x.id}"
    ddb_chat_completion  = "ddb-chat-completion-${var.name}-${random_string.x.id}"
    cwlg_tool_call_audit = "cwlg-tool-call-audit-${var.name}-${random_string.x.id}"
    cwls_func_call_audit = "function_calls"
  }

  input_file_handler = {
    iam_role = "iamr-input-file-${var.name}-${random_string.x.id}"
    lambda   = "lmbd-input-file-${var.name}-${random_string.x.id}"
    sqs      = "sqs-input-file-${var.name}-${random_string.x.id}"
    s3       = "s3-input-file-${var.name}-${random_string.x.id}"
  }
}
