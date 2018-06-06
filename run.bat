set DRV=%~1

rem set VIV_VX_ENABLE_TP=0
rem set NN_LAYER_DUMP=1
rem set VIV_VX_ENABLE_TP_MAX_POOLING=0
rem set VIV_VX_ENABLE_TP_LEAK_RELU=0
rem set VIV_VX_ENABLE_PRINT_TARGET=1
rem set VIV_VX_ENABLE_VIRTUAL_BUFFER=1
rem set VIV_VX_ENABLE_SWTILING_PHASE1=0

net use A: /d/y
subst A: /d
net use A: \\192.168.33.105\data\Cmodel

xcopy /y/e/i \\192.168.33.105\data\Cmodel\scripts\utility utility\
xcopy /y/e/i \\192.168.33.105\data\Cmodel\scripts\runtesting runtesting\
xcopy /y \\192.168.33.105\data\Cmodel\scripts\WinAssertClose.exe .

start WinAssertClose.exe
cd runtesting
python run_test.py %DRV%