@echo off
chcp 65001 > nul
title 鼠标精灵 - 环境设置

echo 检查conda是否已安装...
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Conda未找到，请先安装Anaconda或Miniconda
    echo 可从 https://docs.conda.io/en/latest/miniconda.html 下载
    pause
    exit /b 1
)

echo 创建conda环境 mouse_sprint (Python 3.10)...
call conda env remove -n mouse_sprint --yes
call conda create -n mouse_sprint python=3.10 --yes

echo 激活环境并安装依赖...
call conda activate mouse_sprint

echo 安装依赖包...
call conda install -c conda-forge pyautogui -y
call conda install -c conda-forge pynput -y
call conda install -c conda-forge pillow -y
call conda install -c conda-forge pip -y

call pip install nuitka zstandard ordered-set

echo 创建图标...
python create_icon.py

echo 环境设置完成！
echo 可以使用 run_conda.bat 运行程序
pause 