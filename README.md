# DEP-Notify

![Image of DEP Notify HUD](https://raw.githubusercontent.com/t-lark/DEP-Notify/master/images/depnotify1.png)

## Introduction

This script is meant to be a very quick way to use [DEP Notify](https://gitlab.com/Mactroll/DEPNotify) and to be used as a reusable template for multiple workflows.   This code uses positional parameters to feed lists of manual trigger policies from [Jamf Pro](https://www.jamf.com/lp/jamf-pro/) to configure macOS devices from either a DEP enrollment or an OTA enrollment workflow.

## Usage

To use this script, copy or clone it into your Jamf Pro envrionment, and modify the global variables and verbiage to meet your specific needs.  Since DEP Notify does read values from a log stream, you will need to go over the code and ensure to put in the exact text you wish DEP Notify to dispaly to your end users.   

In a policy, select this script as the payload and fill out the positional parameters like the example picture below:

![jamf parameter config](https://raw.githubusercontent.com/t-lark/DEP-Notify/master/images/dep_paramters.png)

The paramters are split into paramters 4-6, since jamf has a character limit of 255 characters per a parameter in the database.  This was a design decision just in case anyone ever had the neeed to use more than 255 characters total, you can split the polciies between those 3 parameters.   Logically the script will run all dependencies first, all software second, and all security payloads last (since security payloads sometimes reqire reboots).  

```
NOTE: Python will split() these items by comma, so you only need to input the custom policy 
event trigger name and seprate each one by comma.  The code will then split this into a list 
to iterate thorugh them and execute them
```

The health check URL, I put in here so you can test to see if remote clients or remote offices may have issues reaching out to your Jamf Pro server.  Due take notice that I had issues with Jamf Cloud and built this in for that reason, but I have also seen false negatives where the test fails, but my jamf cloud isntance is acutally up and running just fine.   So, this needs to be tested and by default is commented out of the code.  Results may vary form environment to environment.

The `MAIN_POLICY_DICT` is a dictionary of all the jamf policies you may ever want to run in any enrollment workflow, and where you input the value of what you want the name to be displayed by DEP Notify.  In the picture above, I am using the verbiage "Deploying Firefox", but my manual trigger policy is named `Autoupdate-Firefox` which is probably confusing to an end user.  So, you will need to populate the dictionary with the proper values, and if something doesn't match it will break the code.  See the example below:

```
Example Dictionary:

MAIN_POLICY_DICT={"Autoupdate-Firefox": "Firefox", "install_mso365": "Microsoft Office 2019", "install_chrome": "Google Chrome"}
```

## Dependencies

Any dependencies you have will need to be deployed first.  Things like custom branding, and of course the DEP Notify App itself, which this script will do as long as it is deployed in the `DEPENDENCY_LIST` parameter, it will install before DEP Notify is called in code.  

Also, specify the path of where you are deploying DEP Notify.  As a desigh choice, I have chosen to put it into `/Library/Application Support/JAMF` folder, so if a `removeframeork` is called, that app is also removed.  You can choose to deploy it anywhere, just be sure to update the paths in the global variables section of the code.

## Branding

You will need to deploy your custom logos and branding, and then specifcy where they are on the file system in the global variables section of the script, which is defined in code as `DEPSCREEN`


## Reusable Code

This script is used in two workflows at my current job.   One if is for end users and one is for Zoom Rooms.  This is why I chose to build the code more as a template than anything else.  This way when one of our IT employees sets up a new Zoom Room they will get a different workflow using the same DEP Notify code, versus a standard employee running the normal DEP Notify workflow.   So, hopefully this may help in those situations where you also need to split out workflows for various reasons.


## Issues and Features

I do not have a ton of spare time, but please feel free to file an issue here if you find one, or find me on the Mac Admins Slack (@tlark) and ping me there.  I would not be against any added features if people feel strongly to contribute to this.  
