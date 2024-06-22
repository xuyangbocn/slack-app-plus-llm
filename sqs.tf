# kms for sqs
resource "aws_kms_key" "msg_receiver" {
  description         = "Key to encrypt sqs for received slack events"
  policy              = data.aws_iam_policy_document.kms_policy_msg_receiver.json
  enable_key_rotation = true
}

resource "aws_kms_alias" "msg_receiver" {
  name          = "alias/${local.msg_receiver.kms}"
  target_key_id = aws_kms_key.msg_receiver.key_id
}

data "aws_iam_policy_document" "kms_policy_msg_receiver" {
  statement {
    sid       = "AllowOwnAccount"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
  }

  statement {
    sid    = "AllowReceiverPushMsg"
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.msg_receiver.arn]
    }
  }

  statement {
    sid       = "AllowHandlerToConsume"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.msg_handler.arn]
    }
  }
}

# SQS storing slack event
resource "aws_sqs_queue" "msg_receiver" {
  name                       = local.msg_receiver.sqs
  visibility_timeout_seconds = 600
  delay_seconds              = 0
  receive_wait_time_seconds  = 0
  message_retention_seconds  = 604800
  max_message_size           = 262144

  kms_master_key_id                 = aws_kms_key.msg_receiver.key_id
  kms_data_key_reuse_period_seconds = 600

  policy = data.aws_iam_policy_document.sqs_policy_msg_receiver.json
}

data "aws_iam_policy_document" "sqs_policy_msg_receiver" {
  statement {
    sid       = "AllowReceiverPushMsg"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.msg_receiver.sqs}"]

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
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.msg_receiver.sqs}"]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.msg_handler.arn]
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
    resources = ["arn:aws:sqs:${local.region}:${local.account_id}:${local.msg_receiver.sqs}"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotLike"
      variable = "aws:PrincipalARN"
      values   = [aws_iam_role.msg_handler.arn]
    }
  }
}
