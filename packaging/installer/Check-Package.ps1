# Runtime counterpart of packaging/check_package.py; Windows PowerShell 5.1, no Python.
function Assert-Package($Package) {
    function Need($OK, $Why) { if (-not $OK) { throw "Package check: $Why" } }
    function Text($Node, $Tag) {
        $items = @($Node.SelectNodes($Tag))
        Need ($items.Count -eq 1 -and $items[0].InnerText.Length -gt 0) "expected one $Tag"
        return $items[0].InnerText
    }
    function Name($Value) { Need ($Value -cmatch '^[A-Za-z0-9_][A-Za-z0-9_.+-]*$' -and $Value -notin @('.','..')) "unsafe name $Value"; return $Value }
    $doc = New-Object Xml.XmlDocument
    $doc.XmlResolver = $null
    $doc.Load((Join-Path $Package 'app_info.xml'))
    $root = $doc.DocumentElement
    Need ($root.Name -ceq 'app_info') 'root must be app_info'
    Need (@($root.SelectNodes('app')).Count -eq 1) 'expected one app'
    Need ((Text $root.SelectSingleNode('app') 'name') -ceq 'milkyway_nbody') 'wrong server app'
    Need (@($root.SelectNodes('app_version')).Count -eq 1) 'expected one app_version'
    $version = $root.SelectSingleNode('app_version')
    $values = @{app_name='milkyway_nbody';version_num='196';platform='windows_x86_64';plan_class='mt';avg_ncpus='1';max_ncpus='1'}
    foreach ($tag in $values.Keys) { Need ((Text $version $tag) -ceq $values[$tag]) "wrong $tag" }
    Need (@($version.SelectNodes('coproc')).Count -eq 0) 'unexpected coprocessor claim'
    $declared = @{}
    foreach ($node in $root.SelectNodes('file_info')) {
        $n = Name (Text $node 'name')
        Need (-not $declared.ContainsKey($n)) "duplicate name $n"
        $declared[$n] = $node
    }
    $actual = @(Get-ChildItem -LiteralPath $Package -Force | Where-Object { $_.Name -cne 'app_info.xml' })
    Need ($actual.Count -eq $declared.Count) 'file inventory mismatch'
    foreach ($file in $actual) {
        Need ($declared.Keys -ccontains $file.Name) "file inventory mismatch: $($file.Name)"
        Need (-not $file.PSIsContainer -and $file.Length -gt 0 -and -not ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) "empty or nonregular file $($file.Name)"
    }
    $refs = @{}; $mains = @(); $graphics = @()
    foreach ($ref in $version.SelectNodes('file_ref')) {
        $n = Name (Text $ref 'file_name')
        Need ($declared.Keys -ccontains $n) "undeclared reference $n"
        Need (-not $refs.ContainsKey($n)) "duplicate reference $n"
        $refs[$n] = $true
        if ($n -ceq 'knc_nbody_graphics.exe') { Need ((Text $ref 'open_name') -ceq 'graphics_app') 'graphics discovery requires open_name graphics_app' }
        else { Need (@($ref.SelectNodes('open_name')).Count -eq 0) 'ordinary file renamed' }
        if (@($ref.SelectNodes('graphics_app')).Count) {
            Need (@($ref.SelectNodes('graphics_app')).Count -eq 1) 'duplicate graphics_app'; $graphics += $n
        }
        if (@($ref.SelectNodes('main_program')).Count) {
            Need (@($ref.SelectNodes('main_program')).Count -eq 1) 'duplicate main_program'; $mains += $n
        } else { Need (@($ref.SelectNodes('copy_file')).Count -eq 1) "ordinary read needs copy_file: $n" }
    }
    Need ($refs.Count -eq $declared.Count) 'every package file needs a file_ref'
    Need ($mains.Count -eq 1 -and $mains[0] -ceq 'knc_wrapper.exe') 'expected sole knc_wrapper.exe main_program'
    Need ($graphics.Count -eq 1 -and $graphics[0] -ceq 'knc_nbody_graphics.exe') 'expected sole graphics app'
    foreach ($n in @('knc_wrapper.exe','knc_nbody_graphics.exe')) {
        Need (@($declared[$n].SelectNodes('executable')).Count -eq 1) "$n must be executable"
    }
    foreach ($n in @('knc_wrapper.cfg.example','milkyway_nbody.mic','cygwin1.dll','cyggcc_s-seh-1.dll','cygstdc++-6.dll','cygiconv-2.dll','cygintl-8.dll')) {
        Need ($declared.Keys -ccontains $n) "required file missing: $n"
    }
    Need (@($declared.Keys | Where-Object { $_ -clike '*.so*' }).Count -gt 0) 'card runtimes missing'
    return @('app_info.xml') + @($declared.Keys | Sort-Object)
}
