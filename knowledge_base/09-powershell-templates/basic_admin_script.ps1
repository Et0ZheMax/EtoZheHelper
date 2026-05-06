param(
    [Parameter(Mandatory=$true)]
    [string]$Target,

    [switch]$DryRun,

    [string]$LogPath = ".\admin-script.log"
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    Add-Content -Path $LogPath -Value $line
}

try {
    Write-Log "Starting. Target=$Target DryRun=$DryRun"

    if ($DryRun) {
        Write-Log "[DRY-RUN] Would process $Target"
        exit 0
    }

    # TODO: work here
    Write-Log "Done"
}
catch {
    Write-Log "Failed: $($_.Exception.Message)" "ERROR"
    exit 1
}
