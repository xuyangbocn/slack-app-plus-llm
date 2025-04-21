import logging
import json
from typing import Optional, Union, Any, List, Dict, Callable
from typing_extensions import Literal
import time

import boto3
import botocore
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from minagent import Agent
from slackstyler import SlackStyler


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SlackLLMHandler(object):
    def __init__(
        self,
        agent: Agent,

        s3_input_file_bucket: str,

        ddb_chat_completion_table: str,
        ddb_asst_thread_table: str,

        slack_oauth_token: str,
        slack_event,

        mode: Optional[
            Literal["Assistant", "ChatCompletion"]] = 'ChatCompletion',
    ):
        # minagent instance
        self.agent = agent

        # DDB for conversation state management
        self.ddb_client = boto3.client('dynamodb')
        self.ddb_asst_thread_table = ddb_asst_thread_table
        self.ddb_chat_completion_table = ddb_chat_completion_table

        # S3 for input file management
        self.s3_client = boto3.client('s3')
        self.s3_input_file_bucket = s3_input_file_bucket

        # Slack for reply
        self.slack = WebClient(token=slack_oauth_token)

        # Helper: Markdown formatter
        self.styler = SlackStyler()
        # Helper: DDB records data serializer
        self.d = TypeDeserializer()
        self.s = TypeSerializer()

        # User's message from Slack
        self.slack_event = slack_event
        msg_details = self._extract_event_details()
        self.channel_id = msg_details['channel_id']
        self.event_ts = msg_details['event_ts']
        self.thread_ts = msg_details['thread_ts']
        self.user = msg_details['user']
        self.text = msg_details['text']
        self.files = msg_details['files']

        # whether via ChatCompletion or Assistant API
        self.mode = mode

    def reply(self):
        if self.mode == 'ChatCompletion':
            return self.reply_via_chat_completion()
        else:
            return self.reply_via_assistant()

    def reply_via_chat_completion(self):
        # Re-collect past message in the thread
        # Append new user message
        thread_messages = self._ddb_fetch_conversation_state() + [
            {
                'role': 'user',
                'content': self._construct_message_content(self.text, self.files)
            }
        ]

        # Save conversation state: user new msg
        self._ddb_save_conversation_state(
            self.event_ts, 'user', self.text, self.files)

        # Pass whole message history to chat completion
        logger.info(f'Call chat completion api')
        logger.info(f'{"\n".join([str(t)[:100] for t in thread_messages])}')
        response = self.agent.chat_completion(
            user=self.user,
            messages=thread_messages,
        )

        # Respond on slack thread
        logger.info(f'Send response to slack thread')
        resp = self._slack_post_message(response)

        # Save conversation state: response from llm
        self._ddb_save_conversation_state(
            resp['ts'], 'assistant', response, [])
        return

    def reply_via_assistant(self):
        # Get exsiting / Create new thread
        asst_thread_id = self._ddb_get_asst_thread_id()

        # Call OpenAI Assistant
        response = self.agent.ask_assistant(
            user=self.user,
            asst_thread_id=asst_thread_id,
            message=self._asst_construct_message_content(),
        )

        # respond on slack thread
        logger.info(f"Send response to slack thread")
        self._slack_post_message(response)

        return

    '''
    Common functions for both chat completion and assistant
    '''

    def _slack_post_message(self, message: str, styled: bool = True):
        # https://api.slack.com/methods/chat.postMessage
        try:
            message = self.styler.convert(message) if styled else message
        except:
            message = message

        try:
            resp = self.slack.chat_postMessage(
                channel=self.channel_id,
                thread_ts=self.thread_ts,
                text=message
            )
            logger.info(resp)
        except SlackApiError as e:
            logger.error(f"Error: {e}")
            resp = None

        return resp

    def _extract_event_details(self):
        '''
        ref: slack event format follow doc below
        https://api.slack.com/events/message.im
        https://api.slack.com/events/message.channels
        https://api.slack.com/events/message.groups
        '''

        text, channel_id, event_ts, thread_ts, user, files = "", "", "", "", "", []
        try:
            msg = self.slack_event['event']
            text = msg['text']
            channel_id = msg['channel']
            event_ts = msg['event_ts']
            thread_ts = msg.get('thread_ts', event_ts)
            user = msg.get('user', 'unknown')
            files = [
                {
                    "id": f['id'],
                    "name": f['name'],
                    "mimetype": f['mimetype'],
                    "filetype": f['filetype'],
                    "user_team": f['user_team'],
                } for f in msg.get('files', [])
            ]
            logger.info(json.dumps(msg, indent=2))
        except KeyError as e:
            logger.warning("Malformed slack event format")

        return dict(text=text, channel_id=channel_id, event_ts=event_ts, thread_ts=thread_ts, user=user, files=files)

    def _s3_get_input_file(self, team_id, file_id, name, b64: bool = True, decode: bool = True, retry=2, retry_interval=1):
        content = '' if decode else b''
        key = f'base64string/{team_id}/{file_id}/{name}.txt' if b64 else f'original/{team_id}/{file_id}/{name}'

        while retry >= 0:
            try:
                o = self.s3_client.get_object(
                    Bucket=self.s3_input_file_bucket,
                    Key=key)

                if decode:
                    # string
                    content = o['Body'].read().decode('utf-8')
                else:
                    # bytes
                    content = o['Body'].read()
            except self.s3_client.exceptions.NoSuchKey as e:
                # In case file is not uploaded to s3 yet
                time.sleep(retry_interval)
                logger.warning(f'Wait 1s to get input file for {key}')
                retry -= 1
            except Exception as e:
                logger.error(f'Fail to get input file for {key}: {e}')
                time.sleep(retry_interval)
                retry -= 1
            else:
                break
        return content

    '''
    Functions for chat completion only
    '''

    def _ddb_fetch_conversation_state(self, max_historical_messages=25):
        '''
        Fetch all messages in the thread stored in DDB
        '''
        try:
            resp = self.ddb_client.query(
                TableName=self.ddb_chat_completion_table,
                Limit=max_historical_messages,
                ScanIndexForward=False,  # descending order
                KeyConditionExpression='slack_channel_id_thread_ts = :slack_channel_id_thread_ts',
                ExpressionAttributeValues={
                    ':slack_channel_id_thread_ts': {
                        'S': f'{self.channel_id};{self.thread_ts}',
                    }
                }
            )
            logger.info(
                f'DDB records {resp.get("count", "not")} found: {self.channel_id};{self.thread_ts}')

            # reverse descending order to chronological ascending order
            messages = [
                {
                    'role': i['role']['S'],
                    'content': self._construct_message_content(
                        text=i['content']['S'],
                        files=self.d.deserialize(i.get('files', {'L': []}))
                    )
                }
                for i in resp.get('Items')[::-1]
            ]
        except (botocore.exceptions.ClientError, KeyError) as exNotFound:
            logger.info(f'No existing threads: {exNotFound}')
            messages = []
            pass

        return messages

    def _ddb_save_conversation_state(self, slack_event_ts, role, content, files):
        '''
        Save new conversation messages to DDB
        '''
        ddb_search_key = {
            'slack_channel_id_thread_ts': {'S': f'{self.channel_id};{self.thread_ts}'},
            'slack_event_ts': {'S': slack_event_ts},
        }
        try:
            self.ddb_client.update_item(
                TableName=self.ddb_chat_completion_table,
                Key=ddb_search_key,
                UpdateExpression='SET #r=:role, content=:content, files=:files, slack_user_id=:slack_user_id',
                ExpressionAttributeValues={
                    ':role': {'S': role},
                    ':content': {'S': content},
                    ':files': self.s.serialize(files),
                    ':slack_user_id': {'S': self.user},
                },
                ExpressionAttributeNames={
                    "#r": "role"
                }
            )
            logger.info(
                f'DDB record created for {role}[{self.user}]: {self.channel_id};{self.thread_ts}')
        except botocore.exceptions.ClientError as ex:
            logger.error(f'DDB record fail to create: {ex}')
            pass
        return

    def _construct_message_content(self, text, files):
        '''
        Construct the message content that is sent to OpenAI Chat Completion API. Including text, and supported images and files
        Arg:
            text: string, plain text message
            files: list of dictionary capturing the uploaded files details from inside the message event
                [
                    {
                        "id": f['id'],
                        "name": f['name'],
                        "mimetype": f['mimetype'],
                        "filetype": f['filetype'],
                        "user_team": f['user_team'],
                    },
                    ...
                ]
        Ref:
            slack file objec: https://api.slack.com/types/file
            file['mimetype']: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types
            file['filetype']https://api.slack.com/types/file#types
            https://platform.openai.com/docs/guides/images
            https://platform.openai.com/docs/guides/pdf-files?api-mode=chat#base64-encoded-files
        '''
        content_text = [{
            "type": "text",
            "text": text,
        }]

        try:
            content_doc = [{
                "type": "file",
                "file": {
                    "filename": d['name'],
                    "file_data": f"data:{d['mimetype']};base64,{self._s3_get_input_file(
                        d["user_team"], d["id"], d["name"], b64=True, decode=True)}",
                }}
                for d in files if d['mimetype'] in ('application/pdf',)]
        except Exception as e:
            logger.error(f'Fail to extract doc files: {str(e)}')
            content_doc = []

        try:
            content_image = [{
                "type": "image_url",
                "image_url": {
                    "url": f"data:{i['mimetype']};base64,{self._s3_get_input_file(
                        i["user_team"], i["id"], i["name"], b64=True, decode=True)}",
                }}
                for i in files if 'image' in i['mimetype']
            ]
            logger.info(content_image)
        except Exception as e:
            logger.error(f'Fail to extract image: {str(e)}')
            content_image = []

        return content_text + content_doc + content_image

    '''
    Functions for assistant only
    '''

    def _ddb_get_asst_thread_id(self):
        '''
        DDB ddb_asst_thread keeps the mapping from slack channel id + thread ts ==> asst_thread_id
        This function will find the assistant thread id for existing slack thread
        If not found (i.e. a new slack thread), it will create a assistant thread and insert to DDB
        '''
        ddb_search_key = {
            "slack_channel_id": {"S": self.channel_id},
            "slack_thread_ts": {"S": self.thread_ts},
        }
        asst_thread_id = None

        # search thread in DDB
        try:
            resp = self.ddb_client.get_item(
                TableName=self.ddb_asst_thread_table,
                Key=ddb_search_key,
            )
            asst_thread_id = resp["Item"]["asst_thread_id"]['S']
            logger.info(f'DDB record found for thread: {asst_thread_id}')
        except (botocore.exceptions.ClientError, KeyError) as exNotFound:
            # if thread not found in DDB
            thread = self.agent.llm_client.beta.threads.create()
            asst_thread_id = thread.id
            try:
                self.ddb_client.update_item(
                    TableName=self.ddb_asst_thread_table,
                    Key=ddb_search_key,
                    UpdateExpression="SET asst_thread_id=:asst_thread_id, slack_user_id=:slack_user_id",
                    ExpressionAttributeValues={
                        ":asst_thread_id": {"S": asst_thread_id},
                        ":slack_user_id": {"S": self.user},
                    }
                )
                logger.info(f'DDB record created for thread: {asst_thread_id}')
            except botocore.exceptions.ClientError as ex:
                logger.warning(ex)
                pass

        return asst_thread_id

    def _oai_upload_input_file(self, team_id, file_id, name):
        content = self._s3_get_input_file(team_id, file_id, name,
                                          b64=False, decode=False)
        try:
            file = self.agent.llm_client.files.create(
                file=(name, content),
                purpose="user_data"
            )
        except Exception as e:
            logger.error(f'Fail to upload file to OpenAI')
            return None
        return file.id

    def _asst_construct_message_content(self):
        '''
        Construct the message content that is sent to OpenAI Assistant API. Including text, and supported images and files
        Arg:
            text: string, plain text message
            files: list of dictionary capturing the uploaded files details from inside the message event
                [
                    {
                        "id": f['id'],
                        "name": f['name'],
                        "mimetype": f['mimetype'],
                        "filetype": f['filetype'],
                        "user_team": f['user_team'],
                    },
                    ...
                ]
        Ref:
            slack file objec: https://api.slack.com/types/file
            file['mimetype']: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types
            file['filetype']https://api.slack.com/types/file#types
            https://platform.openai.com/docs/api-reference/messages/createMessage
        '''
        content_text = [{
            "type": "text",
            "text": self.text,
        }]

        # TBD, need to attach the files when creating message
        # https://platform.openai.com/docs/assistants/tools/file-search
        content_doc = []

        try:
            content_image = [{
                "type": "image_file",
                "image_file": {
                    "file_id": self._oai_upload_input_file(i["user_team"], i["id"], i["name"]),
                }}
                for i in self.files if 'image' in i['mimetype']
            ]
            logger.info(content_image)
        except Exception as e:
            logger.error(f'Fail to extract image: {str(e)}')
            content_image = []

        return content_text + content_doc + content_image
