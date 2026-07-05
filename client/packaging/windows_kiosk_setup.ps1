<#
.SYNOPSIS
    Configure un poste Windows en kiosque dédié pour le client cybercafé :
    - compte local restreint dédié ("kiosque"), sans droits admin
    - autologin sur ce compte au démarrage
    - remplace le shell de ce compte par l'app kiosque (l'Explorateur/bureau/barre
      des tâches ne se lance JAMAIS pour ce compte)
    - désactive Task Manager et les options gênantes de Ctrl+Alt+Suppr pour ce compte

.NOTES
    ⚠️ NON TESTÉ EN CONDITIONS RÉELLES (rédigé sans machine Windows disponible pour
    validation). À exécuter d'abord sur un poste de test avant déploiement en prod.

    Ctrl+Alt+Suppr lui-même ne peut jamais être intercepté par une app : c'est une
    protection noyau. Ce script désactive seulement les ACTIONS disponibles depuis
    cet écran (Gestionnaire des tâches, verrouiller, changer d'utilisateur...).

    À exécuter en PowerShell **administrateur**.

.PARAMETER AppExePath
    Chemin complet vers l'exécutable packagé du client (voir build_windows.md),
    ou vers python.exe + main.py si vous ne packagez pas en .exe.

.PARAMETER KioskPassword
    Mot de passe du compte kiosque créé (à choisir vous-même, gardez-le).

.EXAMPLE
    .\windows_kiosk_setup.ps1 -AppExePath "C:\CybercafeClient\cybercafe-client.exe" -KioskPassword "MotDePasseSolide!"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$AppExePath,

    [Parameter(Mandatory = $true)]
    [string]$KioskPassword,

    [string]$KioskUser = "kiosque"
)

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Error "Ce script doit être exécuté en tant qu'administrateur."
    exit 1
}

if (-not (Test-Path $AppExePath)) {
    Write-Error "Introuvable : $AppExePath"
    exit 1
}

# 1. Compte local dédié, standard (pas admin)
$existing = Get-LocalUser -Name $KioskUser -ErrorAction SilentlyContinue
if (-not $existing) {
    $securePwd = ConvertTo-SecureString $KioskPassword -AsPlainText -Force
    New-LocalUser -Name $KioskUser -Password $securePwd -PasswordNeverExpires -UserMayNotChangePassword
    Add-LocalGroupMember -Group "Users" -Member $KioskUser
    Write-Host "Compte '$KioskUser' créé (membre du groupe Users standard, pas Administrators)."
} else {
    Write-Host "Compte '$KioskUser' déjà existant, réutilisation."
}

# 2. Autologin sur ce compte au démarrage
$winlogonPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $winlogonPath -Name "AutoAdminLogon" -Value "1"
Set-ItemProperty -Path $winlogonPath -Name "DefaultUserName" -Value $KioskUser
Set-ItemProperty -Path $winlogonPath -Name "DefaultPassword" -Value $KioskPassword
Set-ItemProperty -Path $winlogonPath -Name "DefaultDomainName" -Value $env:COMPUTERNAME

# 3. Remplace le shell UNIQUEMENT pour ce compte (pas globalement) :
#    HKEY_USERS\<SID>\...\Winlogon\Shell = chemin de l'app kiosque au lieu d'explorer.exe
$kioskSid = (New-Object System.Security.Principal.NTAccount($KioskUser)).Translate([System.Security.Principal.SecurityIdentifier]).Value

# Le profil doit exister au moins une fois pour que la ruche HKU\<SID> soit disponible :
# on charge la ruche NTUSER.DAT du compte si l'utilisateur ne s'est jamais connecté.
$profilePath = (Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $kioskSid }).LocalPath
if (-not $profilePath) {
    Write-Warning "Le profil du compte '$KioskUser' n'existe pas encore : connectez-vous une fois manuellement avec ce compte, puis relancez ce script pour l'étape du shell personnalisé."
} else {
    $hiveLoaded = $false
    if (-not (Test-Path "Registry::HKEY_USERS\$kioskSid")) {
        reg load "HKU\$kioskSid" "$profilePath\NTUSER.DAT" | Out-Null
        $hiveLoaded = $true
    }

    $shellKey = "Registry::HKEY_USERS\$kioskSid\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    New-Item -Path $shellKey -Force | Out-Null
    Set-ItemProperty -Path $shellKey -Name "Shell" -Value "`"$AppExePath`""

    if ($hiveLoaded) {
        [gc]::Collect()
        reg unload "HKU\$kioskSid" | Out-Null
    }
    Write-Host "Shell personnalisé configuré pour '$KioskUser' : $AppExePath"
}

# 4. Désactiver le Gestionnaire des tâches et durcir l'écran Ctrl+Alt+Suppr pour ce compte
#    (stratégies appliquées via le registre HKCU du compte kiosque, mêmes precautions que ci-dessus)
if ($profilePath) {
    $hiveLoaded = $false
    if (-not (Test-Path "Registry::HKEY_USERS\$kioskSid")) {
        reg load "HKU\$kioskSid" "$profilePath\NTUSER.DAT" | Out-Null
        $hiveLoaded = $true
    }

    $policyKey = "Registry::HKEY_USERS\$kioskSid\Software\Microsoft\Windows\CurrentVersion\Policies\System"
    New-Item -Path $policyKey -Force | Out-Null
    Set-ItemProperty -Path $policyKey -Name "DisableTaskMgr" -Value 1 -Type DWord
    Set-ItemProperty -Path $policyKey -Name "NoLockWorkstation" -Value 1 -Type DWord
    Set-ItemProperty -Path $policyKey -Name "NoLogoff" -Value 1 -Type DWord

    $explorerPolicyKey = "Registry::HKEY_USERS\$kioskSid\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    New-Item -Path $explorerPolicyKey -Force | Out-Null
    Set-ItemProperty -Path $explorerPolicyKey -Name "NoRun" -Value 1 -Type DWord         # menu "Executer"
    Set-ItemProperty -Path $explorerPolicyKey -Name "NoFind" -Value 1 -Type DWord        # recherche

    if ($hiveLoaded) {
        [gc]::Collect()
        reg unload "HKU\$kioskSid" | Out-Null
    }
    Write-Host "Durcissement (Task Manager, verrouillage, Executer) appliqué pour '$KioskUser'."
}

Write-Host ""
Write-Host "Configuration terminée. Redémarrez le poste pour tester : il doit démarrer"
Write-Host "directement dans l'app kiosque, sans bureau ni barre des tâches Windows."
Write-Host ""
Write-Host "Pour revenir en arrière (dépannage) : reconnectez-vous avec un compte admin,"
Write-Host "remettez AutoAdminLogon à 0 dans $winlogonPath, et redémarrez."
