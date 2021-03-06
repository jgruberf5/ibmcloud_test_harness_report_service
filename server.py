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
        with FileLock(LOCK_FILE):
            with open(REPORT_FILE, 'r') as reports_file:
                json_reports = reports_file.read()
                try:
                    return json.loads(json_reports)
                except json.JSONDecodeError as je:
                    time.sleep(2)
        return read_reports()
    else:
        return {}


def read_reports_json():
    if os.path.exists(REPORT_FILE):
        with FileLock(LOCK_FILE):
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
    now = datetime.datetime.utcnow()
    report['start_time'] = now.timestamp()
    report['readable_start_time'] = now.strftime('%Y-%m-%d %H:%M:%S UTC')
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
        now = datetime.datetime.utcnow()
        results = json.loads(request.data.decode('utf-8'))
        report['stop_time'] = now.timestamp()
        report['readable_stop_time'] = now.strftime('%Y-%m-%d %H:%M:%S UTC')
        report['duration'] = (now.timestamp() - report['start_time'])
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


@app.route('/running', methods=['GET'])
def running_reports():
    reports = read_reports()
    return_reports = []
    for report in reports:
        if reports[report]['duration'] == 0:
            return_reports.append(reports[report])
    json_report = json.dumps(return_reports, sort_keys=True,
                             indent=4, separators=(',', ': '))
    return app.response_class(response=json_report,
                              status=200, mimetype='application/json')


@app.route('/failed', methods=['GET'])
def failed_reports():
    reports = read_reports()
    return_reports = []
    for report in reports:
        if reports[report]['duration'] > 0:
            if 'status' not in reports[report]['results'] or not reports[report]['results']['status'] == 'SUCCESS':
                return_reports.append(reports[report])
    json_report = json.dumps(return_reports, sort_keys=True,
                             indent=4, separators=(',', ': '))
    return app.response_class(response=json_report,
                              status=200, mimetype='application/json')


@app.route('/query', methods=['GET'])
def query_attributes():
    qtype = request.args.get('type')
    qimage = request.args.get('image')
    qzone = request.args.get('zone')
    qfailed = request.args.get('failed')
    qsuccess = request.args.get('success')
    reports = read_reports()
    return_reports = []
    for report in reports:
        add_report = True
        if qtype and not reports[report]['type'].startswith(qtype):
            add_report = False
        if qimage and not reports[report]['image_name'].startswith(qimage):
            add_report = False
        if qzone and not reports[report]['zone'].startswith(qzone):
            add_report = False
        if qfailed and not ('status' not in reports[report]['results'] or not reports[report]['results']['status'] == 'SUCCESS'):
            add_report = False
        if qsuccess and not ('status' in reports[report]['results'] and reports[report]['results']['status'] == 'SUCCESS'):
            add_report = False
        if add_report:
            return_reports.append(reports[report])
    json_report = json.dumps(return_reports, sort_keys=True,
                             indent=4, separators=(',', ': '))
    return app.response_class(response=json_report,
                              status=200, mimetype='application/json')


@app.route('/summary', methods=['GET'])
def summary():
    reports = read_reports()
    zones = {}
    ttypes = {}
    imagez = {}
    running_reports = []
    success_reports = []
    failed_reports = []
    success_durations = 0
    success_duration_min = 0
    success_duration_max = 0
    failed_durations = 0
    failed_duration_min = 0
    failed_duration_max = 0
    failed_in_terraform = 0
    failed_by_timeout = 0
    workspace_create_completed = 0
    workspace_create_completed_seconds = 0
    workspace_create_failed = 0
    workspace_create_failed_seconds = 0
    terraform_plan_completed = 0
    terraform_plan_seconds = 0
    terraform_plan_failed = 0
    terraform_plan_failed_seconds = 0
    terraform_apply_completed = 0
    terraform_apply_seconds = 0
    terraform_apply_failed = 0
    terraform_apply_failed_seconds = 0
    terraform_destroy_completed = 0
    terraform_destroy_seconds = 0
    terraform_destroy_failed = 0
    terraform_destroy_failed_seconds = 0
    terraform_completed = 0
    terraform_completed_seconds = 0
    for report in reports:
        report_zone = reports[report]['zone']
        if report_zone not in zones:
            zones[report_zone] = {
                'running': 0,
                'success': 0,
                'failed': 0,
                'terraform_failed': 0,
                'percent_failure': 0
            }
        report_type = reports[report]['type']
        if report_type not in ttypes:
            ttypes[report_type] = {
                'running': 0,
                'success': 0,
                'failed': 0,
                'terraform_failed': 0,
                'percent_failure': 0
            }
        image_name = reports[report]['image_name']
        if image_name not in imagez:
            imagez[image_name] = {
                'running': 0,
                'success': 0,
                'failed': 0,
                'terraform_failed': 0,
                'percent_failure': 0
            }
        if 'workspace_create_result_code' in reports[report] and reports[report]['workspace_create_result_code'] == 0:
            workspace_create_completed = workspace_create_completed + 1
            workspace_create_completed_seconds = workspace_create_completed_seconds + \
                reports[report]['workspace_create_duration']
        if 'workspace_create_result_code' in reports[report] and reports[report]['workspace_create_result_code'] == 1:
            workspace_create_failed = workspace_create_failed + 1
        if 'terraform_plan_result_code' in reports[report] and reports[report]['terraform_plan_result_code'] == 0:
            terraform_plan_completed = terraform_plan_completed + 1
            terraform_plan_seconds = terraform_plan_seconds + \
                reports[report]['terraform_plan_duration']
        if 'terraform_plan_result_code' in reports[report] and reports[report]['terraform_plan_result_code'] == 1:
            terraform_plan_failed = terraform_plan_failed + 1
        if 'terraform_apply_result_code' in reports[report] and reports[report]['terraform_apply_result_code'] == 0:
            terraform_apply_completed = terraform_apply_completed + 1
            terraform_apply_seconds = terraform_apply_seconds + \
                reports[report]['terraform_apply_duration']
        if 'terraform_apply_result_code' in reports[report] and reports[report]['terraform_apply_result_code'] == 1:
            terraform_apply_failed = terraform_apply_failed + 1
        if 'terraform_destroy_result_code' in reports[report] and reports[report]['terraform_apply_result_code'] == 0:
            terraform_destroy_completed = terraform_destroy_completed + 1
            terraform_destroy_seconds = terraform_destroy_seconds + \
                reports[report]['terraform_destroy_duration']
        if 'terraform_destroy_result_code' in reports[report] and reports[report]['terraform_apply_result_code'] == 1:
            terraform_destroy_failed = terraform_destroy_failed + 1
        if 'terraform_result_code' in reports[report] and reports[report]['terraform_result_code'] == 0:
            terraform_completed = terraform_completed + 1
            terraform_seconds = reports[report]['terraform_apply_stop'] - \
                reports[report]['start_time']
            terraform_completed_seconds = terraform_completed_seconds + terraform_seconds

        if reports[report]['duration'] == 0:
            now = datetime.datetime.utcnow()
            duration = int(now.timestamp() - reports[report]['start_time'])
            running_reports.append("%s - %s seconds - %s - %s" % (report, str(
                duration), reports[report]['type'], reports[report]['zone']))
            zones[report_zone]['running'] = zones[report_zone]['running'] + 1
            ttypes[report_type]['running'] = ttypes[report_type]['running'] + 1
            imagez[image_name]['running'] = imagez[image_name]['running'] + 1
        else:
            if 'status' in reports[report]['results'] and reports[report]['results']['status'] == 'SUCCESS':
                success_reports.append(report)
                zones[report_zone]['success'] = zones[report_zone]['success'] + 1
                ttypes[report_type]['success'] = ttypes[report_type]['success'] + 1
                imagez[image_name]['success'] = imagez[image_name]['success'] + 1
                duration = float(reports[report]['duration'])
                success_durations = success_durations + duration
                if duration > success_duration_max:
                    success_duration_max = duration
                if duration < success_duration_min or success_duration_min == 0:
                    success_duration_min = duration
            else:
                if 'terraform_result_code' in reports[report] and reports[report]['terraform_result_code'] > 0:
                    failed_in_terraform = failed_in_terraform + 1
                    zones[report_zone]['terraform_failed'] = zones[report_zone]['terraform_failed'] + 1
                    ttypes[report_type]['terraform_failed'] = ttypes[report_type]['terraform_failed'] + 1
                    imagez[image_name]['terraform_failed'] = imagez[image_name]['terraform_failed'] + 1
                if 'test timedout' in reports[report]['results']:
                    failed_by_timeout = failed_by_timeout + 1
                failed_reports.append(report)
                zones[report_zone]['failed'] = zones[report_zone]['failed'] + 1
                ttypes[report_type]['failed'] = ttypes[report_type]['failed'] + 1
                imagez[image_name]['failed'] = imagez[image_name]['failed'] + 1
                duration = float(reports[report]['duration'])
                failed_durations = failed_durations + duration
                if duration > failed_duration_max:
                    failed_duration_max = duration
                if duration < failed_duration_min or failed_duration_min == 0:
                    failed_duration_min = duration
            zones_complete = zones[report_zone]['success'] + \
                zones[report_zone]['failed']
            ttype_complete = ttypes[report_type]['success'] + \
                ttypes[report_type]['failed']
            imagez_complete = imagez[image_name]['success'] + \
                imagez[image_name]['failed']
            if zones_complete > 0:
                zones[report_zone]['percent_failure'] = round(
                    (zones[report_zone]['failed'] / zones_complete) * 100, 2)
            if ttype_complete > 0:
                ttypes[report_type]['percent_failure'] = round(
                    (ttypes[report_type]['failed'] / ttype_complete) * 100, 2)
            if imagez_complete > 0:
                imagez[image_name]['percent_failure'] = round(
                    (imagez[image_name]['failed'] / imagez_complete) * 100, 2)
    total_reports = len(reports)
    num_running = len(running_reports)
    num_success = len(success_reports)
    num_failed = len(failed_reports)

    success_avg_duration = 0
    if len(success_reports) > 0:
        success_avg_duration = round(
            success_durations / len(success_reports), 2)

    failed_avg_duration = 0
    if len(failed_reports) > 0:
        failed_avg_duration = round(failed_durations / len(failed_reports), 2)

    terraform_completed_avg = 0
    if terraform_completed > 0:
        terraform_completed_avg = round(
            terraform_completed_seconds / terraform_completed, 2)

    workspace_create_completed_avg = 0
    if workspace_create_completed > 0:
        workspace_create_completed_avg = round(
            workspace_create_completed_seconds / workspace_create_completed, 2)

    terraform_plan_completed_avg = 0
    if terraform_plan_completed > 0:
        terraform_plan_completed_avg = round(
            terraform_plan_seconds / terraform_plan_completed, 2)

    terraform_apply_completed_avg = 0
    if terraform_apply_completed > 0:
        terraform_apply_completed_avg = round(
            terraform_apply_seconds / terraform_apply_completed, 2)

    terraform_destroy_completed_avg = 0
    if terraform_destroy_completed > 0:
        terraform_destroy_completed_avg = round(
            terraform_destroy_seconds / terraform_destroy_completed, 2)

    return_data = {
        'total_tests': total_reports,
        'running_tests': running_reports,
        'success_tests': num_success,
        'success_avg_duration': success_avg_duration,
        'success_duration_min': round(success_duration_min, 2),
        'success_duration_max': round(success_duration_max, 2),
        'failed_tests': num_failed,
        'failed_avg_duration': failed_avg_duration,
        'failed_duration_min': round(failed_duration_min, 2),
        'failed_duration_max': round(failed_duration_max, 2),
        'failed_in_terraform': failed_in_terraform,
        'failed_by_timeout': failed_by_timeout,
        'terraform_completed': terraform_completed,
        'terraform_completed_avg': terraform_completed_avg,
        'workspace_create_completed': workspace_create_completed,
        'workspace_create_completed_avg': workspace_create_completed_avg,
        'workspace_create_failed': workspace_create_failed,
        'terraform_plan_completed': terraform_plan_completed,
        'terraform_plan_completed_avg': terraform_plan_completed_avg,
        'terraform_plan_failed': terraform_plan_failed,
        'terraform_apply_completed': terraform_apply_completed,
        'terraform_apply_completed_avg': terraform_apply_completed_avg,
        'terraform_apply_failed': terraform_apply_failed,
        'terraform_destroy_completed': terraform_destroy_completed,
        'terraform_destroy_completed_avg': terraform_destroy_completed_avg,
        'terraform_destroy_failed': terraform_destroy_failed,
        'zones_summary': zones,
        'test_types': ttypes,
        'image_names': imagez
    }
    json_report = json.dumps(return_data, sort_keys=True,
                             indent=4, separators=(',', ': '))
    return app.response_class(response=json_report,
                              status=200, mimetype='application/json')


if __name__ == '__main__':
    LISTEN_PORT = os.getenv('LISTEN_PORT', '5000')
    app.run(host='0.0.0.0', port=int(LISTEN_PORT), threaded=True)
