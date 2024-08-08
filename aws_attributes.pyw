"""Script to populate the GA custom attributes used for AWS for students enrolled in certain classes in PS.

https://github.com/Philip-Greyson/D118-AWS-Attribute-Population

Looks at all the students in the student OU, gets their current custom attributes.
Finds all students in PS that are in relevant course numbers.
Verifies those students have the correct custom attributes populated.
Removes the custom attributes of students not in the courses.

Needs oraceldb: pip install oracledb
Needs the google-api-python-client, google-auth-httplib2 and the google-auth-oauthlib
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

See the following for table information
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/cc-4-ver3-6-1
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/terms-13-ver3-6-1
"""


# importing module
import datetime  # needed to get current date to check what term we are in
import os  # needed to get environment variables
from datetime import *

import oracledb  # needed for connection to PowerSchool (oracle database)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# set up database connection info
un = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
cs = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

print(f"DBUG: Username: {un} |Password: {pw} |Server: {cs}")  # debug so we can see where oracle is trying to connect to/with

AWS_ATTRIBUTE_CATEGORY = "AWS-SAML-Attributes"  # name of the custom attribute categor
FEDERATION_ROLE_FIELD = "FederationRole"  # name of the field that houses the federation role within the above category
SESSION_DURATION_FIELD = "SessionDuration"  # name of the field that houses the session duration within the above category
CLASS_NUMBERS = ['163']  # list of course 'numbers' to search for, must match exactly

# Google API Scopes that will be used. If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/admin.directory.orgunit', 'https://www.googleapis.com/auth/admin.directory.userschema']


if __name__ == '__main__':  # main file execution
    with open('aws_attribute_log.txt', 'w', encoding='utf-8') as log:  # open logging file
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)

        # Get credentials from json file, ask for permissions on scope or use existing token.json approval, then build the "service" connection to Google API
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('admin', 'directory_v1', credentials=creds)

        with oracledb.connect(user=un, password=pw, dsn=cs) as con:  # create the connecton to the database
            with con.cursor() as cur:  # start an entry cursor
                print("Connection established: " + con.version)
                print("Connection established: " + con.version, file=log)
                today = datetime.now()  # get todays date and store it for finding the correct term later
    
        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)