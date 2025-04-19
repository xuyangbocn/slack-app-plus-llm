# kms for all used sqs and s3
resource "aws_kms_key" "slack_llm" {
  description         = "Key to encrypt s3 or sqs"
  policy              = data.aws_iam_policy_document.slack_llm.json
  enable_key_rotation = true
}

resource "aws_kms_alias" "slack_llm" {
  name          = "alias/${local.kms}"
  target_key_id = aws_kms_key.slack_llm.key_id
}

data "aws_iam_policy_document" "slack_llm" {
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
    sid    = "AllowReadWriteToS3AndSQS"
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = ["*"]
    principals {
      type = "AWS"
      identifiers = [
        aws_iam_role.input_file_handler.arn,
        aws_iam_role.msg_receiver.arn,
      ]
    }
  }

  statement {
    sid       = "AllowReadOnlyToS3AndSQS"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    principals {
      type = "AWS"
      identifiers = [
        aws_iam_role.msg_handler.arn
      ]
    }
  }
}
