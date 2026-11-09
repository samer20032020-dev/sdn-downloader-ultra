import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', encoding='utf-8') as f:
    text = f.read()

script_start = text.find('<script>')
script_text = text[script_start:]

ids = [
    'themeToggle', 'themeBadgeText', 'defaultQualitySelect', 'speedLimitSelect',
    'savePathTxt', 'changeFolderBtn', 'autoPasteToggle', 'youtubeLoginRow',
    'youtubeLoginBtn', 'youtubeLogoutBtn', 'youtubeLoginStatus', 'youtubeBadge',
    'cookieSourceSelect', 'cookieSourceDesc', 'cookieFileRow', 'cookieFileTxt',
    'pickCookieFileBtn', 'proxyInp', 'smartLiveDetectToggle', 'turboModeToggle',
    'autoUpdateToggle', 'soundToggle', 'settingsVersionTxt', 'engineVersionTxt',
    'checkUpdatesManualBtn', 'updateEngineBtn', 'ytPulseDot',
    'statAppVersion', 'statActiveFolder', 'statYoutubeStatus'
]

for an_id in ids:
    matches = len(re.findall(re.escape(an_id), script_text))
    print(f'{an_id}: {matches} matches in script')
