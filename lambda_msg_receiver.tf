# Lambda IAM Role
data "aws_iam_policy_document" "lmbd_role_policy_msg_receiver" {
  statement {
    sid    = "AllowCreateLog"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:${local.account_id}:*"
    ]
  }

  statement {
    sid    = "AllowPushMsgToSQS"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueUrl",
    ]
    resources = [aws_sqs_queue.msg_receiver.arn]
  }

  statement {
    sid    = "AllowAccessSqsKms"
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = [aws_kms_key.msg_receiver.arn]
  }
}

resource "aws_iam_role" "msg_receiver" {
  name               = local.msg_receiver.iam_role
  assume_role_policy = data.aws_iam_policy_document.lmbd_assume_policy.json
}

resource "aws_iam_role_policy" "lmbd_role_policy_msg_receiver" {
  name   = local.msg_receiver.iam_role
  role   = aws_iam_role.msg_receiver.id
  policy = data.aws_iam_policy_document.lmbd_role_policy_msg_receiver.json
}

# Lambda source code
data "archive_file" "msg_receiver" {
  type             = "zip"
  source_dir       = "${path.module}/lambda_msg_receiver/"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_msg_receiver.zip"
}

# Lambda setup
resource "aws_lambda_function" "msg_receiver" {
  function_name    = local.msg_receiver.lambda
  runtime          = "python3.12"
  filename         = data.archive_file.msg_receiver.output_path
  source_code_hash = data.archive_file.msg_receiver.output_base64sha256
  role             = aws_iam_role.msg_receiver.arn
  memory_size      = 128
  timeout          = 30
  handler          = "lambda_function.lambda_handler"

  environment {
    variables = {
      sqs_url          = aws_sqs_queue.msg_receiver.url
      slack_app_tokens = join(",", local.slack_app_tokens)
      slack_app_ids    = join(",", local.slack_app_ids)
    }
  }
}

resource "aws_lambda_function_event_invoke_config" "msg_receiver" {
  function_name                = aws_lambda_function.msg_receiver.function_name
  maximum_event_age_in_seconds = 1200
  maximum_retry_attempts       = 0
}

resource "aws_lambda_function_url" "msg_receiver" {
  function_name      = aws_lambda_function.msg_receiver.function_name
  authorization_type = "NONE"
  cors {
    allow_credentials = true
    allow_origins     = ["*"]
    allow_methods     = ["POST"]
    allow_headers     = ["date", "keep-alive"]
    expose_headers    = ["keep-alive", "date"]
    max_age           = 86400
  }
}
