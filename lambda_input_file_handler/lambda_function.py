import os
import json
import logging
import base64
from io import BytesIO

import httpx
import boto3
import botocore
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')
s3 = boto3.client('s3')
sqs_url = os.environ['input_file_sqs_url']
s3_bucket = os.environ['input_file_bucket_name']

# Slack client
slack_oauth_token = os.environ["slack_oauth_token"]
slack = WebClient(token=slack_oauth_token)


def lambda_handler(event, context):
    for sqs_msg in event['Records']:
        msg_id = sqs_msg['messageId']
        sqs_receipt_handle = sqs_msg['receiptHandle']

        # Get sqs message body (i.e. slack event `file_shared`)
        json_body = sqs_msg["body"]
        body = json.loads(json_body)
        logger.debug(json.dumps(body, indent=2))

        # Process Input file
        try:
            team_id = body['team_id']
            file_id = body['event']['file_id']

            # Find slack download link
            # https://api.slack.com/methods/files.info
            file_info = slack.files_info(file=file_id)
            logger.debug(file_info)
            mimetype = file_info['file']['mimetype']
            name = file_info['file']['name']
            user = file_info['file']['user']
            url = file_info['file']['url_private_download']
            logger.info(f'input file url_private_download: {url}')

            # Download from Slack
            # https://api.slack.com/types/file#auth
            r = httpx.get(url, headers={
                'Authorization': f'Bearer {slack_oauth_token}'})
            r.raise_for_status()
            file_content = r.content

            # Encode to base64
            base64_string = base64.b64encode(file_content).decode("utf-8")

            # Upload base64 string and file bytes to S3
            s3.put_object(
                Bucket=s3_bucket,
                Key=f'base64string/{user}/{file_id}/{name}.txt',
                Body=base64_string,
                ContentType='text/plain'
            )
            s3.put_object(
                Bucket=s3_bucket,
                Key=f'original/{user}/{file_id}/{name}',
                Body=file_content,
                ContentType=mimetype
            )
            logger.info(f"Upload to s3 successful")

        except SlackApiError as e:
            logger.error(f"File id not found {file_id}: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Fail to download input file. HTTP{r.status_code}")
        except botocore.exceptions.ClientError as e:
            logger.error(f'Fail to upload input file to S3: {e}')
        # except Exception as e:
        #     logger.error(f"Error processing input file: {str(e)}")

        # Delete message from SQS
        logger.info("Delete from sqs")
        sqs.delete_message(QueueUrl=sqs_url, ReceiptHandle=sqs_receipt_handle)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
