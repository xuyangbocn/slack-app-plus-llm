output "msg_receiver_lambda_function_url" {
  description = "Endpoint to fill into Slack App Event subscription"
  value       = aws_lambda_function_url.msg_receiver.function_url
}
