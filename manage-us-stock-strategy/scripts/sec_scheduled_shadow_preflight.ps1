function Get-SecScheduledShadowPreflight {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$TimezoneId,
        [AllowEmptyString()][string]$ProcessUserAgent = "",
        [AllowEmptyString()][string]$PersistentUserAgent = ""
    )

    $timezonePass = $TimezoneId -eq "Korea Standard Time"
    $processConfigured = -not [string]::IsNullOrWhiteSpace($ProcessUserAgent)
    $persistentConfigured = -not [string]::IsNullOrWhiteSpace($PersistentUserAgent)
    $failureCode = if (-not $timezonePass) {
        "WINDOWS_TIMEZONE_MISMATCH"
    } elseif (-not $persistentConfigured) {
        "SEC_USER_AGENT_USER_ENV_REQUIRED"
    } elseif (-not $processConfigured) {
        "SEC_USER_AGENT_REQUIRED"
    } else {
        $null
    }

    [pscustomobject]@{
        TimezoneId = $TimezoneId
        TimezoneDisplay = if ($timezonePass) { "Korea Standard Time" } else { "OTHER" }
        TimezonePreflight = if ($timezonePass) { "PASS" } else { "FAIL" }
        ProcessUserAgent = if ($processConfigured) { "CONFIGURED" } else { "NOT_CONFIGURED" }
        PersistentUserAgent = if ($persistentConfigured) { "CONFIGURED" } else { "NOT_CONFIGURED" }
        ActivationReady = $timezonePass -and $processConfigured -and $persistentConfigured
        FailureCode = $failureCode
        NewLogonSessionRequiredAfterChange = $true
    }
}

function Get-SecScheduledShadowSystemPreflight {
    [CmdletBinding()]
    param()

    $timezone = Get-TimeZone -ErrorAction Stop
    $persistentUserAgent = [Environment]::GetEnvironmentVariable(
        "SEC_USER_AGENT",
        [EnvironmentVariableTarget]::User
    )
    Get-SecScheduledShadowPreflight `
        -TimezoneId $timezone.Id `
        -ProcessUserAgent ([string]$env:SEC_USER_AGENT) `
        -PersistentUserAgent ([string]$persistentUserAgent)
}
