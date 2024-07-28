import os
import json
import logging
import boto3
from slack_sdk import WebClient

# from msg_handlers.sample_handler import handler as sample_handler
# from msg_handlers.tag_user_handler import handler as tag_user_handler
from msg_handlers.openai_handler import handler as openai_handler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Slack client
slack_oauth_token = os.environ["slack_oauth_token"]
slack = WebClient(token=slack_oauth_token)

sqs = boto3.client('sqs')
sqs_url = sqs.get_queue_url(
    QueueName=os.environ['sqs_name'],
    QueueOwnerAWSAccountId=os.environ['sqs_owner_account'],
)['QueueUrl']


def lambda_handler(event, context):
    for sqs_msg in event['Records']:
        msg_id = sqs_msg['messageId']
        sqs_receipt_handle = sqs_msg['receiptHandle']

        # Get sqs message body (i.e. slack event)
        json_body = sqs_msg["body"]
        body = json.loads(json_body)
        logger.debug(json.dumps(body, indent=2))

        # Message handling
        openai_handler(body, slack_client=slack)

        # Delete message from SQS
        logger.info("Delete from sqs")
        sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=sqs_receipt_handle)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
