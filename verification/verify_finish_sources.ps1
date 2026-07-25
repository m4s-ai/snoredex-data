$ErrorActionPreference = 'Stop'

$verificationDir = $PSScriptRoot
$overridePath = Join-Path $verificationDir 'finish_overrides.json'
$overrideDocument = Get-Content -LiteralPath $overridePath -Raw -Encoding utf8 | ConvertFrom-Json
$responseCache = @{}
$failures = @()
$networkFailures = @()
$checkedSources = 0
$checkedProducts = 0

function Get-TcgCsvResults([string]$uri) {
  if (-not $script:responseCache.ContainsKey($uri)) {
    try {
      $response = Invoke-RestMethod -Uri $uri -Headers @{'User-Agent' = 'snoredex-data/finish-source-verification'}
      $script:responseCache[$uri] = [pscustomobject]@{Success=$true; Results=@($response.results); Error=$null}
    }
    catch {
      $detail = $_.Exception.Message
      $script:networkFailures += "$uri — $detail"
      $script:responseCache[$uri] = [pscustomobject]@{Success=$false; Results=@(); Error=$detail}
    }
  }
  return $script:responseCache[$uri]
}

foreach ($sourceProperty in $overrideDocument.sources.PSObject.Properties) {
  $sourceName = $sourceProperty.Name
  $source = $sourceProperty.Value
  if (-not $source.expectedSubtypes) {
    continue
  }

  $checkedSources++
  if ([string]::IsNullOrWhiteSpace($source.identityUrl) -or [string]::IsNullOrWhiteSpace($source.url)) {
    $failures += "$sourceName has expectedSubtypes but no identityUrl or price URL"
    continue
  }

  $productResponse = Get-TcgCsvResults $source.identityUrl
  $priceResponse = Get-TcgCsvResults $source.url
  if (-not $productResponse.Success -or -not $priceResponse.Success) {
    continue
  }
  $products = @($productResponse.Results)
  $prices = @($priceResponse.Results)
  foreach ($expectation in $source.expectedSubtypes.PSObject.Properties) {
    $checkedProducts++
    $productId = [int]$expectation.Name
    $product = $products | Where-Object productId -eq $productId | Select-Object -First 1
    if (-not $product) {
      $failures += "$sourceName product $productId is absent from $($source.identityUrl)"
      continue
    }

    $actualSubtypes = @(
      $prices |
        Where-Object productId -eq $productId |
        Select-Object -ExpandProperty subTypeName -Unique
    )
    $expectedSubtypes = @($expectation.Value)
    $missingSubtypes = @($expectedSubtypes | Where-Object {$_ -notin $actualSubtypes})
    if ($missingSubtypes.Count) {
      $failures += "$sourceName product $productId ($($product.name)) is missing: $($missingSubtypes -join ', ')"
      continue
    }

    Write-Host ("[OK  ] {0} product {1}: {2}" -f $sourceName, $productId, ($expectedSubtypes -join ' + '))
  }
}

if ($failures.Count) {
  foreach ($failure in $failures) {
    Write-Host "[FAIL] $failure"
  }
  throw "Finish-source DATA MISMATCH for $($failures.Count) assertion(s)."
}

if ($networkFailures.Count) {
  foreach ($failure in $networkFailures) {
    Write-Host "[RETRY] $failure"
  }
  Write-Error "Finish-source verification could not reach $($networkFailures.Count) endpoint(s); this is a transient network failure, not a data mismatch."
  exit 2
}

Write-Host ""
Write-Host "Verified $checkedProducts TCGCSV products across $checkedSources source records."
