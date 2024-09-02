import logging
import json
import time
import uuid
import boto3
import botocore
from boto3.dynamodb.types import TypeDeserializer

sts_client = boto3.client('sts')
d = TypeDeserializer()

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_sts_client(service, role_arn):
    """
    Get sts assume role credential to call boto3 APIs when assuming cross-account roles.
    Args:
        service: the service name used for calling the boto.client()
        role_arn: the ARN of the role to assume
    Return:
        service boto3 client. 
    """
    resp = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName=f"SlackApp_Assume_role_for_{service}")
    credentials = resp['Credentials']

    return boto3.client(service, aws_access_key_id=credentials['AccessKeyId'],
                        aws_secret_access_key=credentials['SecretAccessKey'],
                        aws_session_token=credentials['SessionToken']
                        )
