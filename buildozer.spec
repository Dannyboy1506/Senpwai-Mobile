[app]
title = Senpcli
package.name = senpcli
package.domain = com.senpcli
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
version = 1.0.0
requirements = python3,kivy==2.3.0,requests,ffpyplayer,plyer
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS
android.api = 33
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
