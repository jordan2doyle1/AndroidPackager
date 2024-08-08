#
# Author: Jordan Doyle
#
# usage: build.py [-h] [-o OUTPUT] [-v] [-c]
#
# options:
#   -h, --help                          show this help message and exit
#   -o OUTPUT, --output OUTPUT          set output directory
#   -v, --verbose                       output all log messages
#   -c, --clean                         delete previous builds
#

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("-o", "--output", type=str, default='output', help="set output directory")
arg_parser.add_argument("-v", "--verbose", default=False, action="store_true", help="output all log messages")
arg_parser.add_argument("-c", "--clean", default=False, action="store_true", help="delete previous builds")
args = arg_parser.parse_args()

log_level = logging.DEBUG if args.verbose else logging.INFO
log_format = '[%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s'
logging.basicConfig(level=log_level, format=log_format,
                    handlers=[logging.FileHandler(os.path.join(args.output, 'build.log')),
                              logging.StreamHandler(sys.stdout)])

if not os.path.isdir(args.output):
    logging.error("Provided output directory (" + args.output + ") does not exist.")
    exit(20)

apk_directory = os.path.join(args.output, "apk")
if not os.path.isdir(apk_directory):
    logging.error("APK directory (" + apk_directory + ") does not exist.")
    exit(40)

dapk_directory = os.path.join(args.output, "dapk")
if args.clean:
    if os.path.isdir(dapk_directory):
        logging.info("Deleting previous debug APK files.")
        shutil.rmtree(dapk_directory)

if not os.path.isdir(dapk_directory):
    logging.info("Creating new debug APK directory (" + dapk_directory + ").")
    os.makedirs(dapk_directory)

if "JAVA_HOME" not in os.environ:
    logging.warning("Java home environment variable is not set.")

if "JAVA_11_HOME" not in os.environ:
    logging.warning("Java 11 home environment variable is not set.")


def update_build_file(build_file):
    if not os.path.isfile(build_file + ".orig"):
        logging.info("Creating backup of gradle build file.")
        shutil.copy(build_file, build_file + ".orig")

    with open(build_file, "r") as file:
        logging.info("Reading app gradle file contents.")
        contents = file.readlines()

    build_block = debug_block = debug_found = debugging = False
    other_block = 0
    for index, line in enumerate(contents):
        if build_block:
            if debug_block:
                if "debuggable true" in line:
                    debugging = True
                elif "}" in line and "{" not in line:
                    debug_block = False
                    if not debugging:
                        logging.info("Adding 'debuggable true' to the gradle build.")
                        contents.insert(index, "\t\t\tdebuggable true\n")
                    debugging = False
                continue
            elif "debug {" in line:
                debug_block = True
                debug_found = True
                continue

            if other_block > 0:
                if "}" in line and "{" not in line:
                    other_block = other_block - 1
                elif "{" in line and "}" not in line:
                    other_block = other_block + 1
                continue

            if "{" in line and "}" not in line:
                other_block = other_block + 1
                continue

            if "}" in line and "{" not in line:
                build_block = False
                if not debug_found:
                    logging.info("Adding debug release to the app gradle build.")
                    contents.insert(index, "\t\t}\n")
                    contents.insert(index, "\t\t\tdebuggable true\n")
                    contents.insert(index, "\t\tdebug {\n")
        elif "buildTypes {" in line:
            build_block = True
            continue

    with open(build_file, "w") as file:
        logging.info("Writing updated content to app gradle file.")
        file.writelines(contents)


def copy_apk_file(title, source, destination, name):
    file = None
    for file_path in Path(source).rglob("*.apk"):
        file = str(file_path.resolve())
        logging.info("Debug APK for " + title + " is " + file)
        break

    if file is None:
        logging.error("Failed to find the debug APK for " + title + ".")
        return

    logging.info("Copying debug APK to DAPK directory.")
    shutil.copy(file, str(os.path.join(destination, name + ".apk")))


def build_apk(title, source, build):
    logging.info("Running gradle build on " + title + ".")
    command = "gradlew.sh assembleDebug -Dorg.gradle.java.home=" + os.environ.get("JAVA_11_HOME") \
        if title in ["Ad-Free", "Gpstest", "Timetable"] else "gradlew.sh assembleDebug"

    exit_code = subprocess.call(os.getcwd() + "/" + command + " > " + source + "/build.log 2>&1", cwd=build, shell=True)
    if exit_code != 0:
        logging.error("Gradle build for " + title + " failed. See log for details.")

    return exit_code


for apk_file in os.listdir(apk_directory):
    if not os.path.isfile(os.path.join(apk_directory, apk_file)) or not apk_file.endswith(".apk"):
        logging.info("Ignoring file " + apk_file)
        continue

    app = os.path.splitext(os.path.basename(apk_file))[0]
    app_title = ''.join([i for i in app if not i.isdigit()]).replace('_', ' ').title().strip()

    if os.path.isfile(os.path.join(dapk_directory, apk_file)):
        logging.info(app_title + " already built, Skipping.")
        continue

    logging.info("Processing '" + app_title + "'.")

    source_directory = os.path.join(args.output, "source", app)
    if not os.path.isdir(source_directory):
        logging.error("Source directory (" + source_directory + ") does not exist.")
        continue

    for path in Path(source_directory).rglob('local.properties'):
        properties_file = str(path.resolve())
        os.remove(properties_file)

    gradle_build_file = None
    for path in Path(source_directory).rglob('*/build.gradle'):
        gradle_build_file = str(path.resolve())
        logging.info("Gradle build file for " + app_title + " is " + gradle_build_file)
        break

    if gradle_build_file is None:
        logging.error("Failed to find gradle build file for " + app_title + ".")
        continue
    update_build_file(gradle_build_file)

    build_directory = None
    for path in Path(source_directory).rglob("build.gradle"):
        build_directory = os.path.dirname(str(path.resolve()))
        logging.info("Build directory for " + app_title + " is " + build_directory)
        break

    if build_directory is None:
        logging.error("Failed to find build directory for " + app_title + ".")
        continue

    if build_apk(app_title, source_directory, build_directory) == 0:
        copy_apk_file(app_title, source_directory, dapk_directory, app)
