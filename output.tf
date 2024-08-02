output "msg_receiver_lambda_function_url" {
  description = "Endpoint to fill into Slack App Event subscription"
  value       = aws_lambda_function_url.msg_receiver.function_url
}

output "msg_handler_lambda_iam_role_arn" {
  description = "Arn of the handler lambda IAM role"
  value       = aws_iam_role.msg_handler.arn
}
