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

$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Authorization", "Basic BASE64-ENCODED-PASS")

$response = Invoke-RestMethod 'https://SERVER-NAME:8443/umsapi/v3/login' -Method 'POST' -Headers $headers -Body $body -SessionVariable wsession

$headers.Add("Cookie", $response.message)
$headers
$r = Invoke-RestMethod "https://SERVER-NAME:8443/umsapi/v3/thinclients" -Method "GET"  -Websession $wsession
# $r


$response = Invoke-RestMethod 'https://SERVER-NAME:8443/umsapi/v3/logout' -Method 'POST' -Websession $wsession