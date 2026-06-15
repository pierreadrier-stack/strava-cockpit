#!/usr/bin/env python3
# ─────────────────────────────────────────────
#  get_strava_token.py  –  Obtenir ton refresh token Strava (une seule fois)
# ─────────────────────────────────────────────
"""
À lancer EN LOCAL, une seule fois, pour récupérer ton STRAVA_REFRESH_TOKEN.

Prérequis (2 min) :
  1. Va sur https://www.strava.com/settings/api
  2. Crée une application :
       - "Application Name"            : Running Cockpit (ou ce que tu veux)
       - "Category"                    : peu importe
       - "Website"                     : http://localhost
       - "Authorization Callback Domain": localhost     ← IMPORTANT
  3. Note ton "Client ID" et ton "Client Secret".

Puis :
    python scripts/get_strava_token.py

Le script t'ouvre la page d'autorisation Strava, tu cliques "Authorize",
ton navigateur est redirigé vers http://localhost/?...&code=XXXX&... (la page
affichera "connexion impossible", c'est NORMAL) → copie le code depuis la barre
d'adresse et colle-le ici. Le script affiche alors ton refresh token.
"""

import urllib.parse
import webbrowser

import requests

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL     = "https://www.strava.com/oauth/token"
SCOPE         = "activity:read_all"   # lit aussi les activités privées


def main() -> None:
    print("\n=== Obtention du refresh token Strava ===\n")
    client_id     = input("Client ID Strava     : ").strip()
    client_secret = input("Client Secret Strava : ").strip()
    if not client_id or not client_secret:
        print("❌ Client ID / Secret manquant. Abandon.")
        return

    params = urllib.parse.urlencode({
        "client_id":       client_id,
        "response_type":   "code",
        "redirect_uri":    "http://localhost",
        "approval_prompt": "force",
        "scope":           SCOPE,
    })
    auth_url = f"{AUTHORIZE_URL}?{params}"

    print("\n1) Ouvre cette URL et clique « Authorize » :\n")
    print("   " + auth_url + "\n")
    print("2) Ton navigateur sera redirigé vers une page « connexion impossible »")
    print("   (c'est normal). Copie le paramètre 'code' depuis la barre d'adresse :")
    print("   http://localhost/?state=&code=COPIE_CECI&scope=...\n")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    code = input("Colle le code ici : ").strip()
    if not code:
        print("❌ Code manquant. Abandon.")
        return

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id":     client_id,
            "client_secret": client_secret,
            "code":          code,
            "grant_type":    "authorization_code",
        },
        timeout=20,
    )

    if resp.status_code != 200:
        print(f"\n❌ Échec ({resp.status_code}) : {resp.text}")
        return

    tok = resp.json()
    refresh_token = tok.get("refresh_token")
    athlete = tok.get("athlete", {})

    print("\n✅ Autorisation réussie pour :",
          athlete.get("firstname", ""), athlete.get("lastname", ""))
    print("\n────────────────────────────────────────────")
    print(" Colle ces lignes dans tes Secrets Streamlit")
    print(" (Streamlit Cloud → ton app → Settings → Secrets)")
    print("────────────────────────────────────────────\n")
    print(f'STRAVA_CLIENT_ID     = "{client_id}"')
    print(f'STRAVA_CLIENT_SECRET = "{client_secret}"')
    print(f'STRAVA_REFRESH_TOKEN = "{refresh_token}"')
    print("\n(Et dans .streamlit/secrets.toml en local si tu testes ici.)\n")


if __name__ == "__main__":
    main()
