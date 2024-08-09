# # D118-AWS-Attribute-Population

Script to populate custom attributes in Google Admin which are used for AWS SAML logins, but only for certain students who are enrolled in specific courses within PowerSchool.

## Overview

The purpose of this script is to allow students in our district to access the AWS appstream programs for certain courses such as computer science or the PLTW engineering courses, while not allowing other students so that the number of seats does not increase past what is expected.
It does this by looking at the custom attributes that are used for the AWS SAML login, compiling a dictionary of users who already have them set. Then it does a query through PowerSchool to find active students within a list of specified buildings, and the current terms for each student. Then each term for each student is searched for enrollments that match a list of course numbers, meaning that student should have access to AWS. If they are not already in the dictionary of users with the attributes set, it will set the custom attributes to the relevant values and add them to the dictionary. Then it goes through the dictionary and finds any accounts who did not have a matching class, and sets the custom attribute values to empty strings in order to remove them. This prevents those users from signing into the AWS SAML app as it will come back with an error instead of letting them continue.

## Requirements

I am assuming you have followed along to the AWS tutorial on setting up appstream to work with SAML found [here](https://aws.amazon.com/blogs/desktop-and-application-streaming/setting-up-g-suite-saml-2-0-federation-with-amazon-appstream-2-0/).

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB
- AWS_FEDERATION_ROLE

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool, as well as the string that will be filled into the custom attribute and has the AWS ARN information. If you wish to directly edit the script and include these credentials or to use other environment variable names, you can.

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)
- [Python-Google-API](https://github.com/googleapis/google-api-python-client#installation)

In addition, an OAuth credentials.json file must be in the same directory as the overall script. This is the credentials file you can download from the Google Cloud Developer Console under APIs & Services > Credentials > OAuth 2.0 Client IDs. Download the file and rename it to credentials.json. When the program runs for the first time, it will open a web browser and prompt you to sign into a Google account that has the permissions to modify users. Based on this login it will generate a token.json file that is used for authorization. When the token expires it should auto-renew unless you end the authorization on the account or delete the credentials from the Google Cloud Developer Console. One credentials.json file can be shared across multiple similar scripts if desired.
There are full tutorials on getting these credentials from scratch available online. But as a quickstart, you will need to create a new project in the Google Cloud Developer Console, and follow [these](https://developers.google.com/workspace/guides/create-credentials#desktop-app) instructions to get the OAuth credentials, and then enable APIs in the project (the Admin SDK API is used in this project).

## Customization

As part of the AWS SAML setup tutorial, you need to create custom attributes in a new category in Google Admin and connect those to the app, the names of the category and fields need to be inserted into `AWS_ATTRIBUTE_CATEGORY`, `FEDERATION_ROLE_FIELD`, and `SESSION_DURATION_FIELD`.

You will need to enter the class numbers of any courses that should grant access into `CLASS_NUMBERS`, and similarly you will need to enter the PowerSchool school codes that will be searched for students in those classes into `VALID_SCHOOL_CODES`.

You can define the duration that will be entered into the custom attribute named `SESSION_DURATION_FIELD` by changing `DURATION_VALUE` to the value in seconds (28800 is 8 hours).

As part of the removal process, we only want to remove the attributes from students, not any other accounts (like staff, utility accounts, etc). If this is not true and you want it removed from *all* accounts that aren't enrolled in the specified classes, you can change `ONLY_REMOVE_FROM_STUDENTS` to False.
If you are using it as default and only removing from students, you will need to define a string that shows up in the Organization Units of all students (but not staff) in `STUDENT_OU_IDENTIFIER`. In our case, students reside in OUs that contain the word "Students" but this may vary for your use.

Finally, the only other thing you will want to change is how a student's email is constructed, by changing the line `email = idNum +  "@d118.org"`. Obviously this will differ from district to district or use case, and you might need to change the SQL query to include other fields if you use something else (like a name) to construct their emails.
