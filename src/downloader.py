import os
import time
from datetime import timedelta

from src.camera import CameraSdk, AuthType, TimeInterval
from src.logger import Logger


def create_directory_for(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


class MediaDownloader:
    def __init__(self, config):
        self.config = config
        self.logger = None

    def init(self, camera_url, camera_channel=1, task_id=None):
        camera_url = camera_url.rstrip('/')

        path_to_media_archive = self.config['path_to_media_archive']
        create_directory_for(path_to_media_archive)

        Logger.init_logger(task_id=task_id)
        self.logger = Logger.get_logger()

        CameraSdk.init(self.config['default_timeout_seconds'], camera_channel)

        return camera_url, path_to_media_archive

    def download(self, camera_url, user_name, user_password, start_datetime_str, end_datetime_str,
                 camera_channel=1, task=None):

        task_id = task.display_id if task else None
        cam_url, path_to_media_archive = self.init(camera_url, camera_channel, task_id=task_id)

        try:
            if task and task.is_cancelled():
                return {'status': 'cancelled'}

            self.logger.info('Processing cam {}: downloading video'.format(cam_url))

            auth_type = CameraSdk.get_auth_type(cam_url, user_name, user_password)
            if auth_type == AuthType.UNAUTHORISED:
                raise RuntimeError('Unauthorised! Check login and password')

            auth_handler = CameraSdk.get_auth(auth_type, user_name, user_password)

            time_interval = TimeInterval.from_string(start_datetime_str, end_datetime_str, timedelta())

            if task and task.is_cancelled():
                return {'status': 'cancelled'}

            tracks = self._get_all_tracks(auth_handler, cam_url, time_interval)
            self.logger.info('Found {} files'.format(len(tracks)))

            if len(tracks) == 0:
                return {'status': 'error', 'message': 'No recordings found for the specified time range'}

            if task:
                task.total = len(tracks)

            if task and task.is_cancelled():
                return {'status': 'cancelled'}

            self._download_tracks(tracks, auth_handler, cam_url, path_to_media_archive, task)

            return {'status': 'success', 'files': len(tracks)}

        except Exception as e:
            self.logger.exception(e)
            return {'status': 'error', 'message': str(e)}

    def _get_all_tracks(self, auth_handler, cam_url, utc_time_interval):
        start_time_text, end_time_text = utc_time_interval.to_local_time().to_text()
        self.logger.info('Start time: {}'.format(start_time_text))
        self.logger.info('End time: {}'.format(end_time_text))
        self.logger.info('Getting track list...')

        tracks = []
        while True:
            answer = self._get_tracks_info(auth_handler, cam_url, utc_time_interval)
            local_time_offset = utc_time_interval.local_time_offset
            if answer:
                new_tracks = CameraSdk.create_tracks_from_info(answer, local_time_offset)
                tracks += new_tracks
                if len(new_tracks) < 50:
                    break

                last_track = tracks[-1]
                utc_time_interval.start_time = last_track.get_time_interval().end_time
            else:
                tracks = []
                break

        return tracks

    def _get_tracks_info(self, auth_handler, cam_url, utc_time_interval):
        result = CameraSdk.get_video_tracks_info(auth_handler, cam_url, utc_time_interval, 50)

        if not result:
            error_message = CameraSdk.get_error_message_from(result)
            self.logger.error('Error occurred during getting track list')
            self.logger.error(error_message)

        return result

    def _download_tracks(self, tracks, auth_handler, cam_url, path_to_media_archive, task=None):
        for idx, track in enumerate(tracks):
            if task and task.is_cancelled():
                return

            while True:
                if self._download_file_with_retry(
                        auth_handler, cam_url, track, path_to_media_archive, task):
                    break
                else:
                    if task and task.is_cancelled():
                        return
                    time.sleep(self.config['retry_delay_seconds'])

            if task:
                task.progress = idx + 1

    def _download_file_with_retry(self, auth_handler, cam_url, track, path_to_media_archive, task=None):
        start_time_text = track.get_time_interval().to_filename_text()
        file_name = path_to_media_archive + start_time_text + '.mp4'
        url_to_download = track.url_to_download()

        create_directory_for(file_name)

        if task:
            task.current_file = file_name

        self.logger.info('Downloading {}'.format(file_name))
        status = CameraSdk.download_file(auth_handler, cam_url, url_to_download, file_name, task)

        if status.result_type != CameraSdk.FileDownloadingResult.OK:
            if status.result_type == CameraSdk.FileDownloadingResult.TIMEOUT:
                self.logger.error("Timeout during file downloading")
            else:
                self.logger.error(status.text)
            return False

        return True
