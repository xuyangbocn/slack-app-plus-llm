import json
import logging
import os
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

slack_app_ids = os.environ['slack_app_ids'].split(",")
slack_app_tokens = os.environ['slack_app_tokens'].split(",")

sqs = boto3.client('sqs')
event_sqs_url = os.environ['event_sqs_url']
input_file_sqs_url = os.environ['input_file_sqs_url']


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
    event_type = slack_event['event']['type']
    channel = slack_event['event'].get('channel', 'NotFoundInEvent')
    user = slack_event['event'].get('user', 'NotFoundInEvent')
    ret = (team_id, event_ts, event_type, channel, user)

    logger.info(f'{ret}')
    return ret


def push_to_sqs(sqs_url, sqs_message_body, team_id, event_ts, event_type, channel="", user=""):
    '''
    ToDo: Slack msg limit 40,000 char, SQS limit 256KB
    Hence long slack msg may not fit in

    Raise:
        If fail to push, exception is raised by boto3
    '''
    logger.info('Push to SQS')
    resp = sqs.send_message(
        QueueUrl=sqs_url,
        MessageBody=sqs_message_body,
        MessageAttributes={
            'team_id': {
                'StringValue': team_id,
                'DataType': 'String'
            },
            'event_ts': {
                'StringValue': event_ts,
                'DataType': 'String'
            },
            'event_type': {
                'StringValue': event_type,
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
    headers = event.get('headers', {})
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
    team_id, event_ts, event_type, channel, user = get_event_key_attrs(body)

    # Send message to SQS
    if body['event'].get('app_id') in slack_app_ids:
        # Ignore bot message sent by self
        logger.info('Ignore bot message sent by self')
    elif headers.get('x-slack-retry-reason', None) == "http_timeout":
        # Ignore retry from slack event api due to 3sec timeout
        logger.info('Ignore retry msg due to slack event api 3sec timeout')
    elif event_type == 'message':
        # https://api.slack.com/events/message
        push_to_sqs(event_sqs_url, json_body, team_id,
                    event_ts, event_type, channel, user)
    elif event_type == 'file_shared':
        # https://api.slack.com/events/file_shared
        push_to_sqs(input_file_sqs_url, json_body, team_id,
                    event_ts, event_type, channel, user)
    else:
        logger.warning(f'Ignore unrecognized slack event type: {event_type}')

    return {
        'statusCode': 200,
        'body': json.dumps('Slack event received')
    }
