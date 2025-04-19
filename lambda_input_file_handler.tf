# Lambda IAM Role
data "aws_iam_policy_document" "input_file_handler" {
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
    resources = [aws_sqs_queue.input_file.arn]
  }

  statement {
    sid     = "AllowAccessSqsKms"
    effect  = "Allow"
    actions = ["kms:Decrypt"]
    resources = [
      aws_kms_key.slack_llm.arn
    ]
  }

  statement {
    sid    = "AllowReadWriteFileInS3"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetBucketAcl",
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = [
      aws_s3_bucket.input_file.arn,
      "${aws_s3_bucket.input_file.arn}/*",
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

resource "aws_iam_role" "input_file_handler" {
  name               = local.input_file_handler.iam_role
  assume_role_policy = data.aws_iam_policy_document.lmbd_assume_policy.json
}

resource "aws_iam_role_policy" "input_file_handler" {
  name   = local.input_file_handler.iam_role
  role   = aws_iam_role.input_file_handler.id
  policy = data.aws_iam_policy_document.input_file_handler.json
}

# Lambda source code
data "archive_file" "input_file_handler" {
  type             = "zip"
  source_dir       = "${path.module}/lambda_input_file_handler/"
  output_file_mode = "0666"
  output_path      = "${path.module}/files/lambda_input_file_handler.zip"
}

# Lambda setup
resource "aws_lambda_function" "input_file_handler" {
  function_name    = local.input_file_handler.lambda
  runtime          = "python3.12"
  filename         = data.archive_file.input_file_handler.output_path
  source_code_hash = data.archive_file.input_file_handler.output_base64sha256
  role             = aws_iam_role.input_file_handler.arn
  memory_size      = 256
  timeout          = 300
  handler          = "lambda_function.lambda_handler"
  layers = [
    aws_lambda_layer_version.slack_sdk.arn,
    aws_lambda_layer_version.openai_sdk.arn, # with httpx library
  ]

  environment {
    variables = {
      slack_oauth_token      = local.slack_oauth_token
      input_file_sqs_url     = aws_sqs_queue.input_file.url
      input_file_bucket_name = aws_s3_bucket.input_file.id
    }
  }
}

resource "aws_lambda_function_event_invoke_config" "input_file_handler" {
  function_name                = aws_lambda_function.input_file_handler.function_name
  maximum_event_age_in_seconds = 1200
  maximum_retry_attempts       = 0
}

# SQS to trigger msg handler lambda
resource "aws_lambda_event_source_mapping" "input_file_handler" {
  event_source_arn = aws_sqs_queue.input_file.arn
  function_name    = aws_lambda_function.input_file_handler.arn
  enabled          = true
}

# Allow SQS to invoke lambda
resource "aws_lambda_permission" "input_file_handler" {
  statement_id  = "AllowExecutionFromSQS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.input_file_handler.arn
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.input_file.arn
}

