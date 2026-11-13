pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "open-e-pin"

// Plain Kotlin: image processing, packing and the BLE upload protocol. Unit-tested on the JVM.
include(":core")
// The Android app: scanning, connecting, image picking, crop UI.
include(":android")
