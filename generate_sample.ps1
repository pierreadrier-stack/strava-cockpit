# generate_sample.ps1 – Génère data/sample_activities.csv
$rng = [System.Random]::new(42)

function RandNorm($mean, $std) {
    $u1 = 1 - $rng.NextDouble()
    $u2 = 1 - $rng.NextDouble()
    $z  = [Math]::Sqrt(-2 * [Math]::Log($u1)) * [Math]::Cos(2 * [Math]::PI * $u2)
    return $mean + $std * $z
}

$start = [DateTime]::new(2025, 10, 1)
$end   = [DateTime]::new(2026, 4, 3)

$runDates = @()
$current  = $start
$weekRuns = 0

while ($current -le $end) {
    if ($current.DayOfWeek -eq 'Monday') { $weekRuns = 0 }
    $prob = if ($weekRuns -lt 3) { 0.58 } else { 0.22 }
    if ($rng.NextDouble() -lt $prob) {
        $runDates += $current
        $weekRuns++
    }
    $current = $current.AddDays(1)
}

$rows = @()
$dow2name = @{
    0 = @("Sortie longue","Long run dominical","Grand tour du week-end")
    1 = @("Run matinal","Footing","Run du lundi")
    2 = @("Tempo run","Sortie soutenue","Run du mardi")
    3 = @("Footing récup","Récupération active","Petite sortie")
    4 = @("Run du jeudi","Sortie standard","Footing")
    5 = @("Run du vendredi","Allure tempo","Sortie qualité")
    6 = @("Sortie longue","Long run","Sortie du samedi")
}

foreach ($d in $runDates) {
    $weekNum  = [Math]::Floor(($d - $start).TotalDays / 7)
    $progress = [Math]::Min($weekNum / 26.0, 1.0)

    # Distance selon le jour
    $dist = switch ($d.DayOfWeek) {
        'Sunday'   { [Math]::Max(2.0, (RandNorm (13 + $progress * 9) 1.5)) }
        'Tuesday'  { [Math]::Max(2.0, (RandNorm (8  + $progress * 4) 1.0)) }
        'Thursday' { [Math]::Max(2.0, (RandNorm (8  + $progress * 3) 1.0)) }
        default    { [Math]::Max(2.0, (RandNorm (6  + $progress * 2) 0.9)) }
    }
    $dist = [Math]::Round($dist, 2)

    # Allure (amélioration de 6:30 → 5:30 sur 6 mois)
    $basePace = 6.5 - $progress * 1.0
    if ($dist -gt 18) { $basePace += 0.45 }
    elseif ($dist -lt 6) { $basePace += 0.3 }
    elseif ($dist -gt 10) { $basePace -= 0.25 }
    $pace = [Math]::Max(4.5, (RandNorm $basePace 0.18))   # min/km

    $movingTime = [int]($pace * $dist * 60)
    $elapsedTime = [int]($movingTime * (1.03 + $rng.NextDouble() * 0.05))
    $elevation  = [int]([Math]::Max(0, (RandNorm ($dist * 8) ($dist * 3))))
    $speedKmh   = [Math]::Round(60.0 / $pace, 2)
    $calories   = [int]($dist * 70 + (RandNorm 0 25))

    # HR (85% des runs)
    $avgHr = ""
    $maxHr = ""
    if ($rng.NextDouble() -lt 0.85) {
        $baseHr = 165 - ($pace - 5) * 12
        $avgHr  = [int](RandNorm $baseHr 5)
        $maxHr  = [int]($avgHr * (1.08 + $rng.NextDouble() * 0.04))
    }

    # Nom
    $dow    = [int]$d.DayOfWeek
    $names  = $dow2name[$dow]
    $name   = $names[$rng.Next($names.Count)]

    $rows += [PSCustomObject]@{
        date           = $d.ToString("yyyy-MM-dd")
        name           = $name
        type           = "Run"
        distance_km    = $dist
        moving_time_s  = $movingTime
        elapsed_time_s = $elapsedTime
        elevation_m    = $elevation
        avg_hr         = $avgHr
        max_hr         = $maxHr
        avg_speed_kmh  = $speedKmh
        calories       = $calories
    }
}

$outPath = "data\sample_activities.csv"
New-Item -ItemType Directory -Path "data" -Force | Out-Null
# Forcer le séparateur décimal en point (invariant culture)
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$lines = @('"date","name","type","distance_km","moving_time_s","elapsed_time_s","elevation_m","avg_hr","max_hr","avg_speed_kmh","calories"')
foreach ($r in $rows) {
    $line = '"{0}","{1}","{2}",{3},{4},{5},{6},{7},{8},{9},{10}' -f `
        $r.date, $r.name, $r.type,
        $r.distance_km.ToString("F2", $culture),
        $r.moving_time_s, $r.elapsed_time_s, $r.elevation_m,
        $r.avg_hr, $r.max_hr,
        $r.avg_speed_kmh.ToString("F2", $culture),
        $r.calories
    $lines += $line
}
[System.IO.File]::WriteAllLines($outPath, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Host "OK: $($rows.Count) activites generees -> $outPath"
