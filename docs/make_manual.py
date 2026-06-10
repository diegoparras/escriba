# -*- coding: utf-8 -*-
"""Generates the Escriba manual as a PDF in 7 languages (reportlab).

Output: docs/Escriba-Manual.pdf (English, default) + Escriba-Manual.<lang>.pdf
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    Preformatted, HRFlowable, ListFlowable, ListItem,
)

HERE = os.path.dirname(__file__)
CORAL = HexColor("#e07f5c"); CORAL_D = HexColor("#c2613e")
INK = HexColor("#2a1b14"); MUTED = HexColor("#6e6157")
CODEBG = HexColor("#f5efe9"); LINE = HexColor("#e3d8cd")


def reg_ttf(name, candidates, subfont=0):
    """Registra una fuente TTF/TTC embebible. Devuelve True si lo logró."""
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path, subfontIndex=subfont))
                return True
            except Exception:
                continue
    return False


WIN = r"C:\Windows\Fonts"
NOTO = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]
zh_ok = reg_ttf("ZH", [os.path.join(WIN, "msyh.ttc"), os.path.join(WIN, "simsun.ttc")] + NOTO)
zhb_ok = reg_ttf("ZHb", [os.path.join(WIN, "msyhbd.ttc"), os.path.join(WIN, "msyh.ttc")] + NOTO)
ja_ok = reg_ttf("JA", [os.path.join(WIN, "YuGothR.ttc"), os.path.join(WIN, "msgothic.ttc")] + NOTO)
jab_ok = reg_ttf("JAb", [os.path.join(WIN, "YuGothB.ttc"), os.path.join(WIN, "YuGothR.ttc")] + NOTO)

# Fallback (no embebido) si no hay TTF CJK disponible.
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

ZH = ("ZH", "ZHb" if zhb_ok else "ZH") if zh_ok else ("STSong-Light", "STSong-Light")
JA = ("JA", "JAb" if jab_ok else "JA") if ja_ok else ("HeiseiKakuGo-W5", "HeiseiKakuGo-W5")

# (regular, bold) font per language.
FONTS = {
    "en": ("Helvetica", "Helvetica-Bold"), "es": ("Helvetica", "Helvetica-Bold"),
    "fr": ("Helvetica", "Helvetica-Bold"), "pt": ("Helvetica", "Helvetica-Bold"),
    "it": ("Helvetica", "Helvetica-Bold"), "zh": ZH, "ja": JA,
}
OUT = {"en": "Escriba-Manual.pdf"}
for L in ("es", "fr", "pt", "it", "zh", "ja"):
    OUT[L] = "Escriba-Manual.%s.pdf" % L

# Shared, language-independent code blocks.
CODE_RUN = ("docker run -d --name escriba -p 8000:8000 \\\n"
            "  -e SECRET_KEY=\"<long-random-key>\" \\\n"
            "  -e GOD_PASSWORD=\"<your-password>\" \\\n"
            "  ghcr.io/diegoparras/escriba:latest")
CODE_COMPOSE = ("git clone https://github.com/diegoparras/escriba.git\n"
                "cd escriba\ncp .env.example .env\ndocker compose up -d --build")
CODE_TOKEN = ("curl -H \"X-API-Key: YOUR_TOKEN\" \\\n"
              "     -F \"file=@document.pdf\" \\\n"
              "     https://your-domain/api/convert")

# ----------------------------------------------------------------------------
# Translations.  Lists are rendered as bullet lists; "|" splits table cells.
# ----------------------------------------------------------------------------
TR = {
    "en": {
        "sub1": "Clean, anonymized Markdown for LLMs", "sub2": "Complete manual — users & administrators",
        "byline": "Developed by Diego Parrás · CeMIACE · SEUBES · FCE-UBA",
        "p1": "Part 1 — For users",
        "whatis_h": "What is Escriba?",
        "whatis": "Escriba converts almost any file into clean Markdown — plain text with formatting, ready to copy, save or feed to an AI. It handles documents, spreadsheets, slides, images, audio, video and YouTube.",
        "howto_h": "Getting started",
        "howto": ["Enter the password and sign in (your level: HUMANO, ANGEL or DIOS).",
                  "Drag files onto the centre area, or click “Select files”.",
                  "Click “Convert all”. A progress bar appears.",
                  "Open the result and use Preview / Markdown / Split. Copy it or download the .md (or a .zip for several files)."],
        "more_h": "Key features",
        "more": ["Audio & video are transcribed locally with Whisper; pick the language under Advanced options.",
                 "Paste a YouTube link to get its transcript.",
                 "Text in images is OCR’d automatically; scanned PDFs are detected, OCR’d and auto-rotated on the fly.",
                 "AI is optional (OpenAI, Gemini, OpenRouter) and defaults to “No AI”. Models are listed automatically.",
                 "PII anonymization for LLMs: a local engine (NER + invoice layout + validated detectors + your own rules) with five output modes — typed, anonymous, reversible pseudonymization (token → send to the LLM → re-hydrate), partial masking (••••-3456) and stable hashing (same data → same pseudonym across documents).",
                 "Visual redaction: download your PDF or scanned image with the PII blacked out on the page — true redaction: the text and the pixels underneath are removed from the file.",
                 "Queue: convert everything or only the selected files.",
                 "Light/dark theme and an interface available in 7 languages."],
        "p2": "Part 2 — Roles & access levels",
        "p2_intro": "Login is required. Each level has its own password and limits, all configurable via environment variables.",
        "roles": [
            "Capability|HUMANO|ANGEL|DIOS",
            "Upload & convert files|Yes|Yes|Yes",
            "Convert from a public URL|No|Yes|Yes",
            "Internal URL / local path|No|No|Yes",
            "Audio / video / ZIP|No|Yes|Yes",
            "YouTube transcripts|Yes|Yes|Yes",
            "OCR (forced / automatic)|No|Yes|Yes",
            "Use server AI keys|No|Yes|Yes",
            "Max file size|25 MB|100 MB|unlimited",
            "Files per batch|3|10|unlimited",
            "Rate limit (req/min)|15|60|unlimited",
        ],
        "p3": "Part 3 — For administrators",
        "arch_h": "Architecture",
        "arch": "Escriba runs in a single, self-contained Docker container that bundles FastAPI + MarkItDown, ffmpeg, Tesseract + OCRmyPDF, faster-whisper and an embedded Redis. It runs as a non-root user with a healthcheck and automatic CPU-core detection.",
        "deploy_h": "Deployment",
        "deploy_run": "Run the prebuilt image (no build needed):",
        "deploy_compose": "Or with Docker Compose:",
        "deploy_easy": "EasyPanel/Portainer/Dokploy: create an App from the Docker image ghcr.io/diegoparras/escriba:latest, add the environment variables, map the domain to container port 8000 with HTTPS, and deploy.",
        "env_h": "Environment variables",
        "env": [
            "Variable|Default|Description",
            "SECRET_KEY|random|Session signing key. Set it in production.",
            "GOD/ANGEL/HUMAN_PASSWORD|—|Password for each access level.",
            "HUMAN_OPEN|false|Allow the HUMANO level without login.",
            "WEB_CONCURRENCY|auto|Parallel workers (auto = CPU cores).",
            "MAX_UPLOAD_MB|100|Maximum upload size (except DIOS).",
            "WHISPER_MODEL|base|Transcription model (tiny … large-v3).",
            "MAX_MEDIA_MINUTES|120|Audio/video length cap (0 = unlimited).",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|Server-side AI keys (fallback).",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|Token for automation and its role.",
            "EMBEDDED_REDIS|true|Embedded Redis for shared rate limiting.",
            "ENABLE_DOCS|false|Expose Swagger at /api/docs.",
        ],
        "aikeys_h": "Server-side AI keys",
        "aikeys": ["If set, users don’t need to paste their own key. Only DIOS and ANGEL use them.",
                   "The cost is on you and is shared. Leave them empty so each user brings their own.",
                   "A user-supplied key always takes priority over the server key."],
        "whisper_h": "Transcription (Whisper)",
        "whisper": ["Set the model with WHISPER_MODEL (larger = more accurate, slower).",
                    "It runs on CPU. MAX_MEDIA_MINUTES caps the duration (DIOS has no cap)."],
        "token_h": "API token (automation)",
        "token": "For n8n or scripts, set API_TOKEN and send it as a header:",
        "sec_h": "Security",
        "sec": ["Authentication required; three roles with distinct permissions.",
                "Anti-SSRF (internal IPs/redirects blocked); local paths only for DIOS.",
                "XSS sanitization (DOMPurify) and security headers (CSP).",
                "Non-root container with no-new-privileges; OCR/Whisper run without a shell.",
                "Per-role rate limiting; the API key is never stored on the server."],
        "priv_h": "Privacy",
        "priv": "Uploaded files are processed in a temporary file and deleted as soon as the conversion finishes (success or error). There is no database and no uploads folder; the result is only sent to your browser.",
        "p4": "Part 4 — API reference",
        "api": [
            "Endpoint|Method|Description",
            "/api/login|POST|Log in; sets a session cookie.",
            "/api/me|GET|Current role and capabilities.",
            "/api/convert|POST|Convert a file or URL to Markdown.",
            "/api/models|POST|List the provider’s models.",
            "/api/stats|GET|Server stats (by role).",
        ],
        "api_fields": "POST /api/convert (multipart/form-data): file or url, plus optional lang, ocr, llm_provider, llm_api_key, llm_model.",
        "p5": "Part 5 — Troubleshooting",
        "faq": ["A long video won’t transcribe: it may exceed MAX_MEDIA_MINUTES — raise the cap or use DIOS.",
                "A YouTube video fails: it may have no captions, or YouTube blocks your server IP — paste your YouTube cookies in Settings, or set YT_PROXY/YT_COOKIES.",
                "Error 413 on upload: raise MAX_UPLOAD_MB and your reverse proxy’s body limit.",
                "A PDF came out empty: it was scanned without OCR for your role — use ANGEL/DIOS or tick “Force OCR”.",
                "Forgot the DIOS password: if unset, a random one is printed in the container logs at startup."],
        "footer": "Escriba — by Diego Parrás · CeMIACE · SEUBES · FCE-UBA · MIT License",
    },
    "es": {
        "sub1": "Markdown limpio y anónimo para LLMs", "sub2": "Manual completo — usuarios y administradores",
        "byline": "Desarrollado por Diego Parrás · CeMIACE · SEUBES · FCE-UBA",
        "p1": "Parte 1 — Para usuarios",
        "whatis_h": "¿Qué es Escriba?",
        "whatis": "Escriba convierte casi cualquier archivo a Markdown limpio —texto plano con formato, listo para copiar, guardar o pasar a una IA. Maneja documentos, hojas de cálculo, presentaciones, imágenes, audio, video y YouTube.",
        "howto_h": "Primeros pasos",
        "howto": ["Introduce la contraseña e inicia sesión (tu nivel: HUMANO, ANGEL o DIOS).",
                  "Arrastra archivos a la zona central, o haz clic en «Seleccionar archivos».",
                  "Haz clic en «Convertir todo». Aparece una barra de progreso.",
                  "Abre el resultado y usa Vista previa / Markdown / Dividido. Cópialo o descarga el .md (o un .zip para varios archivos)."],
        "more_h": "Funciones principales",
        "more": ["El audio y el video se transcriben localmente con Whisper; elige el idioma en Opciones avanzadas.",
                 "Pega un enlace de YouTube para obtener su transcripción.",
                 "El texto de las imágenes se procesa con OCR automáticamente; los PDF escaneados se detectan, procesan y enderezan al vuelo.",
                 "La IA es opcional (OpenAI, Gemini, OpenRouter) y por defecto está en «Sin IA». Los modelos se listan automáticamente.",
                 "Anonimización de PII para LLMs: motor local (NER + layout de facturas + detectores validados + reglas propias) con cinco modos de salida: tipado, anónimo, seudonimizado reversible (token → al LLM → re-hidratas), enmascarado parcial (••••-3456) y hash estable (mismo dato → mismo seudónimo entre documentos).",
                 "Censura visual: descarga tu PDF o imagen escaneada con el PII tachado sobre la página — redacción real: el texto y los píxeles de abajo se eliminan del archivo.",
                 "Cola: convierte todo o solo los archivos seleccionados.",
                 "Tema claro/oscuro e interfaz disponible en 7 idiomas."],
        "p2": "Parte 2 — Roles y niveles de acceso",
        "p2_intro": "Es obligatorio iniciar sesión. Cada nivel tiene su propia contraseña y límites, todos configurables por variables de entorno.",
        "roles": [
            "Capacidad|HUMANO|ANGEL|DIOS",
            "Subir y convertir archivos|Sí|Sí|Sí",
            "Convertir desde URL pública|No|Sí|Sí",
            "URL interna / ruta local|No|No|Sí",
            "Audio / video / ZIP|No|Sí|Sí",
            "Transcripciones de YouTube|Sí|Sí|Sí",
            "OCR (forzado / automático)|No|Sí|Sí",
            "Usar claves de IA del servidor|No|Sí|Sí",
            "Tamaño máx. de archivo|25 MB|100 MB|sin límite",
            "Archivos por lote|3|10|sin límite",
            "Límite de peticiones (req/min)|15|60|sin límite",
        ],
        "p3": "Parte 3 — Para administradores",
        "arch_h": "Arquitectura",
        "arch": "Escriba corre en un único contenedor Docker autosuficiente que incluye FastAPI + MarkItDown, ffmpeg, Tesseract + OCRmyPDF, faster-whisper y un Redis embebido. Se ejecuta como usuario sin privilegios, con healthcheck y detección automática de núcleos.",
        "deploy_h": "Despliegue",
        "deploy_run": "Ejecuta la imagen ya construida (sin compilar):",
        "deploy_compose": "O con Docker Compose:",
        "deploy_easy": "EasyPanel/Portainer/Dokploy: crea una App a partir de la imagen Docker ghcr.io/diegoparras/escriba:latest, agrega las variables de entorno, apunta el dominio al puerto 8000 del contenedor con HTTPS y despliega.",
        "env_h": "Variables de entorno",
        "env": [
            "Variable|Por defecto|Descripción",
            "SECRET_KEY|aleatoria|Clave de firma de sesiones. Defínela en producción.",
            "GOD/ANGEL/HUMAN_PASSWORD|—|Contraseña de cada nivel de acceso.",
            "HUMAN_OPEN|false|Permite el nivel HUMANO sin login.",
            "WEB_CONCURRENCY|auto|Workers paralelos (auto = núcleos de CPU).",
            "MAX_UPLOAD_MB|100|Tamaño máximo de subida (excepto DIOS).",
            "WHISPER_MODEL|base|Modelo de transcripción (tiny … large-v3).",
            "MAX_MEDIA_MINUTES|120|Tope de duración audio/video (0 = sin límite).",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|Claves de IA del servidor (fallback).",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|Token para automatización y su rol.",
            "EMBEDDED_REDIS|true|Redis embebido para el límite compartido.",
            "ENABLE_DOCS|false|Exponer Swagger en /api/docs.",
        ],
        "aikeys_h": "Claves de IA del servidor",
        "aikeys": ["Si las defines, los usuarios no necesitan pegar la suya. Solo las usan DIOS y ANGEL.",
                   "El costo es tuyo y compartido. Déjalas vacías para que cada uno use la propia.",
                   "La clave que pega el usuario siempre tiene prioridad sobre la del servidor."],
        "whisper_h": "Transcripción (Whisper)",
        "whisper": ["Define el modelo con WHISPER_MODEL (mayor = más preciso, más lento).",
                    "Corre en CPU. MAX_MEDIA_MINUTES limita la duración (DIOS sin tope)."],
        "token_h": "Token de API (automatización)",
        "token": "Para n8n o scripts, define API_TOKEN y envíalo como cabecera:",
        "sec_h": "Seguridad",
        "sec": ["Autenticación obligatoria; tres roles con permisos distintos.",
                "Anti-SSRF (IPs internas/redirecciones bloqueadas); rutas locales solo para DIOS.",
                "Sanitización XSS (DOMPurify) y cabeceras de seguridad (CSP).",
                "Contenedor sin root con no-new-privileges; OCR/Whisper sin shell.",
                "Límite de peticiones por rol; la API key nunca se almacena en el servidor."],
        "priv_h": "Privacidad",
        "priv": "Los archivos subidos se procesan en un temporal y se eliminan en cuanto termina la conversión (con éxito o error). No hay base de datos ni carpeta de subidas; el resultado solo se envía a tu navegador.",
        "p4": "Parte 4 — Referencia de API",
        "api": [
            "Endpoint|Método|Descripción",
            "/api/login|POST|Inicia sesión; define una cookie.",
            "/api/me|GET|Rol actual y capacidades.",
            "/api/convert|POST|Convierte un archivo o URL a Markdown.",
            "/api/models|POST|Lista los modelos del proveedor.",
            "/api/stats|GET|Estadísticas del servidor (por rol).",
        ],
        "api_fields": "POST /api/convert (multipart/form-data): file o url, más los opcionales lang, ocr, llm_provider, llm_api_key, llm_model.",
        "p5": "Parte 5 — Problemas frecuentes",
        "faq": ["Un video largo no se transcribe: puede superar MAX_MEDIA_MINUTES — sube el tope o usa DIOS.",
                "Un video de YouTube falla: puede no tener subtítulos, o YouTube bloquea la IP del servidor — pega tus cookies de YouTube en Configuración, o define YT_PROXY/YT_COOKIES.",
                "Error 413 al subir: sube MAX_UPLOAD_MB y el límite de body del proxy inverso.",
                "Un PDF salió vacío: estaba escaneado sin OCR para tu rol — usa ANGEL/DIOS o marca «Forzar OCR».",
                "Olvidaste la contraseña de DIOS: si no la definiste, aparece una aleatoria en los logs al arrancar."],
        "footer": "Escriba — por Diego Parrás · CeMIACE · SEUBES · FCE-UBA · Licencia MIT",
    },
    "fr": {
        "sub1": "Markdown propre et anonymisé pour les LLM", "sub2": "Manuel complet — utilisateurs et administrateurs",
        "byline": "Développé par Diego Parrás · CeMIACE · SEUBES · FCE-UBA",
        "p1": "Partie 1 — Pour les utilisateurs",
        "whatis_h": "Qu’est-ce qu’Escriba ?",
        "whatis": "Escriba convertit presque n’importe quel fichier en Markdown propre — du texte mis en forme, prêt à copier, enregistrer ou transmettre à une IA. Il gère documents, tableurs, présentations, images, audio, vidéo et YouTube.",
        "howto_h": "Premiers pas",
        "howto": ["Saisissez le mot de passe et connectez-vous (votre niveau : HUMANO, ANGEL ou DIOS).",
                  "Glissez des fichiers sur la zone centrale, ou cliquez sur « Sélectionner des fichiers ».",
                  "Cliquez sur « Tout convertir ». Une barre de progression apparaît.",
                  "Ouvrez le résultat et utilisez Aperçu / Markdown / Divisé. Copiez-le ou téléchargez le .md (ou un .zip pour plusieurs fichiers)."],
        "more_h": "Fonctionnalités clés",
        "more": ["L’audio et la vidéo sont transcrits en local avec Whisper ; choisissez la langue dans les options avancées.",
                 "Collez un lien YouTube pour obtenir sa transcription.",
                 "Le texte des images est traité par OCR automatiquement ; les PDF scannés sont détectés, traités et redressés à la volée.",
                 "L’IA est optionnelle (OpenAI, Gemini, OpenRouter) et par défaut sur « Sans IA ». Les modèles sont listés automatiquement.",
                 "Anonymisation des PII pour LLM : moteur local (NER + structure des factures + détecteurs validés + vos règles) avec cinq modes de sortie — typé, anonyme, pseudonymisation réversible (jeton → au LLM → ré-hydratation), masquage partiel (••••-3456) et hash stable (même donnée → même pseudonyme entre documents).",
                 "Caviardage visuel : téléchargez votre PDF ou image scannée avec les PII noircies sur la page — caviardage réel : le texte et les pixels en dessous sont supprimés du fichier.",
                 "File d’attente : convertissez tout ou seulement les fichiers sélectionnés.",
                 "Thème clair/sombre et interface disponible en 7 langues."],
        "p2": "Partie 2 — Rôles et niveaux d’accès",
        "p2_intro": "La connexion est requise. Chaque niveau a son propre mot de passe et ses limites, tous configurables par variables d’environnement.",
        "roles": [
            "Capacité|HUMANO|ANGEL|DIOS",
            "Envoyer et convertir des fichiers|Oui|Oui|Oui",
            "Convertir depuis une URL publique|Non|Oui|Oui",
            "URL interne / chemin local|Non|Non|Oui",
            "Audio / vidéo / ZIP|Non|Oui|Oui",
            "Transcriptions YouTube|Oui|Oui|Oui",
            "OCR (forcé / automatique)|Non|Oui|Oui",
            "Utiliser les clés IA du serveur|Non|Oui|Oui",
            "Taille max de fichier|25 Mo|100 Mo|illimité",
            "Fichiers par lot|3|10|illimité",
            "Limite de débit (req/min)|15|60|illimité",
        ],
        "p3": "Partie 3 — Pour les administrateurs",
        "arch_h": "Architecture",
        "arch": "Escriba s’exécute dans un unique conteneur Docker autonome qui embarque FastAPI + MarkItDown, ffmpeg, Tesseract + OCRmyPDF, faster-whisper et un Redis intégré. Il tourne en utilisateur non-root, avec healthcheck et détection automatique des cœurs.",
        "deploy_h": "Déploiement",
        "deploy_run": "Lancez l’image préconstruite (sans build) :",
        "deploy_compose": "Ou avec Docker Compose :",
        "deploy_easy": "EasyPanel/Portainer/Dokploy : créez une App à partir de l’image Docker ghcr.io/diegoparras/escriba:latest, ajoutez les variables d’environnement, dirigez le domaine vers le port 8000 du conteneur avec HTTPS, puis déployez.",
        "env_h": "Variables d’environnement",
        "env": [
            "Variable|Défaut|Description",
            "SECRET_KEY|aléatoire|Clé de signature des sessions. À définir en production.",
            "GOD/ANGEL/HUMAN_PASSWORD|—|Mot de passe de chaque niveau d’accès.",
            "HUMAN_OPEN|false|Autorise le niveau HUMANO sans connexion.",
            "WEB_CONCURRENCY|auto|Workers parallèles (auto = cœurs CPU).",
            "MAX_UPLOAD_MB|100|Taille max d’envoi (sauf DIOS).",
            "WHISPER_MODEL|base|Modèle de transcription (tiny … large-v3).",
            "MAX_MEDIA_MINUTES|120|Durée max audio/vidéo (0 = illimité).",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|Clés IA côté serveur (repli).",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|Jeton pour l’automatisation et son rôle.",
            "EMBEDDED_REDIS|true|Redis intégré pour la limitation partagée.",
            "ENABLE_DOCS|false|Exposer Swagger sur /api/docs.",
        ],
        "aikeys_h": "Clés IA côté serveur",
        "aikeys": ["Si définies, les utilisateurs n’ont pas besoin de coller la leur. Seuls DIOS et ANGEL les utilisent.",
                   "Le coût est pour vous et partagé. Laissez-les vides pour que chacun apporte la sienne.",
                   "Une clé fournie par l’utilisateur a toujours priorité sur celle du serveur."],
        "whisper_h": "Transcription (Whisper)",
        "whisper": ["Définissez le modèle avec WHISPER_MODEL (plus grand = plus précis, plus lent).",
                    "Il tourne sur CPU. MAX_MEDIA_MINUTES plafonne la durée (DIOS sans limite)."],
        "token_h": "Jeton d’API (automatisation)",
        "token": "Pour n8n ou des scripts, définissez API_TOKEN et envoyez-le en en-tête :",
        "sec_h": "Sécurité",
        "sec": ["Authentification requise ; trois rôles aux permissions distinctes.",
                "Anti-SSRF (IP internes/redirections bloquées) ; chemins locaux réservés à DIOS.",
                "Nettoyage XSS (DOMPurify) et en-têtes de sécurité (CSP).",
                "Conteneur non-root avec no-new-privileges ; OCR/Whisper sans shell.",
                "Limitation de débit par rôle ; la clé API n’est jamais stockée sur le serveur."],
        "priv_h": "Confidentialité",
        "priv": "Les fichiers envoyés sont traités dans un fichier temporaire et supprimés dès la fin de la conversion (succès ou erreur). Aucune base de données ni dossier d’envois ; le résultat n’est transmis qu’à votre navigateur.",
        "p4": "Partie 4 — Référence de l’API",
        "api": [
            "Endpoint|Méthode|Description",
            "/api/login|POST|Connexion ; définit un cookie de session.",
            "/api/me|GET|Rôle actuel et capacités.",
            "/api/convert|POST|Convertit un fichier ou une URL en Markdown.",
            "/api/models|POST|Liste les modèles du fournisseur.",
            "/api/stats|GET|Statistiques serveur (par rôle).",
        ],
        "api_fields": "POST /api/convert (multipart/form-data) : file ou url, plus les options lang, ocr, llm_provider, llm_api_key, llm_model.",
        "p5": "Partie 5 — Dépannage",
        "faq": ["Une longue vidéo ne se transcrit pas : elle dépasse peut-être MAX_MEDIA_MINUTES — augmentez la limite ou utilisez DIOS.",
                "Une vidéo YouTube échoue : pas de sous-titres, ou YouTube bloque l’IP du serveur — collez vos cookies YouTube dans les Paramètres, ou définissez YT_PROXY/YT_COOKIES.",
                "Erreur 413 à l’envoi : augmentez MAX_UPLOAD_MB et la limite de body de votre proxy.",
                "Un PDF est vide : il était scanné sans OCR pour votre rôle — utilisez ANGEL/DIOS ou cochez « Forcer l’OCR ».",
                "Mot de passe DIOS oublié : s’il n’est pas défini, un mot de passe aléatoire est affiché dans les logs au démarrage."],
        "footer": "Escriba — par Diego Parrás · CeMIACE · SEUBES · FCE-UBA · Licence MIT",
    },
    "pt": {
        "sub1": "Markdown limpo e anônimo para LLMs", "sub2": "Manual completo — usuários e administradores",
        "byline": "Desenvolvido por Diego Parrás · CeMIACE · SEUBES · FCE-UBA",
        "p1": "Parte 1 — Para usuários",
        "whatis_h": "O que é o Escriba?",
        "whatis": "O Escriba converte quase qualquer arquivo em Markdown limpo — texto com formatação, pronto para copiar, salvar ou enviar a uma IA. Lida com documentos, planilhas, slides, imagens, áudio, vídeo e YouTube.",
        "howto_h": "Primeiros passos",
        "howto": ["Digite a senha e entre (seu nível: HUMANO, ANGEL ou DIOS).",
                  "Arraste arquivos para a área central, ou clique em «Selecionar arquivos».",
                  "Clique em «Converter tudo». Aparece uma barra de progresso.",
                  "Abra o resultado e use Pré-visualização / Markdown / Dividido. Copie ou baixe o .md (ou um .zip para vários arquivos)."],
        "more_h": "Recursos principais",
        "more": ["Áudio e vídeo são transcritos localmente com Whisper; escolha o idioma nas opções avançadas.",
                 "Cole um link do YouTube para obter a transcrição.",
                 "O texto das imagens é processado por OCR automaticamente; PDFs digitalizados são detectados, processados e endireitados na hora.",
                 "A IA é opcional (OpenAI, Gemini, OpenRouter) e o padrão é «Sem IA». Os modelos são listados automaticamente.",
                 "Anonimização de PII para LLMs: motor local (NER + layout de faturas + detectores validados + regras próprias) com cinco modos de saída — tipado, anônimo, pseudonimização reversível (token → ao LLM → re-hidratar), mascaramento parcial (••••-3456) e hash estável (mesmo dado → mesmo pseudônimo entre documentos).",
                 "Censura visual: baixe seu PDF ou imagem digitalizada com os dados tachados na página — redação real: o texto e os pixels abaixo são removidos do arquivo.",
                 "Fila: converta tudo ou apenas os arquivos selecionados.",
                 "Tema claro/escuro e interface disponível em 7 idiomas."],
        "p2": "Parte 2 — Papéis e níveis de acesso",
        "p2_intro": "O login é obrigatório. Cada nível tem sua própria senha e limites, todos configuráveis por variáveis de ambiente.",
        "roles": [
            "Capacidade|HUMANO|ANGEL|DIOS",
            "Enviar e converter arquivos|Sim|Sim|Sim",
            "Converter de URL pública|Não|Sim|Sim",
            "URL interna / caminho local|Não|Não|Sim",
            "Áudio / vídeo / ZIP|Não|Sim|Sim",
            "Transcrições do YouTube|Sim|Sim|Sim",
            "OCR (forçado / automático)|Não|Sim|Sim",
            "Usar chaves de IA do servidor|Não|Sim|Sim",
            "Tamanho máx. de arquivo|25 MB|100 MB|ilimitado",
            "Arquivos por lote|3|10|ilimitado",
            "Limite de requisições (req/min)|15|60|ilimitado",
        ],
        "p3": "Parte 3 — Para administradores",
        "arch_h": "Arquitetura",
        "arch": "O Escriba roda em um único contêiner Docker autossuficiente que inclui FastAPI + MarkItDown, ffmpeg, Tesseract + OCRmyPDF, faster-whisper e um Redis embutido. Executa como usuário não-root, com healthcheck e detecção automática de núcleos.",
        "deploy_h": "Implantação",
        "deploy_run": "Execute a imagem pronta (sem build):",
        "deploy_compose": "Ou com Docker Compose:",
        "deploy_easy": "EasyPanel/Portainer/Dokploy: crie um App a partir da imagem Docker ghcr.io/diegoparras/escriba:latest, adicione as variáveis de ambiente, aponte o domínio para a porta 8000 do contêiner com HTTPS e implante.",
        "env_h": "Variáveis de ambiente",
        "env": [
            "Variável|Padrão|Descrição",
            "SECRET_KEY|aleatória|Chave de assinatura das sessões. Defina em produção.",
            "GOD/ANGEL/HUMAN_PASSWORD|—|Senha de cada nível de acesso.",
            "HUMAN_OPEN|false|Permite o nível HUMANO sem login.",
            "WEB_CONCURRENCY|auto|Workers paralelos (auto = núcleos da CPU).",
            "MAX_UPLOAD_MB|100|Tamanho máximo de upload (exceto DIOS).",
            "WHISPER_MODEL|base|Modelo de transcrição (tiny … large-v3).",
            "MAX_MEDIA_MINUTES|120|Limite de duração áudio/vídeo (0 = ilimitado).",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|Chaves de IA do servidor (fallback).",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|Token para automação e seu papel.",
            "EMBEDDED_REDIS|true|Redis embutido para o limite compartilhado.",
            "ENABLE_DOCS|false|Expor Swagger em /api/docs.",
        ],
        "aikeys_h": "Chaves de IA do servidor",
        "aikeys": ["Se definidas, os usuários não precisam colar a própria. Apenas DIOS e ANGEL as usam.",
                   "O custo é seu e compartilhado. Deixe-as vazias para cada um usar a própria.",
                   "Uma chave do usuário sempre tem prioridade sobre a do servidor."],
        "whisper_h": "Transcrição (Whisper)",
        "whisper": ["Defina o modelo com WHISPER_MODEL (maior = mais preciso, mais lento).",
                    "Roda na CPU. MAX_MEDIA_MINUTES limita a duração (DIOS sem limite)."],
        "token_h": "Token de API (automação)",
        "token": "Para n8n ou scripts, defina API_TOKEN e envie como cabeçalho:",
        "sec_h": "Segurança",
        "sec": ["Autenticação obrigatória; três papéis com permissões distintas.",
                "Anti-SSRF (IPs internos/redirecionamentos bloqueados); caminhos locais só para DIOS.",
                "Sanitização XSS (DOMPurify) e cabeçalhos de segurança (CSP).",
                "Contêiner não-root com no-new-privileges; OCR/Whisper sem shell.",
                "Limite de requisições por papel; a API key nunca é armazenada no servidor."],
        "priv_h": "Privacidade",
        "priv": "Os arquivos enviados são processados em um temporário e apagados assim que a conversão termina (sucesso ou erro). Não há banco de dados nem pasta de uploads; o resultado é enviado apenas ao seu navegador.",
        "p4": "Parte 4 — Referência da API",
        "api": [
            "Endpoint|Método|Descrição",
            "/api/login|POST|Login; define um cookie de sessão.",
            "/api/me|GET|Papel atual e capacidades.",
            "/api/convert|POST|Converte um arquivo ou URL em Markdown.",
            "/api/models|POST|Lista os modelos do provedor.",
            "/api/stats|GET|Estatísticas do servidor (por papel).",
        ],
        "api_fields": "POST /api/convert (multipart/form-data): file ou url, mais os opcionais lang, ocr, llm_provider, llm_api_key, llm_model.",
        "p5": "Parte 5 — Solução de problemas",
        "faq": ["Um vídeo longo não transcreve: pode exceder MAX_MEDIA_MINUTES — aumente o limite ou use DIOS.",
                "Um vídeo do YouTube falha: pode não ter legendas, ou o YouTube bloqueia o IP do servidor — cole seus cookies do YouTube nas Configurações, ou defina YT_PROXY/YT_COOKIES.",
                "Erro 413 no upload: aumente MAX_UPLOAD_MB e o limite de body do proxy reverso.",
                "Um PDF saiu vazio: estava digitalizado sem OCR para seu papel — use ANGEL/DIOS ou marque «Forçar OCR».",
                "Esqueceu a senha do DIOS: se não a definiu, uma aleatória aparece nos logs ao iniciar."],
        "footer": "Escriba — por Diego Parrás · CeMIACE · SEUBES · FCE-UBA · Licença MIT",
    },
    "it": {
        "sub1": "Markdown pulito e anonimo per gli LLM", "sub2": "Manuale completo — utenti e amministratori",
        "byline": "Sviluppato da Diego Parrás · CeMIACE · SEUBES · FCE-UBA",
        "p1": "Parte 1 — Per gli utenti",
        "whatis_h": "Cos’è Escriba?",
        "whatis": "Escriba converte quasi qualsiasi file in Markdown pulito — testo formattato, pronto da copiare, salvare o passare a un’IA. Gestisce documenti, fogli di calcolo, presentazioni, immagini, audio, video e YouTube.",
        "howto_h": "Per iniziare",
        "howto": ["Inserisci la password e accedi (il tuo livello: HUMANO, ANGEL o DIOS).",
                  "Trascina i file nell’area centrale, o clicca «Seleziona file».",
                  "Clicca «Converti tutto». Appare una barra di avanzamento.",
                  "Apri il risultato e usa Anteprima / Markdown / Diviso. Copialo o scarica il .md (o uno .zip per più file)."],
        "more_h": "Funzioni principali",
        "more": ["Audio e video sono trascritti in locale con Whisper; scegli la lingua nelle opzioni avanzate.",
                 "Incolla un link di YouTube per ottenerne la trascrizione.",
                 "Il testo nelle immagini viene elaborato con OCR automaticamente; i PDF scansionati sono rilevati, elaborati e raddrizzati al volo.",
                 "L’IA è opzionale (OpenAI, Gemini, OpenRouter) e il valore predefinito è «Senza IA». I modelli sono elencati automaticamente.",
                 "Anonimizzazione PII per LLM: motore locale (NER + layout fatture + rilevatori validati + regole proprie) con cinque modalità di output — tipizzata, anonima, pseudonimizzazione reversibile (token → all’LLM → re-idratazione), mascheramento parziale (••••-3456) e hash stabile (stesso dato → stesso pseudonimo tra documenti).",
                 "Censura visiva: scarica il PDF o l’immagine scansionata con i dati oscurati sulla pagina — redazione reale: il testo e i pixel sottostanti vengono rimossi dal file.",
                 "Coda: converti tutto o solo i file selezionati.",
                 "Tema chiaro/scuro e interfaccia disponibile in 7 lingue."],
        "p2": "Parte 2 — Ruoli e livelli di accesso",
        "p2_intro": "Il login è obbligatorio. Ogni livello ha la propria password e i propri limiti, tutti configurabili tramite variabili d’ambiente.",
        "roles": [
            "Capacità|HUMANO|ANGEL|DIOS",
            "Caricare e convertire file|Sì|Sì|Sì",
            "Convertire da URL pubblico|No|Sì|Sì",
            "URL interno / percorso locale|No|No|Sì",
            "Audio / video / ZIP|No|Sì|Sì",
            "Trascrizioni di YouTube|Sì|Sì|Sì",
            "OCR (forzato / automatico)|No|Sì|Sì",
            "Usare le chiavi IA del server|No|Sì|Sì",
            "Dimensione max file|25 MB|100 MB|illimitata",
            "File per lotto|3|10|illimitati",
            "Limite richieste (req/min)|15|60|illimitato",
        ],
        "p3": "Parte 3 — Per gli amministratori",
        "arch_h": "Architettura",
        "arch": "Escriba gira in un unico container Docker autosufficiente che include FastAPI + MarkItDown, ffmpeg, Tesseract + OCRmyPDF, faster-whisper e un Redis integrato. Viene eseguito come utente non-root, con healthcheck e rilevamento automatico dei core.",
        "deploy_h": "Distribuzione",
        "deploy_run": "Esegui l’immagine già pronta (senza build):",
        "deploy_compose": "Oppure con Docker Compose:",
        "deploy_easy": "EasyPanel/Portainer/Dokploy: crea un’App dall’immagine Docker ghcr.io/diegoparras/escriba:latest, aggiungi le variabili d’ambiente, punta il dominio alla porta 8000 del container con HTTPS e distribuisci.",
        "env_h": "Variabili d’ambiente",
        "env": [
            "Variabile|Predefinito|Descrizione",
            "SECRET_KEY|casuale|Chiave di firma delle sessioni. Impostala in produzione.",
            "GOD/ANGEL/HUMAN_PASSWORD|—|Password di ogni livello di accesso.",
            "HUMAN_OPEN|false|Consente il livello HUMANO senza login.",
            "WEB_CONCURRENCY|auto|Worker paralleli (auto = core CPU).",
            "MAX_UPLOAD_MB|100|Dimensione max di caricamento (eccetto DIOS).",
            "WHISPER_MODEL|base|Modello di trascrizione (tiny … large-v3).",
            "MAX_MEDIA_MINUTES|120|Limite durata audio/video (0 = illimitato).",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|Chiavi IA lato server (ripiego).",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|Token per l’automazione e il suo ruolo.",
            "EMBEDDED_REDIS|true|Redis integrato per il limite condiviso.",
            "ENABLE_DOCS|false|Esporre Swagger su /api/docs.",
        ],
        "aikeys_h": "Chiavi IA lato server",
        "aikeys": ["Se impostate, gli utenti non devono incollare la propria. Solo DIOS e ANGEL le usano.",
                   "Il costo è tuo e condiviso. Lasciale vuote così ognuno usa la propria.",
                   "Una chiave fornita dall’utente ha sempre priorità su quella del server."],
        "whisper_h": "Trascrizione (Whisper)",
        "whisper": ["Imposta il modello con WHISPER_MODEL (più grande = più preciso, più lento).",
                    "Gira su CPU. MAX_MEDIA_MINUTES limita la durata (DIOS senza limite)."],
        "token_h": "Token API (automazione)",
        "token": "Per n8n o script, imposta API_TOKEN e invialo come header:",
        "sec_h": "Sicurezza",
        "sec": ["Autenticazione obbligatoria; tre ruoli con permessi distinti.",
                "Anti-SSRF (IP interni/redirect bloccati); percorsi locali solo per DIOS.",
                "Sanificazione XSS (DOMPurify) e header di sicurezza (CSP).",
                "Container non-root con no-new-privileges; OCR/Whisper senza shell.",
                "Limite richieste per ruolo; la chiave API non viene mai memorizzata sul server."],
        "priv_h": "Privacy",
        "priv": "I file caricati vengono elaborati in un file temporaneo ed eliminati appena finisce la conversione (successo o errore). Nessun database né cartella di upload; il risultato viene inviato solo al tuo browser.",
        "p4": "Parte 4 — Riferimento API",
        "api": [
            "Endpoint|Metodo|Descrizione",
            "/api/login|POST|Accesso; imposta un cookie di sessione.",
            "/api/me|GET|Ruolo attuale e capacità.",
            "/api/convert|POST|Converte un file o URL in Markdown.",
            "/api/models|POST|Elenca i modelli del provider.",
            "/api/stats|GET|Statistiche server (per ruolo).",
        ],
        "api_fields": "POST /api/convert (multipart/form-data): file o url, più gli opzionali lang, ocr, llm_provider, llm_api_key, llm_model.",
        "p5": "Parte 5 — Risoluzione dei problemi",
        "faq": ["Un video lungo non si trascrive: può superare MAX_MEDIA_MINUTES — alza il limite o usa DIOS.",
                "Un video YouTube fallisce: potrebbe non avere sottotitoli, o YouTube blocca l’IP del server — incolla i tuoi cookie di YouTube nelle Impostazioni, o imposta YT_PROXY/YT_COOKIES.",
                "Errore 413 al caricamento: alza MAX_UPLOAD_MB e il limite di body del reverse proxy.",
                "Un PDF è vuoto: era scansionato senza OCR per il tuo ruolo — usa ANGEL/DIOS o spunta «Forza OCR».",
                "Password DIOS dimenticata: se non impostata, ne viene stampata una casuale nei log all’avvio."],
        "footer": "Escriba — di Diego Parrás · CeMIACE · SEUBES · FCE-UBA · Licenza MIT",
    },
    "zh": {
        "sub1": "为 LLM 准备干净、匿名的 Markdown", "sub2": "完整手册 —— 用户与管理员",
        "byline": "由 Diego Parrás 开发 · CeMIACE · SEUBES · FCE-UBA",
        "p1": "第 1 部分 —— 面向用户",
        "whatis_h": "什么是 Escriba？",
        "whatis": "Escriba 能将几乎任何文件转换为干净的 Markdown —— 带格式的纯文本，便于复制、保存或交给 AI。支持文档、表格、幻灯片、图片、音频、视频和 YouTube。",
        "howto_h": "快速上手",
        "howto": ["输入密码并登录（你的级别：HUMANO、ANGEL 或 DIOS）。",
                  "将文件拖到中间区域，或点击「选择文件」。",
                  "点击「全部转换」，会出现进度条。",
                  "打开结果，使用 预览 / Markdown / 分屏。复制或下载 .md（多个文件可下载 .zip）。"],
        "more_h": "主要功能",
        "more": ["音频和视频使用 Whisper 在本地转写；在高级选项中选择语言。",
                 "粘贴 YouTube 链接即可获取其转写。",
                 "图片中的文字会自动 OCR；扫描版 PDF 会被检测、即时处理并自动纠正旋转。",
                 "AI 为可选（OpenAI、Gemini、OpenRouter），默认「不使用 AI」。模型会自动列出。",
                 "为 LLM 的 PII 匿名化：本地引擎（NER + 发票版面 + 校验检测器 + 自定义规则），五种输出模式：类型化、匿名、可逆假名化（占位符 → 发给 LLM → 还原）、部分掩码（••••-3456）和稳定哈希（相同数据 → 跨文档相同假名）。",
                 "可视化遮蔽：下载 PII 在页面上被涂黑的 PDF 或扫描图片 — 真正的涂黑：文字与底层像素都从文件中删除。",
                 "队列：可转换全部或仅所选文件。",
                 "浅色/深色主题，界面提供 7 种语言。"],
        "p2": "第 2 部分 —— 角色与访问级别",
        "p2_intro": "必须登录。每个级别都有独立的密码与限额，均可通过环境变量配置。",
        "roles": [
            "能力|HUMANO|ANGEL|DIOS",
            "上传并转换文件|是|是|是",
            "从公开网址转换|否|是|是",
            "内网网址 / 本地路径|否|否|是",
            "音频 / 视频 / ZIP|否|是|是",
            "YouTube 转写|是|是|是",
            "OCR（强制 / 自动）|否|是|是",
            "使用服务器 AI 密钥|否|是|是",
            "单文件最大大小|25 MB|100 MB|无限制",
            "每批文件数|3|10|无限制",
            "限流（次/分钟）|15|60|无限制",
        ],
        "p3": "第 3 部分 —— 面向管理员",
        "arch_h": "架构",
        "arch": "Escriba 在单一、自包含的 Docker 容器中运行，内置 FastAPI + MarkItDown、ffmpeg、Tesseract + OCRmyPDF、faster-whisper 和内嵌 Redis。以非 root 用户运行，带健康检查并自动检测 CPU 核心。",
        "deploy_h": "部署",
        "deploy_run": "运行预构建镜像（无需构建）：",
        "deploy_compose": "或使用 Docker Compose：",
        "deploy_easy": "EasyPanel/Portainer/Dokploy：用 Docker 镜像 ghcr.io/diegoparras/escriba:latest 创建一个 App，添加环境变量，将域名指向容器端口 8000 并启用 HTTPS，然后部署。",
        "env_h": "环境变量",
        "env": [
            "变量|默认值|说明",
            "SECRET_KEY|随机|会话签名密钥。生产环境请设置。",
            "GOD/ANGEL/HUMAN_PASSWORD|—|各访问级别的密码。",
            "HUMAN_OPEN|false|允许 HUMANO 级别免登录。",
            "WEB_CONCURRENCY|auto|并行 worker（auto = CPU 核心数）。",
            "MAX_UPLOAD_MB|100|上传大小上限（DIOS 除外）。",
            "WHISPER_MODEL|base|转写模型（tiny … large-v3）。",
            "MAX_MEDIA_MINUTES|120|音视频时长上限（0 = 无限制）。",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|服务器端 AI 密钥（回退）。",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|自动化令牌及其角色。",
            "EMBEDDED_REDIS|true|内嵌 Redis，用于共享限流。",
            "ENABLE_DOCS|false|在 /api/docs 暴露 Swagger。",
        ],
        "aikeys_h": "服务器端 AI 密钥",
        "aikeys": ["设置后，用户无需粘贴自己的密钥。仅 DIOS 与 ANGEL 使用。",
                   "费用由你承担且为共享。留空则各用户自带密钥。",
                   "用户提供的密钥始终优先于服务器密钥。"],
        "whisper_h": "转写（Whisper）",
        "whisper": ["用 WHISPER_MODEL 设置模型（越大越准但越慢）。",
                    "在 CPU 上运行。MAX_MEDIA_MINUTES 限制时长（DIOS 无上限）。"],
        "token_h": "API 令牌（自动化）",
        "token": "用于 n8n 或脚本：设置 API_TOKEN 并作为请求头发送：",
        "sec_h": "安全",
        "sec": ["需要身份验证；三种角色权限各异。",
                "防 SSRF（拦截内网 IP/重定向）；本地路径仅限 DIOS。",
                "XSS 净化（DOMPurify）与安全响应头（CSP）。",
                "非 root 容器并启用 no-new-privileges；OCR/Whisper 不经 shell。",
                "按角色限流；API 密钥绝不存储在服务器。"],
        "priv_h": "隐私",
        "priv": "上传的文件在临时文件中处理，转换结束（成功或失败）后立即删除。没有数据库，也没有上传目录；结果仅发送到你的浏览器。",
        "p4": "第 4 部分 —— API 参考",
        "api": [
            "端点|方法|说明",
            "/api/login|POST|登录；设置会话 Cookie。",
            "/api/me|GET|当前角色与能力。",
            "/api/convert|POST|将文件或网址转换为 Markdown。",
            "/api/models|POST|列出提供商的模型。",
            "/api/stats|GET|服务器统计（按角色）。",
        ],
        "api_fields": "POST /api/convert（multipart/form-data）：file 或 url，以及可选的 lang、ocr、llm_provider、llm_api_key、llm_model。",
        "p5": "第 5 部分 —— 常见问题",
        "faq": ["长视频无法转写：可能超过 MAX_MEDIA_MINUTES —— 调高上限或使用 DIOS。",
                "YouTube 视频失败：可能没有字幕，或 YouTube 屏蔽了服务器 IP —— 在「设置」中粘贴你的 YouTube Cookies，或设置 YT_PROXY/YT_COOKIES。",
                "上传出现 413：调高 MAX_UPLOAD_MB 以及反向代理的 body 限制。",
                "PDF 结果为空：它是扫描版且你的角色无 OCR —— 使用 ANGEL/DIOS 或勾选「强制 OCR」。",
                "忘记 DIOS 密码：若未设置，启动时会在容器日志中打印一个随机密码。"],
        "footer": "Escriba —— 由 Diego Parrás 开发 · CeMIACE · SEUBES · FCE-UBA · MIT 许可证",
    },
    "ja": {
        "sub1": "LLM 向けのきれいで匿名化された Markdown", "sub2": "完全マニュアル —— 利用者と管理者向け",
        "byline": "開発：Diego Parrás · CeMIACE · SEUBES · FCE-UBA",
        "p1": "第 1 部 —— 利用者向け",
        "whatis_h": "Escriba とは？",
        "whatis": "Escriba は、ほぼあらゆるファイルをきれいな Markdown（書式付きのプレーンテキスト）に変換します。コピー・保存・AI への入力にすぐ使えます。文書、表計算、スライド、画像、音声、動画、YouTube に対応。",
        "howto_h": "はじめに",
        "howto": ["パスワードを入力してサインイン（あなたのレベル：HUMANO、ANGEL、DIOS）。",
                  "中央エリアにファイルをドラッグするか、「ファイルを選択」をクリック。",
                  "「すべて変換」をクリック。進捗バーが表示されます。",
                  "結果を開き、プレビュー / Markdown / 分割 を使用。コピーするか .md をダウンロード（複数なら .zip）。"],
        "more_h": "主な機能",
        "more": ["音声・動画は Whisper でローカルに文字起こし。詳細オプションで言語を選択。",
                 "YouTube のリンクを貼ると文字起こしを取得。",
                 "画像内の文字は自動で OCR。スキャン PDF は検出してその場で OCR・自動回転補正。",
                 "AI は任意（OpenAI、Gemini、OpenRouter）で、既定は「AI を使わない」。モデルは自動で一覧表示。",
                 "LLM 向け PII 匿名化：ローカルエンジン（NER + 請求書レイアウト + 検証付き検出器 + 独自ルール）。出力は 5 モード：型付き・匿名・可逆な仮名化（トークン → LLM → 復元）・部分マスク（••••-3456）・安定ハッシュ（同じデータ → 文書をまたいで同じ仮名）。",
                 "ビジュアル墨消し：PII をページ上で黒塗りした PDF・スキャン画像をダウンロード — 本物の墨消し：テキストと下のピクセルはファイルから削除されます。",
                 "キュー：すべて、または選択したファイルのみを変換。",
                 "ライト/ダークテーマ、UI は 7 言語に対応。"],
        "p2": "第 2 部 —— ロールとアクセスレベル",
        "p2_intro": "ログインが必須です。各レベルに独自のパスワードと制限があり、すべて環境変数で設定できます。",
        "roles": [
            "機能|HUMANO|ANGEL|DIOS",
            "ファイルのアップロードと変換|可|可|可",
            "公開 URL から変換|不可|可|可",
            "内部 URL / ローカルパス|不可|不可|可",
            "音声 / 動画 / ZIP|不可|可|可",
            "YouTube の文字起こし|可|可|可",
            "OCR（強制 / 自動）|不可|可|可",
            "サーバー AI キーの使用|不可|可|可",
            "最大ファイルサイズ|25 MB|100 MB|無制限",
            "1 バッチのファイル数|3|10|無制限",
            "レート制限（req/分）|15|60|無制限",
        ],
        "p3": "第 3 部 —— 管理者向け",
        "arch_h": "アーキテクチャ",
        "arch": "Escriba は単一の自己完結型 Docker コンテナで動作し、FastAPI + MarkItDown、ffmpeg、Tesseract + OCRmyPDF、faster-whisper、組み込み Redis を同梱します。非 root ユーザーで実行され、ヘルスチェックと CPU コアの自動検出を備えます。",
        "deploy_h": "デプロイ",
        "deploy_run": "ビルド済みイメージを実行（ビルド不要）：",
        "deploy_compose": "または Docker Compose で：",
        "deploy_easy": "EasyPanel/Portainer/Dokploy：Docker イメージ ghcr.io/diegoparras/escriba:latest から App を作成し、環境変数を追加、ドメインをコンテナのポート 8000 に HTTPS で割り当ててデプロイします。",
        "env_h": "環境変数",
        "env": [
            "変数|既定値|説明",
            "SECRET_KEY|ランダム|セッション署名鍵。本番では設定すること。",
            "GOD/ANGEL/HUMAN_PASSWORD|—|各アクセスレベルのパスワード。",
            "HUMAN_OPEN|false|HUMANO をログインなしで許可。",
            "WEB_CONCURRENCY|auto|並列ワーカー（auto = CPU コア数）。",
            "MAX_UPLOAD_MB|100|アップロードの上限（DIOS を除く）。",
            "WHISPER_MODEL|base|文字起こしモデル（tiny … large-v3）。",
            "MAX_MEDIA_MINUTES|120|音声/動画の長さ上限（0 = 無制限）。",
            "OPENAI/OPENROUTER/GOOGLE_API_KEY|—|サーバー側 AI キー（フォールバック）。",
            "API_TOKEN / API_TOKEN_ROLE|— / angel|自動化用トークンとそのロール。",
            "EMBEDDED_REDIS|true|共有レート制限用の組み込み Redis。",
            "ENABLE_DOCS|false|/api/docs に Swagger を公開。",
        ],
        "aikeys_h": "サーバー側 AI キー",
        "aikeys": ["設定すると、ユーザーは自分のキーを貼る必要がありません。DIOS と ANGEL のみが使用。",
                   "費用は管理者持ちで共有されます。空にすれば各自が自分のキーを使います。",
                   "ユーザーが入力したキーは常にサーバーのキーより優先されます。"],
        "whisper_h": "文字起こし（Whisper）",
        "whisper": ["WHISPER_MODEL でモデルを指定（大きいほど高精度・低速）。",
                    "CPU で動作。MAX_MEDIA_MINUTES が長さを制限（DIOS は上限なし）。"],
        "token_h": "API トークン（自動化）",
        "token": "n8n やスクリプト向けに、API_TOKEN を設定してヘッダーで送信：",
        "sec_h": "セキュリティ",
        "sec": ["認証が必須。3 つのロールで権限が異なる。",
                "SSRF 対策（内部 IP・リダイレクトを遮断）。ローカルパスは DIOS のみ。",
                "XSS サニタイズ（DOMPurify）とセキュリティヘッダー（CSP）。",
                "非 root コンテナ（no-new-privileges）。OCR/Whisper はシェルを介さず実行。",
                "ロール別レート制限。API キーはサーバーに保存されません。"],
        "priv_h": "プライバシー",
        "priv": "アップロードしたファイルは一時ファイルで処理され、変換が終わると（成功・失敗を問わず）すぐに削除されます。データベースもアップロードフォルダもなく、結果はあなたのブラウザにのみ送られます。",
        "p4": "第 4 部 —— API リファレンス",
        "api": [
            "エンドポイント|メソッド|説明",
            "/api/login|POST|ログイン。セッション Cookie を設定。",
            "/api/me|GET|現在のロールと権限。",
            "/api/convert|POST|ファイルまたは URL を Markdown に変換。",
            "/api/models|POST|プロバイダーのモデル一覧。",
            "/api/stats|GET|サーバー統計（ロール別）。",
        ],
        "api_fields": "POST /api/convert（multipart/form-data）：file または url、加えて任意の lang、ocr、llm_provider、llm_api_key、llm_model。",
        "p5": "第 5 部 —— トラブルシューティング",
        "faq": ["長い動画が文字起こしできない：MAX_MEDIA_MINUTES を超えている可能性 —— 上限を上げるか DIOS を使用。",
                "YouTube 動画が失敗：字幕がない、または YouTube がサーバー IP をブロック —— 「設定」で YouTube の Cookie を貼り付けるか、YT_PROXY/YT_COOKIES を設定。",
                "アップロードで 413：MAX_UPLOAD_MB とリバースプロキシの body 制限を上げる。",
                "PDF が空：スキャンでロールに OCR がない —— ANGEL/DIOS を使うか「OCR を強制」にチェック。",
                "DIOS のパスワードを忘れた：未設定なら起動時にコンテナのログにランダムなものが出力されます。"],
        "footer": "Escriba —— 開発：Diego Parrás · CeMIACE · SEUBES · FCE-UBA · MIT ライセンス",
    },
}


def styles_for(font, bold):
    S = {}
    S["h1"] = ParagraphStyle("h1", fontName=bold, fontSize=18, textColor=CORAL_D, spaceBefore=10, spaceAfter=8, leading=22)
    S["h2"] = ParagraphStyle("h2", fontName=bold, fontSize=13, textColor=INK, spaceBefore=11, spaceAfter=4, leading=17)
    S["body"] = ParagraphStyle("body", fontName=font, fontSize=10, leading=15, textColor=INK, spaceAfter=6, alignment=TA_LEFT)
    S["muted"] = ParagraphStyle("muted", parent=S["body"], textColor=MUTED, fontSize=9)
    S["li"] = ParagraphStyle("li", parent=S["body"], spaceAfter=2)
    S["code"] = ParagraphStyle("code", fontName="Courier", fontSize=8.3, leading=11.5, textColor=INK, backColor=CODEBG, borderColor=LINE, borderWidth=0.5, borderPadding=6, spaceBefore=4, spaceAfter=8)
    S["cover_t"] = ParagraphStyle("cover_t", fontName=bold, fontSize=38, textColor=CORAL_D, leading=42, alignment=TA_CENTER)
    S["cover_s"] = ParagraphStyle("cover_s", fontName=font, fontSize=14, textColor=INK, alignment=TA_CENTER, leading=20)
    S["cover_m"] = ParagraphStyle("cover_m", fontName=font, fontSize=10.5, textColor=MUTED, alignment=TA_CENTER, leading=16)
    S["cell"] = ParagraphStyle("cell", fontName=font, fontSize=8.6, leading=11, textColor=INK)
    S["cellb"] = ParagraphStyle("cellb", fontName=bold, fontSize=8.6, leading=11, textColor=colors.white)
    return S


def build(lang):
    T = TR[lang]
    font, bold = FONTS[lang]
    S = styles_for(font, bold)
    st = []

    def h1(k): st.append(Paragraph(T[k], S["h1"]))
    def h2(k): st.append(Paragraph(T[k], S["h2"]))
    def body(k): st.append(Paragraph(T[k], S["body"]))
    def muted(k): st.append(Paragraph(T[k], S["muted"]))
    def code(txt): st.append(Preformatted(txt, S["code"]))
    def sp(h=6): st.append(Spacer(1, h))

    def blist(k):
        flow = [ListItem(Paragraph(it, S["li"]), leftIndent=10) for it in T[k]]
        st.append(ListFlowable(flow, bulletType="bullet", start="•", bulletColor=CORAL, leftIndent=14, bulletFontSize=7))
        sp(4)

    def grid(k, widths):
        rows = [r.split("|") for r in T[k]]
        data = [[Paragraph(c, S["cellb"] if i == 0 else S["cell"]) for c in r] for i, r in enumerate(rows)]
        t = Table(data, colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, 0), CORAL),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#faf6f1")]),
        ]))
        st.append(t); sp(8)

    # Cover
    st.append(Spacer(1, 5 * cm))
    st.append(Paragraph("Escriba", S["cover_t"])); sp(8)
    st.append(Paragraph(T["sub1"], S["cover_s"])); sp(26)
    st.append(Paragraph(T["sub2"], S["cover_s"])); sp(40)
    st.append(Paragraph(T["byline"], S["cover_m"])); sp(8)
    st.append(Paragraph("github.com/diegoparras/escriba", S["cover_m"]))
    st.append(PageBreak())

    # Part 1
    h1("p1"); h2("whatis_h"); body("whatis")
    h2("howto_h"); blist("howto"); h2("more_h"); blist("more")
    st.append(PageBreak())

    # Part 2
    h1("p2"); body("p2_intro"); grid("roles", [6.6 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
    st.append(PageBreak())

    # Part 3
    h1("p3"); h2("arch_h"); body("arch")
    h2("deploy_h"); body("deploy_run"); code(CODE_RUN); body("deploy_compose"); code(CODE_COMPOSE); body("deploy_easy")
    st.append(PageBreak())
    h2("env_h"); grid("env", [5.6 * cm, 2.4 * cm, 8.2 * cm])
    st.append(PageBreak())
    h2("aikeys_h"); blist("aikeys"); h2("whisper_h"); blist("whisper")
    h2("token_h"); body("token"); code(CODE_TOKEN)
    h2("sec_h"); blist("sec"); h2("priv_h"); body("priv")
    st.append(PageBreak())

    # Part 4 & 5
    h1("p4"); grid("api", [4.4 * cm, 2.4 * cm, 9.4 * cm]); body("api_fields")
    h1("p5"); blist("faq")
    st.append(HRFlowable(width="100%", color=LINE, thickness=0.7, spaceBefore=8, spaceAfter=8))
    muted("footer")
    return st


def on_page(canvas, doc):
    canvas.saveState(); w, h = A4
    canvas.setFillColor(CORAL); canvas.rect(0, h - 0.45 * cm, w, 0.45 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8); canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.1 * cm, "Escriba")
    canvas.drawRightString(w - 2 * cm, 1.1 * cm, str(doc.page))
    canvas.restoreState()


def on_cover(canvas, doc):
    canvas.saveState(); w, h = A4
    canvas.setFillColor(CORAL)
    canvas.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
    canvas.rect(0, 0, w, 0.6 * cm, fill=1, stroke=0)
    canvas.restoreState()


for lang in TR:
    out = os.path.join(HERE, OUT[lang])
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title="Escriba — Manual", author="Diego Parrás")
    doc.build(build(lang), onFirstPage=on_cover, onLaterPages=on_page)
    print("PDF:", out)
