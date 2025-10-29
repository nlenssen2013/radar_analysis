param(
    [string]$BaseUrl = "http://localhost:5000"
)

function Invoke-Request {
    param(
        [string]$Path
    )
    $client = New-Object System.Net.Http.HttpClient
    $client.BaseAddress = $BaseUrl
    try {
        return $client.GetAsync($Path).Result
    } finally {
        $client.Dispose()
    }
}

function Assert-Status {
    param(
        [System.Net.Http.HttpResponseMessage]$Response,
        [int]$Expected,
        [string]$Label
    )
    if ($Response.StatusCode.value__ -ne $Expected) {
        throw "$Label expected HTTP $Expected but received $($Response.StatusCode.value__)"
    }
    Write-Host "$Label : HTTP $Expected"
}

$response = Invoke-Request -Path "/health"
Assert-Status -Response $response -Expected 200 -Label "Health"

$response = Invoke-Request -Path "/static/radar.html"
Assert-Status -Response $response -Expected 200 -Label "radar.html"
Write-Host "Content-Type: $($response.Content.Headers.ContentType)"

$response = Invoke-Request -Path "/static/radar.js"
Assert-Status -Response $response -Expected 200 -Label "radar.js"
Write-Host "Content-Type: $($response.Content.Headers.ContentType)"
if ($response.Content.Headers.ContentType.MediaType -notlike "*javascript*") {
    throw "radar.js missing JavaScript content type"
}

$response = Invoke-Request -Path "/radar_files"
Assert-Status -Response $response -Expected 200 -Label "radar_files"
if ($response.Content.Headers.ContentType.MediaType -ne "application/json") {
    throw "/radar_files did not return JSON"
}

$quickPath = "/radar_filter_q?path=radar_3_data/KMLB_SDUS52_TZ0MCO_202405151906.nc&threshold=23"
$response = Invoke-Request -Path $quickPath
Assert-Status -Response $response -Expected 200 -Label "radar_filter_q"
$mediaType = $response.Content.Headers.ContentType.MediaType
Write-Host "Content-Type: $mediaType"
if ($mediaType -notlike "image/*") {
    throw "radar_filter_q did not return image content"
}

Write-Host "Smoke checks complete."
