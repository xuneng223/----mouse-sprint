@echo off
chcp 65001 > nul
title 鼠标精灵 - 打包程序

echo 激活conda环境 mouse_sprint...
call conda activate mouse_sprint

echo 清理Nuitka历史缓存...
if exist "%LOCALAPPDATA%\Nuitka" (
    echo 删除Nuitka本地缓存文件夹...
    rd /s /q "%LOCALAPPDATA%\Nuitka"
)
if exist "%APPDATA%\.nuitka" (
    echo 删除.nuitka缓存文件夹...
    rd /s /q "%APPDATA%\.nuitka"
)
if exist "__pycache__" (
    echo 删除Python缓存文件夹...
    rd /s /q "__pycache__"
)
if exist "mouse_spirit.build" (
    echo 删除旧的构建文件夹...
    rd /s /q "mouse_spirit.build"
)
if exist "mouse_spirit.onefile-build" (
    echo 删除旧的单文件构建文件夹...
    rd /s /q "mouse_spirit.onefile-build"
)
if exist "mouse_spirit.dist" (
    echo 删除旧的dist文件夹...
    rd /s /q "mouse_spirit.dist"
)


echo 创建输出目录结构...
set OUTPUT_DIR=%USERPROFILE%\MouseSpirit_Build
if exist "%OUTPUT_DIR%" (
    echo 清理旧的构建目录...
    rd /s /q "%OUTPUT_DIR%"
)
mkdir "%OUTPUT_DIR%"

echo 使用Nuitka编译单文件程序...
python -m nuitka ^
  --follow-imports ^
  --windows-disable-console ^
  --enable-plugin=tk-inter ^
  --include-package=pyautogui ^
  --include-package=PIL ^
  --include-package=pynput ^
  --onefile ^
  --output-dir="%OUTPUT_DIR%" ^
  --windows-icon-from-ico=mouse_icon.ico ^
  --jobs=%NUMBER_OF_PROCESSORS% ^
  --assume-yes-for-downloads ^
  --windows-company-name="Mouse Spirit" ^
  --windows-product-name="鼠标精灵" ^
  --windows-file-version=1.0.0 ^
  --windows-product-version=1.0.0 ^
  --windows-file-description="鼠标精灵 - 鼠标自动化工具" ^
  mouse_spirit.py

if %ERRORLEVEL% NEQ 0 (
    echo 编译失败，请查看错误信息
    echo 错误可能是由于路径中包含中文字符导致
    pause
    exit /b 1
)

if exist "%OUTPUT_DIR%\mouse_spirit.exe" (
    echo 复制单文件可执行程序到build目录...
    copy "%OUTPUT_DIR%\mouse_spirit.exe" "鼠标精灵.exe"
    
    echo 完成! 单文件可执行程序位于:
    echo 1. %OUTPUT_DIR%\mouse_spirit.exe (临时目录)
    echo 2. 鼠标精灵.exe (当前目录)
    echo 注意: 这是完全独立的单文件可执行程序，不依赖任何其他文件
) else (
    echo 编译似乎完成，但找不到输出文件。
    echo 请查看 "%OUTPUT_DIR%" 目录中的文件。
)

echo 清理构建目录...
if exist "mouse_spirit.build" rd /s /q "mouse_spirit.build"
if exist "mouse_spirit.onefile-build" rd /s /q "mouse_spirit.onefile-build"
if exist "mouse_spirit.dist" rd /s /q "mouse_spirit.dist"
if exist "__pycache__" rd /s /q "__pycache__"
if exist "%OUTPUT_DIR%" rd /s /q "%OUTPUT_DIR%"

pause 