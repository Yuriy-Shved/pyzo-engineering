@ echo   off
cls

::  1. Automatically detect the root folder
set "STEM_ROOT =%~dp0"
if "%STEM_ROOT :~ -1%"=="\"  set "STEM_ROOT =%STEM_ROOT:~0,-1%"

::  2. Isolate the compiler in  PATH   current session
set "PATH =%STEM_ROOT%\ ArduinoCLI ;% PATH%"

::  3. Fix the path variable to FreeCAD
set "FREECAD_DIR =%STEM_ROOT%\FreeCAD_1.1.3-Windows-x86_64-py311"

::  4. ISOLATION SYSTEM BACKUPS (Redirect  AppData   of  the current session to the program folder )
set "APPDATA =%STEM_ROOT%\ PyzoSource \internal"

::  5. CONFIGURATION FOR  ARDUINO   CLI  IN INTERFACE REMOTE
set "ARDUINO_DIRECTORIES_DATA =%STEM_ROOT%\ ArduinoCLI \data"
set "ARDUINO_DIRECTORIES_USER =%STEM_ROOT%\ ArduinoCLI \user"
set "ARDUINO_DIRECTORIES_DOWNLOADS=%STEM_ROOT%\ArduinoCLI\data\staging"

rem  ==============================================================================
rem  INFORMATIONAL MESSAGES COMMENTED FOR SILENT START
rem   rem  [ STEM ]:  Root folder defined : % STEM _ ROOT %
rem rem  [STEM ]:  Launching Pyzo ...
rem  ==============================================================================

::  6. Go to folder  bin   FreeCAD
cd /d "%STEM_ROOT%\FreeCAD_1.1.3-Windows-x86_64-py311\bin"

::  7. CONSOLELESS STARTUP: Call pythonw.exe
start "" ".\pythonw.exe" - m pyzo  -- userdata ="%STEM_ROOT%\ PyzoSource \internal"

exit
