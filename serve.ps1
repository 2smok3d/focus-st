$root = "$PSScriptRoot"
$http = [System.Net.HttpListener]::new()
$http.Prefixes.Add("http://localhost:3000/")
$http.Start()
Write-Host "Serving focus-st at http://localhost:3000"
$mime = @{ '.html'='text/html; charset=utf-8'; '.json'='application/json'; '.js'='application/javascript'; '.css'='text/css'; '.png'='image/png'; '.ico'='image/x-icon' }
while ($http.IsListening) {
    $ctx  = $http.GetContext()
    $path = $ctx.Request.Url.LocalPath
    if ($path -eq '/') { $path = '/add.html' }
    $file = Join-Path $root $path.TrimStart('/')
    $res  = $ctx.Response
    if (Test-Path $file -PathType Leaf) {
        $bytes = [System.IO.File]::ReadAllBytes($file)
        $ext   = [System.IO.Path]::GetExtension($file)
        $res.ContentType     = if ($mime[$ext]) { $mime[$ext] } else { 'application/octet-stream' }
        $res.ContentLength64 = $bytes.Length
        $res.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
        $res.StatusCode = 404
        $body = [System.Text.Encoding]::UTF8.GetBytes('Not found')
        $res.OutputStream.Write($body, 0, $body.Length)
    }
    $res.Close()
}
