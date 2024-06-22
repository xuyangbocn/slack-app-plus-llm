import os
import json
import logging
import boto3

from slack_msg_handler import handler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        handler(body)

        # Delete message from SQS
        logger.info("Delete from sqs")
        sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=sqs_receipt_handle)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
