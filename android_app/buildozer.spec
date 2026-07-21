[app]

title = SDN Downloader Ultra ⚡
package.name = sdn_downloader_ultra
package.domain = com.sdn.downloader.ultra

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js

version = 2.0.0
requirements = python3,kivy,pyjnius,requests,pillow,yt_dlp

orientation = portrait

fullscreen = 0

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, ACCESS_NETWORK_STATE

# System Share Intent Filter Configuration
android.manifest.intent_filters = AndroidManifest.xml

android.api = 33
android.minapi = 21

android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
