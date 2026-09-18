; Inno Setup 6 script — compile after PyInstaller onedir output exists in dist\ThermoQ
#define MyAppName "ThermoQ"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "ThermoQ"
#define MyAppURL "https://github.com/JunHuaBai96/ThermoQ"
#define MyAppExeName "ThermoQ.exe"

[Setup]
AppId={{8E7C4B21-6A1F-4D3E-9B70-2C5A8F1D4E90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=ThermoQ-{#MyAppVersion}-Windows-Setup
SetupIconFile=..\images\thermoq.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Install to Program Files (requires elevation). Do not touch {userdocs} here —
; ThermoQ creates Documents\ThermoQ itself on first launch (writable plot output).
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
MinVersion=10.0
ChangesAssociations=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\ThermoQ\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
