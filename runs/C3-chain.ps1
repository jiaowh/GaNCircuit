# Candidate C3 (search stage 2; plans/goal-targets-2026-10-08.md, declared 11 October 2026): G extraction of the C3 package, then
# the nominal C3 goals pair (vendor model, assumed 50 pH, ramp/step-Ls50); stock comes from the 8 October report.
$ErrorActionPreference = 'Continue'
$root = 'C:\Users\Jiaow\Documents\github\phd_circuit'
Set-Location $root
$py = 'C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0\python3.12.exe'
$log = "$root\runs\C3-chain.log"
function Note($m) { "$(Get-Date -Format o) $m" | Out-File -Append -Encoding utf8 $log }
$env:PYTHONPATH = 'src'
Note "A extraction and acceptance start"
& $py scripts\epc90133_board_export.py C3 --reuse --extract A:m1:mid *> runs\board-export-C3-A.log
Note "A extraction exit $LASTEXITCODE"
$k = "$root\vendor\epc\epc90133\reconstruction\export\C3"
$env:EPC90133_GERBER_EXPORT = $k
Note "G extraction start"
& $py scripts\epc90133_extract.py G:m1:mid --loop "$k\power-loop.json" --outdir "$k\extraction" --tag C3 --jobs 1 *> runs\C3-extract-G.log
Note "G extraction exit $LASTEXITCODE"
Remove-Item Env:EPC90133_GERBER_EXPORT
$g = "$k\extraction\G-m1-mid-C3.json"
if (Test-Path $g) {
  & $py scripts\epc90133_switching.py --study goals --jobs 2 --timeout 3600 --ext-file "C3=$g" --only C3@ramp-Ls50-gear C3@step-Ls50-gear --output results\gan\epc90133-goals-G-C3.json *> runs\C3-goals.log
  Note "switching exit $LASTEXITCODE"
} else { Note "no G report; switching not run" }
'done' | Out-File "$root\runs\C3-chain.done"
