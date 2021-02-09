[CmdletBinding(
    SupportsShouldProcess = $True
)]
param(
    [string]$checkPartitionSpace,
    [string]$checkPartitionFiles,
    [string]$checkDriveSize,
    [string]$plinkPath = "C:\PuTTY\",
    [string]$user = "root",
    [string]$igelLogin = "https://SERVER-NAME:8443/umsapi/v3/login",
    [string]$igelDevices = "https://SERVER-NAME:8443/umsapi/v3/thinclients?facets=online",
    [string]$igelLogout = "https://SERVER-NAME:8443/umsapi/v3/logout",
    [string]$csv
)

$plinkcmd = Join-Path -Path $plinkPath -ChildPath "plink.exe"
# Disable SSL Checking with c#
# UMS is using self-signed certificates, which throw an error when connecting unless checking is disabled:( 
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@

[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Ssl3, [Net.SecurityProtocolType]::Tls, [Net.SecurityProtocolType]::Tls11, [Net.SecurityProtocolType]::Tls12

# Build the REST Headers
$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Authorization", "Basic dGVjbW14QG1zai5vcmc6WWVsbG93ZHVja3MwMiE=")

# POST the headers to UMS to sign in.
# This gets a cookie: JSESSION: XXXX response, which is uses for later authn with the sessions variable $wsession
Write-Host "Logging into UMS."
$response = Invoke-RestMethod $igelLogin -Method 'POST' -Headers $headers -Body $body -SessionVariable wsession

# Request online status of all thin clients
Write-Host "Retrieving list of online iGels."
$igels = Invoke-RestMethod $igelDevices -Method "GET"  -Websession $wsession

# POST method to sign out

$response = Invoke-RestMethod $igelLogout -Method 'POST' -Websession $wsession

# $response
#Loop for each iGEL to make connection and run queries
$onlineIgels = $igels | Where-Object {$_.Online -eq $true}
# $onlineigels
ForEach ($igel in $onlineIgels) {
    # #Test to see if device responds to a ping
    $pingTest = Test-Connection $iGEL.Name -Count 1 -Quiet
    
    # #If device responds make connection and run queries
    If ($pingTest){
        # Connect using plink.exe to gather Imprivata Partition Information
        $igelPartData = echo Y | &$plinkcmd -l $user $igel.name -m $checkPartitionSpace
        
        #Split Partition Information to get specific variables
        $fileSystem,$1KBlocks,$Used,$Available,$UsePercent,$Mounted,$on,$fsData,$1kData,$usedData,$availData,$usePerData,$mountData = $igelPartData.Split(' ').Where({$_.Trim() -ne ""})
        # $fsData,$1kData,$usedData,$availData,$usePerData,$mountData = ($igelPartData.Split(' ').Where({$_.Trim() -ne ""}))[7..12]

        $igel | Add-Member -MemberType NoteProperty -Name "usePerData" -Value $usePerData
        $igel | Add-Member -MemberTYpe NoteProperty -Name "availData" -Value $availData
        $igel | Add-Member -MemberType NoteProperty -Name "usedData" -Value $usedData
        $igel | Add-Member -MemberType NoteProperty -Name "1kData" -Value $1kData
        

        # Connect using plink.exe to gather Log File information
        $igelLogFiles = echo Y | &$plinkcmd "-batch" -l $user $igel.name -m $checkPartitionFiles
            
        #If Log Files meet the criteria the $igelLogFiles variable will not be empty
        If ($null -ne $igelLogFiles) {
                $igel | Add-Member -MemberType NoteProperty -Name "igelLogsPresent" -Value "Check"
                # $igelLogsPresent = "Check"
                $igelLogFiles = $null
            }
        #Connect using plink.exe to gather Drive Size Information
        $igelDriveSize = echo Y | &$plinkcmd "-batch" -l $user $igel.name -m $checkDriveSize
        
        # #Split the Drive Size Information  to get specific variables
        $driveDisk,$driveData,$driveSizeGB,$driveOther = $igelDriveSize.Split(' ').Where({$_.Trim() -ne ""})
        $igel | Add-Member -MemberType NoteProperty -Name "driveSizeGB" -Value $driveSizeGB
        # #Write out basic info to screen while script runs
        # $igel.name + "," + $usePerData + "," + $igelLogsPresent
        
        # #Create an Array to hold all the wanted data
        # $igelLogInfo = @("$iGEL,$driveSizeGB,$1kData,$usedData,$availData,$usePerData,$igelLogsPresent")
        
        # #Output data to CSV file
        # $igelLogInfo | Add-Content $csv
        
        # #Set $igelLogsPresent back to null
        # $igelLogsPresent = $null
        }
    
    #If device does not respond output that information
    Else {
        $pingTest
        # $igelLogInfo = @("$iGEL,$pingTest")
        # $igel.name + "," + $pingTestFailed
        # $igelLogInfo | Add-Content $csv
        $igel.online = $false
        }
    $igel
}

$onlineIgels | Export-Csv -NoTypeInformation $csv