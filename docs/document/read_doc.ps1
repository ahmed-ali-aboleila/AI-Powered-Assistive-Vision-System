try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $path = "D:\Final Project\Logic_System\emotion & face recognition final_v6\document.doc"
    $doc = $word.Documents.Open($path)
    $text = $doc.Content.Text
    $doc.Close()
    $word.Quit()
    Write-Output "SUCCESS"
    Write-Output $text.Substring(0, [Math]::Min(3000, $text.Length))
} catch {
    Write-Output "ERROR"
    Write-Output $_.Exception.Message
}
