#!/usr/bin/python

"""This script will orchestrate the main enrollment workflow for DEP and OTA on-boarding and enrollment at Snowflake
This will be a no touch deployment workflow by default, but also still allow OTA workflows

by tlark

Mac Admin Slack - @tlark

Please test this code before running it in your environment"""

# import modules
from SystemConfiguration import SCDynamicStoreCopyConsoleUser
from Foundation import NSHomeDirectoryForUser
import sys
import logging
import subprocess
import os
import time
import urllib2
import plistlib
from Cocoa import NSRunningApplication


# positional parameters passed from jamf, always start with $4 as $1-$3 are reserved by jamf
#
# this will be the list of policy triggers we need to run at Enrollment
# list of manual trigger policies in a positional parameter of standard software you want to install
POLICY_LIST = sys.argv[4].split(",")
# this is for security specific payloads to run last so they can run before the reboot
SECURITY_LIST = sys.argv[5].split(",")
# this list for for any dependencies that need to be installed before this script can run, like DEPNotify, or anything
# custom in your env
DEPENDENCY_LIST = sys.argv[6].split(",")
HEALTH_URL = sys.argv[7]

# global vars for the entire code base

# grab current user info, in case we need it
USER, UID, GID = SCDynamicStoreCopyConsoleUser(None, None, None)
# grab home folder in case we need it
USER_HOME = NSHomeDirectoryForUser(USER)
# specify file system path with DEPNotify will live
DEP_NOTIFY_PATH = (
    "/Library/Application Support/JAMF/snowflake/DEPNotify.app/Contents/MacOS/DEPNotify"
)
# global logger info for this workflow, can set path to something else
LOGFILE = "/var/log/snowflake-enrollment.log"
# basic logging config for the logger
logging.basicConfig(
    filename="%s" % LOGFILE, format="%(asctime)s %(message)s", level=logging.DEBUG
)
# log for DEP Notify
DEP_LOG = "/var/tmp/depnotify.log"
# path to icon for DEP Notify, whatever icon you want in the UI
DEPSCREEN = "/path/to/custom/branding.png"
# master dictionary for vanity names to display in DEP Notify
# for example your policy might be called install_app02 and you might want it to display "Application 02"
MAIN_POLICY_DICT = {
    "install_Finder_Prefs": "macOS Finder Preferences",
    "autoupdate-Firefox": "Firefox",
    "install_Chrome": "Google Chrome",
    "install_slack": "Slack",
    "install_office": "Microsoft Office",
}


# start functions


def create_logs():
    """create log file for this specific script"""
    if not os.path.exists(LOGFILE):
        open(LOGFILE, "w")
        LOGFILE.close()
        logging.info("Creating log file...")


def write_to_dnlog(text):
    """function to modify the DEP log and send it commands"""
    depnotify = "/private/var/tmp/depnotify.log"
    with open(depnotify, "a+") as log:
        log.write(text + "\n")


def install_dependencies():
    """function to handle jamf binary dependency.  This actually may be redundant and not needed"""
    # this function may end up being pointless FYI
    while not os.path.exists("/usr/local/bin/jamf"):
        print("waiting for jamf binary to install")
        time.sleep(0.5)
    return True


def check_jss_connection():
    """will use urllib2 to check the status of the healthCheck.html file, not done yet"""
    response = urllib2.urlopen(HEALTH_URL)
    data = response.read()
    result = data.strip()
    if result != "[]":
        write_to_dnlog("Status: can not reach the JSS, exiting now!...")
        write_to_dnlog("Command: Quit")
        logging.error("Can not reach the JSS, forcing exit now...")
        sys.exit(1)


def start_dep_notify():
    """function to launch DEPNotify as end user"""
    # launchctl does not like integer data types, so you must convert the UID to a string
    # build unix command in list
    cmd = ["launchctl", "asuser", str(UID), "open", "-a", DEP_NOTIFY_PATH]
    # run the command
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    # test output, force non zero exit status if fails
    if proc.returncode != 0:
        logging.error("DEPNotify failed to launch")
        sys.exit(1)
    else:
        return True


def run_jamf_policy(run_list):
    """run through all jamf policies that need to be done"""
    write_to_dnlog("Status: Installing software...")
    number_of_policies = len(run_list)
    write_to_dnlog("Command: DeterminateManual: %s" % number_of_policies)
    for index, policy in enumerate(run_list, 1):
        # get the vanity name from the MAIN_POLICY_DICT
        name = MAIN_POLICY_DICT[policy]
        write_to_dnlog("Status: Deploying %s" % name)
        write_to_dnlog("Command: DeterminateManualStep:")
        logging.info("starting %s policy..." % policy)
        cmd = ["jamf", "policy", "-event", str(policy)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, errors = proc.communicate()
        if proc.returncode != 0:
            error_msg = "%s code %s" % (errors.strip(), proc.returncode)
            logging.error("jamf binary failed to install %s, %s", policy, error_msg)
            write_to_dnlog("Status: %s policy failed, please see logs..." % policy)
        elif proc.returncode == 0:
            logging.info("jamf policy %s returned successful.." % policy)
            write_to_dnlog("Status: %s was successfully installed..." % name)
    write_to_dnlog("Command: DeterminateOff:")
    write_to_dnlog("Command: DeterminateOffReset:")


def set_computername():
    """set the computer name to the serial number of the Mac"""
    cmd = ["system_profiler", "SPHardwareDataType", "-xml"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    data = plistlib.readPlistFromString(out)
    serial = data[0]["_items"][0]["serial_number"]
    options = ["HostName", "ComputerName", "LocalHostName"]
    for option in options:
        subprocess.call(["scutil", "--set", option, serial])


def software_updates():
    """update macOS to the latest version plus security updates"""
    write_to_dnlog(
        "Status: Now running Software Updates, this may take up to 30 minutes to complete..."
    )
    write_to_dnlog(
        "Command:  MainText: Now running Apple Updates, the system may reboot here"
    )
    logging.info("starting software updates...")
    cmd = ["softwareupdate", "-iRa"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, errors = proc.communicate()
    if proc.returncode != 0:
        error_msg = "%s code %s" % (errors.strip(), proc.returncode)
        logging.error("Software update failed, %s" % error_msg)
        write_to_dnlog(
            "Status: Software Update failed, please see /var/log/install.log"
        )
    elif proc.returncode == 0:
        logging.info("Software Update successfully ran...")
        write_to_dnlog("Status: Software Update was successful")
    if "restart" not in out or "restart" not in errors:
        # we need to restart the Mac for settings to apply, so if SWU does not do it
        # we will do it now
        restart = ["shutdown", "-r", "NOW"]
        subprocess.call(restart, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def wait_for_userspace():
    """this function will check to see if the Dock and Finder are present to ensure user space
    has fully loaded.  This will stop that race condition"""
    # give the system a few seconds to log into user space
    time.sleep(7.0)
    # check to see if still in the "mac buddy" user context
    while USER == "_mbsetupuser":
        user, uid, gid = SCDynamicStoreCopyConsoleUser(None, None, None)
        logging.info("detected Mac Buddy user context...")
        time.sleep(1.0)
        if user != "_mbsetupuser":
            break
    # test to make sure both the Finder and Dock are running by bundle ID to ensure user space is fully loaded
    app1 = None
    app2 = None
    while not all([app1, app2]):
        app1 = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
            "com.apple.dock"
        )
        app2 = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
            "com.apple.finder"
        )
        logging.info("waiting for apps to appear running..")
        time.sleep(0.5)


# main to run all the things
def main():
    """configure DEP notify for first run and execute enrollment workflow"""
    # create log file first
    create_logs()
    # log start info
    logging.info("Starting new enrollment flow now...")
    logging.info("Waiting for user space to fully load...")
    # waiting for user space
    wait_for_userspace()
    # check if the jss is available
    # check_jss_connection()
    # set the computer name
    logging.info("setting the computer name...")
    set_computername()
    # ensure dependencies and jamf binary is present
    logging.info("Installing initial dependencies for DEP Notify flow...")
    install_dependencies()
    # install dependency list for before we continue...
    run_jamf_policy(DEPENDENCY_LIST)
    # start DEP Notify flow
    write_to_dnlog("Command: Image: %s" % DEPSCREEN)
    write_to_dnlog("Command: MainTitle: Welcome to Company")
    write_to_dnlog(
        "Command: MainText: Please wait while we setup and configure your Mac at Company.  "
        "This should only take a few minutes and will require a restart of your Mac.  "
        "If you need assistance please contact IT at helpdesk@company.com"
    )
    write_to_dnlog("Status: Preparing your system...")
    start_dep_notify()
    # install base software/config
    run_jamf_policy(POLICY_LIST)
    # apply security compliance and reboot last
    run_jamf_policy(SECURITY_LIST)
    software_updates()
    write_to_dnlog("Status: Enrollment is complete, exiting...")
    write_to_dnlog("Command: Quit")


if __name__ == "__main__":
    main()
