# 校园通知爬虫 - Windows 计划任务安装脚本
# 使用方法：以管理员身份运行 PowerShell，执行 .\setup_task.ps1
#
# 注意：请根据你的实际 Python 安装路径修改 $pythonPath
#       如果项目路径含中文，建议使用启动器脚本绕过编码问题

$pythonPath = "C:\Python314\python.exe"
$launcherScript = "cdut_crawler_launcher.py"

$action = New-ScheduledTaskAction -Execute $pythonPath `
    -Argument $launcherScript `
    -WorkingDirectory (Split-Path $pythonPath -Parent)

$trigger1 = New-ScheduledTaskTrigger -Daily -At "12:00"
$trigger2 = New-ScheduledTaskTrigger -Daily -At "22:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun
Register-ScheduledTask -TaskName "CDUT Notice Crawler" -Action $action -Trigger $trigger1,$trigger2 -Settings $settings -Force
Write-Host "Done - Task scheduled at 12:00 and 22:00 daily"
