locals {
  region     = var.region
  account_id = data.aws_caller_identity.current.account_id

  slack_app_ids     = [for k, v in var.slack_app : k]
  slack_app_tokens  = [for k, v in var.slack_app : v]
  slack_oauth_token = var.slack_oauth_token

  msg_receiver = {
    iam_role = "iamr-${var.msg_receiver_name}"
    lambda   = "lmbd-${var.msg_receiver_name}"
    sqs      = "sqs-${var.msg_receiver_name}"
    kms      = "kms-${var.msg_receiver_name}"
  }

  msg_handler = {
    iam_role        = "iamr-${var.msg_handler_name}"
    lambda          = "lmbd-${var.msg_handler_name}"
    lambda_mem      = var.lambda_msg_handler_mem
    lambda_timeout  = var.lambda_msg_handler_timeout
    ddb_asst_thread = "ddb-asst-thread"
  }
}
