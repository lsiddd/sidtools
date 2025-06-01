$H = New-Object Net.HttpListener
$H.Prefixes.Add('http://+:3306/')
$H.Start()

# Optimal buffer size for modern SSDs and 1Gbps+ networks
$BUFFER_SIZE = 4MB  # Test with 4MB-8MB values
$CHUNK_SIZE = 4MB   # Align with buffer size

while ($H.IsListening) {
    $Context = $H.GetContext()
    $Response = $Context.Response
    $FilePath = "E:\" + $Context.Request.Url.AbsolutePath.TrimStart('/')

    try {
        if (Test-Path $FilePath -PathType Leaf) {
            $fileStream = $null
            $buffer = [System.Buffers.ArrayPool]::byte.Shared.Rent($BUFFER_SIZE)
            
            try {
                # File handling
                $fileStream = [System.IO.File]::OpenRead($FilePath)
                $Response.Headers.Add("Accept-Ranges", "bytes")
                $Response.SendChunked = $false
                
                # Range handling
                $start = 0
                $end = $fileStream.Length - 1
                if ($Context.Request.Headers["Range"] -match "bytes=(\d+)-\d*") {
                    $start = [long]$matches[1]
                    if ($start -lt $fileStream.Length) {
                        $fileStream.Position = $start
                        $Response.StatusCode = 206
                        $Response.Headers.Add("Content-Range", "bytes $start-$end/$($fileStream.Length)")
                    }
                }
                
                # Configure response
                $Response.ContentType = 'application/octet-stream'
                $Response.ContentLength64 = $end - $start + 1
                
                # High-speed transfer loop
                $remaining = $Response.ContentLength64
                while ($remaining -gt 0) {
                    $bytesToRead = [Math]::Min($CHUNK_SIZE, $remaining)
                    $bytesRead = $fileStream.Read($buffer, 0, $bytesToRead)
                    $Response.OutputStream.Write($buffer, 0, $bytesRead)
                    $remaining -= $bytesRead
                }
            }
            finally {
                [System.Buffers.ArrayPool]::byte.Shared.Return($buffer)
                if ($fileStream) { $fileStream.Dispose() }
            }
        }
        else {
            $Response.StatusCode = 404
            $buffer = [Text.Encoding]::UTF8.GetBytes("Not Found")
            $Response.OutputStream.Write($buffer, 0, $buffer.Length)
        }
    }
    catch {
        $Response.StatusCode = 500
    }
    finally {
        $Response.Close()
    }
}

$H.Stop()