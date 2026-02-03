@echo off
REM =============================================================================
REM Angular Module Federation POC - Single-Click Deployment Script (Windows)
REM =============================================================================

setlocal enabledelayedexpansion
title Angular Module Federation POC

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Determine docker-compose command
docker-compose version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set COMPOSE_CMD=docker-compose
) else (
    docker compose version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set COMPOSE_CMD=docker compose
    ) else (
        echo [ERROR] docker-compose is not installed.
        pause
        exit /b 1
    )
)

REM Handle commands
if "%1"=="" goto build
if "%1"=="build" goto build
if "%1"=="start" goto build
if "%1"=="stop" goto stop
if "%1"=="clean" goto clean
if "%1"=="help" goto help
goto unknown

:build
echo.
echo ============================================================
echo      Angular Module Federation POC - Docker Deployment
echo ============================================================
echo.
echo   Shell (Host):         http://localhost:4200
echo   Reg Reporting:        http://localhost:4201
echo   Financial Reporting:  http://localhost:4202
echo   Expense Reporting:    http://localhost:4203
echo   Tax Reporting:        http://localhost:4204
echo   Control Tower:        http://localhost:4205
echo.
echo ============================================================
echo.

REM Stop and remove any existing containers first
echo Cleaning up old containers...
docker stop mf-shell mf-reg-reporting mf-financial-reporting mf-expense-reporting mf-tax-reporting mf-control-tower 2>nul
docker rm mf-shell mf-reg-reporting mf-financial-reporting mf-expense-reporting mf-tax-reporting mf-control-tower 2>nul
docker network rm module-federation-network 2>nul

echo.
echo Building and starting all services...
echo This may take several minutes on first run.
echo.

%COMPOSE_CMD% up -d --build --force-recreate

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed. Trying cleanup and retry...
    %COMPOSE_CMD% down --remove-orphans
    docker network prune -f
    %COMPOSE_CMD% up -d --build
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Build failed again. Please run: docker system prune -a
        pause
        exit /b 1
    )
)

echo.
%COMPOSE_CMD% ps
echo.
echo ============================================================
echo   SUCCESS! Open http://localhost:4200 in your browser
echo ============================================================
echo.
pause
goto end

:stop
echo Stopping all services...
docker stop mf-shell mf-reg-reporting mf-financial-reporting mf-expense-reporting mf-tax-reporting mf-control-tower 2>nul
%COMPOSE_CMD% down
echo Done.
pause
goto end

:clean
echo Removing all containers and images...
docker stop mf-shell mf-reg-reporting mf-financial-reporting mf-expense-reporting mf-tax-reporting mf-control-tower 2>nul
docker rm mf-shell mf-reg-reporting mf-financial-reporting mf-expense-reporting mf-tax-reporting mf-control-tower 2>nul
%COMPOSE_CMD% down --rmi all --volumes --remove-orphans
docker network rm module-federation-network 2>nul
echo Done.
pause
goto end

:help
echo Usage: run.bat [command]
echo.
echo Commands:
echo   (none)    Build and start all services
echo   stop      Stop all services
echo   clean     Remove all containers and images
echo   help      Show this help
pause
goto end

:unknown
echo Unknown command: %1
goto help

:end
endlocal
