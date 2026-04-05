[app]
title = Senpcli
package.name = senpcli
package.domain = com.senpcli
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
version = 1.0.0
requirements = python3,kivy==2.3.0,requests,plyer
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
android.enable_androidx = True
android.manifest.activity.launch_mode = singleTop
p4a.branch = master
p4a.source_dir =
p4a.local_recipes =

[buildozer]
log_level = 2
warn_on_root = 1
