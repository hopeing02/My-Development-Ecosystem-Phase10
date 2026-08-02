plugins {
    id("com.android.application")
}

android {
    namespace = "dev.mde.knowledgeviewer"
    compileSdk = 34

    defaultConfig {
        applicationId = "dev.mde.knowledgeviewer"
        minSdk = 26
        targetSdk = 34
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
