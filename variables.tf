variable "region" {
  description = "Region to deploy the slack event handler setup"
  type        = string
  default     = "ap-southeast-1"
}

variable "msg_receiver_name" {
  description = "Name suffix for resources that is used as endpoint for slack msg event"
  type        = string
  default     = "slack_msg_receiver"
}

variable "msg_handler_name" {
  description = "Name suffix for resources that is used to handle slack msg"
  type        = string
  default     = "slack_msg_handler"
}

variable "lambda_msg_handler_timeout" {
  description = "Lambda timeout in second for msg handler"
  type        = number
  default     = 300
}

variable "lambda_msg_handler_mem" {
  description = "Lambda mem in MB for msg handler"
  type        = number
  default     = 128
}

variable "slack_app" {
  #   Ex: {
  #     "app_a_id" : "app_a_verification_token",
  #     "app_b_id" : "app_b_verification_token",
  #   }
  description = "List of Slack App (its id and verification token) that are sending to the receiver lambda"
  type        = map(string)
}

variable "slack_oauth_token" {
  description = "Slack oauth token that allows actions that handler needs to perform (E.g. 1. find user by email, 2. send of message). This can be ommitted if event handling logic does not require to perform any Slack api call."
  type        = string
  default     = ""
}
