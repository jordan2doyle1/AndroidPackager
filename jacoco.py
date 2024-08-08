#
# Author: Jordan Doyle
#
# usage: jacoco.py [-h] [-o OUTPUT] [-d] [-s] [-f] [-a AGE] [-i MIN] [-x MAX] [-c] [-p] [-v] [-g]
#
# options:
#   -h, --help                          show this help message and exit
#   -o OUTPUT, --output OUTPUT          set output directory
#   -j, --jacoco                        set jacoco class directory
#   -v, --verbose                       output all log messages
#   -c, --clean                         delete previous builds
#

import argparse
import logging
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("-o", "--output", type=str, default='output', help="set output directory")
arg_parser.add_argument("-v", "--verbose", default=False, action="store_true", help="output all log messages")
arg_parser.add_argument("-j", "--jacoco", type=str, default='classes', help="set jacoco class directory")
arg_parser.add_argument("-c", "--clean", default=False, action="store_true", help="delete previous builds")
args = arg_parser.parse_args()

log_level = logging.DEBUG if args.verbose else logging.INFO
log_format = '[%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s'
logging.basicConfig(level=log_level, format=log_format,
                    handlers=[logging.FileHandler(os.path.join(args.output, 'jacoco_build.log')),
                              logging.StreamHandler(sys.stdout)])

if not os.path.isdir(args.output):
    logging.error("Provided output directory (" + args.output + ") does not exist.")
    exit(20)

if not os.path.isdir(args.jacoco):
    logging.error("JaCoco class directory (" + args.jacoco + ") does not exist.")
    exit(30)

apk_directory = os.path.join(args.output, "apk")
if not os.path.isdir(apk_directory):
    logging.error("APK directory (" + apk_directory + ") does not exist.")
    exit(40)

japk_directory = os.path.join(args.output, "japk")
if args.clean:
    if os.path.isdir(japk_directory):
        logging.info("Deleting previous JaCoco APK files.")
        shutil.rmtree(japk_directory)

if not os.path.isdir(japk_directory):
    logging.info("Creating new JaCoco APK directory (" + japk_directory + ").")
    os.makedirs(japk_directory)

if "JAVA_HOME" not in os.environ:
    logging.warning("Java home environment variable is not set.")

java_11_enabled = True
if "JAVA_11_HOME" not in os.environ:
    logging.warning("Java 11 home environment variable is not set.")
    java_11_enabled = False


def update_build_file(build_file):
    if not os.path.isfile(build_file + ".orig"):
        logging.info("Creating backup of gradle build file.")
        shutil.copy(build_file, build_file + ".orig")

    with open(build_file, "r") as file:
        logging.info("Reading app gradle file contents.")
        contents = file.readlines()

    androidx = build_block = debug_block = other_block = debug_found = debugging = coverage = False
    for index, line in enumerate(contents):
        if build_block:
            if debug_block:
                if "debuggable true" in line:
                    debugging = True
                elif "testCoverageEnabled true" in line:
                    coverage = True
                elif "}" in line:
                    debug_block = False
                    if not debugging:
                        logging.info("Adding 'debuggable true' to the gradle build.")
                        contents.insert(index, "\t\t\tdebuggable true\n")
                    if not coverage:
                        logging.info("Adding 'testCoverageEnabled true' to the gradle build.")
                        contents.insert(index, "\t\t\ttestCoverageEnabled true\n")
                    debugging = coverage = False
                continue
            elif "debug {" in line:
                debug_block = True
                debug_found = True
                continue

            if other_block:
                if "}" in line:
                    other_block = False
                continue
            elif "{" in line:
                other_block = True
                continue

            if "}" in line:
                build_block = False
                if not debug_found:
                    logging.info("Adding debug release to the app gradle build.")
                    contents.insert(index, "\t\t}\n")
                    contents.insert(index, "\t\t\ttestCoverageEnabled true\n")
                    contents.insert(index, "\t\t\tdebuggable true\n")
                    contents.insert(index, "\t\tdebug {\n")
        elif "buildTypes {" in line:
            build_block = True
            continue

        if "androidx.appcompat:appcompat" in line:
            androidx = True

    with open(build_file, "w") as file:
        logging.info("Writing updated content to app gradle file.")
        file.writelines(contents)

    return androidx


def update_manifest_file(manifest_file):
    if not os.path.isfile(manifest_file + ".orig"):
        logging.info("Creating backup of manifest file.")
        shutil.copy(manifest_file, manifest_file + ".orig")

    logging.info("Parsing manifest file content.")
    tree = ElementTree.parse(manifest_file)
    root = tree.getroot()

    if "package" in root.keys():
        package = root.get("package")
    else:
        return None

    android_namespace = tool_namespace = None
    for key, value in root.attrib.items():
        if "http://schemas.android.com/apk/res/android" in value:
            android_namespace = key
            continue
        if "http://schemas.android.com/tools" in value:
            tool_namespace = key
            continue

    if android_namespace is None:
        root.set("xmlns:android", "http://schemas.android.com/apk/res/android")
        android_namespace = "android"

    if tool_namespace is None:
        root.set("xmlns:tools", "http://schemas.android.com/tools")
        tool_namespace = "tools"

    namespace_link = "{http://schemas.android.com/apk/res/android}"

    add_instrument = True
    for element in tree.findall("instrumentation"):
        if element.get(namespace_link + "name") == package + ".JacocoInstrumentation":
            add_instrument = False
            break

    if add_instrument:
        logging.info("Adding instrument element to manifest content.")
        instrument = ElementTree.Element("instrumentation")
        instrument.set(android_namespace + ":name", package + ".JacocoInstrumentation")
        instrument.set(android_namespace + ":targetPackage", package)
        root.append(instrument)

    add_read_permission = add_write_permission = True
    for element in tree.findall("uses-permission"):
        if element.get(namespace_link + "name") == "android.permission.READ_EXTERNAL_STORAGE":
            add_read_permission = False
            continue
        if element.get(namespace_link + "name") == "android.permission.WRITE_EXTERNAL_STORAGE":
            add_write_permission = False

        if not add_read_permission and not add_write_permission:
            break

    if add_read_permission:
        logging.info("Adding read permission to manifest content.")
        read_permission = ElementTree.Element("uses-permission")
        read_permission.set(android_namespace + ":name", "android.permission.READ_EXTERNAL_STORAGE")
        root.append(read_permission)

    if add_write_permission:
        logging.info("Adding write permission to manifest content.")
        write_permission = ElementTree.Element("uses-permission")
        write_permission.set(android_namespace + ":name", "android.permission.WRITE_EXTERNAL_STORAGE")
        root.append(write_permission)

    application = tree.find("application")

    add_activity = True
    for element in application.findall("activity"):
        if element.get(namespace_link + "name") == package + ".InstrumentActivity":
            add_activity = False
            break

    if add_activity:
        logging.info("Adding instrument activity to manifest content.")
        activity = ElementTree.Element("activity")
        activity.set(android_namespace + ":name", package + ".InstrumentActivity")
        activity.set(android_namespace + ":enabled", "true")
        activity.set(android_namespace + ":exported", "true")
        application.append(activity)

    add_receiver = True
    for element in application.findall("receiver"):
        if element.get(namespace_link + "name") == package + ".EndEmmaBroadcast":
            add_receiver = False
            break

    if add_receiver:
        logging.info("Adding EndEmma broadcast reciever to manifest content.")
        receiver = ElementTree.Element("receiver")
        receiver.set(android_namespace + ":name", package + ".EndEmmaBroadcast")
        receiver.set(android_namespace + ":enabled", "true")
        receiver.set(tool_namespace + ":ignore", "ExportedReceiver")

        intent = ElementTree.Element("intent-filter")
        action = ElementTree.Element("action")
        action.set(android_namespace + ":name", package + ".END_EMMA")
        intent.append(action)
        receiver.append(intent)
        application.append(receiver)

    logging.info("Writing updated content to manifest file.")
    tree.write(manifest_file)

    return package


def read_launch_activity_from_manifest(manifest_file):
    tree = ElementTree.parse(manifest_file)

    application = tree.find("application")
    activities = application.findall("activity")
    for activity in activities:
        intents = activity.findall("intent-filter")
        for intent in intents:
            actions = intent.findall("action")
            for action in actions:
                if "android.intent.action.MAIN" in action.attrib.values():
                    for key in activity.keys():
                        if "name" in key:
                            return activity.get(key)

    return None


def add_instrument_classes(source, package, activity, androidx):
    for file in os.listdir(args.jacoco):
        if not file.endswith('.java'):
            continue

        if os.path.isfile(os.path.join(source, os.path.basename(file))):
            continue

        if "InstrumentActivity.java" in file and androidx:
            file = os.path.join("androidx", file)

        with open(os.path.join(args.jacoco, file), 'r') as class_file:
            logging.info("Reading " + file + " class content.")
            class_content = class_file.read()

        if '<APP-PACKAGE>' in class_content:
            logging.info("Adding package '" + package + "' to " + file)
            class_content = class_content.replace('<APP-PACKAGE>', package)
        if '<LAUNCH-ACTIVITY>' in class_content:
            logging.info("Adding launch activity '" + activity + "' to " + file)
            class_content = class_content.replace('<LAUNCH-ACTIVITY>', activity)

        with open(os.path.join(source, os.path.basename(file)), 'w') as class_file:
            logging.info("Writing updated class content '" + file)
            class_file.write(class_content)


def copy_apk_file(source, destination: str, name, title):
    file = str(None)
    for file_path in Path(source).rglob("*.apk"):
        file = str(file_path.resolve())
        logging.info("JaCoco APK for " + title + " is " + file)
        break

    if file is None:
        logging.error("Failed to find the JaCoco APK for " + title + ".")
        return

    logging.info("Copying JaCoco APK to JAPK directory.")
    shutil.copy(file, os.path.join(destination, name + ".apk"))


for apk_file in os.listdir(apk_directory):
    if not os.path.isfile(os.path.join(apk_directory, apk_file)) or not apk_file.endswith(".apk"):
        logging.info("Ignoring file " + apk_file)
        continue

    app = os.path.splitext(os.path.basename(apk_file))[0]
    app_title = ''.join([i for i in app if not i.isdigit()]).replace('_', ' ').title().strip()

    if os.path.isfile(os.path.join(japk_directory, apk_file)):
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
    use_androidx = update_build_file(gradle_build_file)

    app_manifest = None
    for path in Path(source_directory).rglob('AndroidManifest.xml'):
        if "build" not in str(path.resolve()):
            app_manifest = str(path.resolve())
            logging.info("Manifest file for " + app_title + " is " + app_manifest)
            break

    if app_manifest is None:
        logging.error("Failed to find manifest file for " + app_title + ".")
        continue

    app_package = update_manifest_file(app_manifest)
    if app_package is None:
        logging.error("Failed to find package name for " + app_title + ".")
        continue
    logging.info("Package name for " + app_title + " is " + str(app_package) + "'.")

    launch_activity = read_launch_activity_from_manifest(app_manifest)
    if launch_activity is None:
        logging.error("Failed to find launch activity for " + app_title + ".")
        continue

    if launch_activity.startswith('.'):
        launch_activity = app_package + launch_activity
    logging.info("Launch activity for " + app_title + " is " + str(launch_activity) + "'.")

    package_directory = app_package.replace(".", os.path.sep)
    java_src_directory = None
    for path in Path(source_directory).rglob(package_directory):
        if "test" not in str(path) and "androidTest" not in str(path) and "build" not in str(path):
            java_src_directory = str(path.resolve())
            logging.info("Java SRC directory for " + app_title + " is " + java_src_directory)

    if java_src_directory is None:
        logging.error("Failed to find java src directory for " + app_title + ".")
        continue
    add_instrument_classes(java_src_directory, app_package, launch_activity, use_androidx)

    build_directory = None
    for path in Path(source_directory).rglob("build.gradle"):
        build_directory = os.path.dirname(str(path.resolve()))
        logging.info("Build directory for " + app_title + " is " + build_directory)
        break

    if build_directory is None:
        logging.error("Failed to find build directory for " + app_title + ".")
        continue

    logging.info("Running gradle build on " + app_title + ".")
    if subprocess.call(os.getcwd() + "/gradlew.sh assembleDebug > " + source_directory + "/build.log 2>&1",
                       cwd=build_directory, shell=True) == 0:
        copy_apk_file(source_directory, japk_directory, app, app_title)
    else:
        logging.error("Gradle build for " + app_title + " failed. See log for details.")
        if java_11_enabled:
            logging.info("Running gradle build on " + app_title + " with Java 11.")
            if subprocess.call(os.getcwd() + "/gradlew.sh assembleDebug -Dorg.gradle.java.home=" + os.environ.get(
                    "JAVA_11_HOME") + " > " + source_directory + "/java_11_build.log 2>&1", cwd=build_directory,
                               shell=True) == 0:
                copy_apk_file(source_directory, japk_directory, app, app_title)
            else:
                logging.error("Gradle build for " + app_title + " failed with Java 11. See log for details.")
