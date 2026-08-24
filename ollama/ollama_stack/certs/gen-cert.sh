#!/bin/bash
# Génère un certificat TLS auto-signé pour le reverse proxy nginx devant Open WebUI.
#
# Usage :
#   ./certs/gen-cert.sh                  # CN/SAN = hostname du host
#   ./certs/gen-cert.sh ollama.local     # CN/SAN = nom fourni
#   HOST_IP=192.168.1.10 ./certs/gen-cert.sh ollama.local   # ajoute aussi l'IP au SAN
#
# Produit certs/open-webui.crt et certs/open-webui.key (montés en lecture seule
# dans le conteneur nginx — voir compose.yml et nginx/open-webui.conf).
#
# ─────────────────────────────────────────────────────────────────────────────
# Faire confiance au certificat sur un poste client Windows 11
# ─────────────────────────────────────────────────────────────────────────────
# Un certificat auto-signé déclenche un avertissement navigateur tant qu'il n'est
# pas importé dans le magasin "Autorités de certification racines de confiance".
#
# 1. Récupérer open-webui.crt sur le poste client (scp / clé USB / partage).
# 2. Méthode graphique :
#      - Double-cliquer sur open-webui.crt > "Installer le certificat"
#      - Emplacement : "Ordinateur local"  (nécessite les droits admin ;
#        choisir "Utilisateur actuel" pour ne l'installer que pour soi)
#      - "Placer tous les certificats dans le magasin suivant" > Parcourir >
#        "Autorités de certification racines de confiance" > OK > Terminer
# 2 bis. Méthode PowerShell (admin) — magasin machine :
#      Import-Certificate -FilePath .\open-webui.crt `
#        -CertStoreLocation Cert:\LocalMachine\Root
#    (pour le seul utilisateur courant : Cert:\CurrentUser\Root)
# 3. Redémarrer le navigateur. https://<host>:3000 ne doit plus afficher d'alerte.
#
# Note : le SAN (subjectAltName) doit correspondre à ce qui est tapé dans l'URL
# (nom DNS ou IP), sinon les navigateurs récents rejettent le certificat même
# une fois importé dans le magasin racine.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Dossier du script (les certs sont créés à côté de ce fichier).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CN="${1:-$(hostname -f 2>/dev/null || hostname)}"

SAN="DNS:${CN}"
#if [ -n "${HOST_IP:-}" ]; then
#  SAN="${SAN},IP:${HOST_IP}"
#fi

echo "🔐 Génération du certificat auto-signé (CN=${CN}, SAN=${SAN})..."
# MSYS2_ARG_CONV_EXCL : sous Git Bash (Windows), exclut le SEUL argument
# "/CN=..." de la conversion en chemin Windows (sinon "/CN=..." devient
# "C:/Program Files/Git/CN=..."). Les chemins -keyout/-out, eux, restent
# convertis normalement. Sans effet sur Linux.
# MSYS2_ARG_CONV_EXCL="/CN=" \
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout "${DIR}/open-webui.key" \
  -out    "${DIR}/open-webui.crt" \
  -subj   "/CN=${CN}" \
  -addext "subjectAltName=${SAN}"

chmod 600 "${DIR}/open-webui.key"
echo "✅ Créé :"
echo "   ${DIR}/open-webui.crt"
echo "   ${DIR}/open-webui.key"
