$ErrorActionPreference = "Stop"
$envPath = Join-Path $env:LOCALAPPDATA "hermes\.env"
$envDir = Split-Path -Parent $envPath
if (-not (Test-Path $envDir)) { throw "Hermes folder not found: $envDir" }

$secure = Read-Host "Paste Gemini API key (input is hidden)" -AsSecureString
$bstr = [IntPtr]::Zero
$plain = $null
try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($plain)) { throw "Empty key; nothing was changed." }
    $lines = @()
    if (Test-Path $envPath) {
        $backup = "$envPath.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item -LiteralPath $envPath -Destination $backup
        $lines = @(Get-Content -LiteralPath $envPath | Where-Object { $_ -notmatch '^\s*GEMINI_API_KEY\s*=' })
    }
    $lines += "GEMINI_API_KEY=$plain"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllLines($envPath, $lines, $utf8)
    Write-Host "Gemini key saved. The key value was not displayed."
    Write-Host "Restart the Hermes gateway before testing."
}
finally {
    $plain = $null
    if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($secure) { $secure.Dispose() }
}
