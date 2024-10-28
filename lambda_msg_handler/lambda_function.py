import os
import json
import logging
import boto3

# from msg_handlers.sample_handler import handler
# from msg_handlers.tag_user_handler import handler
# from msg_handlers.az_openai_handler import handler_via_assistant as handler
# from msg_handlers.az_openai_handler import handler_via_chat_completion as handler
from msg_handlers.openai_handler import handler_via_assistant as handler
# from msg_handlers.openai_handler import handler_via_chat_completion as handler
# from msg_handlers.aws_reinvent_helper_handler import handler_via_chat_completion as handler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')
sqs_url = os.environ['sqs_url']


def lambda_handler(event, context):
    for sqs_msg in event['Records']:
        msg_id = sqs_msg['messageId']
        sqs_receipt_handle = sqs_msg['receiptHandle']

        # Get sqs message body (i.e. slack event)
        json_body = sqs_msg["body"]
        body = json.loads(json_body)
        logger.debug(json.dumps(body, indent=2))

        # Message handling
        try:
            handler(body)
        except Exception as error:
            logger.error(f"Error at event handling: {str(error)}")
            # TBD another queue to capture failed message

        # Delete message from SQS
        logger.info("Delete from sqs")
        sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=sqs_receipt_handle)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
