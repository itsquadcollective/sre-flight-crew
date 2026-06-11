@echo off
setlocal enabledelayedexpansion

pushd "%~dp0" >nul
echo ============================================================
echo   SRE Flight Crew — Azure Developer Onboarding (Windows)
echo ============================================================
echo.

rem --- Python check ---
set "PYTHON_CMD="
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py -3"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python is not installed. Please install Python 3.10+ and rerun.
    popd >nul
    exit /b 1
)
for /f "usebackq delims=" %%A in (`%PYTHON_CMD% --version 2^>^&1`) do set "PYTHON_VER=%%A"
echo [SUCCESS] Python detected: %PYTHON_VER%
echo.

rem --- Git check ---
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed. Please install Git and rerun.
    popd >nul
    exit /b 1
)
for /f "usebackq delims=" %%A in (`git --version 2^>^&1`) do set "GIT_VER=%%A"
echo [SUCCESS] Git detected: %GIT_VER%
echo.

rem --- Azure CLI check ---
where az >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Azure CLI ^(az^) was not found.
    echo [INFO] Install Azure CLI with: winget install Microsoft.AzureCLI
    set /p INSTALL_AZURE_CLI=Would you like to try installing Azure CLI via winget? [Y/n]: 
    if /i "%INSTALL_AZURE_CLI%"=="" set "INSTALL_AZURE_CLI=Y"
    if /i "%INSTALL_AZURE_CLI%"=="Y" (
        winget install Microsoft.AzureCLI --silent
        if %errorlevel% neq 0 (
            echo [WARNING] winget install failed or may require elevation. Install Azure CLI manually and rerun.
            popd >nul
            exit /b 1
        )
    ) else (
        echo [INFO] Please install Azure CLI manually and rerun.
        popd >nul
        exit /b 1
    )
)

where az >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Azure CLI still not available after installation attempt.
    popd >nul
    exit /b 1
)
echo [SUCCESS] Azure CLI detected.
echo.

rem --- Azure login ---
echo [INFO] Signing in to Azure...
az login
if %errorlevel% neq 0 (
    echo [ERROR] Azure login failed. Please rerun and authenticate.
    popd >nul
    exit /b 1
)

echo.
echo [INFO] Fetching available subscriptions...
az account list --output table
echo.
set /p SELECTED_SUB=Enter the Subscription ID or Name to target (leave blank to keep current): 
if defined SELECTED_SUB (
    az account set --subscription "%SELECTED_SUB%"
    if %errorlevel% neq 0 (
        echo [WARNING] Failed to set the requested subscription. Using current default instead.
    ) else (
        echo [SUCCESS] Subscription set successfully.
    )
) else (
    echo [INFO] No subscription entered. Keeping current selection.
)
for /f "usebackq delims=" %%A in ('az account show --query "id" -o tsv 2^>^&1') do set "SUB_ID=%%A"
echo [INFO] Active subscription ID: %SUB_ID%
echo.

rem --- Local .env configuration ---
set "ENV_FILE=.env"
if not exist "%ENV_FILE%" (
    if exist ".env.example" (
        copy /Y ".env.example" "%ENV_FILE%" >nul
        echo [INFO] Created .env from .env.example.
    ) else (
        echo [WARNING] .env.example not found. Creating blank .env.
        type nul > "%ENV_FILE%"
    )
)
echo Please enter Azure environment values or press Enter to keep the defaults.
set "PROJECT_ENDPOINT=https://unlockedhackathonteam-resource.services.ai.azure.com/api/projects/unlockedhackathonteam"
set /p PROJECT_ENDPOINT=Azure AI Project Endpoint [Default: %PROJECT_ENDPOINT%]: 
set "RESOURCE_GROUP=rg-ochuko"
set /p RESOURCE_GROUP=Resource Group Name [Default: %RESOURCE_GROUP%]: 
set "MODEL_NAME=gpt-4.1"
set /p MODEL_NAME=Model Deployment Name [Default: %MODEL_NAME%]: 
set "AGENT_ID=none"
set /p AGENT_ID=Diagnoser Agent ID (optional) [Default: %AGENT_ID%]: 
set "AGENT_NAME=DIAGNOSER"
set /p AGENT_NAME=Diagnoser Agent Name [Default: %AGENT_NAME%]: 
set "AGENT_VERSION=11"
set /p AGENT_VERSION=Diagnoser Agent Version [Default: %AGENT_VERSION%]: 

set "TMP_PY=%TEMP%\sre_update_env.py"
(
    echo import os
    echo env_path = r'.env'
    echo updates = {
    echo     'AZURE_PROJECT_ENDPOINT': r'%PROJECT_ENDPOINT%',
    echo     'AZURE_SUBSCRIPTION_ID': r'%SUB_ID%',
    echo     'AZURE_RESOURCE_GROUP': r'%RESOURCE_GROUP%',
    echo     'MODEL_DEPLOYMENT_NAME': r'%MODEL_NAME%',
    echo     'DIAGNOSER_AGENT_ID': r'%AGENT_ID%',
    echo     'DIAGNOSER_AGENT_NAME': r'%AGENT_NAME%',
    echo     'DIAGNOSER_AGENT_VERSION': r'%AGENT_VERSION%'
    echo }
    echo lines = []
    echo if os.path.exists(env_path):
    echo     with open(env_path, 'r', encoding='utf-8') as f:
    echo         lines = f.readlines()
    echo new_lines = []
    echo keys_found = set()
    echo for line in lines:
    echo     stripped = line.strip()
    echo     if stripped and not stripped.startswith('#') and '=' in line:
    echo         k, v = line.split('=', 1)
    echo         k = k.strip()
    echo         if k in updates and updates[k]:
    echo             new_lines.append(f'{k}={updates[k]}\n')
    echo             keys_found.add(k)
    echo             continue
    echo     new_lines.append(line)
    echo for k, v in updates.items():
    echo     if k not in keys_found and v:
    echo         new_lines.append(f'{k}={v}\n')
    echo with open(env_path, 'w', encoding='utf-8') as f:
    echo     f.writelines(new_lines)
    echo print('Updated successfully.')
) > "%TMP_PY%"

%PYTHON_CMD% "%TMP_PY%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to update .env file.
    del /f /q "%TMP_PY%" >nul 2>&1
    popd >nul
    exit /b 1
)
del /f /q "%TMP_PY%" >nul 2>&1
echo [SUCCESS] .env file updated with Azure settings.
echo.

rem --- Python virtual environment setup ---
set /p SETUP_VENV=Would you like to initialize/update the virtual environment (.venv)? [Y/n]: 
if /i "%SETUP_VENV%"=="" set "SETUP_VENV=Y"
if /i "%SETUP_VENV%"=="Y" (
    if not exist ".venv\Scripts\python.exe" (
        echo [INFO] Creating virtual environment (.venv)...
        %PYTHON_CMD% -m venv .venv
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to create virtual environment.
            popd >nul
            exit /b 1
        )
    )
    echo [INFO] Installing dependencies...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Dependency installation failed.
        popd >nul
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed successfully.
)
echo.

rem --- Optional Azure connection check ---
set /p RUN_CHECK=Would you like to run a connection sanity check to verify your RBAC access? [Y/n]: 
if /i "%RUN_CHECK%"=="" set "RUN_CHECK=Y"
if /i "%RUN_CHECK%"=="Y" (
    set "CHECK_PY=%TEMP%\sre_azure_check.py"
    (
        echo import os
        echo import sys
        echo from pathlib import Path
        echo from dotenv import load_dotenv
        echo from azure.identity import DefaultAzureCredential
        echo from azure.ai.projects import AIProjectClient
        echo project_root = Path(r'.').resolve()
        echo load_dotenv(project_root / '.env')
        echo endpoint = os.getenv('AZURE_PROJECT_ENDPOINT')
        echo deployment = os.getenv('MODEL_DEPLOYMENT_NAME', 'gpt-4.1')
        echo if not endpoint:
        echo     print('[ERROR] AZURE_PROJECT_ENDPOINT is not set in .env')
        echo     sys.exit(1)
        echo print(f'Connecting to endpoint: {endpoint}')
        echo print(f'Using deployment: {deployment}')
        echo print('Attempting authentication via DefaultAzureCredential...')
        echo try:
        echo     credential = DefaultAzureCredential()
        echo     client = AIProjectClient(endpoint=endpoint, credential=credential)
        echo     print('DefaultAzureCredential authenticated successfully!')
        echo     print('Retrieving OpenAI client connection...')
        echo     openai_client = client.get_openai_client()
        echo     print('Success! Connection established.')
        echo     print('==== AUTH_OK ====')
        echo except Exception as e:
        echo     print(f'\n[ERROR] Authentication or connection failed: {e}')
        echo     print('\nPlease verify that:')
        echo     print('  1. You ran \'az login\' with the correct account.')
        echo     print('  2. Your account has the Azure AI Developer or Contributor role on the project resource group.')
        echo     print('  3. The AZURE_PROJECT_ENDPOINT in your .env is correct.')
        echo     sys.exit(1)
    ) > "%CHECK_PY%"
    .venv\Scripts\python.exe "%CHECK_PY%"
    if %errorlevel% neq 0 (
        echo [ERROR] Connection sanity check failed.
        del /f /q "%CHECK_PY%" >nul 2>&1
        popd >nul
        exit /b 1
    )
    del /f /q "%CHECK_PY%" >nul 2>&1
)
echo.
echo ============================================================
echo Setup complete! You are ready to build.
echo To start the system:
echo   1. Start the target mock server:    uvicorn simulator.mock_server:app --port 8090
echo   2. Start the recovery pipeline:     python main.py
echo   3. Inject a failure:                python -m simulator.failure_injector db_crash
echo ============================================================
popd >nul
endlocal
