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
from googleapiclient.errors import HttpError

# set up database connection info
un = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
cs = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

print(f"DBUG: Username: {un} |Password: {pw} |Server: {cs}")  # debug so we can see where oracle is trying to connect to/with

AWS_ATTRIBUTE_CATEGORY = "AWS-SAML-Attributes"  # name of the custom attribute categor
FEDERATION_ROLE_FIELD = "FederationRole"  # name of the field that houses the federation role within the above category
SESSION_DURATION_FIELD = "SessionDuration"  # name of the field that houses the session duration within the above category

CLASS_NUMBERS = ['35901','35801','88802','65401','65301','88801','65101','65102','55201']  # list of course 'numbers' to search for, must match exactly
VALID_SCHOOL_CODES = ['5']  # list of PowerSchool school codes to process students from and search for classes, so we can save time not looking through the courses of elementary students if not neccesary

ONLY_REMOVE_FROM_STUDENTS = True  # flag to determine whether we only will remove the attributes from students or from everyone. If everyone, any staff members will need to have different durations assigned to them so they are not removed
STUDENT_OU_IDENTIFIER = 'Students'  # only necessary if using the above flag. A string that should be in any student OU path (but not staff). For instance, our student OUs are all under /D118 Students/ so the word students is enough

ROLE_VALUE = os.environ.get('AWS_FEDERATION_ROLE')  # value to be used for the federation role
DURATION_VALUE = "28800"  # value to be used for the session duration

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

        # first do a query to find all users that have the custom attributes populated by searching for the session duration in users custom attributes
        currentUsers = {}  # create a blank dictionary, will have their emails and whether they should have the attributes removed later
        queryString = AWS_ATTRIBUTE_CATEGORY + '.' + SESSION_DURATION_FIELD + '=' + DURATION_VALUE # construct the query which looks for the specified duration value in the duration field in the AWS custom attribute category
        userToken = ''  # start with an empty token
        print(f'INFO: Finding all GA users with a session duration currently set to {DURATION_VALUE}, this may take a while')
        print(f'INFO: Finding all GA users with a session duration currently set to {DURATION_VALUE}, this may take a while', file=log)
        try:
            while userToken is not None:  # do a while loop while we still have the next page token to get more results with
                userResults = service.users().list(customer='my_customer',orderBy='email',projection='full',pageToken=userToken,query=queryString).execute()
                userToken = userResults.get('nextPageToken')
                users = userResults.get('users', [])
                for user in users:  # go through each user profile
                    # print(user.get('primaryEmail'))  # debug
                    if ONLY_REMOVE_FROM_STUDENTS:  # if we are only worrying about removing from students
                        if STUDENT_OU_IDENTIFIER in user.get('orgUnitPath'):  # see if they are a student by looking to see if the student identifier is somewhere in their OU string
                            currentUsers.update({user.get('primaryEmail'): 'Invalid'})  # if they are a student, initially mark them as invlaid
                        else:  # if they are not a student, mark them as valid
                            currentUsers.update({user.get('primaryEmail'): 'Valid'})
                    else:  # if we are not only worrying about removing attributes from students, everyone will initially be marked invalid
                        currentUsers.update({user.get('primaryEmail'): 'Invalid'})
            # print(f'DBUG: List of current AWS users: {currentUsers}')  # debug
        except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
            status = er.status_code
            details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
            print(f'ERROR {status} from Google API while finding users that have custom attributes set: {details["message"]}. Reason: {details["reason"]}')
            print(f'ERROR {status} from Google API while finding users that have custom attributes set: {details["message"]}. Reason: {details["reason"]}', file=log)
        except Exception as er:
            print(f'ERROR while finding users that have custom attributes set: {er}')
            print(f'ERROR while finding users that have custom attributes set: {er}', file=log)

        try:
            with oracledb.connect(user=un, password=pw, dsn=cs) as con:  # create the connecton to the database
                with con.cursor() as cur:  # start an entry cursor
                    print(f"INFO: Connection established to the PowerSchool server with oracle driver version: {con.version}")
                    print(f"INFO: Connection established to the PowerSchool server with oracle driver version: {con.version}", file=log)
                    today = datetime.now()  # get todays date and store it for finding the correct term later
                    schoolBinds = ",".join(":" + str(i + 1) for i in range(len(VALID_SCHOOL_CODES)))  # dynamically build the binds list based on the school constant variable. See https://python-oracledb.readthedocs.io/en/latest/user_guide/bind.html#bind
                    sqlQuery = f'SELECT student_number, dcid, id, schoolid, grade_level FROM students WHERE enroll_status = 0 AND schoolid IN ({schoolBinds})'
                    cur.execute(sqlQuery, VALID_SCHOOL_CODES)  # execute the query for the given school list
                    students = cur.fetchall()
                    for student in students:
                        try:
                            idNum = str(int(student[0]))  # the student number usually referred to as their "id number"
                            stuDCID = str(student[1])  # the student dcid
                            internalID = str(student[2])  # get the internal id of the student that is referenced in the classes entries
                            schoolID = int(student[3])  # schoolcode
                            grade = int(student[4])  # grade level
                            email = idNum + "@d118.org"  # construct their email. Change if not in D118
                            # print(student)
                            try:
                                cur.execute("SELECT id, firstday, lastday, schoolid, dcid FROM terms WHERE schoolid = :school ORDER BY dcid DESC", school = schoolID)
                                terms = cur.fetchall()
                                for termEntry in terms:  # go through every term result
                                    #compare todays date to the start and end dates with 5 days before start so it populates before the first day of the term
                                    if ((termEntry[1] - timedelta(days=5) < today) and (termEntry[2] + timedelta(days=1) > today)):
                                        termid = str(termEntry[0])
                                        termDCID = str(termEntry[4])
                                        # print(f"DBUG: Found good term for student {idNum} at building {schoolID} : {termid} | {termDCID}")  # debug
                                        # print(f"DBUG: Found good term for student {idNum} at building {schoolID} : {termid} | {termDCID}", file=log)  # debug
                                        # print(f'DBUG: Starting student {idNum} at building {schoolID} in term {termid}')
                                        # print(f'DBUG: Starting student {idNum} at building {schoolID} in term {termid}', file=log)
                                        userClasses = []  # make empty list for storing of the classes that match our queries
                                        # do the query of their courses for the current term, filter to match certain courses
                                        classBinds = ",".join(":" + str(i + 1) for i in range(len(CLASS_NUMBERS)))  # dynamically build the binds list based on the class numbers list
                                        classStudentInfo = CLASS_NUMBERS + [internalID, termid]  # append the student internal ID and termID to the class numbers so we can pass all of them together as binds to the query
                                        sqlQuery = f'SELECT cc.schoolid, cc.course_number, cc.sectionid, cc.section_number, cc.termid, cc.expression, courses.course_name FROM cc LEFT JOIN courses ON cc.course_number = courses.course_number WHERE cc.course_number IN ({classBinds}) AND cc.studentid = :studentInternalID AND cc.termid = :termid ORDER BY cc.course_number'
                                        cur.execute(sqlQuery, classStudentInfo)
                                        currentClassResults = cur.fetchall()
                                        userClasses = userClasses + currentClassResults # append the current results to our total results so we do not overwrite any found classes with blanks

                                        if userClasses:  # if there are any results, it means the student is enrolled in one of our desired class
                                            for entry in userClasses:  # go through each class that matches to print it out for logging purposes. Not neccessary, could be removed if desired
                                                # print(entry)
                                                className = entry[6]
                                                courseNumber = entry[1]
                                                # print(entry, file=log) # debug
                                                print(f'INFO: Student {idNum} should have access because they are enrolled in course number {courseNumber} named "{className}" at building {schoolID} for the current term {termid}')
                                                print(f'INFO: Student {idNum} should have access because they are enrolled in course number {courseNumber} named "{className}" at building {schoolID} for the current term {termid}', file=log)
                                            
                                            if not currentUsers.get(email):  # look to see if the user already has an entry in the current users dictionary, if not we need to update their custom attributes
                                                try:
                                                    print(f'INFO: User {email} does not currently have custom attributes populated when they should, they will be updated')
                                                    print(f'INFO: User {email} does not currently have custom attributes populated when they should, they will be updated', file=log)
                                                    # do the update of custom attributes on the users google account
                                                    service.users().update(userKey=email, body={'customSchemas' : {AWS_ATTRIBUTE_CATEGORY : {FEDERATION_ROLE_FIELD : ROLE_VALUE, SESSION_DURATION_FIELD : DURATION_VALUE}}}).execute()
                                                except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                                                    status = er.status_code
                                                    details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                                                    print(f'ERROR {status} from Google API while updating custom attributes for user {email}: {details["message"]}. Reason: {details["reason"]}')
                                                    print(f'ERROR {status} from Google API while updating custom attributes for user {email}: {details["message"]}. Reason: {details["reason"]}', file=log)
                                                except Exception as er:
                                                    print(f'ERROR while updating custom attributes or users dictionary: {er}')
                                                    print(f'ERROR while updating custom attributes or users dictionary: {er}', file=log)
                                            currentUsers.update({email: 'Valid'})  # change the dictionary entry to be valid instead of invalid               

                            except Exception as er:
                                print(f'ERROR while getting terms for {idNum}: {er}')
                                print(f'ERROR while getting terms for {idNum}: {er}', file=log)
                            
                        except Exception as er:
                            print(f'ERROR on {student[0]}: {er}')
                            print(f'ERROR on {student[0]}: {er}', file=log)
                    
                    # once we have processed all the students in PS and found those in the class list, go back through the users who have the custom attributes and remove them from any still marked invalid
                    # print(currentUsers)  # debug
                    for email, status in currentUsers.items():
                        try:
                            if status == 'Invalid':
                                print(f'INFO: Student {email} should no longer have access to AWS, removing custom attributes')
                                print(f'INFO: Student {email} should no longer have access to AWS, removing custom attributes', file=log)
                                service.users().update(userKey=email, body={'customSchemas' : {AWS_ATTRIBUTE_CATEGORY : {FEDERATION_ROLE_FIELD : '', SESSION_DURATION_FIELD : ''}}}).execute()  # replace the attributes with empty strings
                        except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                            status = er.status_code
                            details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                            print(f'ERROR {status} from Google API while removing custom attributes for user {email}: {details["message"]}. Reason: {details["reason"]}')
                            print(f'ERROR {status} from Google API while removing custom attributes for user {email}: {details["message"]}. Reason: {details["reason"]}', file=log)
                        except Exception as er:
                            print(f'ERROR while doing end process to check users who should no longer have custom attributes: {er}')
                            print(f'ERROR while doing end process to check users who should no longer have custom attributes: {er}', file=log)
        except Exception as er:
            print(f'ERROR while connecting to PowerSchool or doing initial student query: {er}')
            print(f'ERROR while connecting to PowerSchool or doing initial student query: {er}', file=log)
        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)