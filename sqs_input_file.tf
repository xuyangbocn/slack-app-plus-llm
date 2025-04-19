# SQS storing input file from slack event
resource "aws_sqs_queue" "input_file" {
  name                       = local.input_file_handler.sqs
  visibility_timeout_seconds = 600
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  message_retention_seconds  = 604800
  max_message_size           = 262144

  kms_master_key_id                 = aws_kms_key.slack_llm.key_id
  kms_data_key_reuse_period_seconds = 600

  policy = data.aws_iam_policy_document.input_file_sqs_policy.json
}

data "aws_iam_policy_document" "input_file_sqs_policy" {
  statement {
    sid       = "AllowReceiverPushMsg"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.input_file_handler.sqs}"]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.msg_receiver.arn]
    }
  }

  statement {
    sid    = "AllowHandlerToConsume"
    effect = "Allow"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ReceiveMessage"
    ]
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.input_file_handler.sqs}"]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.input_file_handler.arn]
    }
  }

  statement {
    sid    = "DenyOtherConsumersFromReceiving"
    effect = "Deny"
    actions = [
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:ReceiveMessage"
    ]
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.input_file_handler.sqs}"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotLike"
      variable = "aws:PrincipalARN"
      values = [
        aws_iam_role.msg_handler.arn,
        aws_iam_role.input_file_handler.arn,
      ]
    }
  }
}
