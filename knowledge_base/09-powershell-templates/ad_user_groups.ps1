param(
    [Parameter(Mandatory=$true)]
    [string]$SamAccountName
)

Import-Module ActiveDirectory

$user = Get-ADUser $SamAccountName -Properties MemberOf,Enabled,LockedOut,PasswordLastSet
$user | Select-Object SamAccountName, Enabled, LockedOut, PasswordLastSet

Write-Host "`nGroups:"
Get-ADPrincipalGroupMembership $SamAccountName |
    Sort-Object Name |
    Select-Object Name, GroupCategory, GroupScope
