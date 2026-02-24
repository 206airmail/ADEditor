; AutoDrive Editor NSIS Installer Script

Unicode true
;SetCompress off
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "x64.nsh"

; Get the system architecture and set corresponding defines
!searchparse /file "..\build\ADEditor\architecture" 'ARCHITECTURE = ' ARCHI
!if "${ARCHI}" == "64"
  !define ARCHI_LABEL "x64"
!else
  !define ARCHI_LABEL "i386"
!endif

; --- Configuration ---
!searchparse /file "..\Core\version.py" 'self.Major = ' VER_MAJOR
!searchparse /file "..\Core\version.py" 'self.Minor = ' VER_MINOR
!searchparse /file "..\Core\version.py" 'self.Revision = ' VER_REVISION
!searchparse /file "..\Core\version.py" 'self.Build = ' VER_BUILD
!define PRODUCT_VERSION "${VER_MAJOR}.${VER_MINOR}.${VER_REVISION}"

!searchparse /file "..\build\ADEditor\architecture" 'DESCRIPTION = ' APP_DESCRIPTION
!searchparse /file "..\build\ADEditor\architecture" 'COPYRIGHT = ' APP_COPYRIGHT

!define PRODUCT_NAME "AutoDrive Editor"
!define PRODUCT_PUBLISHER "Xav'"
!define PRODUCT_DIR_REGKEY "Software\Xav\AutoDriveEditor"
!define UNINSTALL_REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\AutoDriveEditor"

VIProductVersion "${PRODUCT_VERSION}.${VER_BUILD}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "FileDescription" "${APP_DESCRIPTION}"
VIAddVersionKey "LegalCopyright" "${APP_COPYRIGHT}"

;--------------------------------
Name "${PRODUCT_NAME}"
; Output filename
OutFile "..\build\AutoDriveEditor_Setup_${PRODUCT_VERSION}_${ARCHI_LABEL}.exe"
; Installation folder
InstallDir "$PROGRAMFILES${ARCHI}\${PRODUCT_NAME}"
; Get install folder from registry if available
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" "Install_Dir"
; Request administrator privileges
RequestExecutionLevel admin

; --- MUI Settings ---
!define MUI_ABORTWARNING
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${NSISDIR}\Contrib\Graphics\Header\orange.bmp"
!define MUI_ICON "..\Graphx\appIcon.ico"
!define MUI_UNICON "..\Graphx\appIcon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${NSISDIR}\Contrib\Graphics\Wizard\orange.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${NSISDIR}\Contrib\Graphics\Wizard\orange-uninstall.bmp"
!define MUI_FINISHPAGE_RUN "$INSTDIR\AutoDriveEditor.exe"

; --- Installer Pages ---
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; --- Uninstaller Pages ---
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language Support
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"
LangString WarnX64 ${LANG_ENGLISH} "This installer requires a 64-bit version of Windows."
LangString WarnX64 ${LANG_FRENCH} "Cet installateur nécessite une version 64-bit de Windows."

Function .onInit
  !if "${ARCHI}" == "64"
    ${IfNot} ${RunningX64}
      MessageBox MB_ICONSTOP $(WarnX64)
      Abort
    ${EndIf}
  !endif
FunctionEnd

; --- Sections ---
Section "Install" id0
  !if "${ARCHI}" == "64"
    SetRegView 64
  !else
    SetRegView 32
  !endif
    ; Copy lib folder and all its contents
  SetOutPath "$INSTDIR\lib"
  File /r "..\build\ADEditor\lib\*.*"
  ; Copy langs and help files
  SetOutPath "$INSTDIR\langs"
  File /r "..\build\ADEditor\langs\*.mo"
  File /r "..\build\ADEditor\langs\Help-ADEditor-*.zip"
  
  SetOutPath "$INSTDIR"
  ; Copy main executable
  File "..\build\ADEditor\AutoDriveEditor.exe"
  ; Copy runtime files
  File "..\build\ADEditor\python*.dll"
  File "..\build\ADEditor\frozen_application_license.txt"

  ; Reg keys
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "Version" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayIcon" "$INSTDIR\lib\Graphx\appIcon.ico"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  ; Install required size
  SectionGetSize ${id0} $0
  WriteRegDWORD HKLM "${UNINSTALL_REGKEY}" "EstimatedSize" $0

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Start Menu shortcuts
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\AutoDriveEditor.exe"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

SectionEnd

; --- Uninstaller Section ---
Section "Uninstall"
  !if "${ARCHI}" == "64"
    SetRegView 64
  !else
    SetRegView 32
  !endif
  ; Remove shortcuts
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
  
  ; Remove all installed files
  RMDir /r "$INSTDIR\lib"
  RMDir /r "$INSTDIR\langs"
  Delete "$INSTDIR\AutoDriveEditor.exe"
  Delete "$INSTDIR\python*.dll"
  Delete "$INSTDIR\frozen_application_license.txt"
  Delete "$INSTDIR\Uninstall.exe"
  
  ; Remove installation directory if empty
  RMDir "$INSTDIR"

  ; Remove registry keys
  DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

SectionEnd
