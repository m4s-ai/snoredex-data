$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json

$LIST='https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages'
$JU  ='https://bulbapedia.bulbagarden.net/wiki/Jungle_(TCG)'
$KSS ='https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)'
$SRC_IDX='Bulbapedia (fan wiki), cross-language expansion index'
$SRC_ART='Bulbapedia (fan wiki), expansion article'

$R = @{}
$R['U0125'] = @('confirmed',   $JU,   $SRC_ART, 'Jungle print languages: released in English, Dutch, German, French, Italian, Spanish and Portuguese')
$R['U0095'] = @('confirmed',   $JU,   $SRC_ART, 'Jungle print languages: released in English, Dutch, German, French, Italian, Spanish and Portuguese')
$R['U0364'] = @('confirmed',   $LIST, $SRC_IDX, 'Diamond and Pearl listed in the Polish column as "Diament i Perla"')
$R['U0336'] = @('confirmed',   $LIST, $SRC_IDX, 'Flashfire listed in the Russian column as "Ognennaya Vspyshka"')
$R['U0621'] = @('confirmed',   $LIST, $SRC_IDX, 'Flashfire listed in the Russian column (set-level evidence; V2 is a promo printing of the same set)')
$R['U0212'] = @('confirmed',   $LIST, $SRC_IDX, 'BREAKthrough listed in the Russian column as "Turbo Impuls"')
$R['U0487'] = @('confirmed',   $LIST, $SRC_IDX, 'Kalos Starter Set listed in the Russian column as "Startovyy Nabor Kalosa"')

$R['U0502'] = @('contradicted', $LIST, $SRC_IDX, 'Dutch releases are only Base Set, Jungle and Fossil. Wizards Black Star Promos is NOT listed in Dutch.')
$R['U0490'] = @('contradicted', $KSS,  $SRC_ART, 'Kalos Starter Set released in English, German, French, Italian, Spanish, Portuguese and Russian - Dutch not among them')
$R['U0491'] = @('contradicted', $KSS,  $SRC_ART, 'Kalos Starter Set print languages exclude Polish; Polish releases are only Diamond and Pearl plus Mysterious Treasures')
$R['U0492'] = @('contradicted', $KSS,  $SRC_ART, 'Kalos Starter Set print languages exclude Czech; no Czech-language expansion is documented')
$R['U0493'] = @('contradicted', $KSS,  $SRC_ART, 'Kalos Starter Set print languages exclude Hungarian; no Hungarian-language expansion is documented')
$R['U0200'] = @('contradicted', $LIST, $SRC_IDX, 'Fates Collide shows no entry in the Russian column; the Russian XY run ended with BREAKthrough')
$R['U0248'] = @('contradicted', $LIST, $SRC_IDX, 'Generations shows no entry in the Russian column; the Russian XY run ended with BREAKthrough')

$n=0; $ev=@()
foreach($u in $units){
  $k=[string]$u.unitId
  if(-not $R.ContainsKey($k)){ continue }
  $rec=$R[$k]
  $u.status=$rec[0]; $u.sourceUrl=$rec[1]; $u.sourceType=$rec[2]; $u.evidence=$rec[3]; $u.checkedAt=(Get-Date -Format s)
  $ev+=[pscustomobject]@{unitId=$k;lang=$u.language;status=$rec[0];source=$rec[1];evidence=$rec[3];at=$u.checkedAt}
  $n++
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
$ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8
@{phase='rare-languages';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "rare-language units resolved: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
