plugins {
    id("com.android.application")
}

android {
    namespace = "dev.mde.autoknowledge"
    compileSdk = 34

    defaultConfig {
        applicationId = "dev.mde.autoknowledge"
        minSdk = 26
        targetSdk = 34
        versionCode = 3
        versionName = "0.2.2"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    sourceSets["test"].resources.srcDir(
        "../../../../packages/capture-core/test-vectors"
    )
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
}
