# resource "aws_dynamodb_table" "tool_call_audit" {
#   /*
#   Stores LLM Tool call audit log

#   contains key field: caller_id_tool_name, timestamp
#   and non-key field: function_args, function_resp
#   */

#   billing_mode = "PAY_PER_REQUEST"
#   name         = local.msg_handler.ddb_tool_call_audit
#   hash_key     = "caller_id_tool_name"
#   range_key    = "timestamp"

#   attribute {
#     name = "caller_id_tool_name"
#     type = "S"
#   }

#   attribute {
#     name = "timestamp"
#     type = "S"
#   }
# }

resource "aws_cloudwatch_log_group" "tool_call_audit" {
  name              = local.msg_handler.cwlg_tool_call_audit
  retention_in_days = 365
}

resource "aws_cloudwatch_log_stream" "func_call" {
  name           = local.msg_handler.cwls_func_call_audit
  log_group_name = aws_cloudwatch_log_group.tool_call_audit.name
}
