# Prefer copying this block into PowerShell if downloaded scripts are blocked.
$ErrorActionPreference = "Stop"
$api = "http://127.0.0.1:8000"
$health = Invoke-RestMethod "$api/api/v1/health"
if (-not $health.storage_ready -or $health.increment -ne 4) {
    throw "Start the migrated Increment 4 backend first."
}
$brief = @{ query = "Is full deployment approved?"; domain_key = "education" } | ConvertTo-Json
$decision = Invoke-RestMethod "$api/api/v1/sessions" -Method Post -ContentType "application/json" -Body $brief
$sessionUrl = "$api/api/v1/sessions/$($decision.session_id)"
$policyPath = Join-Path $env:TEMP ("chanakya-policy-" + [guid]::NewGuid().ToString("N") + ".txt")
Set-Content -LiteralPath $policyPath -Encoding utf8NoBOM -NoNewline -Value "Synthetic policy: Only a library pilot is approved. Full deployment is not approved."
try {
    $document = Invoke-RestMethod "$sessionUrl/documents?filename=policy.txt&expected_session_revision=1" -Method Post -ContentType "text/plain" -InFile $policyPath
}
finally {
    Remove-Item -LiteralPath $policyPath -ErrorAction SilentlyContinue
}
$query = @{ query = "full deployment approved"; expected_session_revision = 1; limit = 1 } | ConvertTo-Json
$snapshot = Invoke-RestMethod "$sessionUrl/evidence/search" -Method Post -ContentType "application/json" -Body $query
if ($snapshot.passages.Count -ne 1) { throw "Expected one policy passage." }
$answerRequest = @{
    snapshot_id = $snapshot.snapshot_id
    expected_session_revision = 1
    idempotency_key = [guid]::NewGuid().ToString()
} | ConvertTo-Json
# This is a real call to your local Qwen model.
$answer = Invoke-RestMethod "$sessionUrl/answers" -Method Post -ContentType "application/json" -Body $answerRequest -TimeoutSec 180
if ($answer.response.assessment.insufficient_evidence) { throw "The model abstained. Share its response for inspection." }
if ($answer.response.assessment.source_ids.Count -ne 1 -or $answer.response.assessment.source_ids[0] -cne $snapshot.passages[0].source_id) {
    throw "Expected the supplied policy passage to be cited."
}
# Repeating a completed request returns the same saved answer, without another inference.
$replay = Invoke-RestMethod "$sessionUrl/answers" -Method Post -ContentType "application/json" -Body $answerRequest -TimeoutSec 180
if ($replay.answer_id -ne $answer.answer_id) { throw "Replay did not return the original answer." }
$answerUrl = "$sessionUrl/answers/$($answer.answer_id)"
$loaded = Invoke-RestMethod $answerUrl
if ($loaded.response.assessment.answer -cne $answer.response.assessment.answer) { throw "Saved answer differs." }
$checkPath = Join-Path $env:TEMP "chanakya-answer-restart-check.json"
@{
    answer_url = $answerUrl
    answer_id = $answer.answer_id
    answer_text = $answer.response.assessment.answer
    source_id = $snapshot.passages[0].source_id
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $checkPath -Encoding utf8
$answer | ConvertTo-Json -Depth 20
Write-Host "Saved-answer checks passed. Read the answer above and verify it says full deployment is not approved."
Write-Host "After restarting the backend, run the restart check in the guide."
