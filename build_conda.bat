@echo off
chcp 65001 > nul
title 鼠标精灵 - 打包程序

echo 激活conda环境 mouse_sprint...
call conda activate mouse_sprint

echo 使用Nuitka编译程序...
python -m nuitka ^
  --follow-imports ^
  --windows-disable-console ^
  --enable-plugin=tk-inter ^
  --include-package=pyautogui ^
  --include-package=PIL ^
  --include-package=pynput ^
  --standalone ^
  --output-dir=build ^
  --windows-icon-from-ico=mouse_icon.ico ^
  --jobs=%NUMBER_OF_PROCESSORS% ^
  mouse_spirit.py

if exist build\mouse_spirit.dist (
    echo 创建启动脚本...
    echo @echo off > build\启动.bat
    echo chcp 65001 ^> nul >> build\启动.bat
    echo cd /d "%%~dp0mouse_spirit.dist" >> build\启动.bat
    echo start mouse_spirit.exe >> build\启动.bat
    
    echo 完成! 可执行文件位于build\mouse_spirit.dist目录
)

pause 