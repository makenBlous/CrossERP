$ErrorActionPreference = "Stop"

function Start-CrossERPContainer {
    param(
        [string]$Name,
        [string[]]$Arguments
    )
    docker container inspect $Name *> $null
    if ($LASTEXITCODE -eq 0) {
        docker start $Name | Out-Null
    } else {
        docker run -d --name $Name @Arguments | Out-Null
    }
}

Start-CrossERPContainer -Name "crosserp-mysql" -Arguments @(
    "-p", "13306:3306",
    "-e", "MYSQL_ROOT_PASSWORD=dev",
    "-e", "MYSQL_DATABASE=crosserp",
    "mysql:8.4",
    "--character-set-server=utf8mb4",
    "--collation-server=utf8mb4_0900_ai_ci"
)

Start-CrossERPContainer -Name "crosserp-postgres" -Arguments @(
    "-p", "15432:5432",
    "-e", "POSTGRES_PASSWORD=dev",
    "-e", "POSTGRES_DB=crosserp",
    "postgres:18"
)

Write-Output "MySQL 8.4: 127.0.0.1:13306 (root/dev)"
Write-Output "PostgreSQL 18: 127.0.0.1:15432 (postgres/dev)"
