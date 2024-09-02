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

  msg_receiver = {
    iam_role = "iamr-${var.msg_receiver_name}-${random_string.x.id}"
    lambda   = "lmbd-${var.msg_receiver_name}-${random_string.x.id}"
    sqs      = "sqs-${var.msg_receiver_name}-${random_string.x.id}"
    kms      = "kms-${var.msg_receiver_name}-${random_string.x.id}"
  }

  msg_handler = {
    iam_role             = "iamr-${var.msg_handler_name}-${random_string.x.id}"
    lambda               = "lmbd-${var.msg_handler_name}-${random_string.x.id}"
    lambda_mem           = var.lambda_msg_handler_mem
    lambda_timeout       = var.lambda_msg_handler_timeout
    ddb_asst_thread      = "ddb-asst-thread-${random_string.x.id}"
    ddb_chat_completion  = "ddb-chat-completion-${random_string.x.id}"
    cwlg_tool_call_audit = "cwlg-tool-call-audit-${random_string.x.id}"
    cwls_func_call_audit = "function_calls"
  }
}
