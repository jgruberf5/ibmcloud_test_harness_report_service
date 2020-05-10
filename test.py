#!/usr/bin/env python3

# coding=utf-8
# pylint: disable=broad-except,unused-argument,line-too-long, unused-variable
# Copyright (c) 2016-2018, F5 Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import uuid
import json
import time
import datetime
import requests
import sys

one_nic_start = {
    'zone': 'us-south-3',
    'image_name': 'bigip14-1',
    'test_type': '1nic'
}

one_nic_stop = {
    'version': '14.1',
    'product': 'BIGIP',
    'hostname': 'onenic-test.local',
    'management': '192.168.245.119/24',
    'installed_extensions': ['f5-service-discovery', 'f5-declarative-onboarding', 'f5-appsvcs', 'f5-telemetry'],
    'as3_enabled': True,
    'do_enabled': False,
    'ts_enabled': False,
    'status': 'SUCCESS'
}

two_nic_start = {
    'zone': 'eu-de-1',
    'image_name': 'bigip14-1',
    'test_type': '2nic'
}

two_nic_stop = {
    'version': '14.1',
    'product': 'BIGIP',
    'hostname': 'twonic-test.local',
    'management': '192.168.245.119/24',
    'installed_extensions': ['f5-service-discovery', 'f5-declarative-onboarding', 'f5-appsvcs', 'f5-telemetry'],
    'as3_enabled': True,
    'do_enabled': False,
    'ts_enabled': False,
    'status': 'SUCCESS'
}

three_nic_start = {
    'zone': 'eu-gb-2',
    'image_name': 'bigip14-1',
    'test_type': '3nic'
}

three_nic_stop = {
    'version': '14.1',
    'product': 'BIGIP',
    'hostname': 'threenic-test.local',
    'management': '192.168.245.119/24',
    'installed_extensions': ['f5-service-discovery', 'f5-declarative-onboarding', 'f5-appsvcs', 'f5-telemetry'],
    'as3_enabled': True,
    'do_enabled': False,
    'ts_enabled': False,
    'status': 'SUCCESS'
}


def run_tests():
    base_url = 'http://localhost:5000'
    headers = {
        'Content-Type': 'application/json'
    }
    one_nic_uuid = str(uuid.uuid4())
    requests.post("%s/start/%s" % (base_url, one_nic_uuid),
                  headers=headers, data=json.dumps(one_nic_start))
    time.sleep(10)
    two_nic_uuid = str(uuid.uuid4())
    requests.post("%s/start/%s" % (base_url, two_nic_uuid),
                  headers=headers, data=json.dumps(two_nic_start))
    time.sleep(10)
    three_nic_uuid = str(uuid.uuid4())
    requests.post("%s/start/%s" % (base_url, three_nic_uuid),
                  headers=headers, data=json.dumps(three_nic_start))
    now = time.time()
    update = {
        'terraform_result_code': '0',
        'terraform_output':'It worked!',
        'terraform_completed_at': now,
        'terraform_completed_at_readable': datetime.datetime.fromtimestamp(
            now).strftime('%Y-%m-%d %H:%M:%S')
    }
    requests.put("%s/report/%s" % (base_url, one_nic_uuid),
                 headers=headers, data=json.dumps(update))
    time.sleep(10)
    requests.put("%s/report/%s" % (base_url, two_nic_uuid),
                 headers=headers, data=json.dumps(update))
    time.sleep(10)
    requests.put("%s/report/%s" % (base_url, three_nic_uuid),
                 headers=headers, data=json.dumps(update))
    time.sleep(60)
    requests.post("%s/stop/%s" % (base_url, one_nic_uuid),
                  headers=headers, data=json.dumps(one_nic_stop))
    time.sleep(10)
    requests.post("%s/stop/%s" % (base_url, two_nic_uuid),
                  headers=headers, data=json.dumps(two_nic_stop))
    time.sleep(10)
    requests.post("%s/stop/%s" % (base_url, three_nic_uuid),
                  headers=headers, data=json.dumps(three_nic_stop))
    time.sleep(300)
    requests.delete("%s/report/%s" % (base_url, one_nic_uuid))
    requests.delete("%s/report/%s" % (base_url, two_nic_uuid))
    requests.delete("%s/report/%s" % (base_url, three_nic_uuid))


if __name__ == "__main__":
    run_tests()
