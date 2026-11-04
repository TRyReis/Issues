plugins {
    id("com.android.application")
}

android {
    namespace = "de.kpopradar"
    compileSdk = 35

    defaultConfig {
        applicationId = "de.kpopradar"
        minSdk = 24
        targetSdk = 34
        versionCode = 2
        versionName = "1.1"
    }

    // Optional: fester Signatur-Schlüssel (für Updates ohne Neuinstallation),
    // wird in GitHub Actions aus Secrets erzeugt. Ohne Secrets: Debug-Signatur.
    val ks = file("release.keystore")
    signingConfigs {
        if (ks.exists()) create("release") {
            storeFile = ks
            storePassword = System.getenv("KS_PASSWORD")
            keyAlias = System.getenv("KS_ALIAS")
            keyPassword = System.getenv("KS_PASSWORD")
        }
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = if (ks.exists()) signingConfigs.getByName("release")
                            else signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("web"))
}

// Die Web-App (../index.html) wird bei jedem Build als Asset in die APK kopiert.
val copyWeb by tasks.registering(Copy::class) {
    from(rootProject.file("../index.html"))
    into(layout.buildDirectory.dir("web"))
}
tasks.named("preBuild") { dependsOn(copyWeb) }
