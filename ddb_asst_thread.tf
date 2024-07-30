resource "aws_dynamodb_table" "asst_thread" {
  billing_mode = "PAY_PER_REQUEST"
  name         = local.msg_handler.ddb_asst_thread
  hash_key     = "slack_channel_id"
  range_key    = "slack_thread_ts"

  attribute {
    name = "slack_channel_id"
    type = "S"
  }

  attribute {
    name = "slack_thread_ts"
    type = "S"
  }
}
