try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $path = "D:\Final Project\Logic_System\emotion & face recognition final_v6\document.doc"
    $doc = $word.Documents.Open($path)
    $savePath = "D:\Final Project\Logic_System\emotion & face recognition final_v6\document.docx"
    $doc.SaveAs([ref]$savePath, [ref]16)
    $doc.Close()
    $word.Quit()
    Write-Output "SUCCESS"
} catch {
    Write-Output "ERROR"
    Write-Output $_.Exception.Message
}
