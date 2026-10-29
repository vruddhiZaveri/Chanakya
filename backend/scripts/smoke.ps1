param([string]$ApiBase = "http://127.0.0.1:8000")
$ErrorActionPreference = "Stop"
if (([uri]$ApiBase).Host -notin @("127.0.0.1", "localhost", "::1")) {
    throw "Use a loopback backend URL for this local test."
}

Write-Host "Checking the real running API and installed local model..."
$health = Invoke-RestMethod "$ApiBase/api/v1/health" -TimeoutSec 10
if ($health.status -ne "ok") { throw "API health check failed." }
$model = Invoke-RestMethod "$ApiBase/api/v1/models/status" -TimeoutSec 15
$model | ConvertTo-Json -Depth 8

$body = @{
    mode = "source_grounded"
    question = "Is full deployment approved?"
    sources = @(@{
        id = "S1"
        title = "Synthetic test policy"
        excerpt = "Only a library pilot is approved. Full deployment is not approved."
    })
} | ConvertTo-Json -Depth 10

$result = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/v1/baseline" `
    -ContentType "application/json" -Body $body -TimeoutSec 150
$result | ConvertTo-Json -Depth 12

if (-not $result.validation.schema_valid -or -not $result.validation.citation_ids_valid) {
    throw "Structured output validation failed."
}
if ($result.assessment.source_ids.Count -ne 1 -or $result.assessment.source_ids[0] -ne "S1") {
    throw "The synthetic source test did not cite exactly S1."
}
if ($result.assessment.insufficient_evidence) {
    throw "The model abstained on the simple synthetic policy. Inspect the result."
}
Write-Host "Transport, schema and source-ID smoke checks passed."
Write-Host "Manually verify the answer says FULL deployment is NOT approved."
Write-Host "This is not a multi-agent or research-accuracy benchmark."
