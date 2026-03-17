$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $PSScriptRoot
$backendPython = Join-Path $root "backend\.runtime-venv\Scripts\python.exe"
$testFile = Join-Path $PSScriptRoot "test_ai_design_full_flow.py"

if (-not (Test-Path $backendPython)) {
  Write-Host "未找到运行测试所需的 Python 环境: $backendPython"
  exit 1
}

Write-Host "开始执行 AI设计流程测试..."
Write-Host "测试文件: $testFile"

& $backendPython -m pytest $testFile -q

if ($LASTEXITCODE -ne 0) {
  Write-Host "AI设计流程测试失败"
  exit $LASTEXITCODE
}

Write-Host "AI设计流程测试通过"
