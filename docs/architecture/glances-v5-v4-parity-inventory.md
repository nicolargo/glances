# Glances v5 — inventaire de parité v4 → v5

**Date** : 2026-09-10 · **Branche** : `develop-v5` (`7cf52498`) · **Référence v4** : `develop` (`2bf3aadb`)

Ce document inventorie les fonctions de Glances v4 sur ses **trois surfaces
utilisateur** — options de ligne de commande, clés du fichier de configuration,
raccourcis clavier du TUI — et donne l'état de chacune en v5.

Il est le complément détaillé de la table *v4 feature parity backlog* de
`glances-v5-architecture-decisions.md` §10 : la table y donne les chantiers, ce
document donne l'inventaire ligne à ligne dont ils sortent.

## Méthode

- **Source de vérité v4** : le code, pas la documentation — l'`argparse` de
  `glances/main.py`, les appels `config.get*` du code v4, la table de touches de
  `glances/outputs/glances_curses.py`. Le fichier `conf/glances.conf` livré sert
  de second filet (une clé commentée reste une clé supportée).
- **Vérification v5** : une option/clé/touche n'est comptée `✅ porté` que si sa
  valeur **atteint réellement** le code qui la consomme. Présence dans le parser
  v5, ou dans le fichier de conf partagé entre les deux branches, ne prouve rien.
- **Piège inverse** : v5 concentre beaucoup de comportements dans la machinerie
  générique (`base_v5.py` pour `show`/`hide`/`disable`/`refresh`,
  `thresholds_v5.py` pour toute la famille des seuils et des actions). Une clé
  peut donc être honorée sans apparaître dans le fichier de son plugin.
- Chaque statut cite un `file:line` réellement ouvert. Aucun statut n'est
  « déduit » : les cas non tranchés portent `❓ indéterminé` (il n'y en a aucun
  dans cette édition).

### Vocabulaire des statuts

| Statut | Sens |
|---|---|
| `✅ porté` | Présent en v5 et effectivement câblé jusqu'au consommateur. |
| `⚠️ partiel` | Déclaré ou lu, mais partiellement câblé ou avec une différence de comportement — la note dit laquelle. |
| `❌ absent` | v4 l'a, v5 ne l'a pas. Inclut ce qui est prévu pour une phase ultérieure (la note le précise). |
| `🚫 retiré (décision)` | Abandon délibéré, avec l'emplacement de la décision. |
| `❓ indéterminé` | N'a pas pu être établi. |

## Synthèse

| Surface | Total | ✅ porté | ⚠️ partiel | ❌ absent | 🚫 retiré |
|---|---:|---:|---:|---:|---:|
| Options CLI | 86 | 16 | 10 | 59 | 1 |
| Clés de configuration | 212 | 146 | 16 | 47 | 3 |
| Hotkeys TUI | 62 | 15 | 0 | 47 | 0 |
| **Total** | **360** | **177** | **26** | **153** | **4** |

**2026-09-10 — parity wave 1.** 13 lignes recomptées ici sont passées de
`⚠️ partiel`/`❌ absent` à `✅ porté` : CLI `--disable-unicode`, `--byte` (2) ;
config `[network]` `hide_no_up`, `hide_no_ip`, `hide_zero`,
`hide_threshold_bytes`, `alias`, `[diskio]` `hide_zero`,
`hide_threshold_bytes`, `alias`, `[fs]` `free_space`, `allow`, `alias` (11).
Counted by re-scanning the status column of every row in Parts 1–3 (the
legend/vocabulary rows are not tables and are excluded), not by arithmetic on
the prior totals. See
`docs/superpowers/specs/2026-09-10-glances-v5-parity-wave1-design.md` §4–5.

La lecture de ces chiffres demande une précaution : les trois surfaces ne pèsent
pas le même poids. La configuration — le cœur fonctionnel, 212 clés — est portée
à **69 %**, et l'essentiel de ce qui manque est du phasage assumé (18 exporteurs
sur 24 et le mode browser sont des chantiers de Phase 3). Le TUI et la CLI sont
au contraire très en retard, et c'est là que se trouvent les régressions
ressenties par un utilisateur qui lancerait v5 aujourd'hui.

## Les 10 écarts qui comptent

Classés par ce qu'ils coûtent à un utilisateur v4 qui passerait à v5 aujourd'hui.

1. **Toute la gestion interactive des processus a disparu du TUI** — pas de
   curseur (flèches), pas de `k` (kill), pas de `+`/`-` (nice), pas de `ENTER`
   (filtre), pas de `e` (stats étendues). v5 handle 15 touches, v4 en handle 62.
2. **Les 23 bascules d'affichage par plugin** (`n` réseau, `d` disque, `f` fs,
   `2` sidebar, `3` quicklook…) sont absentes : seules `1` et `4` survivent.
3. **`--bind` change de défaut** : `0.0.0.0` (v4) → `127.0.0.1` (v5). C'est un
   durcissement délibéré et documenté (`…decisions.md:835`), mais **tout
   déploiement serveur non configuré — conteneurs en tête — cesse de répondre**.
   À écrire noir sur blanc dans les notes de version.
4. **`-s` change de sens et `-w` disparaît** : en v4 `-s` = serveur XML-RPC et
   `-w` = serveur web ; en v5 `-s` = API REST + WebUI. Tout script v4 en `-w`
   casse silencieusement.
5. **La famille `<...>_log` n'existe plus** : v5 historise toute transition
   ≥ warning sans possibilité d'exclusion. `[cpu] total_log`, `[load] log`,
   `[network] wlan0_rx_log`… sont des clés mortes.
6. **Des seuils renommés, dont un changement d'unité** :
   `[network] rx_*`/`tx_*` → `bytes_recv_*`/`bytes_sent_*` **et pourcentage →
   ratio [0,1]** ; `[processlist] cpu_*` → `cpu_percent_*` ;
   `[fs] /_careful` → `/_percent_careful`. Les anciennes clés restent ignorées
   (décision maintenue, parity wave 1) mais ne sont plus **silencieuses** :
   une clé de seuil non reconnue déclenche désormais une WARNING au démarrage
   (`base_v5.py::_warn_unknown_threshold_keys`, `…decisions.md` §3.2).
7. ~~**Les filtres d'affichage** `hide_zero`, `hide_threshold_bytes`,
   `hide_no_up`, `hide_no_ip`, `[fs] allow`, `[fs] free_space` sont absents, et
   `alias` n'est porté que par `sensors`~~ — **corrigé (parity wave 1,
   2026-09-10)** : tous portés en générique dans `base_v5` pour `network`,
   `diskio`, `fs` ; `sensors` garde son propre mécanisme, inchangé. Voir §14,
   §18, §19 ci-dessous.
8. **18 exporteurs sur 24 et le mode browser** ne sont pas portés — phasage
   assumé (Phase 3), mais c'est le plus gros volume de clés inertes.
9. ~~**Deux options v5 déclarées mais mortes** : `--disable-unicode` …
   `--byte` …~~ — **corrigées (parity wave 1, 2026-09-10)** : `--disable-unicode`
   est déclaré dans `build_parser()` ; `--byte` est lu par le renderer réseau.
   Voir §4 ci-dessus.
10. **Aucun alias court hors `-C -d -s -b`** : `-V -p -B -u -t -w -c -q -f -0..-6`
    sont absents. Chaque ligne de commande v4 un peu ancienne casse.

## Deux trouvailles hors périmètre

- **`[hddtemp] host`/`port` est une section morte dans les deux branches** :
  le `plugin_name` de `HddtempPlugin` se résout à `sensors`, donc v4 comme v5
  lisent `[sensors] host`/`port`. C'est un bug de documentation de
  `conf/glances.conf`, à corriger côté v4.
- **La touche `r` de v4 ne fait pas ce que son aide annonce** : l'aide intégrée
  et `docs/cmds.rst` disent « Reset history », le code bascule `disable_smart`.
  Bug v4, indépendant de v5.

---


## Partie 1 — Options de ligne de commande

**Périmètre** : toutes les options déclarées par l'`argparse` de v4
(`glances/main.py:182-708`, méthode `init_args()`), plus les entrées
documentées dans `docs/cmds.rst` qui n'existent plus dans le code v4.

**Référence v5** : `glances/main_v5.py:78-261` (`build_parser()`), et la
machinerie générique en aval (`glances/config_v5.py`,
`glances/plugins/plugin/base_v5.py`, `glances/scheduler_v5.py`,
`glances/webserver_v5.py`, `glances/outputs/glances_curses_v5.py`,
`glances/plugins/*/render_curses_v5.py`).

**Règle appliquée** : une option n'est `✅ porté` que si sa valeur atteint
réellement le code qui la consomme. Présence dans le parser v5 ≠ portage.

**Vocabulaire de statut** : `✅ porté` · `⚠️ partiel` · `❌ absent` ·
`🚫 retiré (décision)` · `❓ indéterminé`.

---

### 1. Mode / serveur / client

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-s`, `--server` | `glances/main.py:397` | ⚠️ partiel | `glances/main_v5.py:116` (parser) ; `glances/main_v5.py:597` (branche serveur) ; `glances/main_v5.py:694` (uvicorn) | Le drapeau existe et est câblé, mais sa **sémantique change** : en v4 `-s` démarre le serveur XML-RPC (`:61209`) ; en v5 il démarre l'API REST FastAPI + WebUI (`:61208`), c'est-à-dire le rôle du `-w` de v4. Retrait de XML-RPC : `docs/architecture/glances-v5-architecture-decisions.md:22-28` (§1.1). |
| `-w`, `--webserver` | `glances/main.py:462` | ❌ absent | `glances/main_v5.py:116` (le seul mode serveur v5 est `-s`) | Le comportement (REST + WebUI) est celui de `-s` en v5. Le drapeau `-w` lui-même n'existe pas ; un script v4 utilisant `-w` échoue. |
| `-c`, `--client` | `glances/main.py:394` | ❌ absent | `glances/main_v5.py:78-261` (aucune option client dans le parser) | Prévu **Phase 3** — `docs/architecture/glances-v5-architecture-decisions.md:1126` (« Phase 3 — Remote client + all exporters + browser mode ») et §6 `:904-908`. Question ouverte confirmée `:163-166`. |
| `--browser` | `glances/main.py:400` | ❌ absent | `glances/main_v5.py:78-261` (aucune option browser) | Mode explicitement **préservé** mais non encore implémenté : `docs/architecture/glances-v5-architecture-decisions.md:897` (§5) ; prévu Phase 3 (`:1126`). |
| `--disable-autodiscover` | `glances/main.py:407` | ❌ absent | `glances/main_v5.py:78-261` | L'autodiscovery réseau n'existe pas en v5 (« to be studied ») — `docs/architecture/glances-v5-architecture-decisions.md:900`. Prévu Phase 3. |
| `-p`, `--port` | `glances/main.py:414` | ⚠️ partiel | `glances/main_v5.py:96` (parser, `--port` seul) ; `glances/main_v5.py:592` (résolution `args.port or [outputs] port`) | La forme longue est portée et câblée ; **l'alias court `-p` n'existe pas** en v5. |
| `-B`, `--bind` | `glances/main.py:422` | ⚠️ partiel | `glances/main_v5.py:90` (parser, `--bind` seul) ; `glances/main_v5.py:591` (résolution) ; `glances/main_v5.py:71` (`_DEFAULT_BIND_ADDRESS = "127.0.0.1"`) | Deux différences : (1) **pas d'alias court `-B`** ; (2) le défaut passe de `0.0.0.0` (v4, `main.py:425`) à `127.0.0.1` (v5) — **breaking change** pour les déploiements non configurés. |
| `--cached-time` | `glances/main.py:483` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/scheduler_v5.py:96-102` | Le modèle « serveur passif qui collecte à la demande du client » a disparu : le scheduler v5 poll en continu (`docs/architecture/glances-v5-architecture-decisions.md:937`, §7.1). Le levier CPU équivalent est `[<plugin>] refresh`. Aucune décision écrite ne nomme explicitement `--cached-time`, d'où `absent` et non `retiré`. |
| `--stop-after` | `glances/main.py:490` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/scheduler_v5.py:96` (aucun compteur de cycles) | Utilisé par les tests et les scripts de bench v4. Aucun équivalent v5. |
| `--open-web-browser` | `glances/main.py:497` | ❌ absent | `glances/main_v5.py:745-748` (log de l'URL uniquement) | Aucune ouverture de navigateur en v5. |
| `--disable-webui` | `glances/main.py:231` | ✅ porté | `glances/main_v5.py:128` (parser) ; `glances/webserver_v5.py:145` (`if args is not None and not getattr(args, "disable_webui", False): _wire_webui(app)`) | En v5 le drapeau n'a de sens qu'avec `-s` (aide `main_v5.py:131`). |
| `--enable-mcp` | `glances/main.py:470` | ✅ porté | `glances/main_v5.py:133` (parser) ; `glances/main_v5.py:606-610` (overlay `[outputs] enable_mcp`) ; `glances/webserver_v5.py:200` (lecture du gate) | Contrainte v5 supplémentaire : `--enable-mcp` sans `-s` est une **erreur fatale** (`glances/main_v5.py:281-282`), là où v4 l'ignorait. Double opt-in documenté §11.1 (`docs/architecture/glances-v5-architecture-decisions.md:1174+`). |
| `--mcp-path` | `glances/main.py:477` | ❌ absent | `glances/main_v5.py:133` (seul `--enable-mcp` existe) ; `glances/webserver_v5.py:200-212` | Le point de montage `/mcp` n'est pas configurable en v5. |
| `-q`, `--quiet` | `glances/main.py:505` | ✅ porté | `glances/main_v5.py:189` (parser, `--quiet` / `--no-tui` → `dest="no_tui"`) ; `glances/main_v5.py:616` (`elif not getattr(args, "no_tui", False)`) | **Pas d'alias court `-q`** en v5 (forme longue seulement) — à ce titre on pourrait aussi le lire comme partiel ; le comportement, lui, est intégralement câblé. Le devenir du drapeau est une question ouverte : `docs/architecture/glances-v5-architecture-decisions.md:155-162`. |

### 2. Client/serveur — authentification et SNMP

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-u <username>` | `glances/main.py:429` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/security_v5.py:119-122` (les identifiants viennent de `[outputs] username`/`password`) | En v5 les identifiants sont **uniquement** dans `glances.conf`. |
| `--username` (prompt) | `glances/main.py:430` | ❌ absent | idem ci-dessus | Aucun prompt interactif au démarrage en v5. |
| `--password` (prompt) | `glances/main.py:437` | ⚠️ partiel | `glances/main_v5.py:265` (`--set-password`) ; `glances/main_v5.py:493-525` (`cli_set_password()`) | v5 offre `--set-password`, qui **génère et affiche** un hash PBKDF2 à coller dans `[outputs] password`. Ce n'est pas le même comportement : v4 définit *et persiste* le mot de passe (fichier `.pwd`) et l'utilise pour la session courante ; v5 ne modifie aucun fichier et n'a pas de prompt au démarrage. Les hashes v4 ne sont pas compatibles v5 (`glances/security_v5.py:23`). |
| `--snmp-community` | `glances/main.py:444` | ❌ absent | `glances/main_v5.py:78-261` | Le mode SNMP (fallback client sur machine sans Glances) n'existe pas en v5. Aucune décision écrite ne le retire explicitement — statut `absent`, pas `retiré`. |
| `--snmp-port` | `glances/main.py:445` | ❌ absent | idem | idem. |
| `--snmp-version` | `glances/main.py:446` | ❌ absent | idem | idem. |
| `--snmp-user` | `glances/main.py:447` | ❌ absent | idem | idem. |
| `--snmp-auth` | `glances/main.py:448` | ❌ absent | idem | idem. |
| `--snmp-force` | `glances/main.py:451` | ❌ absent | idem | idem. |

### 3. Configuration / plugins

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-C`, `--config` | `glances/main.py:193` / `:197` (branche shtab) | ✅ porté | `glances/main_v5.py:83` (parser, `dest="config_path"`) ; `glances/main_v5.py:742` (`GlancesConfigV5(cli_config_path=args.config_path)`) ; `glances/config_v5.py:140-141` | v5 ajoute par-dessus un overlay d'environnement `GLANCES_<SECTION>__<KEY>` (§2, `docs/architecture/glances-v5-architecture-decisions.md:171-176`). `config_path` est **redacté** dans `/api/5/args` (`glances/routes_v5.py:70`). |
| `-P`, `--plugins` (`plugin_dir`) | `glances/main.py:198` | ❌ absent | `glances/main_v5.py:320-324` (`pkgutil.iter_modules(_plugins_pkg.__path__)` — découverte limitée au paquet `glances.plugins`) | Pas de répertoire de plugins externe en v5. |
| `--modules-list`, `--module-list` | `glances/main.py:200` | ❌ absent | `glances/main_v5.py:78-261` (pas d'option) ; `glances/main_v5.py:306` (`discover_plugin_classes()` existe mais n'est pas exposé en CLI) | La primitive de listage existe, le drapeau non. |
| `--disable-plugin`, `--disable-plugins`, `--disable` | `glances/main.py:208` | ✅ porté | `glances/main_v5.py:172` (parser) ; `glances/main_v5.py:437-440` (overlay `[<plugin>] disable`) ; `glances/plugins/plugin/base_v5.py:159-166` (`is_disabled()`) | Divergence assumée v5 : un **nom de plugin inconnu est fatal** (`glances/main_v5.py:424-427`), là où v4 l'ignorait silencieusement. Le couplage `processcount` → `processlist` de v4 est reproduit (`glances/main_v5.py:447-451`). |
| `--enable-plugin`, `--enable-plugins`, `--enable` | `glances/main.py:216` | ✅ porté | `glances/main_v5.py:181` (parser) ; `glances/main_v5.py:439-440` | Sémantique v4 conservée : `enable` gagne sur `disable`. `--disable-plugin all` exige `--enable-plugin` (`glances/main_v5.py:429-434`). |
| `--disable-process` | `glances/main.py:223` | ❌ absent | `glances/main_v5.py:78-261` (aucun `disable_process`) | Équivalent générique v5 : `--disable-plugin processcount` (qui désactive aussi `processlist`, `glances/main_v5.py:447-449`). Le drapeau lui-même n'existe pas. |
| `--enable-irq` | `glances/main.py:319` | ❌ absent | `glances/plugins/irq/model_v5.py:92` (`DISABLED_BY_DEFAULT = True`) ; `glances/plugins/plugin/base_v5.py:166` | Comportement disponible génériquement via `--enable-plugin irq`. Le raccourci `--enable-irq` n'existe pas. |
| `-3`, `--disable-quicklook` | `glances/main.py:271` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/outputs/glances_curses_v5.py:147-165` (table des hotkeys, pas de `3`) | Équivalent générique : `--disable-plugin quicklook`. Ni le drapeau ni la hotkey `3` n'existent en v5. |
| `-2`, `--disable-left-sidebar` | `glances/main.py:263` | ❌ absent | `glances/outputs/glances_curses_v5.py:147-165` (pas de hotkey `2`) | En v4 c'est un basculement TUI (hotkey `2`, `glances/outputs/glances_curses.py:45`), pas une désactivation de plugin. Aucun équivalent v5 (ni CLI ni hotkey). |
| `-5`, `--disable-top` | `glances/main.py:287` | ❌ absent | `glances/outputs/glances_curses_v5.py:147-165` (pas de hotkey `5`) | Idem : bascule TUI v4 (`glances/outputs/glances_curses.py:339-341`) sans équivalent v5. |

### 4. Affichage / TUI

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-1`, `--percpu`, `--per-cpu` | `glances/main.py:254` | ⚠️ partiel | `glances/main_v5.py:200` (parser, `--percpu` seul) ; `glances/main_v5.py:654` ; `glances/outputs/glances_curses_v5.py:238`, `:795` ; `glances/plugins/quicklook/render_curses_v5.py:168` | Valeur bien acheminée jusqu'au rendu quicklook. Deux différences : **pas d'alias `-1` ni `--per-cpu`** ; et en v5 le drapeau pilote les barres per-core *dans quicklook*, distinct de la hotkey `1` qui échange le bloc TOP `cpu`↔`percpu` (`glances/outputs/glances_curses_v5.py:158`, `:234-235`). |
| `-4`, `--full-quicklook` | `glances/main.py:279` | ⚠️ partiel | `glances/main_v5.py:207` (parser) ; `glances/main_v5.py:653` ; `glances/outputs/glances_curses_v5.py:237`, `:310` ; `glances/outputs/curses_renderer_v5.py:1430` | Entièrement câblé (drapeau + hotkey `4`). **Pas d'alias court `-4`.** |
| `-6`, `--meangpu` | `glances/main.py:295` | ⚠️ partiel | `glances/main_v5.py:214` (parser) ; `glances/main_v5.py:655` ; `glances/outputs/glances_curses_v5.py:242`, `:796` ; `glances/plugins/gpu/render_curses_v5.py:134` | Câblé jusqu'au renderer GPU. **Pas d'alias court `-6`.** |
| `--fahrenheit` | `glances/main.py:633` | ✅ porté | `glances/main_v5.py:221` (parser) ; `glances/main_v5.py:656` ; `glances/outputs/glances_curses_v5.py:243`, `:797` ; `glances/plugins/sensors/render_curses_v5.py:107` ; `glances/plugins/gpu/render_curses_v5.py:135` | Appliqué aux capteurs *et* au GPU, comme en v4. |
| `--hide-public-info` | `glances/main.py:661` | ✅ porté | `glances/main_v5.py:228` (parser) ; `glances/main_v5.py:657` ; `glances/outputs/glances_curses_v5.py:244`, `:798` ; `glances/plugins/ip/render_curses_v5.py:44` | |
| `-b`, `--byte` | `glances/main.py:604` | ✅ porté | `glances/main_v5.py:235` (parser) ; `glances/main_v5.py:658` ; `glances/outputs/glances_curses_v5.py:247`, `:799` ; `glances/plugins/containers/render_curses_v5.py:257` ; `glances/plugins/network/render_curses_v5.py:100` (`byte = bool((view or {}).get("byte"))`), `:66-69` (pas de ×8, pas de suffixe `b`) | **Corrigé (parity wave 1, 2026-09-10)** : le renderer réseau lit désormais `view["byte"]`, v4 parity (`network/__init__.py:273`). Le `TODO(G2+)` sur `max_width`/`args` reste ouvert (portée hors sujet) mais ne concerne plus `--byte`. |
| `-0`, `--disable-irix` | `glances/main.py:246` | ❌ absent | `glances/plugins/load/render_curses_v5.py:33` (« Irix mode (v4 `args.disable_irix`) is not yet plumbed through v5 ») | Constat écrit dans le code v5. |
| `--light`, `--enable-light` | `glances/main.py:238` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/outputs/glances_curses_v5.py:226` (`[outputs] theme` = dark/light, **couleurs** et non « light mode ») | Attention au faux ami : `theme=light` en v5 est une palette de couleurs, pas le « light mode » de v4 (n'afficher que le menu du haut). |
| `--disable-bold` | `glances/main.py:305` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/outputs/glances_curses_v5.py:1408`, `:1412` (le gras est appliqué inconditionnellement au rôle HEADER) | |
| `--disable-bg` | `glances/main.py:312` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/outputs/glances_curses_v5.py:1376-1378` (paires de couleurs inversées toujours initialisées) | |
| `--disable-unicode` | `glances/main.py:654` | ✅ porté | `glances/main_v5.py:250` (`add_argument("--disable-unicode", dest="disable_unicode", ...)`) ; `glances/main_v5.py:679` (`disable_unicode=getattr(args, "disable_unicode", False)`) ; `glances/outputs/glances_curses_v5.py:203`, `:252` | **Corrigé (parity wave 1, 2026-09-10)** : l'option est désormais déclarée dans `build_parser()` ; le mécanisme consommateur existait déjà et est inchangé. |
| `--sparkline` | `glances/main.py:647` | ❌ absent | `glances/plugins/quicklook/model_v5.py:19` (« **No sparkline** (no v5 history store yet) — bars only ») | Dépend de l'absence d'historique en v5 (voir `--disable-history`). |
| `--disable-separator` (`enable_separator`) | `glances/main.py:329` | ❌ absent | `glances/main_v5.py:78-261` | Aucune occurrence de `enable_separator`/`disable_separator` dans les fichiers `*_v5.py`. |
| `--disable-cursor` | `glances/main.py:336` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/outputs/glances_curses_v5.py:147-165` | Il n'y a pas de curseur de sélection de processus en v5, donc rien à désactiver. |
| `--arrow-keys-sort` | `glances/main.py:343` | ❌ absent | `glances/outputs/glances_curses_v5.py:148-156` (tri par lettres `a c m i t p u o` uniquement) | Issue v4 #3385, sans équivalent v5. |
| `--strftime` (`strftime_format`) | `glances/main.py:685` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/plugins/now/model_v5.py:12` (la clé de config `[global] strftime_format` est bien lue) | Le **comportement** est disponible par configuration ; le drapeau CLI ne l'est pas. |
| `--disable-history` | `glances/main.py:298` | ❌ absent | `glances/webserver_v5.py:238-240` (« History is also unsupported … no history buffer yet ») | Il n'y a pas d'historique en v5, donc rien à désactiver — mais c'est bien un manque de fonctionnalité côté v5, pas une décision de retrait écrite. |
| `--disable-check-update` | `glances/main.py:678` | ❌ absent | `glances/main_v5.py:78-261` (aucune option) ; aucun module de vérification de version dans les fichiers `*_v5.py` | La vérification en ligne n'existe pas en v5, donc le drapeau n'a pas d'objet — aucun équivalent trouvé. |

### 5. Processus

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-f`, `--process-filter` | `glances/main.py:513` | ❌ absent | `glances/plugins/processlist/model_v5.py:23` (« no filter UI (deferred) ») ; `docs/architecture/glances-v5-architecture-decisions.md:1158` | Explicitement listé dans le backlog de parité : « Never wired : `main_v5.py` does not push `args` into `glances_processes` ». Le moteur partagé `glances/processes.py` + `glances/filter.py` est pourtant déjà commun aux deux branches. |
| `--process-focus` | `glances/main.py:522` | ❌ absent | `docs/architecture/glances-v5-architecture-decisions.md:1158` (même ligne de backlog) | Cible « Phase 2.X — wire the CLI args into the shared engine ». |
| `--process-short-name` | `glances/main.py:529` | ❌ absent | `glances/outputs/glances_curses_v5.py:160` (hotkey `/` uniquement) ; `glances/main_v5.py:78-261` (aucun drapeau) | La bascule existe **en runtime** (touche `/`), pas au démarrage. Défaut v5 identique au défaut v4 (nom court). |
| `--process-long-name` | `glances/main.py:536` | ❌ absent | idem `glances/outputs/glances_curses_v5.py:160` | idem. |
| `--programs`, `--program` | `glances/main.py:357` | ❌ absent | `glances/outputs/glances_curses_v5.py:161` (hotkey `j`) ; `glances/outputs/glances_curses_v5.py:565-567` | Le plugin `programlist` est porté (`glances/plugins/programlist/model_v5.py:158`) et la bascule TUI existe ; seul le drapeau de démarrage manque. |
| `--sort-processes` | `glances/main.py:350` | ❌ absent | `glances/outputs/glances_curses_v5.py:148-156` (hotkeys de tri) | Tri disponible uniquement par hotkey en v5. |
| `--enable-process-extended` | `glances/main.py:322` | ❌ absent | `glances/plugins/processcount/model_v5.py:18` (« Extended view, programs aggregation and the filter UI are NOT wired ») ; `:20` (`disable_extended_tag` reste `False`) | |
| `--hide-kernel-threads` (`no_kernel_threads`, non-Windows) | `glances/main.py:597` | ❌ absent | `glances/main_v5.py:78-261` ; aucune occurrence de `kernel_threads` dans `glances/plugins/processlist/*_v5.py` ni `glances/plugins/processcount/*_v5.py` | |

### 6. Plugins spécifiques (fs / diskio)

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `--fs-free-space` | `glances/main.py:640` | ❌ absent | `glances/plugins/fs/render_curses_v5.py:26` (`TODO(G4+): plumb max_width / args so --fs-free-space … `) | Le renderer v5 affiche toujours l'espace *utilisé*. |
| `--diskio-iops` | `glances/main.py:619` | ❌ absent | `glances/plugins/diskio/render_curses_v5.py:26-27` (`TODO(G4+)`) | |
| `--diskio-latency` | `glances/main.py:626` | ❌ absent | `glances/plugins/diskio/model_v5.py:23-25` (« `read_latency` / `write_latency` of v4 are not ported — deferred to a later phase with the `--diskio-latency` mode ») | Les champs sous-jacents ne sont pas collectés non plus. |
| `--diskio-show-ramfs` | `glances/main.py:612` | ❌ absent | `glances/main_v5.py:78-261` ; aucune occurrence de `ramfs` dans `glances/plugins/diskio/*_v5.py` | Filtrage possible seulement via les clés génériques `show=`/`hide=` (`glances/plugins/plugin/base_v5.py:202-203`), ce qui n'est pas le même comportement (v4 *ajoute* les ramfs, il ne les retire pas). |

### 7. Export

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `--export` | `glances/main.py:366` | ⚠️ partiel | `glances/main_v5.py:139` (parser) ; `glances/main_v5.py:381-392` (`apply_export_flags`) ; `glances/main_v5.py:465-485` (`discover_exporters`) | Le mécanisme est complet et fidèle à v4, mais **6 exporteurs sur 24 seulement** ont un `export_v5.py` : `csv`, `json`, `influxdb`, `influxdb2`, `influxdb3`, `prometheus`. Les 18 autres provoquent un `sys.exit(2)` (`glances/main_v5.py:476-477`). Reste prévu Phase 3 (`docs/architecture/glances-v5-architecture-decisions.md:1131`). |
| `--export-csv-file` | `glances/main.py:367` | ✅ porté | `glances/main_v5.py:145` (parser) ; `glances/exports/glances_csv/export_v5.py:60` | |
| `--export-csv-overwrite` | `glances/main.py:370` | ✅ porté | `glances/main_v5.py:152` (parser) ; `glances/exports/glances_csv/export_v5.py:68`, `:251` | |
| `--export-json-file` | `glances/main.py:377` | ✅ porté | `glances/main_v5.py:158` (parser) ; `glances/exports/glances_json/export_v5.py:46` | |
| `--export-graph-path` | `glances/main.py:380` | ❌ absent | `glances/main_v5.py:78-261` ; pas de `glances/exports/glances_graph/export_v5.py` (seuls 6 `export_v5.py` existent) | L'exporteur `graph` n'est pas porté ; le drapeau n'aurait rien à configurer. Prévu Phase 3. |
| `--export-process-filter` | `glances/main.py:386` | ✅ porté | `glances/main_v5.py:165` (parser) ; `glances/main_v5.py:557-562` (overlay `[processlist] export`) ; `glances/plugins/processlist/model_v5.py:167`, `:169-186` | Parité v4 issue #794 explicitement respectée. Divergence mineure : v4 force `export_process_filter='.*'` en mode `--stdout` (`glances/main.py:773-774`) ; v5 n'a pas de mode stdout. |

### 8. Sécurité

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `--disable-config-exec` | `glances/main.py:668` | ⚠️ partiel | `glances/main_v5.py:257` (parser) ; `glances/main_v5.py:550-556` (overlay `[global] disable_config_exec`, sens unique — CVE-2026-68519) ; `glances/actions_v5/shell/__init__.py:79` ; `glances/amps_list_v5.py:61-67` | Câblé pour les actions shell et les AMP. **Différence** : en v4 le drapeau couvre *aussi* l'exécution des backticks dans les valeurs de configuration (aide `glances/main.py:673-675`) ; côté v5 je n'ai trouvé aucune évaluation de backtick dans `glances/config_v5.py`, donc ce volet est sans objet — mais je n'ai pas de trace écrite confirmant que c'est une décision plutôt qu'un oubli. |

### 9. Divers / diagnostic

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-V`, `--version` | `glances/main.py:190` | ⚠️ partiel | `glances/main_v5.py:270` (`--version` seul, `version=f"Glances {_VERSION}"`) | **Pas d'alias court `-V`** ; et la sortie v5 est une seule ligne, là où v4 imprime aussi la version Python, psutil, l'API et le chemin du fichier de log (`glances/main.py:170-178`). |
| `-d`, `--debug` | `glances/main.py:191` | ✅ porté | `glances/main_v5.py:110` (parser) ; `glances/main_v5.py:736` (`setup_logging(args.debug)`) ; `glances/main_v5.py:290-299` | |
| `-t`, `--time` | `glances/main.py:454` | ❌ absent | `glances/main_v5.py:78-261` ; `glances/scheduler_v5.py:96-102` (`[<plugin>] refresh` puis `[global] refresh` / `refresh_time`) ; `glances/main_v5.py:630-639` (cadence TUI) | Le **comportement** est disponible par configuration (`[global] refresh`), pas en ligne de commande. Un script v4 avec `-t 5` échoue. |
| `--stdout` | `glances/main.py:543` | ❌ absent | `glances/main_v5.py:78-261` (aucune option stdout) | |
| `--stdout-json` | `glances/main.py:549` | ❌ absent | idem | |
| `--stdout-csv` | `glances/main.py:555` | ❌ absent | idem | |
| `--issue` (`stdout_issue`) | `glances/main.py:561` | ❌ absent | idem | Outil de diagnostic pour les rapports de bug ; sans équivalent v5. |
| `--fetch`, `--stdout-fetch` | `glances/main.py:692` | ❌ absent | `glances/main_v5.py:78-261` ; aucune occurrence de `stdout_fetch` dans les fichiers `*_v5.py` | |
| `--fetch-template`, `--stdout-fetch-template` | `glances/main.py:700` | ❌ absent | idem | |
| `--api-doc` | `glances/main.py:582` | ❌ absent | `glances/main_v5.py:103-108` (`--api-doc` v5 = `BooleanOptionalAction` qui active/désactive Swagger) ; `glances/main_v5.py:604-605` ; `glances/webserver_v5.py:114` | **Collision de noms, pas un portage.** En v4 `--api-doc` imprime la documentation de l'API Python sur stdout puis quitte. En v5 la même chaîne d'option pilote l'exposition de `/docs` et `/redoc`. Le comportement v4 est absent ; le drapeau v5 est un ajout. |
| `--api-restful-doc` | `glances/main.py:589` | ❌ absent | `glances/main_v5.py:78-261` | Le besoin est en partie couvert autrement : FastAPI sert `/docs` et `/redoc` (`glances/webserver_v5.py:114`), mais il n'y a pas de génération sur stdout. |
| `--trace-malloc` | `glances/main.py:568` | ❌ absent | `glances/main_v5.py:78-261` ; aucune occurrence de `trace_malloc` dans les fichiers `*_v5.py` | |
| `--memory-leak` | `glances/main.py:575` | ❌ absent | idem (`memory_leak` absent des `*_v5.py`) | |
| `--print-completion` (shtab, conditionnel) | `glances/main.py:188-189` | ❌ absent | `glances/main_v5.py:78-261` (aucun import ni usage de `shtab`) | Complétion shell non portée. |
| `-h`, `--help` | implicite argparse — `glances/main.py:182` | ✅ porté | `glances/main_v5.py:79-82` (`argparse.ArgumentParser`, `add_help` par défaut) | Les familles/groupes du `--help` v4 ne sont pas reproduits : le parser v5 est plat (pas de `add_argument_group`). |
| `--theme-white` | *(aucune)* — documenté seulement `docs/cmds.rst:231` | 🚫 retiré (décision) | `glances/main_v5.py:78-261` | **Déjà absent de v4** : aucune occurrence dans `glances/`. C'est un bug de documentation v4 (`docs/cmds.rst:231`), pas un écart v4→v5. Signalé ici pour mémoire. |

---

### Récapitulatif

| Statut | Nombre |
|---|---|
| ✅ porté | 16 |
| ⚠️ partiel | 10 |
| ❌ absent | 59 |
| 🚫 retiré (décision) | 1 (`--theme-white`, en réalité déjà absent de v4) |
| ❓ indéterminé | 0 |
| **Total** | **86** |

85 de ces lignes sont de vraies options acceptées par v4 (`glances/main.py`
`init_args()`, y compris `-h/--help` et `--print-completion` conditionnel à
shtab) ; la 86ᵉ (`--theme-white`) n'existe que dans `docs/cmds.rst`.

### Ajouts v5 sans équivalent v4

| Option v5 | Preuve (file:line) | Note |
|---|---|---|
| `--set-password` | `glances/main_v5.py:265` ; `glances/main_v5.py:493-525` | Génère un hash PBKDF2 sur stdout ; ne touche pas `glances.conf`. |
| `--api-doc` / `--no-api-doc` | `glances/main_v5.py:103-108` ; `glances/webserver_v5.py:114` | Réutilise le nom d'une option v4 au comportement totalement différent (voir §9). |
| `--no-tui` (alias de `--quiet`) | `glances/main_v5.py:189-199` | Devenir non tranché : `docs/architecture/glances-v5-architecture-decisions.md:155-162`. |

### Points de vigilance pour la release

1. **`--bind` change de défaut** : `0.0.0.0` (v4, `glances/main.py:425`) → `127.0.0.1` (v5, `glances/main_v5.py:71`). Impact sur *tous* les déploiements serveur non configurés, y compris les conteneurs.
2. **`-s` change de sens** : XML-RPC (v4) → REST+WebUI (v5). Les scripts v4 utilisant `-w` cassent.
3. **Aucun alias court n'a été porté** hors `-C`, `-d`, `-s`, `-b` : `-V -0 -1 -2 -3 -4 -5 -6 -p -B -u -t -w -c -q -f` n'existent pas en v5.

**Corrigés (parity wave 1, 2026-09-10)** — retirés de la liste ci-dessus, voir
les lignes correspondantes dans la table §4 : `--byte` agit désormais sur le
renderer `network` ; `--disable-unicode` est déclaré dans `build_parser()`.


---

## Partie 2 — Clés du fichier de configuration

Branche analysée : `develop-v5` (`e7616114`). Référence v4 : `conf/glances.conf`
(1163 lignes, 60 sections) + le code v4 qui lit effectivement les clés.

Vocabulaire de statut : `✅ porté` · `⚠️ partiel` · `❌ absent` ·
`🚫 retiré (décision)` · `❓ indéterminé`.

---

### 0. Machinerie générique v5 (à lire avant toute ligne `❌`)

Beaucoup de clés v4 sont honorées en v5 **sans apparaître dans le fichier du
plugin** : la classe de base et le moteur de seuils les traitent par famille.

| Mécanisme | Fichier v5 | Formes de clés couvertes |
|---|---|---|
| `disable` | `glances/plugins/plugin/base_v5.py:166` | `[<plugin>] disable` (défaut = `DISABLED_BY_DEFAULT` de la classe) |
| Filtres d'items | `glances/plugins/plugin/base_v5.py:202-203`, `227-245`, `291-309` | `[<plugin>] show=` / `hide=` (regex CSV, `re.search` sur la valeur de la clé primaire) |
| Cadence | `glances/scheduler_v5.py:142-182` | `[<plugin>] refresh` puis `refresh_time`, sinon `DEFAULT_REFRESH_TIME` de la classe, sinon `[global] refresh` / `refresh_time` |
| Seuils numériques | `glances/plugins/plugin/thresholds_v5.py:83-150` | `<pk>_<field>_<level>` → `<field>_<level>` → `<level>` (le dernier sauté si `strict_thresholds`), `level ∈ {careful, warning, critical}`, valeur négative = « absent » |
| Seuils catégoriels | `glances/plugins/plugin/thresholds_v5.py:206-247` | `<pk>_<field>_<level>` → `<field>_<level>`, `level ∈ {ok, careful, warning, critical}`, valeur = CSV |
| Anti-flapping | `glances/alerts_v5.py:555-606` | `<pk>_<field>_<level>_min_duration_seconds` → `<pk>_<field>_…` → `<field>_<level>_…` → `<field>_…` → `min_duration_seconds` (section plugin) → `[alerts] min_duration_seconds` |
| Actions sur alerte | `glances/alerts_v5.py:761-789` + `glances/actions_v5/shell/__init__.py:64` (`action_name="action"`) | `<pk>_<field>_<level>_action[_repeat]` → `<field>_<level>_action[_repeat]` → `<level>_action[_repeat]` |
| Overlay d'environnement | `glances/config_v5.py:221-233` | `GLANCES_<SECTION>__<KEY>=<valeur>` |
| Overlay CLI (écriture directe dans `config._merged`) | `glances/main_v5.py:449`, `556`, `562`, `605`, `610` | `[processlist] disable`, `[global] disable_config_exec`, `[processlist] export`, `[outputs] api_doc`, `[outputs] enable_mcp` |

**Deux pièges systématiques mesurés dans cet inventaire :**

1. **Le nom de la clé de seuil = le nom du champ v5**, pas celui de v4. Là où v4
   nomme le préfixe librement (`rx_careful`, `cpu_careful` dans `[processlist]`),
   v5 utilise `fields_description` — sauf si le champ déclare `threshold_field`
   (`base_v5.py:513-522`), ce que seuls `containers` et `vms` font.
2. **v5 n'a pas de famille `_log`.** `thresholds_v5.py` et `alerts_v5.py` ne
   lisent jamais `<...>_log` ; toute transition ≥ `warning` est historisée
   inconditionnellement (`alerts_v5.py:355-410`).

Six plugins court-circuitent la marche générique en surchargeant
`_derived_parameters()` — `sensors`, `wifi`, `folders`, `raid`, `ports`, `amps`
(cf. `base_v5.py:620-627`) : pour eux les formes de clés sont propres au plugin
et sont détaillées dans leur sous-table.

---

### 1. `[global]` (conf:5-19)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `refresh` | `glances/main.py:720` | ✅ porté | `glances/scheduler_v5.py:172-182` ; TUI `glances/main_v5.py:630-639` | Sert aussi de repli pour la cadence de chaque plugin et de l'export. |
| `check_update` | `glances/outdated.py:66` | ❌ absent | — (aucun `outdated`/`check_update` dans un fichier `*_v5.py`) | Pas de vérification de version PyPI en v5. |
| `history_size` | `glances/plugins/plugin/model.py:736` ; `glances/main.py:877` | ⚠️ partiel | `glances/exports/export_base_v5.py:362` | Lue **uniquement** pour remplir le dict `limits` envoyé aux exporteurs. v5 n'a pas de buffer d'historique (docs/architecture/glances-v5-architecture-decisions.md §11) ; `history_size=0` ne désactive donc rien. |
| `strftime_format` | `glances/plugins/now/__init__.py:52` | ✅ porté | `glances/plugins/now/model_v5.py:41` | |
| `plugin_dir` | `glances/stats.py:200-201` | ❌ absent | `glances/main_v5.py:306-340` (`discover_plugin_classes` n'itère que `pkgutil.iter_modules(glances.plugins.__path__)`) | Aucun chargement de plugins externes en v5. |
| `refresh_time` | — (clé v5 uniquement) | ✅ porté | `glances/scheduler_v5.py:174` | Alias de `refresh`, lu en second. Non livré dans `conf/glances.conf`. |
| `disable_config_exec` | — (v4 : drapeau CLI seulement, `glances/main.py:117`, `672`) | ✅ porté | `glances/amps_list_v5.py:67` ; overlay CLI `glances/main_v5.py:556` | Nouvelle clé de config v5, non livrée dans le fichier. |

### 2. `[alerts]` (conf:25-39) — section **v5 uniquement**

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `min_duration_seconds` | — | ✅ porté | `glances/alerts_v5.py:161` | N'est **pas** l'équivalent de `[alert] min_duration` (debounce vs. rejet a posteriori) — cf. conf:31-33. |
| `history_size` | — | ✅ porté | `glances/alerts_v5.py:162` | |
| `warmup_cycles` | — | ✅ porté | `glances/alerts_v5.py:163` | |

### 3. `[outputs]` (conf:45-136)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `separator` | `glances/outputs/glances_curses.py:215` | ✅ porté | `glances/outputs/glances_curses_v5.py:221`, `1094-1101` | TUI. Côté WebUI, non vérifiable : réécriture partielle en cours (groupe G9). |
| `left_menu` | `glances/outputs/glances_curses.py:219` | ❌ absent | — | La colonne gauche du TUI v5 est déterminée par le renderer, pas par la config. |
| `max_processes_display` | `glances/outputs/glances_restful_api.py:393` | ❌ absent | — | Clé consommée par la **WebUI v4** (servie par le serveur REST). WebUI v5 = G9 en cours ; à re-vérifier à la fin de G9. |
| `disable_bg` | `glances/outputs/glances_curses.py:221` | ❌ absent | — | |
| `theme` | — (clé v5 uniquement) | ✅ porté | `glances/outputs/glances_curses_v5.py:226` | `dark` (défaut) / `light`. |
| `url_prefix` | `glances/outputs/glances_restful_api.py:396` | 🚫 retiré (décision) | `glances/webserver_v5.py:262-264` (« v5 has no `url_prefix` ») | |
| `webui_root_path` | `glances/outputs/glances_restful_api.py:277` | ❌ absent | `glances/webserver_v5.py:266-278` (chemins `_STATIC_PATH` / `index_v5.html` en dur) | |
| `cors_origins` | `glances/outputs/glances_restful_api.py:294`, `578` ; `glances/server.py:130` | ✅ porté | `glances/webserver_v5.py:317` | Défaut v5 = liste vide → middleware CORS non câblé (v4 : `*`). Changement de défaut assumé. |
| `cors_credentials` | `glances/outputs/glances_restful_api.py:295` | ⚠️ partiel | `glances/webserver_v5.py:318` | v5 lit `cors_allow_credentials` — **clé renommée**. `cors_credentials=True` d'une conf v4 est silencieusement ignorée. |
| `cors_methods` | `glances/outputs/glances_restful_api.py:315` | 🚫 retiré (décision) | `glances/webserver_v5.py:334` (`allow_methods=["GET","POST"]`) ; docs/architecture/glances-v5-architecture-decisions.md:733 | |
| `cors_headers` | `glances/outputs/glances_restful_api.py:316` | 🚫 retiré (décision) | même décision, docs…decisions.md:733 (`Authorization, Content-Type` en dur) | |
| `ssl_keyfile` / `ssl_certfile` / `ssl_keyfile_password` | `glances/outputs/glances_restful_api.py:401-403` | ❌ absent | `glances/main_v5.py:700-706` (`uvicorn.Config` sans paramètre SSL) | Pas de HTTPS natif en v5. |
| `jwt_secret_key` | `glances/outputs/glances_restful_api.py:265` | ✅ porté | `glances/webserver_v5.py:351` | |
| `jwt_expire_minutes` | `glances/outputs/glances_restful_api.py:266` | ✅ porté | `glances/webserver_v5.py:352` | |
| `webui_allowed_hosts` | `glances/outputs/glances_restful_api.py:406` | ✅ porté | `glances/webserver_v5.py:297-307` | + WARNING au démarrage si bind non-loopback et clé absente. |
| `enable_mcp` | `glances/outputs/glances_restful_api.py:408` | ✅ porté | `glances/webserver_v5.py:200` ; overlay `--enable-mcp` `glances/main_v5.py:610` | |
| `mcp_path` | `glances/outputs/glances_restful_api.py:409` | ❌ absent | `glances/webserver_v5.py:225` (`app.mount("/mcp", …)` en dur) | |
| `mcp_allowed_hosts` | `glances/outputs/glances_mcp.py:138` | ✅ porté | même module v4 réutilisé par v5 : `glances/webserver_v5.py:224` (`GlancesMcpServer(..., config=config)`) | Moteur partagé v4/v5. |
| `xmlrpc_allowed_hosts` | `glances/server.py:140` | ❌ absent | — | Pas de serveur XML-RPC en v5 (mode client/serveur = Phase 3, docs…decisions.md:1126-1132). |
| `bind_address` | — (v4 : CLI `-B`, `glances/main.py:426`) | ✅ porté | `glances/main_v5.py:591` ; `glances/webserver_v5.py:299` | Clé v5 uniquement, non livrée. |
| `port` | — (v4 : CLI `-p`) | ✅ porté | `glances/main_v5.py:592` | Clé v5 uniquement, non livrée. |
| `password` | — (v4 : `--password`, fichier `.pwd`) | ✅ porté | `glances/webserver_v5.py:346`, `436` ; `glances/routes_v5.py:94` | Hash PBKDF2 `salt$hex`. Clé v5 uniquement. |
| `username` | — | ✅ porté | `glances/webserver_v5.py:350` ; `glances/routes_v5.py:109` | Défaut `glances`. Clé v5 uniquement. |
| `api_doc` | — | ✅ porté | `glances/webserver_v5.py:114` ; overlay CLI `glances/main_v5.py:605` | Clé v5 uniquement. |
| `tui_refresh_interval` | — | ✅ porté | `glances/main_v5.py:633-639` | Clé v5 uniquement ; défaut = `[global] refresh`. |

### 4. `[quicklook]` (conf:142-175)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `list` | `glances/plugins/plugin/model.py:741-754` (`load_limits`) | ✅ porté | `glances/plugins/quicklook/model_v5.py:269` | `cpu,mem,load,swap,gpu_mem,gpu_proc`. |
| `bar_char` | idem | ✅ porté | `glances/plugins/quicklook/model_v5.py:292` | |
| Seuils `cpu_*`, `mem_*`, `swap_*`, `load_*`, `gpu_proc_*`, `gpu_mem_*` | `glances/plugins/plugin/model.py:964` (`get_limit`) | ✅ porté | champs surveillés `cpu`/`mem`/`swap`/`load`/`gpu_mem`/`gpu_proc` (`glances/plugins/quicklook/model_v5.py`), résolus par `thresholds_v5.py:83-150` | Formes : `<field>_<level>` et `<level>` nu. Noms de champs identiques à v4. |
| Actions `<field>_<level>_action[_repeat]` | `glances/plugins/plugin/model.py:980` | ✅ porté | `glances/alerts_v5.py:761-789` | |

### 5. `[system]` (conf:178-188)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773-782` | ✅ porté | `glances/scheduler_v5.py:157-159` | |
| `system_info_msg` | `glances/plugins/system/__init__.py:128` | ✅ porté | `glances/plugins/system/model_v5.py:87` | |

### 6. `[cpu]` (conf:190-227)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| Seuils `<field>_<level>` : `total`, `user`, `system`, `iowait`, `steal`, `ctx_switches` (+ `dpc` en v5) | `glances/plugins/plugin/model.py:964` | ✅ porté | champs surveillés dans `glances/plugins/cpu/model_v5.py` ; résolution `thresholds_v5.py:83-150` | Noms de champs identiques à v4. `ctx_switches` est normalisé par `cpucore` des deux côtés. |
| `<field>_log` (`total_log`, `user_log`, `system_log`, `steal_log`) | `glances/plugins/plugin/model.py:1002` (`get_limit_log`), appelé `model.py:883` | ❌ absent | — (aucune lecture de `_log` dans `thresholds_v5.py` ni `alerts_v5.py`) | Conséquence : v5 historise **toutes** les transitions ≥ `warning` ; on ne peut plus désactiver la journalisation d'un champ. |
| `<field>_<level>_action[_repeat]` (ex. `user_critical_action`) | `glances/plugins/plugin/model.py:980` | ✅ porté | `glances/alerts_v5.py:783` | |
| `<field>_[<level>_]min_duration_seconds` | — (clé v5 uniquement) | ✅ porté | `glances/alerts_v5.py:594-595` | |

### 7. `[percpu]` (conf:229-246)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `max_cpu_display` | `glances/plugins/percpu/__init__.py:119` ; `glances/plugins/quicklook/__init__.py:108` | ⚠️ partiel | lue par quicklook : `glances/plugins/quicklook/model_v5.py:261` ; **ignorée** par percpu : `glances/plugins/percpu/render_curses_v5.py:28` (`_DEFAULT_MAX_CPU_DISPLAY = 4` en dur) + TODO explicite l.35-37 | Le plugin `percpu` affiche toujours 4 cœurs quelle que soit la valeur. |
| Seuils `user_*`, `iowait_*`, `system_*` | `glances/plugins/plugin/model.py:964` | ❌ absent | `glances/plugins/percpu/model_v5.py:19-27` (aucun champ `watched`, `_levels` toujours vide) | Divergence assumée et documentée dans le modèle : pas d'alerte par cœur en v5. |

### 8. `[gpu]` (conf:248-261)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| Seuils `proc_*`, `mem_*`, `temperature_*` | `glances/plugins/plugin/model.py:964` | ✅ porté | champs surveillés `proc`/`mem`/`temperature` (`glances/plugins/gpu/model_v5.py`) ; `thresholds_v5.py:83-150` | Surcharge par GPU possible via `<gpu_id>_<field>_<level>`. |

### 9. `[npu]` (conf:263-276)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/npu/model_v5.py:59` (`DISABLED_BY_DEFAULT = True`) + `base_v5.py:166` | |
| Seuils `load_*`, `freq_*`, `temperature_*` | `glances/plugins/plugin/model.py:964` | ✅ porté | champs surveillés `load`/`freq`/`temperature` (+ `mem`, nouveau) dans `glances/plugins/npu/model_v5.py` | |

### 10. `[mpp]` (conf:278-283)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/mpp/model_v5.py:53` + `base_v5.py:166` | |
| Seuils `load_*` | `glances/plugins/plugin/model.py:964` | ✅ porté | champ surveillé `load` (`glances/plugins/mpp/model_v5.py`) | |

### 11. `[mem]` (conf:285-294)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `available` | `glances/plugins/mem/__init__.py:131` | ❌ absent | `glances/plugins/mem/render_curses_v5.py:114-117` | Le TUI v5 affiche `available` dès que le champ est présent (Linux/macOS), sans consulter la clé. **Changement de comportement par défaut** : v4 affiche `used` sauf si `available=True`. |
| `careful` / `warning` / `critical` (nus) | `glances/plugins/plugin/model.py:964` | ✅ porté | champ `percent` non-strict → repli sur `<level>` nu (`thresholds_v5.py:130-137`) | |
| `critical_action_repeat` | `glances/plugins/plugin/model.py:980` | ✅ porté | `glances/alerts_v5.py:779-784` (`<level>_action_repeat`) | |

### 12. `[memswap]` (conf:296-315)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `percent_<level>` | `glances/plugins/plugin/model.py:964` | ✅ porté | champ `percent` (`glances/plugins/memswap/model_v5.py`) ; `thresholds_v5.py:83-150` | |
| `warning_action` | `glances/plugins/plugin/model.py:980` | ✅ porté | `glances/alerts_v5.py:784` (`<level>_action`) | |
| `sin_<level>` / `sout_<level>` | — (clés v5 uniquement) | ✅ porté | champs `sin`/`sout` avec `strict_thresholds=True` ; `thresholds_v5.py:125-133` | `strict` ⇒ pas de repli sur `<level>` nu : une vieille conf v4 avec `careful=50` dans `[memswap]` ne déclenche pas d'alerte d'E/S swap. |
| `sin_min_duration_seconds` / `sout_min_duration_seconds` | — | ✅ porté | `glances/alerts_v5.py:595` | |

### 13. `[load]` (conf:317-327)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `careful` / `warning` / `critical` (nus) | `glances/plugins/plugin/model.py:964` | ✅ porté | champs `min5`/`min15` (`normalize_by: cpucore`) non-stricts → `<level>` nu, `thresholds_v5.py:130-137` | Même sémantique « valeur × nombre de cœurs » qu'en v4. |
| `log` | `glances/plugins/plugin/model.py:1002` | ❌ absent | — | Famille `_log` non portée (cf. §0). |

### 14. `[network]` (conf:329-364)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203`, `291-309` | Filtre sur `interface_name` (clé primaire). |
| `rx_<level>` / `tx_<level>` | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | champs v5 `bytes_recv` / `bytes_sent`, `glances/plugins/network/model_v5.py:47` (`_DEFAULT_BANDWIDTH_THRESHOLDS = {careful:0.7, warning:0.8, critical:0.9}`) | **Clés renommées ET unité changée** : v5 attend `bytes_recv_careful` / `bytes_sent_careful` exprimés en **ratio [0,1]** de la capacité, pas en pourcentage. `rx_careful=70` livré dans la conf est ignoré ; les défauts intégrés reproduisent 70/80/90 %. |
| `<iface>_rx_<level>` / `<iface>_tx_<level>` (ex. `wlan0_rx_careful`) | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | `thresholds_v5.py:124-128` | Forme v5 : `wlan0_bytes_recv_careful` / `wlan0_bytes_sent_careful`. |
| `<iface>_rx_<level>_action` (ex. `wlan0_rx_critical_action`) | `glances/plugins/plugin/model.py:980` | ⚠️ partiel | `glances/alerts_v5.py:782` | Forme v5 : `wlan0_bytes_recv_critical_action`. |
| `<iface>_rx_log` / `<iface>_tx_log` | `glances/plugins/plugin/model.py:1002` | ❌ absent | — | |
| `hide_no_up` | `glances/plugins/network/__init__.py:96` | ✅ porté | `glances/plugins/network/model_v5.py:152` (lecture) ; `:177-178` (`_grab_stats`, retire l'item) | **Corrigé (parity wave 1, 2026-09-10)**. Parité v4 : l'interface est retirée de la charge utile, pas seulement masquée. |
| `hide_no_ip` | `glances/plugins/network/__init__.py:97` | ✅ porté | `glances/plugins/network/model_v5.py:153` (lecture) ; `:164-165`, `:179-182` (`_grab_stats`, retire l'item) | **Corrigé (parity wave 1, 2026-09-10)**. |
| `hide_zero` | `glances/plugins/network/__init__.py:86` | ✅ porté | `glances/plugins/plugin/base_v5.py:261` (lecture générique) ; `network/model_v5.py:63` (`HIDE_ZERO_FIELDS = ["bytes_recv", "bytes_sent"]`) ; `base_v5.py:616-660` (`_compute_hide_zero`) ; `network/render_curses_v5.py:137` (le renderer saute la ligne) | **Corrigé (parity wave 1, 2026-09-10)**, mécanisme générique dans `base_v5` (§5.1 du plan). **Divergence délibérée documentée** : v5 publie un seul booléen `hidden` par item (réduction `all(...)` déjà faite côté modèle), là où v4 exposait un état par champ — les deux consommateurs v4 (`network`, `diskio`) recalculaient le même `all(...)`, donc pas de perte fonctionnelle pour le rendu. |
| `hide_threshold_bytes` | `glances/plugins/network/__init__.py:87` | ✅ porté | `glances/plugins/plugin/base_v5.py:262` (lecture générique) ; `base_v5.py:616-660` (`_compute_hide_zero`, seuil strict `>`) | **Corrigé (parity wave 1, 2026-09-10)**. |
| `alias` | `glances/plugins/plugin/model.py:1075-1081` (`read_alias`) | ✅ porté | `glances/plugins/plugin/base_v5.py:392-409` (`_read_alias`, générique) ; `:690-714` (`_apply_alias`) ; `network/render_curses_v5.py` affiche l'alias quand présent | **Corrigé (parity wave 1, 2026-09-10)** : `alias` est désormais générique dans `base_v5`, appliqué à `network`/`diskio`/`fs` (et matché par `show`/`hide`, v4 parity) ; `sensors` garde son propre mécanisme, plus riche, inchangé. |
| Nouveaux seuils v5 `errors_in_<level>` / `errors_out_<level>` | — | ✅ porté | `glances/plugins/network/model_v5.py:50` (`_DEFAULT_ERROR_THRESHOLDS`) | Défauts 1/5/20 err/s ; nouveau en v5. |

### 15. `[ip]` (conf:366-399)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |
| `public_disabled` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/ip/model_v5.py:138` | |
| `public_refresh_interval` | idem | ✅ porté | `glances/plugins/ip/model_v5.py:131-134` | |
| `public_api` | idem | ✅ porté | `glances/plugins/ip/model_v5.py:126` | |
| `public_username` | idem | ✅ porté | `glances/plugins/ip/model_v5.py:127` | |
| `public_password` | idem | ✅ porté | `glances/plugins/ip/model_v5.py:128` | |
| `public_field` | idem | ✅ porté | `glances/plugins/ip/model_v5.py:129` | |
| `public_template` | idem | ✅ porté | `glances/plugins/ip/model_v5.py:130` | |
| `public_api_allow_internal` | idem (CVE-2026-35587) | ✅ porté | `glances/plugins/ip/model_v5.py:135` | Défaut `False` = URL interne rejetée. |

### 16. `[connections]` (conf:401-411)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/connections/model_v5.py:64` (`DISABLED_BY_DEFAULT = True`) + `base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |
| `nf_conntrack_percent_<level>` | `glances/plugins/plugin/model.py:964` | ✅ porté | champ surveillé `nf_conntrack_percent`, défauts 70/80/90 (`glances/plugins/connections/model_v5.py`) | Nom de champ identique à v4. |

### 17. `[wifi]` (conf:413-419)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `careful` / `warning` / `critical` | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/wifi/model_v5.py:136-138` (lecture directe, `_derived_parameters` surchargé) | Sémantique « lower is better » (dBm) conservée. Pas de surcharge par SSID (ni en v4 ni en v5). |

### 18. `[diskio]` (conf:421-460)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203`, `291-309` | Filtre sur `disk_name`. |
| `hide_zero` | `glances/plugins/diskio/__init__.py:93` | ✅ porté | `glances/plugins/plugin/base_v5.py:261` (lecture générique) ; `diskio/model_v5.py:52` (`HIDE_ZERO_FIELDS = ["read_bytes", "write_bytes"]`) ; `base_v5.py:616-660` (`_compute_hide_zero`) ; `diskio/render_curses_v5.py:105` (le renderer saute la ligne) | **Corrigé (parity wave 1, 2026-09-10)**, même mécanisme générique et même divergence documentée qu'en `[network]` ci-dessus (un seul booléen `hidden` par item). |
| `hide_threshold_bytes` | `glances/plugins/diskio/__init__.py:94` | ✅ porté | `glances/plugins/plugin/base_v5.py:262` (lecture générique) ; `base_v5.py:616-660` (`_compute_hide_zero`, seuil strict `>`) | **Corrigé (parity wave 1, 2026-09-10)**. |
| `alias` | `glances/plugins/plugin/model.py:1075` | ✅ porté | `glances/plugins/plugin/base_v5.py:392-409` (`_read_alias`, générique) ; `:690-714` (`_apply_alias`) ; `diskio/render_curses_v5.py:120` affiche l'alias quand présent | **Corrigé (parity wave 1, 2026-09-10)** : générique dans `base_v5`, cf. la ligne `alias` de `[network]` ci-dessus. |
| `rx_latency_<level>` / `tx_latency_<level>` (+ formes `<disk>_…`, `_log`) | `glances/plugins/plugin/model.py:964` | ❌ absent | `glances/plugins/diskio/model_v5.py:23-25` (« `read_time`/`write_time` et les `read_latency`/`write_latency` dérivés de v4 ne sont pas portés — reportés au mode `--diskio-latency` ») | Toute la famille latence disparaît. |
| `<disk>_rx_<level>` / `<disk>_tx_<level>` (débit, ex. `dm-0_rx_careful`) | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | champs v5 `read_bytes` / `write_bytes` avec `strict_thresholds=True` (`glances/plugins/diskio/model_v5.py:19`, `75`) | Forme v5 : `dm-0_read_bytes_careful` / `dm-0_write_bytes_careful`. `strict` ⇒ pas de repli sur `<level>` nu. Aucun défaut : seuils opt-in, comme en v4. |

### 19. `[fs]` (conf:462-488)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `free_space` | `glances/main.py:832` | ✅ porté | `glances/plugins/fs/model_v5.py:104-111` (lecture + merge CLI) ; `glances/main_v5.py:245-248` (`--fs-free-space`), `:577-582` (CLI gagne sur la clé de config, v4 parity `main.py:832`) ; `fs/render_curses_v5.py:78-80` (bascule used↔free) | **Corrigé (parity wave 1, 2026-09-10)** pour la clé de config et l'option CLI. **Reste absent** : la touche `F` du TUI v4 — délibérément différée au groupe TUI (§10, roadmap `glances-v5-architecture-decisions.md`, design §5.4), pas encore de bascule au clavier en v5. |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203` | Filtre sur `mnt_point`. |
| `careful` / `warning` / `critical` (nus) | `glances/plugins/plugin/model.py:964` | ✅ porté | champ `percent` non-strict → `<level>` nu (`thresholds_v5.py:130-137`) | |
| `<mnt>_<level>` (ex. `/_careful`) | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | `thresholds_v5.py:124-128` (formes acceptées : `<pk>_<field>_<level>`) | Forme v5 : `/_percent_careful`. `/_careful` est ignoré. |
| `<mnt>_<level>_action` (ex. `/_critical_action`) | `glances/plugins/plugin/model.py:980` | ⚠️ partiel | `glances/alerts_v5.py:782` | Forme v5 : `/_percent_critical_action`. |
| `allow` | `glances/plugins/fs/__init__.py:161` | ✅ porté | `glances/plugins/fs/model_v5.py:101-104` (lecture) ; `:122-147` (`_collect_sync`, filtrage par `fstype` en substring, v4 parity issue #448) | **Corrigé (parity wave 1, 2026-09-10)**. |
| `alias` | `glances/plugins/plugin/model.py:1075` | ✅ porté | `glances/plugins/plugin/base_v5.py:392-409` (`_read_alias`, générique) ; `:690-714` (`_apply_alias`) ; `fs/render_curses_v5.py:113` affiche l'alias quand présent | **Corrigé (parity wave 1, 2026-09-10)** : générique dans `base_v5`, cf. la ligne `alias` de `[network]` ci-dessus. |

### 20. `[irq]` (conf:490-493)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/irq/model_v5.py:92` (`DISABLED_BY_DEFAULT = True`) + `base_v5.py:166` | |

### 21. `[folders]` (conf:495-519)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` ; `glances/plugins/folders/model_v5.py:56` | |
| `folder_<n>_path` | `glances/folder_list.py:64` | ✅ porté | moteur v4 réutilisé tel quel : `glances/plugins/folders/model_v5.py:41` | |
| `folder_<n>_refresh` | `glances/folder_list.py:71` | ✅ porté | idem | |
| `folder_<n>_careful` / `_warning` / `_critical` | `glances/folder_list.py:75-76` | ✅ porté | idem + `glances/plugins/folders/model_v5.py:78-85` (`_derived_parameters` surchargé, seuils en Mo → octets) | |
| `folder_<n>_<level>_action` | `glances/folder_list.py:80` | ❌ absent | valeur lue par `folder_list.py` mais jamais consommée : `glances/alerts_v5.py:761-789` n'interroge que `<path>_size_<level>_action`, `size_<level>_action`, `<level>_action` | Les actions par dossier ne se déclenchent plus. |

### 22. `[cloud]` (conf:521-527)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/cloud/model_v5.py:100` + `base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |

### 23. `[raid]` (conf:529-532)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | La conf livre `disable=True` ; `DISABLED_BY_DEFAULT` reste `False` côté classe, donc sans fichier de conf le plugin est actif — identique à v4 (`main.py:734`, défaut `False`). |

### 24. `[smart]` (conf:534-543)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203` | Filtre sur `name`. |
| `hide_attributes` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/smart/model_v5.py:65-70` | |

### 25. `[hddtemp]` (conf:545-549)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ❌ absent | — | v4 fabriquait `args.disable_hddtemp` ; v5 n'a pas de plugin `hddtemp` (fusionné dans `sensors`), la clé n'a plus d'effet. |
| `host` | `glances/plugins/sensors/sensor/glances_hddtemp.py:30` | ⚠️ partiel | `glances/plugins/sensors/model_v5.py:137` | **Section morte des deux côtés** : `HddtempPlugin` hérite de `GlancesPluginModel`, dont `plugin_name` vaut `sensors` (`glances/plugins/plugin/model.py:85-86`, le module est `glances.plugins.sensors.sensor.glances_hddtemp`). v4 lit donc `[sensors] host`, comme v5. La section `[hddtemp]` livrée n'est lue par personne. |
| `port` | `glances/plugins/sensors/sensor/glances_hddtemp.py:31` | ⚠️ partiel | `glances/plugins/sensors/model_v5.py:138` | Idem. |

### 26. `[sensors]` (conf:551-602)

`sensors` surcharge `_derived_parameters()` : les formes de clés lui sont propres
(`glances/plugins/sensors/model_v5.py:347-380`).

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203` | Filtre sur `label`. |
| `mean` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/sensors/model_v5.py:255` | Bascule globale du repli « `<préfixe> (mean)` ». |
| `<type>_mean` (`temperature_core_mean`, `fan_speed_mean`, `temperature_hdd_mean`, `battery_mean`) | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/sensors/model_v5.py:252-254` | Surcharge par type ; gagne sur `mean`. |
| `<type>_<level>` (`temperature_core_careful`, `temperature_hdd_*`, `battery_*`, `fan_speed_careful`) | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/sensors/model_v5.py:353-355`, `367-380` (tier 2) | |
| `<type>_<label>_<level>` (ex. `temperature_core_Ambient_careful`) | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/sensors/model_v5.py:350-352` (tier 1, issue #2058) | |
| `<type>_<label>_log` | `glances/plugins/plugin/model.py:1002` | ❌ absent | — | |
| `<type>_<label>_<level>_action` (ex. `temperature_core_Ambient_critical_action`) | `glances/plugins/plugin/model.py:980` | ❌ absent | `glances/alerts_v5.py:761-789` interroge `<label>_value_<level>_action`, `value_<level>_action`, `<level>_action` | Forme v4 non reconnue ; seule `<label>_value_<level>_action` (label = clé primaire) fonctionne. |
| `alias` | `glances/plugins/plugin/model.py:1075` | ✅ porté | `glances/plugins/sensors/model_v5.py:194-214` | Mécanisme propre à `sensors` (label / `label_type`), inchangé. Depuis parity wave 1 (2026-09-10) un `alias` générique existe aussi dans `base_v5` pour `network`/`diskio`/`fs` (§14, §18, §19) — `sensors` n'est plus le seul, mais garde le sien, plus riche. |
| `host` / `port` (hddtemp) | `glances/plugins/sensors/sensor/glances_hddtemp.py:30-31` | ✅ porté | `glances/plugins/sensors/model_v5.py:137-138` | Non livrées dans `[sensors]` (elles apparaissent, à tort, sous `[hddtemp]`). |

### 27. `[processcount]` (conf:604-607)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` ; couplage processlist `glances/main_v5.py:446-449` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |

### 28. `[processlist]` (conf:609-650) — s'applique aussi à `programlist`

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `sort_key` | `glances/plugins/processlist/__init__.py:244-248` | ❌ absent | — (aucune lecture de `[processlist] sort_key` dans `*_v5.py`) | Le tri v5 reste sur l'auto-tri de `glances_processes`. |
| `disable_stats` | `glances/plugins/processlist/__init__.py:258-264` | ❌ absent | — | Toutes les statistiques par processus sont collectées. |
| `disable_virtual_memory` | `glances/plugins/plugin/model.py:741-754` | ❌ absent | — | |
| `export` | `glances/plugins/processlist/__init__.py:249-252` | ✅ porté | `glances/plugins/processlist/model_v5.py:167` ; `glances/plugins/programlist/model_v5.py:142` ; overlay CLI `glances/main_v5.py:562` | |
| `focus` | `glances/plugins/processlist/__init__.py:253-256` | ❌ absent | — | |
| `cpu_<level>` / `mem_<level>` | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | champs v5 `cpu_percent` / `memory_percent`, défauts 50/70/90 (`glances/plugins/processlist/model_v5.py:101-118`) | **Clés renommées** : v5 attend `cpu_percent_careful` / `memory_percent_careful`. Les valeurs livrées coïncident avec les défauts, donc l'effet visible est nul tant que l'utilisateur ne les modifie pas. |
| `nice_ok` / `nice_careful` / `nice_warning` / `nice_critical` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | champ catégoriel `nice` ; `thresholds_v5.py:206-247` | Nom de champ identique. |
| `status_ok` / `status_critical` (et `_careful` / `_warning`) | idem | ✅ porté | champ catégoriel `status` ; `thresholds_v5.py:206-247` | |

### 29. `[ports]` (conf:652-698)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `refresh` | `glances/ports_list.py:39` ; `glances/web_list.py:42` | ✅ porté | `glances/plugins/ports/model_v5.py:105`, `119-132` | Découplé de la publication : le plugin est publié à la cadence globale (`SCHEDULE_AT_GLOBAL_REFRESH`, `base_v5.py:107-121`) et `refresh` ne throttle que le scan. |
| `timeout` | `glances/ports_list.py:40` ; `glances/web_list.py:43` | ✅ porté | moteur v4 réutilisé : `glances/plugins/ports/model_v5.py:105` | |
| `port_default_gateway` | `glances/ports_list.py:43` | ✅ porté | idem | |
| `port_<x>_host` / `_port` / `_description` / `_timeout` / `_rtt_warning` | `glances/ports_list.py:64-86` | ✅ porté | idem | |
| `web_<x>_url` / `_description` / `_timeout` / `_rtt_warning` | `glances/web_list.py:51-78` | ✅ porté | idem (`GlancesWebList`) | |
| `web_<x>_ssl_verify` / `_http_proxy` / `_https_proxy` | `glances/web_list.py:87-91` | ✅ porté | idem | Lues par v4 mais **non livrées** dans `conf/glances.conf`. |

### 30. `[vms]` (conf:700-722)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/vms/model_v5.py:85` (`DISABLED_BY_DEFAULT = True`) + `base_v5.py:166` | |
| `cpu_<level>` / `mem_<level>` / `load_<level>` | `glances/plugins/plugin/model.py:964` | ✅ porté | champs `cpu_time`/`memory_percent`/`load_1min` avec `threshold_field` = `cpu`/`mem`/`load` (`glances/plugins/vms/model_v5.py`) ; `base_v5.py:513-522` | Le `threshold_field` préserve exactement les noms de clés v4. |
| `<vmname>_<field>_<level>` (ex. `vmname_mem_careful`) | `glances/plugins/plugin/model.py:964` | ✅ porté | `thresholds_v5.py:124-128` (pk = `name`) | |
| `max_name_size` | `glances/plugins/vms/__init__.py:281` | ✅ porté | `glances/plugins/vms/model_v5.py:136` | |
| `all` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/vms/model_v5.py:139` | |

### 31. `[containers]` (conf:724-754)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `show` / `hide` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203` | Filtre sur `name`. |
| `max_name_size` | `glances/plugins/containers/__init__.py:430` | ✅ porté | `glances/plugins/containers/model_v5.py:112` | |
| `disable_stats` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/containers/model_v5.py:105` ; rendu `glances/plugins/containers/render_curses_v5.py:56`, `83` | |
| `cpu_<level>` / `mem_<level>` | `glances/plugins/plugin/model.py:964` | ✅ porté | champs `cpu_percent`/`memory_percent` avec `threshold_field` = `cpu`/`mem` | |
| `<containername>_cpu_<level>` etc. | `glances/plugins/plugin/model.py:964` | ✅ porté | `thresholds_v5.py:124-128` (pk = `name`) | |
| `all` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/containers/model_v5.py:137` | |
| `podman_sock` | idem | ✅ porté | `glances/plugins/containers/model_v5.py:123` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` ; usage interne `glances/plugins/containers/model_v5.py:129` | |

### 32. `[amps]` (conf:756-758) et `[amp_*]` (conf:1111-1163)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `[amps] disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `[amp_<name>] enable` / `regex` / `refresh` / `timeout` / `one_line` / `command` / `countmin` / `countmax` / clés libres `<foo>` | `glances/amps/amp.py:79-81` (`load_config` itère `config.items(section)`) ; accesseurs `amp.py:124-142` | ✅ porté | moteur v4 réutilisé : `glances/amps_list_v5.py:46` ; accesseurs de config servis par `glances/config_v5.py:262-279` (`get_float_value`) et `:313-321` (`items`) | Le `ValueError` de `get_float_value` est volontairement conservé — il aiguille les valeurs texte vers la branche de repli de `load_config` (`config_v5.py:266-275`). |
| `[amp_<name>] command` avec opérateurs shell | `glances/amps/amp.py:121` (`allow_operators`, via `args.disable_config_exec`) | ✅ porté | `glances/amps_list_v5.py:61-68` (shim `SimpleNamespace`) ; overlay CLI `glances/main_v5.py:556` | |

### 33. `[alert]` (conf:760-769)

Section **entièrement remplacée** par `[alerts]` (§2). Aucune lecture de
`config.get("alert", …)` dans le code v5.

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ❌ absent | — | Le bloc d'alertes du TUI v5 est synthétisé par le renderer, sans plugin `alert` ni `model_v5.py` associé ; il n'existe aucune bascule de configuration. |
| `max_events` | `glances/plugins/alert/__init__.py:112` | ⚠️ partiel | `glances/alerts_v5.py:162` (`[alerts] history_size`, défaut 200) | Clé renommée et sémantique élargie (taille de l'historique servi par l'API, pas nombre de lignes affichées ; le plafond de 10 lignes du TUI est en dur). |
| `min_duration` | `glances/plugins/alert/__init__.py:113` | ⚠️ partiel | `glances/alerts_v5.py:161` (`[alerts] min_duration_seconds`) | Sémantique **différente** et documentée conf:31-33 : v4 jetait un événement terminé trop court, v5 debounce la transition avant enregistrement. |
| `min_interval` | `glances/plugins/alert/__init__.py:114` | ❌ absent | — | Pas de fusion d'événements rapprochés en v5. |

### 34. `[serverlist]` (conf:775-796)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `columns` | `glances/servers_list.py:84-85` | ❌ absent | — (aucune occurrence de `serverlist` / `servers_list` dans `*_v5.py`) | Mode browser reporté en Phase 3 : docs/architecture/glances-v5-architecture-decisions.md:895-899, 1126-1132. |
| `server_<n>_name` / `_alias` / `_port` / `_protocol` | `glances/servers_list_static.py:40-42` | ❌ absent | — | Idem. |

### 35. `[passwords]` (conf:798-808)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `<host>=<password>` / `default` | `glances/password_list.py:38` (`dict(config.items("passwords"))`) | ❌ absent | — | Phase 3 (docs…decisions.md:1126-1132). |
| `local_password_path` | `glances/password.py:40` | ❌ absent | — | v5 authentifie via `[outputs] password` (hash PBKDF2), pas via un fichier `.pwd`. |

### 36. `[export]` (conf:814-822)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `exclude_fields` | `glances/exports/export.py:86-90` | ✅ porté | `glances/exports/export_base_v5.py:121`, `176-178` | |
| `refresh` | — (clé v5 uniquement ; aucun lecteur v4) | ✅ porté | `glances/exports/export_base_v5.py:82` ; `glances/scheduler_v5.py:193-198` | Livrée dans la conf mais **jamais lue par v4**. Valeur inférieure au refresh global : clampée. |

### 37. `[graph]` (conf:824-837)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `path`, `generate_every`, `width`, `height`, `style` | `glances/exports/glances_graph/__init__.py:33` | ❌ absent | — (pas de `glances/exports/glances_graph/export_v5.py`) | Exporteur non porté ; tous les exporteurs restants sont en Phase 3 (docs…decisions.md:1126-1132). |

### 38. Exporteurs — sections `[influxdb]` → `[clickhouse]` (conf:839-1093)

v5 n'embarque que 6 exporteurs : `csv`, `json`, `influxdb`, `influxdb2`,
`influxdb3`, `prometheus` (`find glances/exports -name '*_v5.py'`). `csv` et
`json` n'ont pas de section de configuration (options CLI uniquement).

| Section | Clés | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `[influxdb]` | `host`, `port`, `user`, `password`, `db` (obligatoires) ; `protocol`, `prefix`, `tags` | `glances/exports/glances_influxdb/__init__.py:42-43` | ✅ porté | `glances/exports/glances_influxdb/export_v5.py:56-59` | Liste identique à v4. |
| `[influxdb2]` | `host`, `port`, `org`, `bucket`, `token` (obligatoires) ; `protocol`, `prefix`, `tags`, `interval` | `glances/exports/glances_influxdb2/__init__.py:42-43` | ⚠️ partiel | `glances/exports/glances_influxdb2/export_v5.py:71-72`, `77-85` | v4 exigeait aussi `user` et `password` ; v5 les a retirés de la liste des obligatoires (ils ne sont pas livrés dans la conf). `interval=0` ⇒ cadence d'export. |
| `[influxdb3]` | `host`, `org`, `database`, `token` (obligatoires) ; `prefix`, `tags`, `port` | `glances/exports/glances_influxdb3/__init__.py:42-43` | ⚠️ partiel | `glances/exports/glances_influxdb3/export_v5.py:60-61` | v4 rendait `port` obligatoire ; v5 le rend optionnel (la conf livre `host=http://localhost:8181`, sans `port`). `interval` commenté conf:895 : **lu ni par v4 ni par v5**. |
| `[prometheus]` | `host`, `port`, `labels` (obligatoires) ; `prefix` | `glances/exports/glances_prometheus/__init__.py:30` | ✅ porté | `glances/exports/glances_prometheus/export_v5.py:63` | |
| `[cassandra]` | `host`, `port`, `keyspace` ; `protocol_version`, `replication_factor`, `table`, `username`, `password` | `glances/exports/glances_cassandra/__init__.py:55-58` | ❌ absent | — | Phase 3. |
| `[opentsdb]` | `host`, `port` ; `prefix`, `tags` | `glances/exports/glances_opentsdb/__init__.py:35` | ❌ absent | — | Phase 3. |
| `[statsd]` | `host`, `port` ; `prefix` | `glances/exports/glances_statsd/__init__.py:33` | ❌ absent | — | Phase 3. |
| `[elasticsearch]` | `scheme`, `host`, `port`, `index` | `glances/exports/glances_elasticsearch/__init__.py:31-32` | ❌ absent | — | Phase 3. |
| `[riemann]` | `host`, `port` | `glances/exports/glances_riemann/__init__.py:35` | ❌ absent | — | Phase 3. |
| `[rabbitmq]` | `host`, `port`, `user`, `password`, `queue` ; `protocol` | `glances/exports/glances_rabbitmq/__init__.py:40-41` | ❌ absent | — | Phase 3. |
| `[mqtt]` | `host`, `password` ; `port`, `devicename`, `user`, `topic`, `tls`, `topic_structure`, `callback_api_version` | `glances/exports/glances_mqtt/__init__.py:38-41` | ❌ absent | — | Phase 3. |
| `[couchdb]` | `host`, `port`, `db`, `user`, `password` | `glances/exports/glances_couchdb/__init__.py:37` | ❌ absent | — | Phase 3. |
| `[mongodb]` | `host`, `port`, `db` ; `user`, `password` | `glances/exports/glances_mongodb/__init__.py:35` | ❌ absent | — | Phase 3. |
| `[kafka]` | `host`, `port`, `topic` ; `compression`, `tags` | `glances/exports/glances_kafka/__init__.py:35-36` | ❌ absent | — | Phase 3. |
| `[zeromq]` | `host`, `port`, `prefix` | `glances/exports/glances_zeromq/__init__.py:34` | ❌ absent | — | Phase 3. |
| `[restful]` | `host`, `port`, `protocol`, `path` | `glances/exports/glances_restful/__init__.py:31` | ❌ absent | — | Phase 3. |
| `[graphite]` | `host`, `port` ; `prefix`, `system_name` | `glances/exports/glances_graphite/__init__.py:36` | ❌ absent | — | Phase 3. |
| `[timescaledb]` | `host`, `port`, `db` ; `user`, `password`, `hostname` | `glances/exports/glances_timescaledb/__init__.py:51-52` | ❌ absent | — | Phase 3. |
| `[nats]` | `host` ; `prefix` | `glances/exports/glances_nats/__init__.py:31-34` | ❌ absent | — | Phase 3. |
| `[duckdb]` | `database` ; `user`, `password`, `hostname` | `glances/exports/glances_duckdb/__init__.py:60-61` | ❌ absent | — | Phase 3. |
| `[clickhouse]` | `host`, `port`, `db`, `user`, `password` ; `hostname` | `glances/exports/glances_clickhouse/__init__.py:86-87` | ❌ absent | — | Phase 3. |

---

### 39. Clés lues par v4 mais **non livrées** dans `conf/glances.conf`

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `[ports] web_<x>_ssl_verify` | `glances/web_list.py:87` | ✅ porté | moteur v4 réutilisé, `glances/plugins/ports/model_v5.py:105` | |
| `[ports] web_<x>_http_proxy` / `_https_proxy` | `glances/web_list.py:89-91` | ✅ porté | idem | |
| `[<plugin>] <level>` nu appliqué à tout champ surveillé | `glances/plugins/plugin/model.py:964`, `1002` | ✅ porté | `glances/plugins/plugin/thresholds_v5.py:130-137` | Sauf champs `strict_thresholds` (`memswap.sin/sout`, `diskio.read_bytes/write_bytes`). |
| `[<plugin>] <level>_action` / `<level>_action_repeat` | `glances/plugins/plugin/model.py:980` | ✅ porté | `glances/alerts_v5.py:779-789` | |
| `[<plugin>] refresh_time` | — (alias v5) | ✅ porté | `glances/scheduler_v5.py:174` | |
| `[<plugin>] min_duration_seconds` | — (v5) | ✅ porté | `glances/alerts_v5.py:596` | |

---

### 40. Récapitulatif

| Statut | Nombre de lignes |
|---|---|
| ✅ porté | 146 |
| ⚠️ partiel | 16 |
| ❌ absent | 47 |
| 🚫 retiré (décision) | 3 |
| ❓ indéterminé | 0 |
| **Total** | **212 lignes sur 40 sous-tables** |

**2026-09-10 — parity wave 1.** 11 lignes passées de `❌ absent` à `✅ porté` :
`[network]` `hide_no_up`, `hide_no_ip`, `hide_zero`, `hide_threshold_bytes`,
`alias` ; `[diskio]` `hide_zero`, `hide_threshold_bytes`, `alias` ; `[fs]`
`free_space`, `allow`, `alias`. Voir
`docs/superpowers/specs/2026-09-10-glances-v5-parity-wave1-design.md` §5.

Les familles de seuils / actions / `min_duration` sont comptées comme **une
ligne par section** (cf. consigne), pas clé par clé.

#### Les 5 écarts les plus lourds

1. **Famille `_log` totalement absente** (§6, §13, §14, §18, §26). v5 historise
   toutes les transitions ≥ `warning` sans possibilité d'exclure un champ.
2. **Seuils réseau et processlist renommés** (§14, §28) : `rx_*`/`tx_*` →
   `bytes_recv_*`/`bytes_sent_*` **avec changement d'unité** (% → ratio) ;
   `cpu_*`/`mem_*` → `cpu_percent_*`/`memory_percent_*`. Les clés livrées sont
   silencieusement ignorées.
3. **Mode browser et 18 exporteurs sur 24 non portés** (§34, §35, §37, §38) —
   décision de phasage explicite (Phase 3), mais c'est le plus gros volume de
   clés mortes.
4. **Famille latence disque supprimée** (§18) : `rx_latency_*` / `tx_latency_*`
   et toutes leurs variantes par disque ne sont plus lues.
5. ~~**Filtres d'affichage réseau/diskio perdus** (§14, §18)~~ — **corrigé
   (parity wave 1, 2026-09-10)** : `hide_no_up`, `hide_no_ip`, `hide_zero`,
   `hide_threshold_bytes`, `alias` (§14, §18), `[fs] allow` / `free_space`
   (§19) sont tous portés.

#### Divergences de comportement par défaut à documenter en breaking change

- `[outputs] cors_origins` : défaut v4 `*`, défaut v5 = middleware non câblé.
- `[outputs] cors_credentials` renommée en `cors_allow_credentials`.
- `[mem] available` : v5 affiche `available` inconditionnellement quand psutil le
  fournit ; v4 affichait `used` par défaut.
- `[alert] min_duration` → `[alerts] min_duration_seconds` : sémantique
  différente (rejet a posteriori vs. debounce), avertissement déjà présent
  conf:31-33.
- La section `[hddtemp]` est morte **dans les deux branches** : v4 comme v5
  lisent `host`/`port` dans `[sensors]` — bug de documentation à corriger dans
  `conf/glances.conf`.


---

## Partie 3 — Raccourcis clavier du TUI

Sources read:

- v4 dispatch table + handlers: `glances/outputs/glances_curses.py`
  (`_hotkeys` dict: lines 41-98; `catch_actions_from_hotkey`/`catch_other_actions_maybe_return_to_browser`/`__catch_key`:
  lines 263-304; individual `_handle_*` methods: lines 306-428).
- v4 in-app help screen data: `glances/plugins/help/__init__.py` (lines 58-144, `generate_view_data`).
- v4 documented keys: `docs/cmds.rst` (Interactive Commands section, lines 239-455).
- v5 dispatch table + handlers: `glances/outputs/glances_curses_v5.py`
  (`_HOTKEYS` dict: lines 147-165; `_handle_key`: lines 266-330; `_handle_help_key`: lines 335-361).
- v5 full-quicklook sibling-hiding: `glances/outputs/curses_renderer_v5.py` (lines 89, 1430).
- v5 process/program mutual exclusion: `glances/outputs/glances_curses_v5.py` lines 562-568.

**Method note on `v4 (file:line)`**: v4 dispatches every letter/digit key through one shared
`_hotkeys` dict (`glances/outputs/glances_curses.py:41-98`) plus a second `catch_other_actions_maybe_return_to_browser`
dict for non-ASCII/arrow keys (`glances/outputs/glances_curses.py:272-288`). The file:line given per row
is the entry inside whichever of those two dicts defines the key, plus the `_handle_*` method it calls
where one exists.

**Method note on absence in v5**: `glances/outputs/glances_curses_v5.py` handles every keypress through
exactly one function, `_handle_key` (lines 266-330), which only recognises `curses.KEY_RESIZE`, `27` (ESC),
and characters present in the `_HOTKEYS` dict (lines 147-165: `a c m i t p u o 1 4 / j h q`). I grepped the
whole file for `kill_process`, `nice_increase`, `nice_decrease`, `process_filter`, `edit_filter`,
`cursor_position`, `reset_minmax`, `curses.KEY_` and `ord("` to confirm no other branch exists outside
`_handle_key`/`_handle_help_key` (which only fires while the help overlay itself is open, for scrolling).
Every "❌ absent" below is therefore an absence from that closed set, not a guess.

---

### SORT PROCESSES

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `a` | Sort processes automatically (alert-driven) | `glances_curses.py:53` (`_hotkeys['a']`) → `_handle_sort_key`, `glances_curses.py:325-326` | ✅ porté | `glances_curses_v5.py:149` (`_HOTKEYS['a']`), dispatch `glances_curses_v5.py:321-329` | `set_sort_key(key, key=='auto')` — same engine call as v4. |
| `c` | Sort by CPU% | `glances_curses.py:57` | ✅ porté | `glances_curses_v5.py:150` | |
| `i` | Sort by I/O rate | `glances_curses.py:68` | ✅ porté | `glances_curses_v5.py:152` | |
| `o` | Sort by CPU core number | `glances_curses.py:79` | ✅ porté | `glances_curses_v5.py:156` | Undocumented in v4's in-app help and in `docs.rst`, but real in v4 code — see Note on `o` below table. |
| `m` | Sort by MEM% | `glances_curses.py:75` | ✅ porté | `glances_curses_v5.py:151` | |
| `p` | Sort by process name | `glances_curses.py:80` | ✅ porté | `glances_curses_v5.py:154` | |
| `t` | Sort by CPU time (TIME+) | `glances_curses.py:88` | ✅ porté | `glances_curses_v5.py:153` | |
| `u` | Sort by USER | `glances_curses.py:90` | ✅ porté | `glances_curses_v5.py:155` | |

Note on `o`: `docs/cmds.rst` never documents this key, and the in-app help screen
(`glances/plugins/help/__init__.py:66`) does list `sort_cpu_num` for `o` ("CPU core number") — so it is
documented in-app, just missing from `docs.rst`. Correcting the earlier cell: v4 in-app help does cover it;
only the RST docs are incomplete. Not a v5 gap.

All 8 v4 sort keys are ported 1:1, same letters, same underlying `glances_processes.set_sort_key` engine call.

---

### SHOW/HIDE SECTION

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `A` | Show/hide AMPs (Application Monitoring Process) | `glances_curses.py:54` (`switch: disable_amps`) | ❌ absent | not in `_HOTKEYS` dict, `glances_curses_v5.py:147-165` | AMPs plugin itself is ported (memory: G6C-amps done), but no hotkey exists in v5 to toggle it. |
| `d` | Show/hide Disk I/O | `glances_curses.py:59` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `D` | Show/hide Docker/containers | `glances_curses.py:60` | ❌ absent | `glances_curses_v5.py:147-165` | Containers plugin ported (G6A), no v5 hotkey. |
| `e` | Show/hide top process extended stats | `glances_curses.py:274` (`catch_other_actions` dict) → `_handle_process_extended`, `glances_curses.py:345-351` | ❌ absent | `glances_curses_v5.py:147-165` (no `action`/`switch` for extended stats anywhere in file) | |
| `f` | Show/hide filesystem + folders | `glances_curses.py:63` (`handler: _handle_fs_stats`) → `glances_curses.py:356-358` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `G` | Show/hide GPU | `glances_curses.py:66` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `I` | Show/hide IP module | `glances_curses.py:69` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `K` | Show/hide TCP connections | `glances_curses.py:72` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `l` | Show/hide alert/log messages | `glances_curses.py:73` | ❌ absent | `glances_curses_v5.py:147-165` | v5's alert block (G7, memory: `project_v5_g7_done`) is a static incident grid; nothing in `glances_curses_v5.py` toggles its visibility. |
| `n` | Show/hide network stats | `glances_curses.py:77` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `N` | Show/hide current time | `glances_curses.py:78` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `P` | Show/hide ports stats | `glances_curses.py:81` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `Q` | Show/hide IRQ module | `glances_curses.py:83` (`switch: enable_irq`, inverted-polarity flag) | ❌ absent | `glances_curses_v5.py:147-165` | |
| `R` | Show/hide RAID plugin | `glances_curses.py:85` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `s` | Show/hide sensors | `glances_curses.py:86` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `V` | Show/hide VMS plugin | `glances_curses.py:92` | ❌ absent | `glances_curses_v5.py:147-165` | VMS plugin ported (G6A), no v5 hotkey. |
| `W` | Show/hide Wifi module | `glances_curses.py:94` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `z` | Show/hide processes | `glances_curses.py:96` (`handler: _handle_disable_process`) → `glances_curses.py:382-387` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `7` | Show/hide NPU | `glances_curses.py:50` | ❌ absent | `glances_curses_v5.py:147-165` | Not documented in v4 in-app help or `docs.rst` either — real only in v4 code. |
| `8` | Show/hide MPP | `glances_curses.py:51` | ❌ absent | `glances_curses_v5.py:147-165` | Same as `7`: undocumented anywhere in v4 docs, real in v4 code only. |
| `2` | Show/hide left sidebar | `glances_curses.py:45` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `3` | Show/hide Quick Look | `glances_curses.py:46` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `4` | Full quicklook (hide cpu/npu/mpp/gpu/mem/memswap, keep quicklook+load) | `glances_curses.py:47` (`handler: _handle_quicklook`) → `enable_fullquicklook`/`disable_fullquicklook`, `glances_curses.py:447-456` | ✅ porté | `glances_curses_v5.py:159` (`_HOTKEYS['4']`), dispatch `glances_curses_v5.py:310-315`; sibling-hiding set `curses_renderer_v5.py:89` (`_FULL_QUICKLOOK_HIDDEN = {"cpu","npu","mpp","gpu","mem","memswap"}`), applied `curses_renderer_v5.py:1430` | Exact same 6-plugin hidden set as v4's `enable_fullquicklook` (`glances_curses.py:455`). |
| `5` | Show/hide top menu (QuickLook, CPU, MEM, SWAP, LOAD) | `glances_curses.py:48` (`handler: _handle_top_menu`) → `disable_top`/`enable_top`, `glances_curses.py:437-445` | ❌ absent | `glances_curses_v5.py:147-165` | |

---

### TOGGLE DATA TYPE

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `b` | Network I/O: bit/s ↔ byte/s | `glances_curses.py:55` | ❌ absent | `glances_curses_v5.py:147-165` | v5 has a `--byte` CLI/constructor flag (`glances_curses_v5.py:202,247`) consumed at startup, but no runtime hotkey toggles it. |
| `B` | Disk I/O: count ↔ IOPS | `glances_curses.py:56` (`handler: _handle_diskio_iops`) → `glances_curses.py:389-393` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `L` | Disk I/O: bytes/s ↔ latency | `glances_curses.py:74` (`handler: _handle_diskio_latency`) → `glances_curses.py:395-399` | ❌ absent | `glances_curses_v5.py:147-165` | Undocumented in v4 in-app help and in `docs.rst` — real only in v4 code (mutually exclusive with `B`, see `glances_curses.py:392-393,397-398`). |
| `F` | Filesystem: used ↔ free space | `glances_curses.py:64` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `S` | Quicklook: bar ↔ sparkline | `glances_curses.py:87` (`switch: sparkline`) | ❌ absent | `glances_curses_v5.py:147-165` | |
| `T` | Network I/O: separate ↔ combined | `glances_curses.py:89` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `U` | Network I/O: live ↔ cumulative | `glances_curses.py:91` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `0` | Load: Linux-style ↔ percentage (Irix mode) | `glances_curses.py:43` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `1` | CPU: aggregate ↔ per-CPU | `glances_curses.py:44` (`switch: percpu`) | ✅ porté | `glances_curses_v5.py:158` (`_HOTKEYS['1']`); mutual exclusion `glances_curses_v5.py:562-564` (`hidden_top = "cpu" if show_percpu else "percpu"`) | |
| `6` | GPU: individual ↔ mean | `glances_curses.py:49` (`switch: meangpu`) | ❌ absent | `glances_curses_v5.py:147-165` | v5 has a `--meangpu` constructor/CLI flag (`glances_curses_v5.py:199,242`) consumed at startup only, not a runtime hotkey. |
| `/` | Process names: short ↔ full | `glances_curses.py:52` (`switch: process_short_name`) | ✅ porté | `glances_curses_v5.py:160` (`_HOTKEYS['/']`); consumed `glances/plugins/processlist/render_curses_v5.py:391` | Consumed only by the `processlist` renderer, same scope as v4 (`glances/plugins/processlist/__init__.py:558` — `programlist` doesn't reference it in either version). |

---

### MISCELLANEOUS

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `ENTER` | Edit process filter pattern | `glances_curses.py:42` (`handler: _handle_enter`) → `glances_curses.py:328-329`; popup at `glances_curses.py:610-625` | ❌ absent | `glances_curses_v5.py:266-330` (`_handle_key` never tests for `\n`/`10`) | No interactive process filter of any kind exists in v5's curses code (`process_filter`/`edit_filter` do not appear in `glances_curses_v5.py`). |
| `E` | Erase process filter | `glances_curses.py:62` (`handler: _handle_erase_filter`) → `glances_curses.py:353-354` | ❌ absent | `glances_curses_v5.py:147-165` | Consequence of ENTER being absent — nothing to erase either. |
| `g` | Generate history graphs (export) | `glances_curses.py:65` (`switch: generate_graph`) | ❌ absent | `glances_curses_v5.py:147-165` | |
| `h` | Show/hide help screen | `glances_curses.py:67` (`switch: help_tag`) | ✅ porté | `glances_curses_v5.py:163` (`_HOTKEYS['h']`), dispatch `glances_curses_v5.py:306-309`; closes via `q`/ESC/`h`, `glances_curses_v5.py:343-345` | v5's overlay content is generated from the `_HOTKEYS` table itself (`glances_curses_v5.py:144-146,1196`), so it only ever lists v5's own (much smaller) key set — by construction it cannot drift from what v5 actually handles, but it also cannot show v4's full list. |
| `j` | Threads ↔ programs (process list aggregation) | `glances_curses.py:70` (`switch: programs`) | ✅ porté | `glances_curses_v5.py:161` (`_HOTKEYS['j']`); mutual exclusion `glances_curses_v5.py:565-568` (`hidden_right = "processlist" if programs else "programlist"`) | While the help overlay is open, `j`/`k` are repurposed for scroll-down/scroll-up (`glances_curses_v5.py:346,349`) instead of their normal action — by design (`_handle_help_key` intercepts all keys first, `glances_curses_v5.py:290-291`), not a bug. |
| `+` | Increase nice level of selected process | `glances_curses.py:97` (`handler: _handle_increase_nice`) → `glances_curses.py:360-361` | ❌ absent | `glances_curses_v5.py:147-165` | No process cursor/selection exists in v5 at all (see `k`/arrows below), so nice adjustment has nothing to target. |
| `-` | Decrease nice level of selected process | `glances_curses.py:98` (`handler: _handle_decrease_nice`) → `glances_curses.py:363-364` | ❌ absent | `glances_curses_v5.py:147-165` | Same as `+`. |
| `k` | Kill selected process | `glances_curses.py:275` (`catch_other_actions` dict) → `_handle_kill_process`, `glances_curses.py:366-367`; confirm popup `glances_curses.py:641-644` | ❌ absent | `glances_curses_v5.py:147-165` (no `kill_process`/`kill(` anywhere in the file) | |
| `M` | Reset processes summary min/max | `glances_curses.py:76` (`switch: reset_minmax_tag`) | ❌ absent | `glances_curses_v5.py:147-165` | |
| `q` | Quit | `glances_curses.py:287` (`catch_other_actions` dict, `ord('q')`) → `_handle_quit`, `glances_curses.py:417-425` | ✅ porté | `glances_curses_v5.py:164` (`_HOTKEYS['q']`), dispatch `glances_curses_v5.py:303-305` | |
| `r` | **Real v4 behaviour: show/hide SMART stats** (`switch: disable_smart`) | `glances_curses.py:84` | ❌ absent | `glances_curses_v5.py:147-165` | Flagging a pre-existing v4-internal inconsistency, unrelated to v5: v4's own in-app help (`glances/plugins/help/__init__.py:137`, `misc_reset_history`) and `docs/cmds.rst:353-354` both label `r` as "Reset history", but the actual `_hotkeys` dispatch table binds `r` to `disable_smart` (SMART plugin visibility), not to any reset-history code path — `reset_history_tag` (`glances_curses.py:236`) is set once at init and never toggled by any key. Whichever v4 behaviour is intended, v5 has no `r` hotkey and no SMART-visibility toggle at all. |
| `w` | Delete finished warning log messages | `glances_curses.py:93` (`handler: _handle_clean_logs`) → `glances_curses.py:376-377` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `x` | Delete finished warning+critical log messages | `glances_curses.py:95` (`handler: _handle_clean_critical_logs`) → `glances_curses.py:379-380` | ❌ absent | `glances_curses_v5.py:147-165` | |

---

### NAVIGATION (documented in `docs.rst`'s Interactive Commands list, not in the in-app help screen)

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `ESC` | Quit (also closes nothing else in v4 — no modal-close semantics) | `glances_curses.py:287` (`ord('\x1b')`) → `_handle_quit` | ✅ porté | `glances_curses_v5.py:293-294` (`if key == 27: return "quit"`) | In v5, ESC is context-sensitive: it quits normally, but closes the help overlay instead of quitting while the overlay is open (`glances_curses_v5.py:343-345`) — a v5-only modal-close behavior v4 doesn't have (v4's help screen is a `switch`, closed by pressing `h` again, not ESC). Not a regression since ESC-to-close is additive, but it is a behavioural difference worth naming: ⚠️ partiel would also be defensible here; recording as ✅ porté for the "ESC quits" core contract with this caveat noted. |
| `UP` (or ANSI code `65`) | Move process-list cursor up | `glances_curses.py:284` (`catch_other_actions` dict) → `_handle_cursor_up`, `glances_curses.py:409-411` | ❌ absent | `glances_curses_v5.py:147-165`, and no `curses.KEY_UP` reference outside `_handle_help_key` (`glances_curses_v5.py:349`, help-scroll only) | v5 has no process-selection cursor at all — `cursor_position` does not appear in `glances_curses_v5.py`. |
| `DOWN` (or ANSI code `66`) | Move process-list cursor down | `glances_curses.py:285` → `_handle_cursor_down`, `glances_curses.py:413-415` | ❌ absent | same as `UP` | |
| `LEFT` / `SHIFT-LEFT` | Scroll process name left / navigate sort left (swapped by `arrow_keys_sort` config) | `glances_curses.py:276-277,280-281` → `_handle_sort_left` (`glances_curses.py:401-403`) / `_handle_process_name_left` (`glances_curses.py:369-371`) | ❌ absent | `glances_curses_v5.py:147-165`; no `curses.KEY_LEFT`/`KEY_SLEFT` anywhere in the file | |
| `RIGHT` / `SHIFT-RIGHT` | Scroll process name right / navigate sort right (swapped by `arrow_keys_sort` config) | `glances_curses.py:278-279,282-283` → `_handle_sort_right` (`glances_curses.py:405-407`) / `_handle_process_name_right` (`glances_curses.py:373-374`) | ❌ absent | `glances_curses_v5.py:147-165`; no `curses.KEY_RIGHT`/`KEY_SRIGHT` anywhere in the file | |
| `F5` / `Ctrl-R` (ASCII `18`) | Force-refresh (reset internal process cache) | `glances_curses.py:286` (`{curses.KEY_F5, 18}`) → `_handle_refresh`, `glances_curses.py:427-428` | ❌ absent | `glances_curses_v5.py:147-165`; no `curses.KEY_F5` or literal `18` anywhere in the file | |

`Ctrl-C` is documented in `docs/cmds.rst:347` (`q|ESC|CTRL-C`) as a quit key, but it is not part of v4's curses
key-handling code at all — `_handle_quit`'s trigger set is only `{ord('\x1b'), ord('q')}` (`glances_curses.py:287`);
Ctrl-C works because it is the OS-level SIGINT → `KeyboardInterrupt`, unrelated to `__catch_key`. Excluded as a
row (not a curses hotkey in either version); ❓ indéterminé whether v5's thread/signal handling reproduces the
same SIGINT behaviour — I did not trace `main_v5.py`'s signal wiring, which is out of this section's scope
(curses key handling only).

---

### Summary

- **v4 hotkeys found:** 62 rows tabulated above, from two v4 dispatch tables — `_hotkeys`
  (`glances_curses.py:41-98`, 54 real entries: 8 sort + 46 switch/handler keys) and
  `catch_other_actions_maybe_return_to_browser` (`glances_curses.py:272-288`: `e`, `k`, `LEFT`, `RIGHT`,
  `SHIFT-LEFT`, `SHIFT-RIGHT`, `UP`, `DOWN`, `F5`/`Ctrl-R`, `ESC`) — grouped into 5 sections (8 sort +
  24 show/hide + 11 toggle-data-type + 13 miscellaneous + 6 navigation). Two navigation rows each fold
  two physical key encodings that share one action (`LEFT`/`SHIFT-LEFT`, `RIGHT`/`SHIFT-RIGHT`,
  `F5`/`Ctrl-R`), matching how `docs.rst` itself presents them.
- **Status counts (62 rows):** ✅ porté = 15 (`a c i o m p t u` sort keys, `4` full-quicklook, `1` percpu,
  `/` short/full name, `h` help, `j` threads/programs, `q` quit, `ESC` quit) · ⚠️ partiel = 0 ·
  ❌ absent = 47 · 🚫 retiré (décision) = 0 (no recorded maintainer decision found to drop any of these;
  every absence reads as "not yet built", not "deliberately removed") · ❓ indéterminé = 0 rows (one open
  question flagged in prose, not counted as a row: whether v5 reproduces v4's Ctrl-C/SIGINT quit behaviour —
  out of scope since Ctrl-C isn't a curses-layer hotkey in v4 either).
- **Most significant gaps:** the entire interactive process-management surface is missing from v5 — no
  process cursor (`UP`/`DOWN`), no kill (`k`), no nice adjustment (`+`/`-`), no process filter (`ENTER`/`E`),
  no extended-stats toggle (`e`), no min/max reset (`M`). All 20 individual plugin show/hide toggles
  (`A d D f G I K l n N P Q R s V W z 7 8`, plus layout toggles `2 3 5`) are absent — v5 currently has no
  per-plugin visibility hotkeys at all, only the two structural view toggles `1` (percpu) and `4` (full
  quicklook). All 9 other "toggle data type" keys are absent (`b B L F S T U 0 6`), leaving only `1` and `/` ported. `F5`/`Ctrl-R`
  refresh and the sort-navigation arrow keys are absent.
- **v4-internal finding (not a v5 gap):** the `r` key's documented action ("Reset history", per both the
  in-app help screen and `docs.rst`) does not match its actual code (`disable_smart` toggle) — a pre-existing
  v4 documentation bug, flagged in the `r` row above.
- File written to: `/tmp/claude-1000/-home-nicolargo-dev-glances/7c4d4fe8-f74e-4428-a265-e88f3a2cb602/scratchpad/inventory/hotkeys.md`

---

## Suites proposées

Par ordre de valeur pour l'utilisateur, pas par ordre de difficulté.

1. ~~**Trancher la question des seuils renommés**~~ — **fait (parity wave 1,
   2026-09-10)** : rename gardé, WARNING au démarrage sur toute clé de seuil
   non reconnue (`base_v5.py::_warn_unknown_threshold_keys`). Reste à écrire
   dans les notes de version 5.0.0 (breaking change).
2. **Reconstituer le TUI interactif** — gestion des processus d'abord (curseur,
   `k`, `+`/`-`, filtre), bascules d'affichage ensuite. La mécanique existe
   déjà (`ViewState` + table `_HOTKEYS` pilotée par les données) : chaque
   bascule est une entrée de dict plus une garde dans le renderer. Désormais un
   groupe possédé dans la roadmap (`…decisions.md` §10, « Phase 2.X — TUI
   interactive surface »), aucune implémentation encore.
3. **Reprendre les options CLI d'affichage et de processus**, y compris les
   alias courts. Beaucoup sont un simple `parser.add_argument` plus un accès
   dans le renderer concerné.
4. ~~**Corriger les deux options mortes**~~ — **fait (parity wave 1,
   2026-09-10)**.
5. **Porter la famille `<...>_log`** — reste à faire. ~~puis les filtres
   d'affichage restants (`hide_zero`, `hide_no_up`, `hide_no_ip`, `alias`
   générique, `[fs] allow`, `[fs] free_space`)~~ — **faits (parity wave 1,
   2026-09-10)**.
6. **Écrire les notes de version des changements de défaut** identifiés ici :
   `--bind` en loopback, `-s`/`-w`, `[mem] available` affiché
   inconditionnellement, seuils renommés.

Le phasage déjà décidé (18 exporteurs, mode browser, client distant, SNMP →
Phase 3) n'a pas besoin d'arbitrage ; il n'entre dans ce document que pour que
le volume de clés inertes soit visible.
