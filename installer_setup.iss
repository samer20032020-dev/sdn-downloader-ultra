; Script generated for Inno Setup - SDN Downloader Setup
#define MyAppName "SDN"
#define MyAppVersion "1.0.49"
#define MyAppPublisher "SDN"
#define MyAppExeName "SDN_Downloader_Standalone.exe"

[Setup]
AppId={{D37E60FA-7128-4691-889E-758B7998D0A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist
OutputBaseFilename=SDN_Downloader_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
WizardImageFile=wizard_sidebar.bmp
WizardSmallImageFile=wizard_header.bmp
SetupIconFile=app_icon.ico

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[InstallDelete]
Type: files; Name: "{app}\python3*.dll"
Type: files; Name: "{app}\vcruntime140*.dll"
Type: files; Name: "{app}\msvcp140*.dll"
Type: files; Name: "{app}\WebView2Loader*.dll"
Type: files; Name: "{app}\*.old"
Type: files; Name: "{app}\*.bak"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait

