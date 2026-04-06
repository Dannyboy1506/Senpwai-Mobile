[app]
title = Senpcli
package.name = senpcli
package.domain = com.senpcli
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_exts = pyc,pyo,db
source.exclude_patterns = make_icon.py
version = 1.0.0

requirements = python3,kivy==2.3.0,requests,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,POST_NOTIFICATIONS

android.api = 34
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True
android.enable_androidx = True

android.meta_data = android.usb.telemetry=false

[buildozer]
log_level = 2
warn_on_root = 1