$ErrorActionPreference = 'Stop'

$verificationDir = $PSScriptRoot
$overridePath = Join-Path $verificationDir 'finish_overrides.json'
$overrideDocument = Get-Content -LiteralPath $overridePath -Raw -Encoding utf8 | ConvertFrom-Json
$responseCache = @{}
$failures = @()
$checkedSources = 0
$checkedProducts = 0

function Get-TcgCsvResults([string]$uri) {
  if (-not $script:responseCache.ContainsKey($uri)) {
    $response = Invoke-RestMethod -Uri $uri -Headers @{'User-Agent' = 'snoredex-data/finish-source-verification'}
    $script:responseCache[$uri] = @($response.results)
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

  $products = Get-TcgCsvResults $source.identityUrl
  $prices = Get-TcgCsvResults $source.url
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
  throw "Finish-source verification failed for $($failures.Count) assertion(s)."
}

Write-Host ""
Write-Host "Verified $checkedProducts TCGCSV products across $checkedSources source records."
