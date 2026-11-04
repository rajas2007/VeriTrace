; ============================================================
; VeriTrace Desktop - Inno Setup Compiler Script
; Generates: VeriTrace-Setup.exe (Windows 10/11 x64 Installer)
; ============================================================

#define MyAppName "VeriTrace"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "VeriTrace Forensic Technologies"
#define MyAppURL "https://github.com/rajas2007/VeriTrace"
#define MyAppExeName "VeriTrace.exe"

[Setup]
AppId={{9F3B4A2C-5D1E-4F8A-9C2E-7D4F8A1B2C3D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
PrivilegesRequired=lowest
OutputDir=..\Output
OutputBaseFilename=VeriTrace-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\VeriTrace\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Bundled Tesseract OCR binaries and tessdata
; Source: "..\..\dist\tesseract\*"; DestDir: "{app}\resources\tesseract"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Preserve user investigation databases and evidence in %LOCALAPPDATA%/VeriTrace/
; Only clean up temporary installation caches if explicitly requested.
Type: files; Name: "{app}\*.log"
