resource "aws_cloudwatch_log_group" "tool_call_audit" {
  name              = local.msg_handler.cwlg_tool_call_audit
  retention_in_days = 365
}

resource "aws_cloudwatch_log_stream" "func_call" {
  name           = local.msg_handler.cwls_func_call_audit
  log_group_name = aws_cloudwatch_log_group.tool_call_audit.name
}
