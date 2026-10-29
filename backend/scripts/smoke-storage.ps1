param([string]$ApiBase = "http://127.0.0.1:8000")
$ErrorActionPreference = "Stop"
if (([uri]$ApiBase).Host -notin @("127.0.0.1", "localhost", "::1")) {
    throw "Use a loopback backend URL."
}

function Send-Json($Path, $Payload) {
    Invoke-RestMethod -Method Post -Uri "$ApiBase$Path" -ContentType "application/json" `
        -Body ($Payload | ConvertTo-Json -Depth 15) -TimeoutSec 20
}

$health = Invoke-RestMethod "$ApiBase/api/v1/health" -TimeoutSec 10
if (-not $health.storage_ready) { throw "Run python -m app.db.migrate first." }

$session = Send-Json "/api/v1/sessions" @{
    query = "Should our organisation approve full deployment?"
    domain_key = "education"
    objective = "Storage smoke test using synthetic policy context"
    constraints = @("Only the library pilot is currently approved")
}
$sessionPath = "/api/v1/sessions/$($session.session_id)"
$content = @{
    type = "factual"
    claim = "Full deployment is not approved."
    scope = "Synthetic policy S1; manually supplied hypothesis, not verified evidence"
}
$hypothesis = Send-Json "$sessionPath/hypotheses" @{
    expected_session_revision = 1
    content = $content
}
$hypothesisPath = "$sessionPath/hypotheses/$($hypothesis.hypothesis_id)"
$investigation = Send-Json "$hypothesisPath/transitions" @{
    expected_revision = 1
    target_status = "under_investigation"
    reason = "Human marks this hypothesis for investigation; no agent job is started"
}
if ($investigation.current.revision -ne 2) { throw "Status version did not advance." }

$content.claim = "Only a limited library pilot is currently approved."
$revised = Send-Json "$hypothesisPath/revisions" @{
    expected_revision = 2
    expected_session_revision = 1
    content = $content
    revision_reason = "Narrow the original claim to the approved scope"
}
$history = Invoke-RestMethod "$ApiBase$hypothesisPath/versions" -TimeoutSec 20
if ($history.total -ne 3 -or $history.items[0].content.claim -ne "Full deployment is not approved.") {
    throw "Original hypothesis history was not preserved."
}
if ($revised.current.status -ne "revised" -or $null -ne $revised.current.probability.posterior) {
    throw "Unexpected lifecycle or probability result."
}
$saved = Invoke-RestMethod "$ApiBase$sessionPath" -TimeoutSec 20
if ($saved.hypothesis_count -ne 1) { throw "Session hypothesis count is incorrect." }

[pscustomobject]@{
    session_id = $session.session_id
    hypothesis_id = $hypothesis.hypothesis_id
    current_hypothesis_revision = $revised.current.revision
    history_versions = $history.total
    reload_url = "$ApiBase$sessionPath"
} | ConvertTo-Json
Write-Host "Storage smoke checks passed. These are human-authored synthetic test records, not model findings."
Write-Host "Restart the API and GET reload_url to confirm this saved session remains available."
