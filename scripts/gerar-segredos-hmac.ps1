# Gera LINK_HMAC_SECRET e APROVACAO_HMAC_SECRET (32 bytes aleatórios, hex) e grava cada um DIRETO
# no GitHub (gh secret set) e no Worker (wrangler secret put, via stdin), sem imprimir os valores (ADR-009).
#
# Pré-requisitos: `gh auth login` feito, `npx wrangler login` feito e o Worker já publicado
# (`npx wrangler deploy` dentro de worker/). Rodar da raiz do repositório:
#   powershell -ExecutionPolicy Bypass -File scripts\gerar-segredos-hmac.ps1
#
# Atenção: rodar de novo TROCA os segredos. Links de e-mail já enviados e aprovações já gravadas
# (aprovacao.json) deixam de valer; será preciso reenviar o e-mail da semana.
param([string]$Repo = "diogokammers/pastoral-dizimo-instagram")

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot

foreach ($cmd in @("gh", "npx")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Comando '$cmd' não encontrado no PATH." }
}

function Novo-Segredo {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

Push-Location (Join-Path $raiz "worker")
try {
    foreach ($nome in @("LINK_HMAC_SECRET", "APROVACAO_HMAC_SECRET")) {
        $valor = Novo-Segredo
        # O PowerShell acrescenta quebra de linha ao valor enviado pelo pipe; Python e Worker fazem trim.
        $valor | gh secret set $nome --repo $Repo | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "gh secret set $nome falhou." }
        $valor | npx wrangler secret put $nome | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "wrangler secret put $nome falhou." }
        Remove-Variable valor
        Write-Host "$nome gravado no GitHub e no Worker (valor não exibido)."
    }
} finally {
    Pop-Location
}
