<div align="center">

# ✍️ Escriba

**N’importe quel document en Markdown propre et anonymisé — prêt pour les LLM.**

Une application web auto‑hébergeable basée sur [Microsoft MarkItDown](https://github.com/microsoft/markitdown).

[![License: MIT](https://img.shields.io/badge/License-MIT-e07f5c.svg)](../../LICENSE)
[![Image Docker](https://img.shields.io/badge/image-ghcr.io%2Fdiegoparras%2Fescriba-2496ED?logo=docker&logoColor=white)](https://github.com/diegoparras/escriba/pkgs/container/escriba)
[![UI : 7 langues](https://img.shields.io/badge/UI-7%20langues-f0a98c.svg)](#-internationalisation)
![Auto-hébergé](https://img.shields.io/badge/auto--hébergé-✓-30d158.svg)

<img src="../../assets/demo.gif" alt="Démonstration d’Escriba" width="840">

📖 **Manuel complet (PDF) :** [`docs/Escriba-Manual.fr.pdf`](../Escriba-Manual.fr.pdf)

[English](../../README.md) · [Español](README.es.md) · **Français** · [Português](README.pt.md) · [Italiano](README.it.md) · [中文](README.zh.md) · [日本語](README.ja.md)

</div>

---

## ✨ Fonctionnalités

- 📄 **Documents** — PDF, Word, Excel, PowerPoint, HTML, CSV, EPUB, ZIP et plus.
- 🖼️ **Images** — OCR automatique (Tesseract) ; description par IA en option.
- 🎙️🎬 **Audio et vidéo** — transcription locale et hors ligne avec Whisper (mp3, wav, mp4, mov, mkv…).
- 🔗 **URL et YouTube** — convertit une page web ou récupère la transcription d’une vidéo YouTube.
- 🔍 **OCR intelligent** — le texte des images est reconnu automatiquement ; les PDF scannés **et pivotés** sont détectés, traités par OCR et redressés à la volée.
- 🤖 **IA en option** — OpenAI, Google Gemini (AI Studio) ou OpenRouter, avec un réglage par défaut **« Sans IA »**. Les modèles sont listés automatiquement.
- 🛡️ **Anonymisation des PII pour LLM** — moteur de confidentialité local complet : modèle NER ([OpenAI Privacy Filter](https://github.com/openai/privacy-filter)) + champs de factures par mise en page + détecteurs validés (carte **Luhn**, **IBAN**) + vos propres règles **RE2**. Cinq modes de sortie : *typé*, *anonyme*, **pseudonymisation réversible** («PERSONA_1» → envoyez au LLM → ré-hydratez localement), **masquage partiel** (••••-3456) et **hash stable** (même donnée → même pseudonyme d’un document à l’autre).
- ⬛ **Caviardage visuel** — téléchargez votre PDF ou image scannée avec les PII **noircies sur la page**. Caviardage réel : le texte et les pixels en dessous sont supprimés du fichier, pas recouverts.
- 🌍 **7 langues d’interface** — English, Español, Français, Português, Italiano, 中文, 日本語 (détectées automatiquement, changeables).
- 👑😇👤 **Trois niveaux d’accès** — DIOS / ANGEL / HUMANO, chacun avec son mot de passe et ses limites.
- 🔒 **Privé par conception** — les fichiers envoyés sont supprimés juste après la conversion ; rien n’est stocké.
- 🛡️ **Renforcé** — anti‑SSRF, nettoyage XSS, limitation de débit par rôle, conteneur sans root, en‑têtes de sécurité.
- 🐳 **Une seule image autonome** — ffmpeg, OCR, Whisper et Redis inclus. Aucun service supplémentaire requis.

---

## 🚀 Démarrage rapide

Téléchargez l’image préconstruite et lancez‑la en une commande :

```bash
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e GOD_PASSWORD="à-changer" \
  ghcr.io/diegoparras/escriba:latest
```

Ouvrez **http://localhost:8000** et connectez‑vous avec le `GOD_PASSWORD` défini.

> L’image embarque tout (ffmpeg, Tesseract OCR, Whisper, Redis intégré). Aucun service supplémentaire n’est nécessaire.

---

## 🛳️ Déploiement

Choisissez votre plateforme. Tout fonctionne à partir de l’image ci‑dessus.

> Avant de commencer, copiez `.env.example` vers `.env` et définissez vos secrets
> (`SECRET_KEY`, `GOD_PASSWORD`, …). Générez des clés avec `openssl rand -hex 32`.

<details open>
<summary><b>EasyPanel</b></summary>

1. **Project → + Service → App**, puis dans **Source → Docker Image** mettez `ghcr.io/diegoparras/escriba:latest`.
2. Ajoutez vos **variables d’environnement** (voir [Configuration](#-configuration)).
3. Dans **Domains**, définissez **Container Port `8000`**, ajoutez votre domaine et activez HTTPS.
4. **Deploy.**
</details>

<details>
<summary><b>Docker Compose</b></summary>

```bash
git clone https://github.com/diegoparras/escriba.git
cd escriba
cp .env.example .env          # définissez vos secrets
docker compose up -d --build
```
</details>

<details>
<summary><b>Portainer</b></summary>

**Stacks → Add stack → Repository** avec
`https://github.com/diegoparras/escriba` et le chemin de compose `docker-compose.yml`
(ou collez le `docker-compose.yml` dans l’éditeur web). Définissez les variables
d’environnement et déployez ; l’app écoute sur le port `8000`.
</details>

<details>
<summary><b>Dokploy</b></summary>

**Create Application → GitHub** (dépôt `diegoparras/escriba`) avec **Build Type :
Dockerfile**, ajoutez vos variables d’environnement, définissez le domaine sur
**Container Port `8000`** avec HTTPS, puis déployez.
</details>

<details>
<summary><b>Docker simple / proxy inverse</b></summary>

```bash
docker build -t escriba .
docker run -d --name escriba --restart unless-stopped -p 8000:8000 \
  -e SECRET_KEY="$(openssl rand -hex 32)" -e GOD_PASSWORD="à-changer" escriba
```

Pour le TLS, placez un proxy inverse devant. Exemple de `Caddyfile` (HTTPS automatique) :

```caddy
exemple.com {
    reverse_proxy localhost:8000
}
```

Avec Nginx, redirigez vers `localhost:8000` et augmentez `client_max_body_size` pour les gros envois.
</details>

---

## ⚙️ Configuration

Tous les réglages sont des variables d’environnement. Minimum recommandé :

```env
SECRET_KEY=<openssl rand -hex 32>   # requis en production (sinon les sessions sont réinitialisées)
GOD_PASSWORD=<un mot de passe fort>
ANGEL_PASSWORD=<optionnel>
HUMAN_PASSWORD=<optionnel>
```

Si aucun mot de passe n’est défini, un `GOD_PASSWORD` aléatoire est généré au démarrage
et affiché dans les **logs** du conteneur.

| Variable | Défaut | Description |
|---|---|---|
| `SECRET_KEY` | *(aléatoire)* | Clé de signature des sessions. **À définir** en production. |
| `GOD_PASSWORD` / `ANGEL_PASSWORD` / `HUMAN_PASSWORD` | — | Mot de passe de chaque niveau d’accès. |
| `HUMAN_OPEN` | `false` | Autorise le niveau HUMANO sans connexion (convertisseur public). |
| `WEB_CONCURRENCY` | `auto` | Workers parallèles. `auto` = nombre de cœurs CPU. |
| `MAX_UPLOAD_MB` | `100` | Limite absolue d’envoi (sauf DIOS). |
| `WHISPER_MODEL` | `base` | Modèle de transcription : `tiny` · `base` · `small` · `medium` · `large-v3`. |
| `MAX_MEDIA_MINUTES` | `120` | Durée max d’audio/vidéo à transcrire (`0` = illimité ; DIOS sans limite). |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `GOOGLE_API_KEY` | — | Clés IA côté serveur (utilisées si l’utilisateur n’en fournit pas). DIOS et ANGEL uniquement. |
| `API_TOKEN` / `API_TOKEN_ROLE` | — / `angel` | Jeton statique pour l’automatisation (n8n, scripts) et le rôle associé. |
| `EMBEDDED_REDIS` | `true` | Redis intégré pour la limitation de débit partagée. `false` + `REDIS_URL` pour un externe. |
| `ENABLE_DOCS` | `false` | Exposer Swagger sur `/api/docs`. |
| `PORT` | `8000` | Port du conteneur. |

Les limites par niveau (`*_MAX_MB`, `*_MAX_BATCH`, `*_RATE`) et les presets sont documentés dans
[`.env.example`](../../.env.example).

**Performance :** par défaut l’app lance un worker par cœur CPU, donc elle s’adapte à
n’importe quel hôte (VPS 1 cœur → 1 worker ; serveur 24 threads → 24). Chaque worker utilise
~250 Mo de RAM ; définissez `WEB_CONCURRENCY` avec un nombre fixe pour le plafonner.

---

## 🔐 Rôles et niveaux d’accès

La connexion est requise. Chaque niveau a son propre mot de passe et ses limites.

| Capacité | 👤 HUMANO | 😇 ANGEL | 👑 DIOS |
|---|:---:|:---:|:---:|
| Envoyer et convertir des fichiers | ✓ | ✓ | ✓ |
| Convertir depuis une URL publique | — | ✓ (anti‑SSRF) | ✓ |
| URL interne / `file://` / chemin local | — | — | ✓ |
| Audio / vidéo / ZIP | — | ✓ | ✓ |
| Transcriptions YouTube | ✓ | ✓ | ✓ |
| OCR (forcé / automatique) | — | ✓ | ✓ |
| Utiliser les clés IA du serveur | — | ✓ | ✓ |
| Taille max de fichier | 25 Mo | 100 Mo | illimité |
| Fichiers par lot | 3 | 10 | illimité |
| Statistiques serveur (CPU/RAM) | — | partiel | complet |
| Limite de débit (req/min) | 15 | 60 | illimité |

Toutes les limites sont configurables via des variables d’environnement.

**Points de sécurité :** l’accès aux fichiers locaux et le SSRF sont réservés à DIOS ;
la récupération d’URL bloque les IP internes et les redirections ; les envois sont plafonnés
par streaming ; l’aperçu est nettoyé avec DOMPurify ; CSP et en‑têtes de sécurité sont appliqués ;
le conteneur s’exécute en utilisateur non‑root avec `no-new-privileges` ; la limitation de débit
est partagée entre workers via le Redis intégré.

---

## 🔌 API

Utile pour l’automatisation (n8n, scripts). Authentification requise.

**Avec un jeton d’API** (définissez `API_TOKEN`) :

```bash
curl -H "X-API-Key: VOTRE_JETON" \
     -F "file=@document.pdf" \
     https://votre-domaine/api/convert
# Forcer l’OCR / la langue :  -F "ocr=true"  -F "lang=fr-FR"
```

**Avec un cookie de session :**

```bash
curl -c cookies.txt -F "password=$GOD_PASSWORD" https://votre-domaine/api/login
curl -b cookies.txt -F "file=@document.pdf"     https://votre-domaine/api/convert
```

`POST /api/convert` (multipart/form-data) : `file` *ou* `url`, plus les options `lang`,
`ocr`, `llm_provider`, `llm_api_key`, `llm_model`. Réponse :

```json
{ "source": "…", "title": "…", "markdown": "…",
  "words": 1234, "chars": 5678, "elapsed_ms": 87,
  "pdf_type": "scanné", "ocr_applied": true, "note": null }
```

`POST /api/redact` (multipart/form-data) : `file` (PDF ou image), options `lang`, `anon_strict`, `anon_detectors`, `anon_rules`. Renvoie le **PDF caviardé** (binaire) avec l’en-tête `X-Redacted-Entities`.

---

## 🌍 Internationalisation

L’interface est disponible en **7 langues** — English, Español, Français, Português,
Italiano, 中文 et 日本語. La langue est détectée automatiquement depuis le navigateur et peut
être changée à tout moment depuis le panneau ⚙️ ; le choix est mémorisé par navigateur.

---

## 💻 Développement local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> L’OCR et la transcription nécessitent `ffmpeg`, `tesseract-ocr` et `ocrmypdf` installés sur
> le système (l’image Docker les inclut déjà). Les autres formats fonctionnent sans eux.

---

## 📜 Crédits et licence

**Escriba** — développé par **Diego Parrás**
CeMIACE · SEUBES · FCE‑UBA (Facultad de Ciencias Económicas, Universidad de Buenos Aires).

Construit sur [Microsoft MarkItDown](https://github.com/microsoft/markitdown),
[FastAPI](https://fastapi.tiangolo.com/),
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract),
[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) et
[faster‑whisper](https://github.com/SYSTRAN/faster-whisper).
Sous [Licence MIT](../../LICENSE).
