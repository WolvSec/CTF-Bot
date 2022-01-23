import datetime
import json

import requests

HEADERS = {
    'User-Agent': 'WolvSec Discord Bot/0.1.0',
}

BASE_URL = 'https://ctftime.org/api/v1'


def _get_https_json(url: str):
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return json.loads(response.content)


def get_upcoming(start: datetime.datetime = None, finish: datetime.datetime = None, limit: int = 100) -> dict:
    start = start or datetime.datetime.utcnow()
    finish = finish or start + datetime.timedelta(weeks=1)
    assert start <= finish
    start_timestamp = int(start.timestamp())
    finish_timestamp = int(finish.timestamp())
    return _get_https_json(f'{BASE_URL}/events/?limit={limit}&start={start_timestamp}&finish={finish_timestamp}')


def get_event(event_id: int) -> dict:
    return _get_https_json(f'{BASE_URL}/events/{event_id}/')


def get_team(team_id: int) -> dict:
    return _get_https_json(f'{BASE_URL}/teams/{team_id}/')
