@echo off
chcp 65001 > nul
title 鼠标精灵 - 运行程序

echo 激活conda环境 mouse_sprint...
call conda activate mouse_sprint

echo 启动鼠标精灵...
python mouse_spirit.py

echo 程序已退出
pause 