$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c C:\Users\29035\01 文件夹\学习办公\cdut-notice-crawler\run.bat"
$trigger1 = New-ScheduledTaskTrigger -Daily -At "12:00"
$trigger2 = New-ScheduledTaskTrigger -Daily -At "22:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun
Register-ScheduledTask -TaskName "CDUT Notice Crawler" -Action $action -Trigger $trigger1,$trigger2 -Settings $settings -Force
Write-Host "Done - Task scheduled at 12:00 and 22:00 daily"
