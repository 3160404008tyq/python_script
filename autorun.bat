setlocal
set CHIP=%~1
set DRV_BRANCH=%~2
set CMODEL_BRANCH=%~3
set OTHERS=%~4

if "%CMODEL_BRANCH%" == "" (
	set CMODEL_BRANCH=projects.v620_v2
)

net use A: /d/y
subst A: /d
net use A: \\192.168.33.105\data\Cmodel

REM xcopy /y/e/i A:\scripts\utility utility\
REM xcopy /y/e/i A:\scripts\runtesting\client runtesting\client\
xcopy /y A:\scripts\WinAssertClose.exe .
REM xcopy /y A:\scripts\runtesting\models.py runtesting\
REM xcopy /y A:\scripts\runtesting\utils.py runtesting\

start WinAssertClose.exe

python A:\scripts\runtesting\client\slave.py %DRV_BRANCH% %CHIP% --cmodel_branch %CMODEL_BRANCH% %OTHERS%

endlocal