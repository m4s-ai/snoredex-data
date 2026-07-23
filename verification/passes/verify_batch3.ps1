$ErrorActionPreference='Stop'
$V=Split-Path -Parent $PSScriptRoot
$units=Get-Content "$V\units.json" -Raw -Encoding utf8|ConvertFrom-Json
$B='https://bulbapedia.bulbagarden.net/wiki/'

$rows=@(
 [pscustomobject]@{code='BA20'; langs=@('English'); page='Battle_Academy_2020_(TCG)'
   type='Bulbapedia (fan wiki), product article, deck list'
   ev='Battle Academy 2020 Mewtwo deck list row: 50/68 Snorlax [Hidden Fates] x2. The stamped printing is also recorded in the Hidden Fates set list as "Mewtwo Deck stamp Battle Academy 2020 exclusive".'}
 [pscustomobject]@{code='BA20'; langs=@('French','German','Italian'); page='Battle_Academy_2020_(TCG)'
   type='Bulbapedia (fan wiki), product article, "In other languages" table'
   ev='Battle Academy 2020 official localized product names: fr "Academie de Combat du Jeu de Cartes a Collectionner Pokemon", de "Pokemon-Sammelkartenspiel: Kampfakademie", it "Accademia Lotta del Gioco di Carte Collezionabili Pokemon". Spanish and Portuguese are absent from the table and are therefore left open, not contradicted.'}
)
$n=0;$ev=@()
foreach($r in $rows){
  foreach($u in $units){
    if($u.setCode -ne $r.code){continue}
    if($u.language -notin $r.langs){continue}
    if($u.status -in @('confirmed','contradicted')){continue}
    $u.status='confirmed'; $u.sourceUrl=$B+$r.page; $u.sourceType=$r.type; $u.evidence=$r.ev
    $u.checkedAt=(Get-Date -Format s)
    $ev+=[pscustomobject]@{unitId=$u.unitId;lang=$u.language;status='confirmed';source=$u.sourceUrl;evidence=$u.evidence;at=$u.checkedAt}
    $n++
  }
}
$units|ConvertTo-Json -Depth 4|Set-Content "$V\units.json" -Encoding utf8
if($ev){ $ev|ForEach-Object{$_|ConvertTo-Json -Compress}|Add-Content "$V\evidence.jsonl" -Encoding utf8 }
@{phase='batch3';completedAt=(Get-Date -Format s)}|ConvertTo-Json|Set-Content "$V\state.json" -Encoding utf8
Write-Host "confirmed: $n"
$units|Group-Object status|Sort-Object Count -Desc|Format-Table Count,Name -Auto
