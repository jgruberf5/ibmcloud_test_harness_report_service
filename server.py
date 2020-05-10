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

import os
import time
import datetime
import json

from flask import Flask, request, abort
from filelock import FileLock

REPORT_FILE = './reports.json'
LOCK_FILE = './reports.lock'

app = Flask(__name__)


def read_reports():
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, 'r') as reports_file:
            json_reports = reports_file.read()
            return json.loads(json_reports)
    else:
        return {}


def read_reports_json():
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, 'r') as reports_file:
            reports_json = reports_file.read()
            return reports_json
    else:
        return "{}"


def add_report(report_id, report):
    if not os.path.exists(REPORT_FILE):
        with FileLock(LOCK_FILE):
            with open(REPORT_FILE, 'w') as reports_file:
                reports = {}
                reports[report_id] = report
                reports_file.write(json.dumps(reports, sort_keys=True,
                                              indent=4, separators=(',', ': ')))
    else:
        with FileLock(LOCK_FILE):
            reports_json = None
            with open(REPORT_FILE, 'r') as reports_file:
                reports_json = reports_file.read()
            if reports_json:
                reports = json.loads(reports_json)
                reports[report_id] = report
                with open(REPORT_FILE, 'w') as reports_file:
                    reports_file.write(json.dumps(reports, sort_keys=True,
                                                  indent=4, separators=(',', ': ')))


def delete_report(report_id):
    if os.path.exists(REPORT_FILE):
        with FileLock(LOCK_FILE):
            reports_json = None
            with open(REPORT_FILE, 'r') as reports_file:
                reports_json = reports_file.read()
            if reports_json:
                reports = json.loads(reports_json)
                try:
                    del reports[report_id]
                except KeyError:
                    pass
                with open(REPORT_FILE, 'w') as reports_file:
                    reports_file.write(json.dumps(reports, sort_keys=True,
                                                  indent=4, separators=(',', ': ')))


def delete_reports():
    if os.path.exists(REPORT_FILE):
        with FileLock(LOCK_FILE):
            os.unlink(REPORT_FILE)


@app.route('/start/<uuid:test_id>', methods=['POST'])
def start_test(test_id):
    test_id = str(test_id)
    report = request.json
    report['start_time'] = time.time()
    report['readable_start_time'] = datetime.datetime.fromtimestamp(
        report['start_time']).strftime('%Y-%m-%d %H:%M:%S')
    report['stop_time'] = None
    report['readable_stop_time'] = None
    report['duration'] = 0
    report['results'] = {}
    add_report(test_id, report)
    return app.response_class(status=200)


@app.route('/stop/<uuid:test_id>', methods=['POST'])
def stop_test(test_id):
    reports = read_reports()
    test_id = str(test_id)
    if test_id in reports:
        report = reports[test_id]
        results = request.json
        done_time = time.time()
        report['stop_time'] = done_time
        report['readable_stop_time'] = datetime.datetime.fromtimestamp(
            report['stop_time']).strftime('%Y-%m-%d %H:%M:%S')
        report['duration'] = (done_time - report['start_time'])
        report['results'] = results
        add_report(test_id, report)
        return app.response_class(status=200)
    else:
        abort(404)


@app.route('/report', methods=['GET', 'DELETE'])
def test_reports():
    if request.method == 'DELETE':
        delete_reports()
        return app.response_class(response='',
                                  status=200, mimetype='application/json')
    else:
        reports = read_reports_json()
        return app.response_class(response=reports,
                                  status=200, mimetype='application/json')


@app.route('/report/<uuid:test_id>', methods=['GET', 'DELETE', 'PUT'])
def report_on_test(test_id):
    test_id = str(test_id)
    if request.method == 'DELETE':
        delete_report(test_id)
        return app.response_class(response='',
                                  status=200, mimetype='application/json')
    elif request.method == 'PUT':
        reports = read_reports()
        test_id = str(test_id)
        if test_id in reports:
            report = reports[test_id]
            update = request.json
            for prop in update:
                report[prop] = update[prop]
            add_report(test_id, report)
            return app.response_class(response=json.dumps(report),
                                      status=200, content_type='application/json')
        else:
            abort(404)
    else:
        reports = read_reports()
        if test_id in reports:
            json_report = json.dumps(reports[test_id], sort_keys=True,
                                     indent=4, separators=(',', ': '))
            return app.response_class(response=json_report,
                                      status=200, mimetype='application/json')
        else:
            abort(404)


if __name__ == '__main__':
    LISTEN_PORT = os.getenv('LISTEN_PORT', '5000')
    app.run(host='0.0.0.0', port=int(LISTEN_PORT), threaded=True)
