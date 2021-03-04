# Copyright (C) 2020 Graylog, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the Server Side Public License, version 1,
# as published by MongoDB, Inc.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Server Side Public License for more details.
#
# You should have received a copy of the Server Side Public License
# along with this program. If not, see
# <http://www.mongodb.com/licensing/server-side-public-license>.

import argparse
import logging

from pprint import pformat
from pymongo import MongoClient

logging.basicConfig(filename='HTTPAlarmCallbackMigration.log', level=logging.INFO,
                    format='%(asctime)s :: %(levelname)s :: %(message)s ')

def convert_http_alarm_callbacks_to_notifications(client, new_endpoint, write):
    event_notifications = client.graylog.event_notifications
    legacy_http_callback_count = event_notifications.count_documents({'config.type': 'legacy-alarm-callback-notification-v1',
                                                           'config.callback_type': 'org.graylog2.alarmcallbacks.HTTPAlarmCallback'})
    legacy_http_callbacks = event_notifications.find({'config.type': 'legacy-alarm-callback-notification-v1',
                                                      'config.callback_type': 'org.graylog2.alarmcallbacks.HTTPAlarmCallback'})
    updated_records = 0

    logging.info('Found %s Legacy HTTP Alarm Callbacks', legacy_http_callback_count)

    for callback in legacy_http_callbacks:
        logging.info('Processing record graylog.event_notifications[%s]', callback['_id'])
        logging.info('Record before udpate:\n%s', pformat(callback))

        callback['config']['type'] = 'http-notification-v1'
        if new_endpoint and len(new_endpoint) > 0:
            callback['config']['url'] = new_endpoint
        else:
            callback['config']['url'] = callback['config']['configuration']['url']

        callback['config'].pop('callback_type', None)
        callback['config'].pop('configuration', None)
        callback['description'] = callback['description'] + ' - Migrated from legacy HTTP Alarm Callback'

        logging.info('Record after update:\n%s', pformat(callback))
        if write:
            logging.info('Updating record graylog.event_notifications[%s]', callback['_id'])
            event_notifications.replace_one(filter={'_id': callback['_id']}, replacement=callback, upsert=True)
            updated_records += 1
        else:
            logging.info('Not updating record graylog.event_notifications[%s] because write flag not set', callback['_id'])

    logging.info('Updated %s Legacy HTTP Alarm Callbacks to HTTP Notifications', updated_records)

def build_connection_string(args):
    conn_str = 'mongodb://'

    # Username and password must either both be present or both be absent
    if args.user and args.password:
        conn_str = conn_str + args.user + ':' + args.password + '@'
    elif args.user or args.password:
        return ''

    conn_str = conn_str + args.server + ':' + str(args.port)

    logging.info('Using MongoDB connection string [%s]', conn_str)

    return conn_str

def confirm_update():
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='A program for migrating Graylog HTTP Alarm Callbacks to HTTP Notifications')
    parser.add_argument('-s', '--server', help='The MongoDB server (defaults to "localhost")', default='localhost', type=str)
    parser.add_argument('-p', '--port', help='The MongoDB port (defaults to 27017)', default=27017, type=int)
    parser.add_argument('-u', '--user', help='The MongoDB user id (required if password is specified)', type=str)
    parser.add_argument('-w', '--password', help='The password for the MongoDB user (required if user is specified)', type=str)
    parser.add_argument('-e', '--endpoint', help='The new endpoint/URL for HTTP Notifications.  If not provided, the old endpoint will continue to be used.  Note that HTTP Notifications use a different schema than Legacy HTTP Alarm Callbacks, which may not be compatible with endpoints built for HTTP Alarm Callbacks', type=str)
    parser.add_argument('-W', '--write', help='If this flag is not added, the script will execute a dry-run and no modifications will be made to records in MongoDB', action='store_true')
    args = parser.parse_args()

    connection_string = build_connection_string(args)

    if len(connection_string) > 0:
        client = MongoClient(connection_string)
        convert_http_alarm_callbacks_to_notifications(client, args.endpoint, args.write)
    else:
        parser.print_help()
