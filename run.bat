@echo off
REM =============================================================================
REM Angular Module Federation POC - Single-Click Deployment Script (Windows)
REM =============================================================================
REM
REM This script builds and runs the complete micro-frontend architecture
REM using Docker Compose with a single command.
REM
REM Usage:
REM   run.bat          - Build and start all services
REM   run.bat start    - Start existing containers
REM   run.bat stop     - Stop all services
REM   run.bat restart  - Restart all services
REM   run.bat logs     - View logs
REM   run.bat clean    - Remove all containers and images
REM   run.bat status   - Show container status
REM
REM =============================================================================

setlocal enabledelayedexpansion

REM Set title
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
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="status" goto status
if "%1"=="clean" goto clean
if "%1"=="help" goto help
if "%1"=="--help" goto help
if "%1"=="-h" goto help
goto unknown

:build
echo.
echo ===============================================================
echo      Angular Module Federation POC - Docker Deployment
echo ===============================================================
echo.
echo   Shell (Host):         http://localhost:4200
echo   Reg Reporting:        http://localhost:4201  (AG Grid v31)
echo   Financial Reporting:  http://localhost:4202  (AG Grid v30)
echo   Expense Reporting:    http://localhost:4203  (AG Grid v31)
echo   Tax Reporting:        http://localhost:4204  (AG Grid v29)
echo   Control Tower:        http://localhost:4205  (AG Grid v31)
echo.
echo ===============================================================
echo.
echo Building and starting all services...
echo This may take several minutes on first run.
echo.
%COMPOSE_CMD% up -d --build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)
echo.
echo Waiting for health checks...
timeout /t 10 /nobreak >nul
echo.
%COMPOSE_CMD% ps
echo.
echo ===============================================================
echo   Deployment Complete! Open http://localhost:4200 in browser
echo ===============================================================
echo.
pause
goto end

:start
echo Starting services...
%COMPOSE_CMD% up -d
echo Services started.
%COMPOSE_CMD% ps
pause
goto end

:stop
echo Stopping all services...
%COMPOSE_CMD% down
echo All services stopped.
pause
goto end

:restart
echo Restarting all services...
%COMPOSE_CMD% restart
echo All services restarted.
%COMPOSE_CMD% ps
pause
goto end

:logs
echo Showing logs (Ctrl+C to exit)...
%COMPOSE_CMD% logs -f
goto end

:status
echo.
echo Container Status:
echo ---------------------------------------------------------------
%COMPOSE_CMD% ps
echo ---------------------------------------------------------------
pause
goto end

:clean
echo Stopping and removing all containers, networks, and images...
%COMPOSE_CMD% down --rmi all --volumes --remove-orphans
echo Cleanup complete.
pause
goto end

:help
echo Usage: run.bat [command]
echo.
echo Commands:
echo   (none)    Build and start all services (default)
echo   start     Start existing containers
echo   stop      Stop all services
echo   restart   Restart all services
echo   logs      View container logs
echo   status    Show container status
echo   clean     Remove all containers and images
echo   help      Show this help message
pause
goto end

:unknown
echo Unknown command: %1
goto help

:end
endlocal
