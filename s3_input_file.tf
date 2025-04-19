# s3 bucket for input file
resource "aws_s3_bucket" "input_file" {
  bucket = local.input_file_handler.s3
}


resource "aws_s3_bucket_server_side_encryption_configuration" "input_file" {
  bucket = aws_s3_bucket.input_file.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.slack_llm.arn
      sse_algorithm     = "aws:kms"
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "input_file" {
  bucket = aws_s3_bucket.input_file.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "input_file" {
  depends_on = [aws_s3_bucket_versioning.input_file]

  bucket = aws_s3_bucket.input_file.id

  rule {
    id = "DeleteAfter366Days"

    filter {
      prefix = ""
    }

    expiration {
      days = 366
    }

    noncurrent_version_expiration {
      noncurrent_days = 366
    }

    status = "Enabled"
  }
}

data "aws_iam_policy_document" "input_file_s3_policy" {

  statement {
    sid    = "AllowReadWriteToS3"
    effect = "Allow"

    resources = [
      aws_s3_bucket.input_file.arn,
      "${aws_s3_bucket.input_file.arn}/*",
    ]

    principals {
      type = "AWS"
      identifiers = [
        aws_iam_role.input_file_handler.arn,
      ]
    }

    actions = [
      "s3:PutObject",
      "s3:GetBucketAcl",
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectVersion"
    ]
  }

  statement {
    sid    = "AllowReadToS3"
    effect = "Allow"

    resources = [
      aws_s3_bucket.input_file.arn,
      "${aws_s3_bucket.input_file.arn}/*",
    ]

    principals {
      type = "AWS"
      identifiers = [
        aws_iam_role.msg_handler.arn,
      ]
    }

    actions = [
      "s3:GetBucketAcl",
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectVersion"
    ]
  }

  statement {
    sid    = "DenyUnsecuredTransport"
    effect = "Deny"

    resources = [
      aws_s3_bucket.input_file.arn,
      "${aws_s3_bucket.input_file.arn}/*",
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = ["s3:*"]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

}

resource "aws_s3_bucket_policy" "input_file" {
  bucket = aws_s3_bucket.input_file.id
  policy = data.aws_iam_policy_document.input_file_s3_policy.json
}

resource "aws_s3_bucket_public_access_block" "input_file" {
  bucket                  = aws_s3_bucket.input_file.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "input_file" {
  bucket = aws_s3_bucket.input_file.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
