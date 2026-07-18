plugins {
    id("com.android.application")
}

android {
    namespace = "dev.mde.autoknowledge"
    compileSdk = 35

    defaultConfig {
        applicationId = "dev.mde.autoknowledge"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
