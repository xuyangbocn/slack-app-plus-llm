resource "aws_dynamodb_table" "asst_thread" {
  /*
  Stores Assistance thread id Mapping to Slack thread id
  in order to facilitate assistant api
  
  contains key field: slack_channel_id, slack_thread_ts
  and non-key field: asst_thread_id

  TBD: consider again the choice of key, and data type for thread ts be N?
  */

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
