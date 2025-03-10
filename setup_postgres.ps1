# Проверяем наличие PostgreSQL
$pgPath = Get-ChildItem "C:\Program Files\PostgreSQL" -ErrorAction SilentlyContinue | 
    Sort-Object Name -Descending | 
    Select-Object -First 1 -ExpandProperty FullName

if (-not $pgPath) {
    Write-Host "PostgreSQL не найден. Устанавливаем..."
    
    # Установка PostgreSQL с помощью winget
    winget install -e --id PostgreSQL.PostgreSQL --accept-package-agreements --accept-source-agreements
    
    # Даем время на завершение установки
    Start-Sleep -Seconds 10
    
    # Обновляем путь после установки
    $pgPath = Get-ChildItem "C:\Program Files\PostgreSQL" -ErrorAction SilentlyContinue | 
        Sort-Object Name -Descending | 
        Select-Object -First 1 -ExpandProperty FullName
}

if ($pgPath) {
    Write-Host "PostgreSQL найден в: $pgPath"
    
    # Добавляем путь к PostgreSQL в PATH
    $binPath = Join-Path $pgPath "bin"
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if (-not $currentPath.Contains($binPath)) {
        [Environment]::SetEnvironmentVariable(
            "Path",
            "$currentPath;$binPath",
            "User"
        )
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "User")
        Write-Host "Путь к PostgreSQL добавлен в PATH"
    }
    
    # Проверяем службу PostgreSQL
    $serviceName = Get-Service *postgresql* | Select-Object -First 1 -ExpandProperty Name
    if ($serviceName) {
        $service = Get-Service $serviceName
        Write-Host "Найдена служба PostgreSQL: $serviceName (Статус: $($service.Status))"
        
        if ($service.Status -ne 'Running') {
            Write-Host "Запускаем службу PostgreSQL..."
            Start-Service $serviceName
            Start-Sleep -Seconds 5
        }
        
        # Проверяем статус после запуска
        $service = Get-Service $serviceName
        Write-Host "Статус службы PostgreSQL: $($service.Status)"
    } else {
        Write-Host "Служба PostgreSQL не найдена"
    }
    
    # Настраиваем пароль postgres
    if (Test-Path (Join-Path $pgPath "bin\psql.exe")) {
        $env:PGPASSWORD = "postgres"  # Используем пароль из .env
        Write-Host "Настраиваем пароль для пользователя postgres..."
        
        try {
            & "$pgPath\bin\psql.exe" -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
            Write-Host "Пароль успешно установлен"
            
            # Проверяем подключение
            & "$pgPath\bin\psql.exe" -U postgres -c "\conninfo"
        } catch {
            Write-Host "Ошибка при настройке пароля: $_"
        }
    }
} else {
    Write-Host "PostgreSQL не найден после установки"
} 