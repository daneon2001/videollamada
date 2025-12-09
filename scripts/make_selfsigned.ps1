param(
  [string]$DnsName="video.sybi.local",
  [string]$OutPfx="C:\certs\video-selfsigned.pfx",
  [string]$Password="ChangeThis!"
)
$cert = New-SelfSignedCertificate -DnsName $DnsName -CertStoreLocation "cert:\LocalMachine\My" -FriendlyName "Video SelfSigned" -KeyExportPolicy Exportable -NotAfter (Get-Date).AddYears(1)
$pwd = ConvertTo-SecureString -String $Password -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $OutPfx -Password $pwd
Write-Host "PFX listo en $OutPfx. Úsalo en IIS."
