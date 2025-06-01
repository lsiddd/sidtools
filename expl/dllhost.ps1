$H = New-Object Net.HttpListener
$H.Prefixes.Add('http://+:3306/')  # Change port if needed
$H.Start()

while ($H.IsListening) {
    $C = $H.GetContext()
    $R = $C.Response
    $F = $C.Request.Url.AbsolutePath.TrimStart('/')
    $LocalPath = "E:\$F"  # Change base directory if needed

    try {
        # Handle directory requests
        if (Test-Path $LocalPath -PathType Container) {
            $R.ContentType = 'text/html'
            $HTML = "<html><head><title>Index of /$F</title></head><body>"
            $HTML += "<h1>Index of /$F</h1><hr/><pre>"
            $HTML += "<a href='../'>../</a><br/>"
            
            Get-ChildItem $LocalPath | ForEach-Object {
                $Item = $_.Name
                $Size = if ($_.PSIsContainer) { "" } else { "{0:N2} MB" -f ($_.Length/6MB) }
                $Modified = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
                if ($_.PSIsContainer) { $Item += "/" }
                $HTML += "<a href='$Item'>$Item</a>" + 
                         " " * (60 - $Item.Length) + 
                         "$Modified" + 
                         " " * 20 + 
                         "$Size<br/>"
            }
            
            $HTML += "</pre><hr/></body></html>"
            $Buffer = [System.Text.Encoding]::UTF8.GetBytes($HTML)
            $R.OutputStream.Write($Buffer, 0, $Buffer.Length)
        }
        # Handle file requests
        elseif (Test-Path $LocalPath -PathType Leaf) {
            $FileStream = $null
            try {
                $FileStream = [System.IO.File]::OpenRead($LocalPath)
                $R.ContentType = 'application/octet-stream'
                $R.ContentLength64 = $FileStream.Length
                
                # Stream file in 6MB chunks
                $Buffer = New-Object byte[] 6MB
                while (($BytesRead = $FileStream.Read($Buffer, 0, $Buffer.Length)) -gt 0) {
                    $R.OutputStream.Write($Buffer, 0, $BytesRead)
                    $R.OutputStream.Flush()
                }
            }
            finally {
                if ($FileStream) { $FileStream.Close() }
            }
        }
        else {
            $R.StatusCode = 404
            $Buffer = [System.Text.Encoding]::UTF8.GetBytes("404 - File Not Found")
            $R.OutputStream.Write($Buffer, 0, $Buffer.Length)
        }
    }
    catch {
        Write-Host "Error processing request: $_"
        $R.StatusCode = 500
        $Buffer = [System.Text.Encoding]::UTF8.GetBytes("500 - Internal Server Error")
        $R.OutputStream.Write($Buffer, 0, $Buffer.Length)
    }
    finally {
        $R.Close()
    }
}

$H.Stop()
