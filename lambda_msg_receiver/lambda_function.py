import json
import logging
import os
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

slack_app_ids = os.environ['slack_app_ids'].split(",")
slack_app_tokens = os.environ['slack_app_tokens'].split(",")


def get_event_key_attrs(slack_event):
    '''
    Get team_id, event_ts, channel, user(sender) from slack event
    channel and user may not always exist in slack event
    Arg:
        slack_event: python object loaded from json
    Raise:
        if team id, event ts doesnt exist, i.e. event format is malformed
    '''
    logger.info(f'Getting Slack key attr')
    team_id = slack_event['team_id']
    event_ts = slack_event['event']['event_ts']
    channel = slack_event['event'].get('channel', '')
    user = slack_event['event'].get('user', '')
    ret = (team_id, event_ts, channel, user)

    logger.info(f'{ret}')
    return ret


def push_to_sqs(json_slack_event, team_id, event_ts, channel="", user=""):
    '''
    ToDo: Slack msg limit 40,000 char, SQS limit 256KB
    Hence long slack msg may not fit in

    Raise:
        If fail to push, exception is raised by boto3
    '''
    logger.debug('Get SQS url')
    sqs = boto3.client('sqs')
    sqs_url = sqs.get_queue_url(
        QueueName=os.environ['sqs_name'],
        QueueOwnerAWSAccountId=os.environ['sqs_owner_account'],
    )['QueueUrl']

    logger.info('Push to SQS')
    resp = sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=json_slack_event,
        MessageAttributes={
            'team_id': {
                'StringValue': team_id,
                'DataType': 'String'
            },
            'event_ts': {
                'StringValue': event_ts,
                'DataType': 'String'
            },
            'channel': {
                'StringValue': channel,
                'DataType': 'String'
            },
            'user': {
                'StringValue': user,
                'DataType': 'String'
            },
        },
    )
    logger.info(f'{resp}')

    return resp


def lambda_handler(event, context):
    # Get lambda event body which contains slack event
    logger.debug(json.dumps(event, indent=2))
    json_body = event.get('body', '{}')
    body = json.loads(json_body)
    logger.debug(json.dumps(body, indent=2))

    # Verify if is from known slack app
    if 'token' not in body or body['token'] not in slack_app_tokens:
        logger.warning('Not from known Slack App')
        return {
            'statusCode': 403,
            'body': "Not authorized"
        }

    # First time Slack challenge verification
    if 'challenge' in body and body['type'] == 'url_verification':
        logger.info('Handle Slack challenge')
        return {
            'statusCode': 200,
            'body': body['challenge']
        }

    # Get Slack event key attributes
    team_id, event_ts, channel, user = get_event_key_attrs(body)

    # Send message to SQS
    if body['event']['app_id'] in slack_app_ids:
        # Ignore bot message sent by self
        logger.info('Ignore bot message sent by self')
    else:
        push_to_sqs(json_body, team_id, event_ts, channel, user)

    return {
        'statusCode': 200,
        'body': json.dumps('Slack event received')
    }
