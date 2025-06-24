@echo off
setlocal

:: =================================================================
:: 自动从 .env 文件读取项目路径
:: =================================================================
echo 正在读取配置文件...

:: 检查 .env 文件是否存在
if not exist ".env" (
    echo 错误: .env 文件未找到!
    pause
    exit /b
)

:: 循环读取 .env 文件的每一行，查找 PROJECT_PATH
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if /i "%%a"=="PROJECT_PATH" (
        set "project_dir=%%~b"
    )
)

:: 检查是否成功读取到路径
if not defined project_dir (
    echo 错误: 未能在 .env 文件中找到 PROJECT_PATH。
    pause
    exit /b
)

:: =================================================================
:: 使用读取到的路径启动应用
:: =================================================================
echo 正在启动 Notion 智能助手服务器...

:: 使用变量切换到项目文件夹路径
cd /d %project_dir%

echo 服务器已就绪，正在打开浏览器...

:: 启动浏览器并打开网页
start http://127.0.0.1:5000/

:: 启动Python后端程序
python app.py

endlocal