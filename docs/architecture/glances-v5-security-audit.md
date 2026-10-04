# Glances v5 — audit de sécurité complet (`develop-v5`)

**Date :** 2026-10-04 · **Branche :** `develop-v5` (`c8de5c7`) · **Exigence :**
architecture §4.8 et Phase 4 (« release blocker » pour `5.0.0`).

## Périmètre et méthode

Cinq passes indépendantes, chacune sur une partie de la surface v5 :

1. Serveur web : authentification (Basic + JWT), `UNAUTH_PATHS`, rate limiting
   (§4.5), CORS, TrustedHost, service de la WebUI.
2. Routes REST : `/api/5/config`, `/api/5/args`, routes qui modifient l'état,
   MCP, historique.
3. Exécution de commandes et requêtes sortantes : actions, AMP, plugins
   (`vms`, `ip`, `cloud`, `ports`, `folders`, `sensors`…), `--fetch`,
   `--issue`, découverte des plugins, séquences d'échappement terminal.
4. Côté distant : client `-c`, navigateur `--browser`, Zeroconf (face à un
   serveur malveillant), et les 18 exporteurs.
5. Configuration, fichiers écrits, journaux, imports de code v4 depuis le
   code v5, primitives dangereuses, WebUI v5 (XSS), dépendances.

Chaque constat a été vérifié dans le code, et la plupart par une sonde
exécutée : vrais serveurs `glances.main_v5 -s` sur loopback, `TestClient`,
uvicorn réel par socket brute, PostgreSQL 16 et DuckDB réels pour les CVE SQL,
pty pour le TUI. Versions : fastapi 0.141/0.142, starlette 1.7, uvicorn 0.54,
python-jose 3.5, mcp 2.3. Les suites de tests v5 du périmètre passent
(688 + 103 + 134 tests, aucun échec). Aucun fichier du dépôt n'a été modifié.

**Modèle de menace** (CLAUDE.md) : sans `[outputs] password`, l'API est ouverte
par choix, en général sur un réseau privé. Ce n'est pas un constat en soi.
Comptent : un secret servi à un appelant non authentifié, un contournement de
l'authentification quand un mot de passe est défini, l'injection ou
l'exécution de code, la SSRF, un déni de service bon marché, et les défauts
qui contredisent la documentation. Glances tourne souvent en root et lit des
données non fiables (noms de processus, conteneurs, VM, points de montage,
réponses HTTP, annonces Zeroconf).

## Synthèse

| Sévérité | Nombre |
|---|---:|
| Critique | 0 |
| Haute | 0 |
| Bloquant de fusion (structurel, pas une faille) | 1 |
| Moyenne | 11 |
| Basse | 22 |
| Info | 14 |

**Aucune faille critique ou haute.** L'authentification tient : avec un mot de
passe, toutes les routes répondent 401 sauf `/status`, `/healthz` et
`POST /api/5/token`. L'algorithme JWT est épinglé, aucun contournement de
chemin n'aboutit, le CORS est correct. Toutes les CVE du §8 tiennent, sauf
CVE-2026-53925 qui régresse en partie (M4).

**Verdict pour la fusion :** l'audit ne bloque pas la fusion vers `develop`.
Il bloque `5.0.0b1` tant que B1 et les constats moyens marqués « avant b1 »
ne sont pas traités (voir « Plan de correction »).

---

## B1 — Le code v5 passe encore par le code v4 (bloquant de fusion)

- **Où :** tout import `glances.plugins.<x>.model_v5` exécute d'abord
  `glances/plugins/<x>/__init__.py`, qui **est le plugin v4**. De même
  `glances/exports/glances_<x>/__init__.py` (exporteur v4, qui importe
  `glances.exports.export`), et `glances/__init__.py:37-39` importe
  `glances.main` (la ligne de commande v4), qui importe `glances.config`.
- **Effet :** toute la pile des plugins v4 est chargée à chaque démarrage v5
  (`plugins.plugin.model`, `actions`, `thresholds`, `history`…), et une partie
  s'exécute : `glances/plugins/load/__init__.py:65-66` construit un
  `CorePlugin()` v4 à l'import.
- **Modules v4 utilisés comme bibliothèques par v5 :**
  `ports/model_v5.py:39` (`ThreadScanner`),
  `sensors/model_v5.py:34-36` (`GlancesGrabSensors`, `sensors_definition`),
  `smart/model_v5.py:30` et `smart/render_curses_v5.py:32` (`get_smart_data`,
  `LARGE_VALUE_KEYS`), `psutilversion/model_v5.py:19`, et
  `glances.config.secure_option` (`web_list.py:11`, moteurs de conteneurs).
- **Conséquence sécurité :** `glances.config` reste livré avec la substitution
  backtick `system_exec` (`config.py:369-379`, CVE-2026-33641). C'est du code
  mort aujourd'hui (la sonde confirme 0 appel), mais un appel futur la
  réactiverait.
- **Correction :** avant de supprimer v4, vider chaque `__init__.py` de
  paquet, déplacer les helpers partagés (`ThreadScanner`, grabbers de
  capteurs, `get_smart_data`, `secure_option`) dans des modules neutres, puis
  supprimer `glances.config.Config`.

Ce que v5 n'atteint jamais à l'exécution : `outdated`, `password`,
`password_list`, `client`, `client_browser`, `server`, `webserver`,
`glances_restful_api`, `standalone`, `stats*`, `snmp`, `glances_curses`,
`glances_stdout*`, xmlrpc. Aucun appel à pickle dans `glances/`.

---

## Constats moyens

### M1 — `/api/5/config` sert des secrets : la redaction est une liste noire

- **Où :** `glances/config_v5.py:111-135` (noms de clés), `:64` (regex des
  identifiants d'URL), `:363-389`. Servi par `routes_v5.py:306-308`.
- **Constat :** la redaction ne voit que des noms de clés et l'identifiant
  `user:pass@` d'une URL. Passent en clair, toutes dans des clés que v5 lit :
  - `*_action` et `*_action_repeat` : jeton Bearer dans un `curl -H`, webhook
    Slack, jeton de bot Telegram, `curl -u user:pw`, URL apprise ;
  - commandes AMP : `command=mysqladmin -uroot -pSECRET status` ;
  - jetons en query string : `[ip] public_api=…?token=`,
    `[ports] web_N_url=…?access_token=`, `[restful] path=…?api_key=`,
    `[duckdb] database=md:…?motherduck_token=` ;
  - identifiant sans schéma : `[elasticsearch] host=elastic:PW@es.example` ;
  - noms de clés absents de la liste : `apikey` (v4 le redactait : régression),
    `key`, `private_key`, `auth`, `credentials`.
- **Voisin (bas, même cause) :** la regex `(?<=://)[^/?#@\s]+@` s'arrête au
  premier `@`. `https://u:p@ssPW@h` devient `https://***@ssPW@h`, et la fin du
  mot de passe fuit, y compris dans `/api/5/ports` et la ressource MCP
  `glances://stats/ports`. La même regex est en v4.
- **Usage réel :** la WebUI lit quatre clés (`global.refresh`,
  `outputs.theme`, `outputs.max_processes_display`, `outputs.api_doc`,
  `static/js/v5/api.js:135-162`). Le client TUI n'appelle jamais `/config`.
- **Correction :** servir une **liste blanche** des clés utiles à l'interface
  (affichage, seuils). Le dump complet redacté n'est servi qu'avec un mot de
  passe, ou plus du tout. Corriger la regex en `(?<=://)[^/?#\s]+@`. Pour
  `ports`, publier `scheme://host[:port]/path` sans la query.
- **Réponse à la question ouverte du §4.8 :** non, la redaction ne suffit pas
  à garder l'endpoint ouvert tel quel. La liste blanche, oui.

### M2 — Pas de protection contre le DNS rebinding dans le déploiement par défaut

- **Où :** `glances/webserver_v5.py:360-371`. `TrustedHostMiddleware` n'est
  branché que si `webui_allowed_hosts` est défini, et l'avertissement ne
  s'affiche que pour une adresse d'écoute non loopback.
- **Scénario :** `glances -s` écoute sur 127.0.0.1 sans mot de passe (le
  défaut). Une page web visitée rebinde son nom sur 127.0.0.1. Elle lit alors
  `/api/5/config` (donc M1), `/api/5/all` et les lignes de commande des
  processus, et peut appeler les routes POST.
- **Preuve :** `Host: evil.attacker.example` → 200 sur `/api/5/config`, aucun
  avertissement au démarrage.
- **Correction :** avec une adresse loopback et sans liste configurée, prendre
  `localhost,127.0.0.1` par défaut, comme MCP le fait déjà
  (`glances_mcp.py:151`). Sinon, toujours avertir.

### M3 — Le limiteur d'échecs d'authentification verrouille tous les utilisateurs d'une même adresse

- **Où :** `glances/ratelimit_v5.py:142-145`. Un essai est consommé **avant**
  la vérification, donc le bon mot de passe est refusé pendant le verrouillage.
- **Scénario :** derrière un reverse proxy (Traefik dans `docs/docker.rst`, un
  ingress Kubernetes), derrière du NAT ou du NAT64, tous les clients
  partagent une adresse. Dix essais faux par minute verrouillent tout le
  monde.
- **Preuve :** 15 essais faux → 10×401 puis 5×429, puis le bon mot de passe →
  **429**.
- **Voisin (bas) :** chaque requête avec un en-tête `Authorization` prend un
  jeton jusqu'à la fin de la réponse. Douze requêtes valides simultanées
  donnent 10×200 et 2×429, et un flux SSE MCP garde son jeton. Quelques
  onglets WebUI suffisent, d'autant que chaque requête Basic coûte ~280 ms de
  PBKDF2.
- **Correction :** accepter sans consommer d'essai un jeton Bearer valide, ou
  un en-tête Basic déjà validé (HMAC en cache, ce qui supprime aussi le coût
  PBKDF2), et ne décompter que les échecs. Exposer `forwarded_allow_ips` (B-6).

### M4 — `--disable-config-exec` : non appliqué sous `--issue`/`--fetch`, et contournable par `sh -c`

- **Où :**
  - Le flag n'est appliqué que dans `assemble()` (`main_v5.py:1154-1160`).
    `run_issue` (`:1622-1630`) construit les plugins (AMP compris) sans lui ;
    `--fetch` (`:1746-1748`) passe par `GlancesAPI(config_path)`, qui recharge
    la configuration sans le flag (`api_v5.py:159`).
  - `secure_popen` (`glances/secure.py:47-73`) garde une chaîne entre
    guillemets comme un seul argument, puis exécute `argv[0]` quel qu'il soit.
- **Preuve :** avec `--disable-config-exec`, une redirection `>` d'AMP a écrit
  son fichier sous `--issue` et sous `--fetch`.
  `secure_popen('sh -c "id -u > F && echo chained >> F"', allow_operators=False)`
  a écrit les deux lignes.
- **Portée :** la première partie est une régression partielle du correctif de
  CVE-2026-53925. La seconde existe aussi en v4 : le flag retire les
  opérateurs, ce n'est pas un bac à sable.
- **Correction :** appliquer le flag dans `main()` juste après le chargement de
  la configuration, et le passer à `GlancesAPI`, avec un test pour chaque
  mode. Puis, soit le flag désactive toute commande issue de la configuration
  (AMP `command`/`service_cmd`, `*_action`), soit `argv[0]` est refusé quand
  c'est un shell ou un interpréteur. À défaut, documenter la limite.

### M5 — Une valeur rendue dans la cible d'une redirection choisit le fichier écrit par root

- **Où :** `glances/secure.py:113-117` rend la cible, `:157` fait
  `open(path, "w")`, en suivant les liens symboliques. Fonctionnalité testée
  (`tests/test_action_shell_v5.py:341`).
- **Scénario :** `critical_action=echo … > /var/log/glances/{{name}}.log`. Un
  processus nommé `../../../etc/cron.d/x` (tient dans les 15 caractères de
  `comm`), une commande de conteneur ou un point de montage oriente
  l'écriture.
- **Preuve :** `name="../victim/owned"` a créé `victim/owned.log`.
- **Correction :** dans la cible, refuser une valeur rendue contenant `/`,
  `..` ou NUL (ou résoudre le chemin et exiger qu'il reste sous le répertoire
  littéral), et ouvrir avec `O_NOFOLLOW`. Voisin : un argument rendu qui
  commence par `-` est lu comme une option par la commande (`ls {{name}}`
  avec `--version`).

### M6 — Client hddtemp sans délai ni limite de taille

- **Où :** `glances/plugins/sensors/sensor/glances_hddtemp.py:131-137` (pas
  de `settimeout`, `data +=` jusqu'à EOF), activé par défaut sur
  127.0.0.1:7634.
- **Scénario :** si le démon hddtemp ne tourne pas, un utilisateur local prend
  le port 7634 (non privilégié). Il ne ferme jamais la connexion, ou envoie
  des gigaoctets : la collecte des capteurs (températures, ventilateurs,
  batterie) se fige, ou la mémoire de root grossit. Il peut aussi injecter de
  fausses valeurs.
- **Preuve :** `GlancesGrabHDDTemp.get()` toujours bloqué après 5 s.
- **Correction :** `settimeout`, plafond de 64 Kio, fermeture garantie. hddtemp
  est abandonné en amont : envisager de le rendre opt-in.

### M7 — Exporteur graph : dossier partagé `/tmp/glances` et liens symboliques suivis

- **Où :** `glances/exports/glances_graph/export_v5.py:49`
  (`DEFAULT_PATH = <tmp>/glances`), `:80` (`makedirs(exist_ok=True)` accepte un
  dossier créé par un autre), `:157` (noms fixes). `conf/glances.conf:882`
  livre `path=/tmp/glances`.
- **Scénario :** `mkdir /tmp/glances; ln -s /etc/shadow /tmp/glances/cpu.svg`
  par un utilisateur local, puis root génère les graphes : `/etc/shadow` est
  remplacé par du SVG. `fs.protected_symlinks` ne protège pas un dossier non
  sticky appartenant à l'attaquant.
- **Preuve :** sonde, fichier victime écrasé par `<?xml … <svg`. v4 fait pire
  (directement dans `/tmp`).
- **Correction :** dossier par utilisateur en `0o700`, refus d'un dossier
  existant qui n'appartient pas à l'uid effectif ou qui est inscriptible par
  le groupe ou les autres, écriture par fichier temporaire + `os.replace()`.
  Corriger `conf/glances.conf`.

### M8 — Le journal peut retomber sur `/tmp/glances-<user>.log`, lisible par tous, liens suivis

- **Où :** `glances/logger.py:22-38` (module v4 partagé, réutilisé par
  `main_v5.setup_logging`), ouvert par `RotatingFileHandler` (`:52-59`).
- **Scénario :** root sans `HOME` ou sans `~/.local/share` (hôtes minimaux,
  conteneurs, unités systemd sans `User=`) journalise dans `/tmp`. Sans
  protection des liens, un utilisateur local fait ajouter du texte par root à
  n'importe quel fichier. Avec `protected_regular=1`, un fichier préplacé
  empêche Glances de démarrer. Le journal est en `0644`, et au niveau DEBUG il
  contient les commandes d'action et leur sortie.
- **Preuve :** `env -i` → `$TMPDIR/glances-root.log` créé en `0644`, ligne
  WARNING ajoutée au fichier victime via le lien.
- **Correction :** jamais de dossier temporaire partagé : `/var/log/glances`
  en root, `~/.local/state/glances` sinon, créés en `0o700`. Ouverture en
  `O_NOFOLLOW`, mode `0o600`.

### M9 — Exporteurs InfluxDB 1.x et 2.x : certificat TLS jamais vérifié

- **Où :** `glances/exports/glances_influxdb/export_v5.py:81` et
  `glances_influxdb2/export_v5.py:102`, `verify_ssl=False` en dur. Identique en v4.
- **Scénario :** avec `protocol=https`, un attaquant sur le chemin réseau
  récupère le mot de passe (1.x) ou le jeton, souvent tous droits (2.x).
- **Correction :** vérifier par défaut ; clé `ssl_verify` (booléen ou chemin
  de CA) comme `[client] ssl_verify`.

### M10 — Les exporteurs envoient les options des sections de plugins, secrets compris

- **Où :** `glances/exports/export_base_v5.py:363-375` (`_limits_for`),
  fusionné au payload (`:427`, et `_merge_limits` pour ClickHouse,
  TimescaleDB, DuckDB). Seules les clés contenant `_action` sont exclues.
- **Constat :** `[ip] public_username` / `public_password` (documentés dans
  `conf/glances.conf`) et les `[ports] web_N_url` avec `user:pass@` partent en
  clair vers tous les backends qui gardent les chaînes : JSON, CSV, InfluxDB,
  Kafka, NATS, ZeroMQ (livré avec `host=*`, donc publié sans authentification
  sur toutes les interfaces), MQTT, restful, Elasticsearch, Mongo, CouchDB,
  ClickHouse, TimescaleDB, DuckDB.
- **Preuve :** sortie JSON :
  `"ip_public_password": "S3CRET-PW"`,
  `"ports_web_1_url": "https://bob:hunter2@intranet.example/"`. Identique en v4.
- **Correction :** passer ces options par la même redaction que
  `as_dict_secure()`, ou n'exporter que les seuils numériques.

### M11 — Une annonce Zeroconf peut se faire passer pour un serveur connu et récupérer son mot de passe

- **Où :** `glances/zeroconf_v5.py:383-386` (alias libre, 64 caractères
  imprimables) ; `browser_curses_v5.py:119` et `static/js/v5/browser.js`
  affichent `alias or name` sans source ni adresse ; `main_v5.py:1457` demande
  `Password for glances@<alias>`.
- **Scénario :** sur le LAN, l'attaquant annonce `prod-db` avec `api=5` à sa
  propre adresse et répond 401. L'entrée apparaît comme PROTECTED sous le nom
  « prod-db », l'utilisateur tape le vrai mot de passe, qui part chez
  l'attaquant. Le correctif de CVE-2026-32634 protège les mots de passe
  **configurés**, pas ceux que l'on tape.
- **Correction :** marquer les entrées découvertes dans les deux interfaces
  (`prod-db (zeroconf 192.168.1.66)`), mettre l'adresse dans l'invite, et
  signaler ou refuser un alias identique à une entrée statique.

---

## Constats bas

| Id | Constat | Où | Correction |
|---|---|---|---|
| B-1 | Le temps de réponse révèle si le nom d'utilisateur est correct (1,7 ms contre 288 ms) : `and` court-circuité avant PBKDF2. | `webserver_v5.py:467-469`, `routes_v5.py:240-242` | Toujours exécuter `verify_password` (hash factice au besoin), combiner sans court-circuit. |
| B-2 | Le `jwt_secret_key` d'exemple de `conf/glances.conf:120`, une fois décommenté, est accepté : n'importe qui forge un jeton. Aucune longueur minimale. | `security_v5.py:106-108`, `webserver_v5.py:433-435` | Refuser le texte d'exemple et toute clé de moins de 32 octets (clé éphémère + WARNING). |
| B-3 | PBKDF2-SHA256 à 100 000 itérations avec `dklen=128` : le serveur fait 4× le travail de l'attaquant ; le format `salt$hex` ne dit ni l'algorithme ni le nombre d'itérations. | `security_v5.py:40-42, 76-83` | `dklen=32`, ≥ 600 000 itérations, format `pbkdf2_sha256$<iter>$<salt>$<hash>`, l'ancien format reste lu. |
| B-4 | Les clés `ssl_keyfile`/`ssl_certfile` sont documentées mais ignorées : le serveur reste en HTTP clair, sans avertissement. | `main_v5.py:1679-1685`, `conf/glances.conf:112-115`, `docs/config.rst:131-133` | Les passer à `uvicorn.Config`, ou WARNING quand elles sont définies. |
| B-5 | Les trois routes POST (tri, épinglage) se déclenchent depuis un autre site (requête « simple », sans prévol) ; aucune en-tête anti-iframe. | `routes_v5.py:146-203`, `webserver_v5.py` | Refuser un `Origin` présent et étranger sur POST ; `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`. |
| B-6 | uvicorn fait confiance à `X-Forwarded-For` venant de loopback : un client local contourne le limiteur (30 essais, aucun 429) ou fait verrouiller une autre IP. La doc cite `--forwarded-allow-ips`, qui n'existe pas. | `main_v5.py:1679-1685`, `ratelimit_v5.py:29` | Clé `[outputs] forwarded_allow_ips`, vide par défaut, passée à uvicorn. |
| B-7 | Avec une grande plage IPv6, l'attaquant remplit la table (10 000 entrées) et l'éviction lui rend un seau plein. | `ratelimit_v5.py:52, 108-111` | Second seau par /48 ou plafond global d'échecs ; évincer d'abord les seaux pleins. |
| B-8 | Un `-C` inexistant ne fait qu'un WARNING : le serveur démarre sans mot de passe (`-s -C /nonexistent` → 200 sans identifiants). Un fichier illisible, lui, est fatal. | `config_v5.py:189-197` | Rendre fatal un `-C` absent (exit 2). |
| B-9 | En root, la configuration utilisateur (`~/.config/glances/glances.conf`, via `$HOME`) est lue avant `/etc`, sans contrôle de propriétaire : sous `sudo -E` ou un sudo qui garde `HOME`, un `critical_action` posé par l'utilisateur s'exécute en root. Identique en v4. | `config_v5.py:204-212` | En euid 0, ignorer une configuration qui n'appartient pas à root ou qui est inscriptible par d'autres ; journaliser le fichier chargé. |
| B-10 | `GlancesConfigV5.reload()` reconstruit `_merged` et perdrait `--disable-config-exec` ; aucun appelant aujourd'hui. | `config_v5.py:400-406` | Garder les surcharges CLI dans une couche réappliquée par `_load()`, limiter le rechargement à une liste de clés sûres. |
| B-11 | `/docs` et `/redoc` (actifs par défaut) chargent Swagger/ReDoc depuis jsDelivr, version flottante, sans `integrity`. | `webserver_v5.py:141-147` | Servir les fichiers localement, ou `api_doc` désactivé par défaut. |
| B-12 | `/api/5/args` renvoie les chemins absolus (`export_csv_file`, `export_json_file`, `export_graph_path`) et les regex de filtre. | `routes_v5.py:78, 432-458` | Liste blanche des drapeaux d'affichage lus par la WebUI. |
| B-13 | Plafonds de dépendances trop bas : `fastapi>=0.82.0` admet starlette < 0.49.1 (CVE-2025-62727, déni de service par en-tête `Range` sur `FileResponse`, atteignable) ; `python-jose>=3.3.0` (CVE-2024-33663/33664, non atteignables ici) ; `mcp>=1.0.0`, `requests` sans plancher. Les fichiers figés utilisent des versions sûres. | `pyproject.toml:108-113` | `starlette>=0.49.1`, `python-jose>=3.4.0`, `mcp>=1.23.0`, `requests>=2.32.4`, `jinja2>=3.1.6`. |
| B-14 | Le plugin `ip` : une redirection vers `ftp://` échappe à la garde SSRF (le gestionnaire FTP d'urllib reste actif). | `plugins/ip/model_v5.py:238-241` | `OpenerDirector` avec les seuls gestionnaires http/https, ou refus de tout autre schéma dans `redirect_request`. |
| B-15 | `--stdout`, `--stdout-csv` et `--fetch` écrivent les noms bruts : un nom de processus change le titre du terminal, efface l'écran, simule un lien. CSV sans module `csv` (virgules, formules `=`). Identique en v4. | `outputs/stdout_v5.py:95, 131-160`, `outputs/fetch_v5.py:188-197` | Remplacer C0, DEL et C1 comme le TUI, tronquer, écrire le CSV avec `csv`. |
| B-16 | La redaction de `--issue` oublie `ports.description`/`url`, `containers.command`/`name`/`engine_url`, `amps.result`, `vms.name`, `fs.mnt_point`, `wifi.ssid` et la section « Warnings » (URL `public_api` complète). | `outputs/issue_v5.py:46-54, 253-259` | Compléter la liste, passer les avertissements par le même filtre. |
| B-17 | Un serveur malveillant arrête le client sans le dire (JSON profond → `RecursionError`, jeton non-dict → `AttributeError`, l'écran reste « Connected ») ou fait sortir `--browser`. | `client_v5.py:138, 170, 344-356`, `main_v5.py:1527-1532` | Convertir toute exception en `NotAGlancesV5Server`, vérifier les types, plafonner la taille du corps. |
| B-18 | Un serveur malveillant fige toute la liste du navigateur : `_levels` en liste fait échouer tout le tour, et un corps envoyé octet par octet n'expire jamais (`timeout` par lecture). | `servers_list_v5.py:147-151, 244-251`, `client_v5.py:157` | `except Exception` par serveur, délai total par requête, taille maximale. |
| B-19 | Adresses Zeroconf annoncées acceptées telles quelles (127.0.0.1, 169.254.169.254) et sans limite de nombre (5 002 entrées acceptées) : SSRF aveugle en GET et sonde de ports depuis `-s --browser`. | `zeroconf_v5.py:423-442` | Refuser loopback, link-local, multicast, non spécifiées ; plafond (256) ; corriger les docstrings. |
| B-20 | Graphite et StatsD : un retour à la ligne dans un nom (processus via `prctl`, ou clé envoyée par un serveur en `-c --export`) injecte des points. Prometheus : `x,src:spoofed` écrase un label, `a,b` fait sauter l'export du plugin pour le cycle. | `glances_graphite/export_v5.py:32-34`, `glances_statsd/export_v5.py:31-33`, `glances_prometheus/export_v5.py:115-122` | Liste blanche `[A-Za-z0-9_.-]` ; labels Prometheus construits en dict, pas reparsés. |

Plus, au même niveau : le plugin `folders` est mis hors service par 1 100
dossiers imbriqués (`RecursionError`, `globals.py:531-552`, parcours
itératif borné) ; le socket Podman par défaut appartient à l'uid 1000
(`containers/model_v5.py:35`, root fait confiance à un utilisateur).

## Info

- **I-1** Le §8 du document d'architecture décrit, pour CVE-2026-32608,
  GHSA-73wf et GHSA-qcpp, un mécanisme (`shlex.quote`,
  `create_subprocess_shell`, `allow_shell()`) que le code n'utilise plus : il
  rend chaque argument après le découpage par `secure_popen(render=…)`, avec
  `allow_operators()`. Le test s'appelle
  `test_nested_list_value_reaches_one_argument`. À corriger dans le document.
- **I-2** JWT : un jeton sans `exp` est accepté (il faut la clé pour le
  forger) ; `sub` n'est pas comparé au nom configuré ; pas de révocation ;
  `jwt_expire_minutes` sans plafond. Passer
  `require_exp`/`require_iat`/`require_sub`.
- **I-3** Configuration et doc divergent du code : `conf/glances.conf:99`
  annonce un CORS `*` par défaut (v5 n'en met aucun), `:104` documente
  `cors_credentials` (v5 lit `cors_allow_credentials`), `password`/`username`
  et `--set-password` ne sont documentés que dans l'architecture,
  `webui_root_path`/`url_prefix` sont ignorés. Toujours dans le sens sûr.
- **I-4** Un `password` stocké invalide échoue fermé mais en silence (401
  partout) ; un caractère non ASCII fait lever `TypeError` à
  `hmac.compare_digest` : 500 sur chaque essai Basic (`security_v5.py:83`).
  Valider le format au démarrage.
- **I-5** Avec `webui_allowed_hosts`, `/status` et `/healthz` sont aussi
  filtrés (sondes Kubernetes par IP de pod → 400) ; la comparaison est
  sensible à la casse ; `[::1]:61208` ne peut jamais correspondre (limite
  Starlette). Échec fermé.
- **I-6** L'exemption de `/api/5/token` vaut pour toutes les méthodes ; un
  `GET` non authentifié tombe sur la route plugin et rend 404. Sans effet ;
  n'exempter que `POST`.
- **I-7** Code mort : `RateLimitMiddleware._reserve_auth_try`
  (`ratelimit_v5.py:123-124`).
- **I-8** `--fetch-template` utilise un environnement Jinja2 non sandboxé
  (`fetch_v5.py:197`). Les données surveillées n'atteignent jamais la source
  du modèle ; seul un modèle partagé ou téléchargé est un risque.
  `SandboxedEnvironment` suffit.
- **I-9** MCP : `top_processes_report` met les lignes de commande des
  processus dans le prompt (injection de prompt vers le consommateur LLM). Pas
  d'outil MCP, donc rien ne s'exécute.
- **I-10** `GLANCES_<SECTION>__<KEY>` peut tout changer, sécurité comprise
  (`OUTPUTS__PASSWORD`, `OUTPUTS__AUTH_FAIL_PER_MINUTE=0`,
  `<plugin>__<level>_ACTION`), et `$LOG_CFG` passe un JSON à `dictConfig`, dont
  les fabriques `"()"` exécutent n'importe quel appelable. Même principal ;
  sudo efface ces variables. À documenter ; en root, ignorer un `LOG_CFG` qui
  n'appartient pas à root.
- **I-11** Exporteurs sans TLS ou sans vérification par défaut, comme en v4 :
  CouchDB toujours `http://`, Kafka sans SSL/SASL, ClickHouse sans `secure`,
  TimescaleDB en `sslmode=prefer`, Cassandra sans `ssl_context`, MQTT en clair
  avec `port=8883` dans la configuration livrée.
- **I-12** Fuites partielles de mot de passe dans les journaux : URL RabbitMQ
  non encodée (un `/` ou `#` met un fragment dans le message CRITICAL), la
  redaction NATS manque les URL sans schéma et les mots de passe avec `@`,
  l'exporteur restful journalise son URL complète en INFO.
- **I-13** Le navigateur ignore `[client] ssl_verify` (il vérifie toujours, ce
  qui est plus strict) et `-u` ; il envoie `[passwords]` en HTTP clair avec un
  simple WARNING que l'utilisateur du TUI ne voit pas.
- **I-14** Déni de service bon marché : la limite générale est désactivée par
  défaut, et `/all`, `/processlist`, `/history` recopient les données à chaque
  appel (`history_v5.py:190-195`, `nb` ne réduit pas le travail). Le levier
  est `rate_limit_per_minute`.

---

## Réponses aux points ouverts du §4.8

| Point du §4.8 | Réponse |
|---|---|
| `/api/5/config` redacté peut-il rester sans authentification ? | **Non, pas en l'état** (M1). Recommandation : une liste blanche des clés utiles à l'interface sans authentification, le dump complet seulement avec un mot de passe. La redaction actuelle reste appliquée même avec mot de passe, et `[passwords]` est bloqué quelle que soit la casse (`config_v5.py:373`). |
| `UNAUTH_PATHS` sans énumération ni oracle ? | **Sain pour les chemins** : correspondance exacte d'un `frozenset` sur le chemin (`webserver_v5.py:73, 446`). `/api/5/token/../config`, `%2f`, `/status/../…`, slash final, casse, `//`, forme absolue : tous 401 ou 404 sur un uvicorn réel. **Un oracle** : le temps de réponse révèle le nom d'utilisateur (B-1). |
| Rate limiting câblé et sain ? | **Câblé**, ordre conforme (`TrustedHost → RateLimit → CORS → Auth`, `webserver_v5.py:159-162`), table bornée (~1 Mo pour 10 000 entrées), IPv6 groupé par /64, IPv4 mappé ramené à IPv4. **À corriger** : M3, B-6, B-7. |
| Chaque CVE du §8 revérifiée contre le code v5 | Voir le tableau suivant. |
| Aucun module v4 en fin de vie importé par un fichier `_v5` | **Non tenu** (B1). Aucun module v4 vulnérable n'est **exécuté** (sonde : 0 appel à `Config`, `system_exec`, `GlancesActions`), mais tous les `__init__.py` v4 sont chargés et `glances.config` reste livré. |

## Revérification des CVE du §8

| Avis | Verdict | Code v5 | Test qui le verrouille |
|---|---|---|---|
| CVE-2026-30928 / 32609 (secrets dans config/args) | Sain pour les noms de clés ; **insuffisant pour les valeurs** (M1, B-12) | `config_v5.py:111-135, 363-396`, `routes_v5.py:78` | `tests/test_config_v5.py`, `test_routes_v5.py::test_args_redacts_the_username` |
| CVE-2026-30930 (SQL TimescaleDB) | Sain | `glances_timescaledb/export_v5.py` (`sql.Identifier` + `%%`, paramètres) | `test_phase3_cve_v5.py` : 9/9 sur un vrai PostgreSQL 16 |
| CVE-2026-32596 (WARNING sans authentification) | Sain | `webserver_v5.py:170-174` | `test_webserver_v5.py` |
| CVE-2026-32608, GHSA-73wf, GHSA-qcpp (actions) | Sain, par un autre mécanisme que celui du §8 (I-1) | `secure.py:55-125`, `actions_v5/shell/__init__.py:296-305` | `test_action_shell_v5.py:103, 114, 134, 288` |
| CVE-2026-32610, 34839, GHSA-fp27 (CORS) | Sain | `webserver_v5.py:374-400` | `test_webserver_v5.py::test_cors_multi_origin_allowlist_with_wildcard_downgrades` et suivants |
| CVE-2026-32611 (DuckDB) | Sain | `glances_duckdb/export_v5.py` | `test_duckdb_stores_hostile_names_as_data_on_a_real_database` |
| CVE-2026-32632 (DNS rebinding) | Sain quand `webui_allowed_hosts` est défini ; **défaut loopback non protégé** (M2) | `webserver_v5.py:353-371` | `test_trusted_host_*` |
| CVE-2026-32633 (serverslist) | Sain | `servers_list_v5.py:84-117`, `routes_v5.py:419-429` | `test_serverslist_never_carries_a_credential` |
| CVE-2026-32634 (Zeroconf) | Sain pour les mots de passe configurés ; risque résiduel M11, B-19 | `servers_list_v5.py:182-189` | `test_a_discovered_server_is_sent_no_configured_credential` |
| CVE-2026-33533, 46608, 46611 (XML-RPC) | Sans objet : pas de XML-RPC en v5 | — | — |
| CVE-2026-33641 (backticks dans la config) | Sain par architecture (`interpolation=None`, `config_v5.py:223`, sonde : rien n'est exécuté) ; **pas de test v5** ; `glances.config` v4 reste livré (B1) | `config_v5.py` | à ajouter |
| CVE-2026-35587 (SSRF `ip`) | Sain pour http/https ; **brèche FTP** (B-14) | `plugins/ip/model_v5.py:60-200, 278-286` | `test_plugin_ip_v5.py:111-161, 272, 424-494` |
| CVE-2026-35588 (Cassandra) | Sain | `glances_cassandra/export_v5.py:51-95, 148-149` | `test_cassandra_allowlist_refuses_every_hostile_identifier` |
| CVE-2026-46606 (virsh) | Sain (liste d'arguments, `shell=False`) ; option injectable faute de `--` (I : faible, accès libvirt requis) | `vms/engines/virsh.py:38-50, 209, 228` | `test_plugin_virsh_injection.py:88-181` |
| CVE-2026-46607 (pickle du cache de version) | Pas encore porté : v5 n'a pas de vérification de version | — | à écrire avec le portage (GAP de la migration des tests) |
| CVE-2026-53925, GHSA-59fj, CVE-2026-68519 (`--disable-config-exec`) | **Régression partielle** sous `--issue`/`--fetch`, contournable par `sh -c` (M4) | `main_v5.py:1154-1160`, `amps_list_v5.py:66-68`, `shell/__init__.py:271-282` | `test_action_shell_v5.py:307-352`, `test_main_v5.py:458`, `test_amps_list_v5.py:185, 202` (aucun ne couvre `--issue`/`--fetch`) |
| CVE-2026-68520 (identifiants dans une URL) | Sain sauf mot de passe contenant `@` (M1) | `config_v5.py:64, 389` | `tests/test_config_v5.py` |
| Constat P3-7 (`[passwords]` dans `/config`) | Sain | `config_v5.py:143, 373` | `test_config_route_never_serves_the_passwords_section` |
| GHSA-mcm7 (chargement de plugins) | Sain : imports limités à l'espace de noms du paquet, noms vérifiés par `isidentifier()`, pas de modification de `sys.path` ; **pas de test dédié** | `main_v5.py:851-857, 1026`, `amps_list_v5.py:126-144` | à ajouter |
| Durcissement terminal (sans avis) | Sain dans le TUI (C0/DEL remplacés, ncurses neutralise ESC/C1) ; **non appliqué** à `--stdout`, `--stdout-csv`, `--fetch` (B-15) | `glances_curses_v5.py:65, 2300` | `test_curses_v5.py` |

## Vérifié et sain

- **Authentification :** PBKDF2 hors de la boucle asyncio, comparaison à temps
  constant, clé JWT `secrets.token_urlsafe(32)` en mémoire si non configurée,
  `algorithms=["HS256"]` + émetteur : `alg=none`, HS512, mauvaise clé, jeton
  expiré, `nbf` futur, `sub` non chaîne, tous refusés
  (`security_v5.py:45-139`).
- **`--set-password` :** `getpass` avec confirmation, mot de passe vide
  refusé, hash affiché sur stdout uniquement, aucun fichier écrit
  (`main_v5.py:1043-1077`).
- **Avec un mot de passe**, sans identifiants, en GET/POST/OPTIONS/HEAD : 401
  sur `/`, `/static/*`, `/docs`, `/redoc`, `/openapi.json`, `/browser`,
  `/api/5/*`, `/mcp`, `/mcp/sse`, `/mcp/messages/`. Pas de route WebSocket.
- **Fichiers statiques :** toutes les variantes de traversée (`..`, `%2f`,
  `%2e%2e`, `%5c`, `%00`) → 404. `/static/glances5.js` en `no-cache`.
- **Validation des entrées REST :** noms de plugins par dictionnaire, clé de
  tri sur tuple fixe, `pid` typé `int`, `nb` borné, aucune regex fournie par
  le client, aucun corps lu. Aucune réponse 500 en balayant toutes les
  routes de tous les plugins.
- **MCP :** opt-in, derrière l'authentification, `TransportSecuritySettings`
  correct (Host étranger → 421), aucun outil, URI inconnues refusées.
- **Exécution de commandes :** contexte des actions sans appelable, actions
  dédoublonnées dans un pool de 4, `ChevronError` = commande refusée ; AMP
  limités à un run à la fois, systemd sans shell ; `secure_popen` gère les
  délais et récolte les pipelines ; `ports` vérifie TLS par défaut et garde
  identifiants et proxys hors du payload ; URL des moteurs de conteneurs
  redactées.
- **Client et navigateur :** `requests` retire `Authorization` sur une
  redirection vers un autre hôte, port ou schéma (sonde) ; jamais
  d'identifiant dans une URL ; jeton en mémoire seulement ; TLS vérifié par
  défaut ; alias Zeroconf limité à 64 caractères imprimables ; seules les
  annonces `api=5` sont retenues.
- **Exporteurs :** échappement correct du line protocol InfluxDB par les
  bibliothèques, sujets NATS validés, topics MQTT en liste blanche,
  identifiants ClickHouse vérifiés puis cités, Kafka/ZeroMQ/Mongo/CouchDB/
  Elasticsearch en JSON encadré, RabbitMQ `amqps` vérifie les certificats,
  Prometheus n'expose que des nombres sur `localhost` (configuration livrée).
- **Primitives dangereuses** dans tout le code v5 : ni pickle, marshal,
  `yaml.load`, `eval`/`exec`, `shell=True`, `os.system`, `mktemp`, `0o777`,
  `random` pour un secret, ni md5/sha1. `verify=False` seulement en M9.
- **Journaux :** aucun mot de passe ni jeton dans un appel `logger.*` v5 ;
  journal d'accès uvicorn désactivé.
- **WebUI v5 :** ni `v-html`, ni `innerHTML`, ni `eval` ; tout passe par
  l'échappement de Vue ; lien du navigateur limité à http(s) sans
  identifiant ; aucun mot de passe ni jeton dans le navigateur (`localStorage`
  ne contient que `glances.refresh`) ; CSP en meta
  `default-src 'none'; script-src 'self'`.

**Non vérifié :** un MITM réel contre M9 ; l'analyse des lignes injectées par
de vrais démons carbon et statsd (seuls les octets sur le réseau ont été
capturés) ; l'appel interne de `smartctl` par pySMART et l'analyse de
pymdstat ; que le bundle `public/glances5.js` corresponde aux sources ;
qu'une requête POST cross-site emporte les identifiants Basic en cache dans
un vrai navigateur ; un slowloris contre uvicorn.

---

## Plan de correction

**Avant la suppression du code v4 (fusion) :** B1.

**Avant `5.0.0b1` :**

1. M1 — `/api/5/config` en liste blanche, regex `@` corrigée, query de `ports`.
2. M2 — TrustedHost loopback par défaut.
3. M4 — `--disable-config-exec` appliqué dans `main()`, tests `--issue` et
   `--fetch`, décision sur `sh -c`.
4. M3 — ne pas consommer d'essai pour un identifiant déjà validé.
5. M7, M8 — plus aucun fichier dans un dossier temporaire partagé.
6. M10 — options de plugins redactées avant export.
7. B-4 — TLS branché, ou WARNING.
8. B-13 — planchers de dépendances.
9. Tests de non-régression manquants : CVE-2026-33641, GHSA-mcm7.

**Avant `5.0.0` :** M5, M6, M9, M11 et les constats bas restants ; I-1 et
I-3 (documentation).

Les constats identiques en v4 (M4 `sh -c`, M7, M8, M9, M10, B-9, B-15) sont
à reporter sur `support/glancesv4`.
