import json
import logging
from typing import Union, Optional, List, Dict, Any
import concurrent.futures as cf

import gitlab
from gitlab.v4.objects import Project, ProjectTrigger, ProjectPipeline


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class GitLabRepoManager(object):
    def __init__(self,
                 gitlab_host: str,
                 gitlab_pa_token: str,
                 project: str,
                 identifier: str,
                 ssl_verify: bool = False):

        self.gl = gitlab.Gitlab(
            url=gitlab_host,
            private_token=gitlab_pa_token,
            ssl_verify=ssl_verify)
        self.project = self.gl.projects.get(project)
        self.main_branch = self._get_main_branch()

        self.identifier = identifier
        self.default_commit_msg = f'commit by {self.identifier}'
        self.default_trigger_token_description = \
            f'{self.identifier} temp pipeline token'

    def commit_file(self, path: str, file_content: str, branch: str = '') -> None:
        try:
            self.project.files.get(path, branch or self.main_branch)
            action = "update"
            logger.info(f'{self.project.name}: {path} existed.')
        except gitlab.exceptions.GitlabGetError as ex:
            action = "create"
            logger.info(f'{self.project.name}: {path} not found.')

        try:
            data = {
                'branch': branch or self.main_branch,
                'commit_message': self.default_commit_msg,
                'actions': [
                    {
                        'action': action,
                        'file_path': path,
                        'content': file_content,
                    },
                ]
            }
            commit = self.project.commits.create(data)
            logger.info(f'{self.project.name}: create/updated {path}.')
        except gitlab.exceptions.GitlabCreateError as ex:
            logger.warning(f'{self.project.name}: fail to commit {path}.')
        return

    def trigger_pipeline(self, branch: str = '', variables: Dict[str, Any] = {}) -> ProjectPipeline:
        self.trigger = self._get_pipeline_trigger()
        # create trigger if not existed
        if self.trigger is None:
            self.trigger = self._create_pipeline_trigger()

        # trigger pipeline for branch or main branch
        pipeline = self._trigger_pipeline(
            self.trigger.token,
            branch or self.main_branch,
            variables,
        )
        return pipeline

    def _get_main_branch(self) -> str:
        branches = self.project.protectedbranches.list()
        return "main" if "main" in branches else "master"

    def _get_pipeline_trigger(self) -> Union[ProjectTrigger, None]:
        trigger = None
        for t in self.project.triggers.list():
            if t.description == self.default_trigger_token_description:
                trigger = t
                logger.info(f'{self.project.name}: Trigger existed.')
                break
        if trigger is None:
            logger.info(f'{self.project.name}: Trigger not found.')
        return trigger

    def _create_pipeline_trigger(self) -> ProjectTrigger:
        trigger = self.project.triggers.create(
            {'description': self.default_trigger_token_description})
        logger.info(f'{self.project.name}: Trigger created.')
        return trigger

    def _trigger_pipeline(self, trigger_token: str, ref: str, variables: Dict[str, Any]) -> ProjectPipeline:
        try:
            pipeline = self.project.trigger_pipeline(
                token=trigger_token,
                ref=ref,
                variables=variables)
            logger.info(f'{self.project.name}: [{ref}] Pipeline triggered.')
        except gitlab.exceptions.GitlabCreateError as ex:
            logger.info(
                f'{self.project.name}: [{ref}]Fail to trigger pipeline.')
            raise ex

        return pipeline

    def delete_pipeline_trigger(self) -> None:
        '''
        clean up: delete pipeline trigger token
        '''
        if self.trigger:
            logger.info(
                f'{self.project.name}: Trigger found and deleted.')
            self.trigger.delete()
        else:
            logger.info(f'{self.project.name}: Trigger not found.')

        return

    def check_pipeline(self, pipeline_id) -> Dict[str, Any]:
        '''
        Get pipeline status and failed jobs
        '''
        output = {
            'pipeline_status': None,
            'failed_jobs': []
        }
        pipeline = self.project.pipelines.get(pipeline_id)
        output['pipeline_status'] = pipeline.status

        if output['pipeline_status'] != "success":
            failed_jobs = [
                j for j in pipeline.jobs.list() if j.status == 'failed']
            with cf.ThreadPoolExecutor() as pool:
                fs = {
                    pool.submit(
                        self.project.jobs.get(j.id, lazy=True).trace
                    ): {
                        'job_name': j.name,
                        'job_status': j.status,
                    }
                    for j in failed_jobs
                }
                for f in cf.as_completed(fs):
                    output['failed_jobs'].append(
                        {
                            "job_name": fs[f]['job_name'],
                            "job_status": fs[f]['job_status'],
                            "job_log": f.result(),
                        }
                    )
        return output


def check_project_pipeline_status(
        gitlab_pa_token: str,
        gitlab_host: str,
        project: str,
        pipeline_id: str
) -> str:
    gl = GitLabRepoManager(
        gitlab_host=gitlab_host,
        gitlab_pa_token=gitlab_pa_token,
        project=project,
        identifier='GitLabRepoManager',
        ssl_verify=False,  # Set False if cloudflare is on
    )
    ret = gl.check_pipeline(pipeline_id)
    return str(ret)
