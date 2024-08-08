# Android Packager #

Android Packager is a collection of Python scripts that select, modify, and build Android APK files for applications downloaded from the F-Droid marketplace.

### select.py ###

Randomly selects an Android application from each category within the F-Droid marketplace. Before a selection is made, applications are filtered with criteria such as age and SDK version. The APK and source code for each of the selected applications is downloaded.

### build.py ###

Builds an Android APK file from an applications source code using the Gradle build system and the F-Droid marketplace build process.

### jacoco.py ###

Updates the source code of Android applications to include the JaCoCo framework. JaCoCo is a free Java code coverage library providing coverage data during an applications runtime. Instrumentation files are added to the application source code and the Gradle configuration files are updated to include JaCoCo settings and dependencies. After modifying the source code, the application is built to create an executable APK file. 
