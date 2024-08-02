resource "aws_dynamodb_table" "chat_completion" {

  /*
  Stores history message in each Slack thread (slack thread retrieval is rate limited low, ~50/min/workspace)
  in order to facilitate chat completion api
  Not needed for assistant api
  
  contains key field: slack_channel_id_thread_ts, slack_event_ts
  and non-key field : role, content
  */

  billing_mode = "PAY_PER_REQUEST"
  name         = local.msg_handler.ddb_chat_completion
  hash_key     = "slack_channel_id_thread_ts"
  range_key    = "slack_event_ts"

  attribute {
    name = "slack_channel_id_thread_ts"
    type = "S"
  }

  attribute {
    name = "slack_event_ts"
    type = "S"
  }
}
