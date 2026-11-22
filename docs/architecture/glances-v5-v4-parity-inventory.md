# Glances v5 — inventaire de parité v4 → v5

**Date** : 2026-09-10, recomptée le 2026-11-15 · **Branche** : `develop` (`417a291`, après la bascule `develop-v5 → develop`) · **Référence v4** : `support/glancesv4`

> **Recompte du 2026-11-15.** Les statuts des trois parties ont été revérifiés contre le code de `develop`. Seules les lignes dont le statut a changé ont un nouveau « Statut » et un nouveau « Preuve » ; les autres lignes `✅ porté` n'ont pas été rouvertes. Les `file:line` des lignes non modifiées datent du 2026-09-10 : ils citent encore les fichiers `*_v5.py`, dont le suffixe `_v5` a disparu à la bascule (`main_v5.py` est devenu `main.py`, etc.).

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
| Options CLI | 86 | 71 | 0 | 0 | 15 |
| Clés de configuration | 211 | 178 | 14 | 9 | 10 |
| Hotkeys TUI | 62 | 58 | 0 | 2 | 2 |
| **Total** | **359** | **307** | **14** | **11** | **27** |

Avant le recompte (2026-09-10, mêmes lignes recomptées par balayage de la colonne « Statut ») : 177 `✅`, 26 `⚠️`, 152 `❌`, 4 `🚫`. Le total est de 359 lignes et non 360 : une ligne de la partie 2 (le rappel barré de `[hddtemp] host/port`) ne porte pas de statut balisé.

**2026-11-15 — recompte.** 154 lignes ont changé de statut (129 vers `✅ porté`, 23 vers `🚫 retiré (décision)`, 2 vers `⚠️ partiel`) :

* **129 lignes → `✅ porté`** : presque toute la CLI (mode client et browser, `-w`, alias courts `-p -B -V -c -u -t -0..-6`, `--stdout*`, `--fetch*`, `--issue`, `--process-*`, `--sort-processes`, `--diskio-*`, `--fs-free-space`, `--disable-*`…), 58 touches sur 62 (processus, bascules par plugin, types de données), la famille `_log`, la latence disque, les seuils per-CPU, `[serverlist]`, `[passwords]`, `[graph]` et les 17 sections d'exporteurs qui manquaient (24 modules d'export au total).
* **23 lignes → `🚫 retiré (décision)`** (27 au total avec les 4 d'origine) : `--cached-time`, `-P`, `--sparkline` et la touche `S`, `--disable-check-update`, `--enable-process-extended` et la touche `e`, `--trace-malloc`, le prompt `--username`, le sens v4 de `--api-doc`, les 6 options SNMP, `[global] check_update` / `plugin_dir`, `[outputs] xmlrpc_allowed_hosts`, `[hddtemp]` et `[passwords] local_password_path` (chaque ligne cite sa décision : `NEWS.rst`, spec Phase 3, #3486).
* **Les 11 `❌` qui restent** : `[outputs] left_menu` et `webui_root_path` ; `folder_<n>_<level>_action` ; `<type>_<label>_log` et `<type>_<label>_<level>_action` (sensors) ; `[processlist] sort_key` et `disable_stats` ; `[alert] disable` et `min_interval` ; les touches `w` et `x` (effacer les alertes terminées).
* **Les 14 `⚠️` qui restent** sont des clés renommées sans alias (seuils réseau, disque, fs, processlist, `cors_credentials`), les deux clés d'alerte à sémantique différente, `max_processes_display` (lue par la WebUI, côté TUI non vérifié) et deux sections d'exporteurs dont la liste de clés obligatoires diffère.

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

## Les écarts qui comptent (recompte du 2026-11-15)

La liste du 2026-09-10 (processus interactifs, bascules par plugin, alias courts,
`_log`, exporteurs, browser) est **soldée**. Ce qui reste :

1. **Changements de défaut et de sens, à garder dans les notes de version** :
   `--bind` passe de `0.0.0.0` à `127.0.0.1` ; `-s` lance l'API REST et la
   WebUI au lieu du serveur XML-RPC ; `--password` ne demande le mot de passe
   qu'en mode client ; `--api-doc` change de sens. Tous sont dans `NEWS.rst`.
2. **Clés de seuil renommées, sans alias** : `[network] rx_*`/`tx_*` →
   `bytes_recv_*`/`bytes_sent_*` (pourcentage → ratio [0,1]), `[processlist]
   cpu_*` → `cpu_percent_*`, `[fs] /_careful` → `/_percent_careful`. Une clé non
   reconnue déclenche un WARNING au démarrage.
3. **Actions d'alerte par dossier et par capteur** : `folder_<n>_<level>_action`
   et `<type>_<label>_<level>_action` ne se déclenchent pas.
4. **`[processlist] sort_key` et `disable_stats`** ne sont pas lus ; le tri se
   règle par `--sort-processes` ou au clavier. (`disable_virtual_memory` est
   porté depuis : voir la ligne de la partie 3.)
5. **Touches `w` et `x`** (effacer les alertes terminées) : absentes, l'historique
   d'alertes v5 est un tampon borné.
6. **`[alert]`** : `disable` et `min_interval` n'ont pas d'équivalent dans `[alerts]`.
7. **`[outputs] left_menu` et `webui_root_path`** : clés sans équivalent.

## Deux trouvailles hors périmètre

- ~~**`[hddtemp] host`/`port` est une section morte dans les deux branches** :
  le `plugin_name` de `HddtempPlugin` se résout à `sensors`, donc v4 comme v5
  lisent `[sensors] host`/`port`. C'est un bug de documentation de
  `conf/glances.conf`, à corriger côté v4.~~ — **caduc** : hddtemp est retiré
  de la v5 (#3486, PR #3530).
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
| `-s`, `--server` | `glances/main.py:397` | ✅ porté | `glances/main.py:250` (`build_parser`) | sémantique changée (XML-RPC → REST + WebUI), documentée dans `NEWS.rst`. |
| `-w`, `--webserver` | `glances/main.py:462` | ✅ porté | `glances/main.py:254` (`build_parser`) | `-w/--webserver` est un alias de `-s`. |
| `-c`, `--client` | `glances/main.py:394` | ✅ porté | `glances/main.py:266` (`build_parser`) | `--client` affiche un serveur v5 dans le TUI (`run_client`). |
| `--browser` | `glances/main.py:400` | ✅ porté | `glances/main.py:291` (`build_parser`) | mode browser livré (TUI, WebUI, Zeroconf). |
| `--disable-autodiscover` | `glances/main.py:407` | ✅ porté | `glances/main.py:301` (`build_parser`) | recomptée. |
| `-p`, `--port` | `glances/main.py:414` | ✅ porté | `glances/main.py:229` (`build_parser`) | alias court `-p` présent. |
| `-B`, `--bind` | `glances/main.py:422` | ✅ porté | `glances/main.py:222` (`build_parser`) | alias `-B` présent ; défaut `127.0.0.1` documenté dans `NEWS.rst`. |
| `--cached-time` | `glances/main.py:483` | 🚫 retiré (décision) | — | retiré en 5.0 (`NEWS.rst`, « Removed options »). |
| `--stop-after` | `glances/main.py:490` | ✅ porté | `glances/main.py:612` (`build_parser`) | recomptée. |
| `--open-web-browser` | `glances/main.py:497` | ✅ porté | `glances/main.py:620` (`build_parser`) | recomptée. |
| `--disable-webui` | `glances/main.py:231` | ✅ porté | `glances/main_v5.py:128` (parser) ; `glances/webserver_v5.py:145` (`if args is not None and not getattr(args, "disable_webui", False): _wire_webui(app)`) | En v5 le drapeau n'a de sens qu'avec `-s` (aide `main_v5.py:131`). |
| `--enable-mcp` | `glances/main.py:470` | ✅ porté | `glances/main_v5.py:133` (parser) ; `glances/main_v5.py:606-610` (overlay `[outputs] enable_mcp`) ; `glances/webserver_v5.py:200` (lecture du gate) | Contrainte v5 supplémentaire : `--enable-mcp` sans `-s` est une **erreur fatale** (`glances/main_v5.py:281-282`), là où v4 l'ignorait. Double opt-in documenté §11.1 (`docs/architecture/glances-v5-architecture-decisions.md:1174+`). |
| `--mcp-path` | `glances/main.py:477` | ✅ porté | `glances/main.py:319` (`build_parser`) | recomptée. |
| `-q`, `--quiet` | `glances/main.py:505` | ✅ porté | `glances/main_v5.py:189` (parser, `--quiet` / `--no-tui` → `dest="no_tui"`) ; `glances/main_v5.py:616` (`elif not getattr(args, "no_tui", False)`) | **Pas d'alias court `-q`** en v5 (forme longue seulement) — à ce titre on pourrait aussi le lire comme partiel ; le comportement, lui, est intégralement câblé. Le devenir du drapeau est une question ouverte : `docs/architecture/glances-v5-architecture-decisions.md:155-162`. |

### 2. Client/serveur — authentification et SNMP

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-u <username>` | `glances/main.py:429` | ✅ porté | `glances/main.py:277` (`build_parser`) | `-u/--username` prend le nom d'utilisateur en valeur. |
| `--username` (prompt) | `glances/main.py:430` | 🚫 retiré (décision) | — | v5 : `-u/--username` prend une valeur, plus de prompt (`NEWS.rst`). |
| `--password` (prompt) | `glances/main.py:437` | ✅ porté | `glances/main.py:284` (`build_parser`) | le prompt ne vaut qu'en mode client ; serveur protégé par `[outputs] password` (hash de `--set-password`). Documenté dans `NEWS.rst`. |
| `--snmp-community` | `glances/main.py:444` | 🚫 retiré (décision) | — | SNMP abandonné par le mainteneur le 2026-09-27 (`docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md` §1). |
| `--snmp-port` | `glances/main.py:445` | 🚫 retiré (décision) | — | SNMP abandonné par le mainteneur le 2026-09-27 (`docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md` §1). |
| `--snmp-version` | `glances/main.py:446` | 🚫 retiré (décision) | — | SNMP abandonné par le mainteneur le 2026-09-27 (`docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md` §1). |
| `--snmp-user` | `glances/main.py:447` | 🚫 retiré (décision) | — | SNMP abandonné par le mainteneur le 2026-09-27 (`docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md` §1). |
| `--snmp-auth` | `glances/main.py:448` | 🚫 retiré (décision) | — | SNMP abandonné par le mainteneur le 2026-09-27 (`docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md` §1). |
| `--snmp-force` | `glances/main.py:451` | 🚫 retiré (décision) | — | SNMP abandonné par le mainteneur le 2026-09-27 (`docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md` §1). |

### 3. Configuration / plugins

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-C`, `--config` | `glances/main.py:193` / `:197` (branche shtab) | ✅ porté | `glances/main_v5.py:83` (parser, `dest="config_path"`) ; `glances/main_v5.py:742` (`GlancesConfigV5(cli_config_path=args.config_path)`) ; `glances/config_v5.py:140-141` | v5 ajoute par-dessus un overlay d'environnement `GLANCES_<SECTION>__<KEY>` (§2, `docs/architecture/glances-v5-architecture-decisions.md:171-176`). `config_path` est **redacté** dans `/api/5/args` (`glances/routes_v5.py:70`). |
| `-P`, `--plugins` (`plugin_dir`) | `glances/main.py:198` | 🚫 retiré (décision) | — | plugins externes retirés en 5.0 (`NEWS.rst`). |
| `--modules-list`, `--module-list` | `glances/main.py:200` | ✅ porté | `glances/main.py:627` (`build_parser`) | recomptée. |
| `--disable-plugin`, `--disable-plugins`, `--disable` | `glances/main.py:208` | ✅ porté | `glances/main_v5.py:172` (parser) ; `glances/main_v5.py:437-440` (overlay `[<plugin>] disable`) ; `glances/plugins/plugin/base_v5.py:159-166` (`is_disabled()`) | Divergence assumée v5 : un **nom de plugin inconnu est fatal** (`glances/main_v5.py:424-427`), là où v4 l'ignorait silencieusement. Le couplage `processcount` → `processlist` de v4 est reproduit (`glances/main_v5.py:447-451`). |
| `--enable-plugin`, `--enable-plugins`, `--enable` | `glances/main.py:216` | ✅ porté | `glances/main_v5.py:181` (parser) ; `glances/main_v5.py:439-440` | Sémantique v4 conservée : `enable` gagne sur `disable`. `--disable-plugin all` exige `--enable-plugin` (`glances/main_v5.py:429-434`). |
| `--disable-process` | `glances/main.py:223` | ✅ porté | `glances/main.py:484` (`build_parser`) | recomptée. |
| `--enable-irq` | `glances/main.py:319` | ✅ porté | `glances/main.py:501` (`build_parser`) | recomptée. |
| `-3`, `--disable-quicklook` | `glances/main.py:271` | ✅ porté | `glances/main.py:469` (`build_parser`) | recomptée. |
| `-2`, `--disable-left-sidebar` | `glances/main.py:263` | ✅ porté | `glances/main.py:461` (`build_parser`) | recomptée. |
| `-5`, `--disable-top` | `glances/main.py:287` | ✅ porté | `glances/main.py:477` (`build_parser`) | recomptée. |

### 4. Affichage / TUI

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-1`, `--percpu`, `--per-cpu` | `glances/main.py:254` | ✅ porté | `glances/main.py:397` (`build_parser`) | alias `-1` et `--per-cpu` présents. |
| `-4`, `--full-quicklook` | `glances/main.py:279` | ✅ porté | `glances/main.py:406` (`build_parser`) | alias `-4` présent. |
| `-6`, `--meangpu` | `glances/main.py:295` | ✅ porté | `glances/main.py:414` (`build_parser`) | alias `-6` présent. |
| `--fahrenheit` | `glances/main.py:633` | ✅ porté | `glances/main_v5.py:221` (parser) ; `glances/main_v5.py:656` ; `glances/outputs/glances_curses_v5.py:243`, `:797` ; `glances/plugins/sensors/render_curses_v5.py:107` ; `glances/plugins/gpu/render_curses_v5.py:135` | Appliqué aux capteurs *et* au GPU, comme en v4. |
| `--hide-public-info` | `glances/main.py:661` | ✅ porté | `glances/main_v5.py:228` (parser) ; `glances/main_v5.py:657` ; `glances/outputs/glances_curses_v5.py:244`, `:798` ; `glances/plugins/ip/render_curses_v5.py:44` | |
| `-b`, `--byte` | `glances/main.py:604` | ✅ porté | `glances/main_v5.py:235` (parser) ; `glances/main_v5.py:658` ; `glances/outputs/glances_curses_v5.py:247`, `:799` ; `glances/plugins/containers/render_curses_v5.py:257` ; `glances/plugins/network/render_curses_v5.py:100` (`byte = bool((view or {}).get("byte"))`), `:66-69` (pas de ×8, pas de suffixe `b`) | **Corrigé (parity wave 1, 2026-09-10)** : le renderer réseau lit désormais `view["byte"]`, v4 parity (`network/__init__.py:273`). Le `TODO(G2+)` sur `max_width`/`args` reste ouvert (portée hors sujet) mais ne concerne plus `--byte`. |
| `-0`, `--disable-irix` | `glances/main.py:246` | ✅ porté | `glances/main.py:509` (`build_parser`) | recomptée. |
| `--light`, `--enable-light` | `glances/main.py:238` | ✅ porté | `glances/main.py:492` (`build_parser`) | recomptée. |
| `--disable-bold` | `glances/main.py:305` | ✅ porté | `glances/main.py:530` (`build_parser`) | recomptée. |
| `--disable-bg` | `glances/main.py:312` | ✅ porté | `glances/main.py:537` (`build_parser`) | recomptée. |
| `--disable-unicode` | `glances/main.py:654` | ✅ porté | `glances/main_v5.py:250` (`add_argument("--disable-unicode", dest="disable_unicode", ...)`) ; `glances/main_v5.py:679` (`disable_unicode=getattr(args, "disable_unicode", False)`) ; `glances/outputs/glances_curses_v5.py:203`, `:252` | **Corrigé (parity wave 1, 2026-09-10)** : l'option est désormais déclarée dans `build_parser()` ; le mécanisme consommateur existait déjà et est inchangé. |
| `--sparkline` | `glances/main.py:647` | 🚫 retiré (décision) | — | `--sparkline` et la touche `S` retirées en 5.0 (`glances-v4-vs-v5.md`). |
| `--disable-separator` (`enable_separator`) | `glances/main.py:329` | ✅ porté | `glances/main.py:544` (`build_parser`) | recomptée. |
| `--disable-cursor` | `glances/main.py:336` | ✅ porté | `glances/main.py:723` (`build_parser`) | recomptée. |
| `--arrow-keys-sort` | `glances/main.py:343` | ✅ porté | `glances/main.py:715` (`build_parser`) | recomptée. |
| `--strftime` (`strftime_format`) | `glances/main.py:685` | ✅ porté | `glances/main.py:430` (`build_parser`) | recomptée. |
| `--disable-history` | `glances/main.py:298` | ✅ porté | `glances/main.py:685` (`build_parser`) | recomptée. |
| `--disable-check-update` | `glances/main.py:678` | 🚫 retiré (décision) | — | vérification PyPI retirée, plus aucune requête réseau au démarrage (`NEWS.rst`). |

### 5. Processus

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-f`, `--process-filter` | `glances/main.py:513` | ✅ porté | `glances/main.py:700` (`build_parser`) | recomptée. |
| `--process-focus` | `glances/main.py:522` | ✅ porté | `glances/main.py:707` (`build_parser`) | recomptée. |
| `--process-short-name` | `glances/main.py:529` | ✅ porté | `glances/main.py:444` (`build_parser`) | recomptée. |
| `--process-long-name` | `glances/main.py:536` | ✅ porté | `glances/main.py:451` (`build_parser`) | recomptée. |
| `--programs`, `--program` | `glances/main.py:357` | ✅ porté | `glances/main.py:641` (`build_parser`) | recomptée. |
| `--sort-processes` | `glances/main.py:350` | ✅ porté | `glances/main.py:635` (`build_parser`) | recomptée. |
| `--enable-process-extended` | `glances/main.py:322` | 🚫 retiré (décision) | — | retiré : sélectionner le processus puis `ENTER` (`NEWS.rst`). |
| `--hide-kernel-threads` (`no_kernel_threads`, non-Windows) | `glances/main.py:597` | ✅ porté | `glances/main.py:516` (`build_parser`) | recomptée. |

### 6. Plugins spécifiques (fs / diskio)

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `--fs-free-space` | `glances/main.py:640` | ✅ porté | `glances/main.py:678` (`build_parser`) | recomptée. |
| `--diskio-iops` | `glances/main.py:619` | ✅ porté | `glances/main.py:437` (`build_parser`) | recomptée. |
| `--diskio-latency` | `glances/main.py:626` | ✅ porté | `glances/main.py:671` (`build_parser`) | recomptée. |
| `--diskio-show-ramfs` | `glances/main.py:612` | ✅ porté | `glances/main.py:523` (`build_parser`) | recomptée. |

### 7. Export

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `--export` | `glances/main.py:366` | ✅ porté | `glances/main.py:327` (`build_parser`) | les 24 modules d'export de v4 existent (`glances/exports/`). |
| `--export-csv-file` | `glances/main.py:367` | ✅ porté | `glances/main_v5.py:145` (parser) ; `glances/exports/glances_csv/export_v5.py:60` | |
| `--export-csv-overwrite` | `glances/main.py:370` | ✅ porté | `glances/main_v5.py:152` (parser) ; `glances/exports/glances_csv/export_v5.py:68`, `:251` | |
| `--export-json-file` | `glances/main.py:377` | ✅ porté | `glances/main_v5.py:158` (parser) ; `glances/exports/glances_json/export_v5.py:46` | |
| `--export-graph-path` | `glances/main.py:380` | ✅ porté | `glances/main.py:353` (`build_parser`) | recomptée. |
| `--export-process-filter` | `glances/main.py:386` | ✅ porté | `glances/main_v5.py:165` (parser) ; `glances/main_v5.py:557-562` (overlay `[processlist] export`) ; `glances/plugins/processlist/model_v5.py:167`, `:169-186` | Parité v4 issue #794 explicitement respectée. Divergence mineure : v4 force `export_process_filter='.*'` en mode `--stdout` (`glances/main.py:773-774`) ; v5 n'a pas de mode stdout. |

### 8. Sécurité

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `--disable-config-exec` | `glances/main.py:668` | ✅ porté | `glances/main.py:730` (`build_parser`) | l'exécution de backticks dans la configuration est retirée (CVE-2026-33641), donc le volet « config » est sans objet. |

### 9. Divers / diagnostic

| Option | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `-V`, `--version` | `glances/main.py:190` | ✅ porté | `glances/main.py:745` (`build_parser`) | alias `-V` présent. |
| `-d`, `--debug` | `glances/main.py:191` | ✅ porté | `glances/main_v5.py:110` (parser) ; `glances/main_v5.py:736` (`setup_logging(args.debug)`) ; `glances/main_v5.py:290-299` | |
| `-t`, `--time` | `glances/main.py:454` | ✅ porté | `glances/main.py:422` (`build_parser`) | recomptée. |
| `--stdout` | `glances/main.py:543` | ✅ porté | `glances/main.py:551` (`build_parser`) | recomptée. |
| `--stdout-json` | `glances/main.py:549` | ✅ porté | `glances/main.py:558` (`build_parser`) | recomptée. |
| `--stdout-csv` | `glances/main.py:555` | ✅ porté | `glances/main.py:565` (`build_parser`) | recomptée. |
| `--issue` (`stdout_issue`) | `glances/main.py:561` | ✅ porté | `glances/main.py:595` (`build_parser`) | recomptée. |
| `--fetch`, `--stdout-fetch` | `glances/main.py:692` | ✅ porté | `glances/main.py:572` (`build_parser`) | recomptée. |
| `--fetch-template`, `--stdout-fetch-template` | `glances/main.py:700` | ✅ porté | `glances/main.py:580` (`build_parser`) | recomptée. |
| `--api-doc` | `glances/main.py:582` | 🚫 retiré (décision) | — | le sens v4 (afficher la doc de l'API Python) est retiré ; `--api-doc/--no-api-doc` active ou coupe Swagger et ReDoc (`NEWS.rst`). |
| `--api-restful-doc` | `glances/main.py:589` | ✅ porté | `glances/main.py:588` (`build_parser`) | recomptée. |
| `--trace-malloc` | `glances/main.py:568` | 🚫 retiré (décision) | — | retiré en 5.0 : `PYTHONTRACEMALLOC` à la main (`NEWS.rst`). |
| `--memory-leak` | `glances/main.py:575` | ✅ porté | `glances/main.py:602` (`build_parser`) | recomptée. |
| `--print-completion` (shtab, conditionnel) | `glances/main.py:188-189` | ✅ porté | `glances/main.py:209` (`build_parser`) | conditionnel à `shtab`, comme en v4. |
| `-h`, `--help` | implicite argparse — `glances/main.py:182` | ✅ porté | `glances/main_v5.py:79-82` (`argparse.ArgumentParser`, `add_help` par défaut) | Les familles/groupes du `--help` v4 ne sont pas reproduits : le parser v5 est plat (pas de `add_argument_group`). |
| `--theme-white` | *(aucune)* — documenté seulement `docs/cmds.rst:231` | 🚫 retiré (décision) | `glances/main_v5.py:78-261` | **Déjà absent de v4** : aucune occurrence dans `glances/`. C'est un bug de documentation v4 (`docs/cmds.rst:231`), pas un écart v4→v5. Signalé ici pour mémoire. |

---

### Récapitulatif

| Statut | Nombre |
|---|---|
| ✅ porté | 71 |
| ⚠️ partiel | 0 |
| ❌ absent | 0 |
| 🚫 retiré (décision) | 15 (dont `--theme-white`, en réalité déjà absent de v4) |
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

1. **`--bind` change de défaut** : `0.0.0.0` (v4) → `127.0.0.1` (v5). Impact sur *tous* les déploiements serveur non configurés, y compris les conteneurs (les images Docker écoutent sur `0.0.0.0` via leur conf livrée). Documenté dans `NEWS.rst`.
2. **`-s` change de sens** : XML-RPC (v4) → REST + WebUI (v5) ; `-w` reste un alias de `-s`.
3. **Les alias courts sont portés** (`-V -0..-6 -p -B -u -t -w -c -q -f`) : ce point du 2026-09-10 est soldé.

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
| `check_update` | `glances/outdated.py:66` | 🚫 retiré (décision) | — | vérification PyPI retirée (`NEWS.rst`). |
| `history_size` | `glances/plugins/plugin/model.py:736` ; `glances/main.py:877` | ✅ porté | `glances/main.py:61` | alimente le `HistoryStore` (`resolve_history_size`, `--disable-history`). |
| `strftime_format` | `glances/plugins/now/__init__.py:52` | ✅ porté | `glances/plugins/now/model_v5.py:41` | |
| `plugin_dir` | `glances/stats.py:200-201` | 🚫 retiré (décision) | — | plugins externes retirés (`NEWS.rst`). |
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
| `max_processes_display` | `glances/outputs/glances_restful_api.py:393` | ⚠️ partiel | `glances/config.py` (clés publiques) | lue côté WebUI et exposée par `/api/5/config` (`glances/config.py`) ; côté TUI non vérifié. |
| `disable_bg` | `glances/outputs/glances_curses.py:221` | ✅ porté | `glances/outputs/glances_curses.py:590` | recomptée. |
| `theme` | — (clé v5 uniquement) | ✅ porté | `glances/outputs/glances_curses_v5.py:226` | `dark` (défaut) / `light`. |
| `url_prefix` | `glances/outputs/glances_restful_api.py:396` | 🚫 retiré (décision) | `glances/webserver_v5.py:262-264` (« v5 has no `url_prefix` ») | |
| `webui_root_path` | `glances/outputs/glances_restful_api.py:277` | ❌ absent | `glances/webserver_v5.py:266-278` (chemins `_STATIC_PATH` / `index_v5.html` en dur) | |
| `cors_origins` | `glances/outputs/glances_restful_api.py:294`, `578` ; `glances/server.py:130` | ✅ porté | `glances/webserver_v5.py:317` | Défaut v5 = liste vide → middleware CORS non câblé (v4 : `*`). Changement de défaut assumé. |
| `cors_credentials` | `glances/outputs/glances_restful_api.py:295` | ⚠️ partiel | `glances/webserver_v5.py:318` | v5 lit `cors_allow_credentials` — **clé renommée**. `cors_credentials=True` d'une conf v4 est silencieusement ignorée. |
| `cors_methods` | `glances/outputs/glances_restful_api.py:315` | 🚫 retiré (décision) | `glances/webserver_v5.py:334` (`allow_methods=["GET","POST"]`) ; docs/architecture/glances-v5-architecture-decisions.md:733 | |
| `cors_headers` | `glances/outputs/glances_restful_api.py:316` | 🚫 retiré (décision) | même décision, docs…decisions.md:733 (`Authorization, Content-Type` en dur) | |
| `ssl_keyfile` / `ssl_certfile` / `ssl_keyfile_password` | `glances/outputs/glances_restful_api.py:401-403` | ✅ porté | `glances/main.py:1739-1751` (`server_ssl_options`) | recomptée. |
| `jwt_secret_key` | `glances/outputs/glances_restful_api.py:265` | ✅ porté | `glances/webserver_v5.py:351` | |
| `jwt_expire_minutes` | `glances/outputs/glances_restful_api.py:266` | ✅ porté | `glances/webserver_v5.py:352` | |
| `webui_allowed_hosts` | `glances/outputs/glances_restful_api.py:406` | ✅ porté | `glances/webserver_v5.py:297-307` | + WARNING au démarrage si bind non-loopback et clé absente. |
| `enable_mcp` | `glances/outputs/glances_restful_api.py:408` | ✅ porté | `glances/webserver_v5.py:200` ; overlay `--enable-mcp` `glances/main_v5.py:610` | |
| `mcp_path` | `glances/outputs/glances_restful_api.py:409` | ✅ porté | `glances/webserver.py:228` | recomptée. |
| `mcp_allowed_hosts` | `glances/outputs/glances_mcp.py:138` | ✅ porté | même module v4 réutilisé par v5 : `glances/webserver_v5.py:224` (`GlancesMcpServer(..., config=config)`) | Moteur partagé v4/v5. |
| `xmlrpc_allowed_hosts` | `glances/server.py:140` | 🚫 retiré (décision) | — | XML-RPC retiré. |
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
| `<field>_log` (`total_log`, `user_log`, `system_log`, `steal_log`) | `glances/plugins/plugin/model.py:1002` (`get_limit_log`), appelé `model.py:883` | ✅ porté | `glances/plugins/plugin/thresholds.py:150` ; `glances/alerts.py:594` | `read_log_flag` (`<pk>_<field>_log`, `<field>_log`, `log`). |
| `<field>_<level>_action[_repeat]` (ex. `user_critical_action`) | `glances/plugins/plugin/model.py:980` | ✅ porté | `glances/alerts_v5.py:783` | |
| `<field>_[<level>_]min_duration_seconds` | — (clé v5 uniquement) | ✅ porté | `glances/alerts_v5.py:594-595` | |

### 7. `[percpu]` (conf:229-246)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `max_cpu_display` | `glances/plugins/percpu/__init__.py:119` ; `glances/plugins/quicklook/__init__.py:108` | ✅ porté | `glances/plugins/percpu/model.py:162` | champ déclaré dans le modèle percpu. |
| Seuils `user_*`, `iowait_*`, `system_*` | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/percpu/model.py:63-106` | colonnes surveillées avec seuils 50/70/90 par défaut (`[percpu] <colonne>_careful/_warning/_critical`). |

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
| `available` | `glances/plugins/mem/__init__.py:131` | ✅ porté | `glances/plugins/mem/model_v5.py` (`_show_available`), `render_curses_v5.py`, `static/js/v5/PluginMem.vue` | **Porté le 2026-10-05** (GAP de la migration des tests) : comme en v4, `used` par défaut, `avail` si `available=True`, dans le TUI et la WebUI. |
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
| `log` | `glances/plugins/plugin/model.py:1002` | ✅ porté | `glances/plugins/plugin/thresholds.py:150` | `read_log_flag`, forme `log`. |

### 14. `[network]` (conf:329-364)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203`, `291-309` | Filtre sur `interface_name` (clé primaire). |
| `rx_<level>` / `tx_<level>` | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | champs v5 `bytes_recv` / `bytes_sent`, `glances/plugins/network/model_v5.py:47` (`_DEFAULT_BANDWIDTH_THRESHOLDS = {careful:0.7, warning:0.8, critical:0.9}`) | **Clés renommées ET unité changée** : v5 attend `bytes_recv_careful` / `bytes_sent_careful` exprimés en **ratio [0,1]** de la capacité, pas en pourcentage. `rx_careful=70` livré dans la conf est ignoré ; les défauts intégrés reproduisent 70/80/90 %. |
| `<iface>_rx_<level>` / `<iface>_tx_<level>` (ex. `wlan0_rx_careful`) | `glances/plugins/plugin/model.py:964` | ⚠️ partiel | `thresholds_v5.py:124-128` | Forme v5 : `wlan0_bytes_recv_careful` / `wlan0_bytes_sent_careful`. |
| `<iface>_rx_<level>_action` (ex. `wlan0_rx_critical_action`) | `glances/plugins/plugin/model.py:980` | ⚠️ partiel | `glances/alerts_v5.py:782` | Forme v5 : `wlan0_bytes_recv_critical_action`. |
| `<iface>_rx_log` / `<iface>_tx_log` | `glances/plugins/plugin/model.py:1002` | ⚠️ partiel | `glances/plugins/plugin/thresholds.py:150` | famille `_log` portée ; forme v5 `<iface>_bytes_recv_log`. |
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
| `rx_latency_<level>` / `tx_latency_<level>` (+ formes `<disk>_…`, `_log`) | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/diskio/model.py:96-122` | champs `read_latency`/`write_latency` avec `threshold_field` (clés v4 conservées). |
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

**Section retirée en 5.0** (#3486, PR #3530) : le support du démon hddtemp,
abandonné en amont, est supprimé ; les clés ci-dessous n'ont plus d'effet
(breaking change, voir `glances-v5-architecture-decisions.md`). Tableau
conservé pour l'historique.

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | 🚫 retiré (décision) | — | hddtemp retiré (#3486). |
| `host` | `glances/plugins/sensors/sensor/glances_hddtemp.py:30` | 🚫 retiré (décision) | — | hddtemp retiré (#3486). |
| `port` | `glances/plugins/sensors/sensor/glances_hddtemp.py:31` | 🚫 retiré (décision) | — | hddtemp retiré (#3486). |

### 26. `[sensors]` (conf:551-602)

`sensors` surcharge `_derived_parameters()` : les formes de clés lui sont propres
(`glances/plugins/sensors/model_v5.py:347-380`).

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `disable` | `glances/main.py:734` | ✅ porté | `glances/plugins/plugin/base_v5.py:166` | |
| `refresh` | `glances/plugins/plugin/model.py:773` | ✅ porté | `glances/scheduler_v5.py:157-159` | |
| `hide` / `show` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/plugin/base_v5.py:202-203` | Filtre sur `label`. |
| `mean` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/sensors/model_v5.py:255` | Bascule globale du repli « `<préfixe> (mean)` ». |
| `<type>_mean` (`temperature_core_mean`, `fan_speed_mean`, `battery_mean`) | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/sensors/model_v5.py:252-254` | Surcharge par type ; gagne sur `mean`. |
| `<type>_<level>` (`temperature_core_careful`, `battery_*`, `fan_speed_careful`) | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/sensors/model_v5.py:353-355`, `367-380` (tier 2) | |
| `<type>_<label>_<level>` (ex. `temperature_core_Ambient_careful`) | `glances/plugins/plugin/model.py:964` | ✅ porté | `glances/plugins/sensors/model_v5.py:350-352` (tier 1, issue #2058) | |
| `<type>_<label>_log` | `glances/plugins/plugin/model.py:1002` | ❌ absent | — | |
| `<type>_<label>_<level>_action` (ex. `temperature_core_Ambient_critical_action`) | `glances/plugins/plugin/model.py:980` | ❌ absent | `glances/alerts_v5.py:761-789` interroge `<label>_value_<level>_action`, `value_<level>_action`, `<level>_action` | Forme v4 non reconnue ; seule `<label>_value_<level>_action` (label = clé primaire) fonctionne. |
| `alias` | `glances/plugins/plugin/model.py:1075` | ✅ porté | `glances/plugins/sensors/model_v5.py:194-214` | Mécanisme propre à `sensors` (label / `label_type`), inchangé. Depuis parity wave 1 (2026-09-10) un `alias` générique existe aussi dans `base_v5` pour `network`/`diskio`/`fs` (§14, §18, §19) — `sensors` n'est plus le seul, mais garde le sien, plus riche. |
| ~~`host` / `port` (hddtemp)~~ | `glances/plugins/sensors/sensor/glances_hddtemp.py:30-31` | retiré | — | hddtemp retiré en 5.0 (#3486). |

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
| `disable_virtual_memory` | `glances/plugins/plugin/model.py:741-754` | ✅ porté | `glances/plugins/processlist/model.py:196` (lecture unique, publiée `:252`) ; `glances/plugins/processlist/render_curses.py:763-767` ; `glances/plugins/programlist/render_curses.py:136-138` ; `glances/outputs/static/js/processlist_columns.js:23-27` ; `glances/outputs/static/js/PluginProgramlist.vue:136-138` | Masque la colonne VIRT (TUI et WebUI, processlist et programlist, comme en v4) ; `memory_info.vms` reste collecté et exporté. |
| `export` | `glances/plugins/processlist/__init__.py:249-252` | ✅ porté | `glances/plugins/processlist/model_v5.py:167` ; `glances/plugins/programlist/model_v5.py:142` ; overlay CLI `glances/main_v5.py:562` | |
| `focus` | `glances/plugins/processlist/__init__.py:253-256` | ✅ porté | `glances/main.py:1352` | `[processlist] focus` lu à côté de `--process-focus`. |
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
| `columns` | `glances/servers_list.py:84-85` | ✅ porté | `glances/servers_list.py:266` | recomptée. |
| `server_<n>_name` / `_alias` / `_port` / `_protocol` | `glances/servers_list_static.py:40-42` | ✅ porté | `glances/servers_list.py:124-127` | `_protocol` ignoré avec un WARNING (v5 parle REST uniquement). |

### 35. `[passwords]` (conf:798-808)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `<host>=<password>` / `default` | `glances/password_list.py:38` (`dict(config.items("passwords"))`) | ✅ porté | `glances/main.py:1488` | entrée par hôte, sinon `default` ; jamais appliqué aux serveurs Zeroconf. |
| `local_password_path` | `glances/password.py:40` | 🚫 retiré (décision) | — | pas de fichier `.pwd` ; mot de passe serveur dans `[outputs] password` (hash PBKDF2). |

### 36. `[export]` (conf:814-822)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `exclude_fields` | `glances/exports/export.py:86-90` | ✅ porté | `glances/exports/export_base_v5.py:121`, `176-178` | |
| `refresh` | — (clé v5 uniquement ; aucun lecteur v4) | ✅ porté | `glances/exports/export_base_v5.py:82` ; `glances/scheduler_v5.py:193-198` | Livrée dans la conf mais **jamais lue par v4**. Valeur inférieure au refresh global : clampée. |

### 37. `[graph]` (conf:824-837)

| Clé | v4 lit où (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|
| `path`, `generate_every`, `width`, `height`, `style` | `glances/exports/glances_graph/__init__.py:33` | ✅ porté | `glances/exports/glances_graph/export.py` | exporteur graph livré. |

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
| `[cassandra]` | `host`, `port`, `keyspace` ; `protocol_version`, `replication_factor`, `table`, `username`, `password` | `glances/exports/glances_cassandra/__init__.py:55-58` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[opentsdb]` | `host`, `port` ; `prefix`, `tags` | `glances/exports/glances_opentsdb/__init__.py:35` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[statsd]` | `host`, `port` ; `prefix` | `glances/exports/glances_statsd/__init__.py:33` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[elasticsearch]` | `scheme`, `host`, `port`, `index` | `glances/exports/glances_elasticsearch/__init__.py:31-32` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[riemann]` | `host`, `port` | `glances/exports/glances_riemann/__init__.py:35` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[rabbitmq]` | `host`, `port`, `user`, `password`, `queue` ; `protocol` | `glances/exports/glances_rabbitmq/__init__.py:40-41` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[mqtt]` | `host`, `password` ; `port`, `devicename`, `user`, `topic`, `tls`, `topic_structure`, `callback_api_version` | `glances/exports/glances_mqtt/__init__.py:38-41` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[couchdb]` | `host`, `port`, `db`, `user`, `password` | `glances/exports/glances_couchdb/__init__.py:37` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[mongodb]` | `host`, `port`, `db` ; `user`, `password` | `glances/exports/glances_mongodb/__init__.py:35` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[kafka]` | `host`, `port`, `topic` ; `compression`, `tags` | `glances/exports/glances_kafka/__init__.py:35-36` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[zeromq]` | `host`, `port`, `prefix` | `glances/exports/glances_zeromq/__init__.py:34` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[restful]` | `host`, `port`, `protocol`, `path` | `glances/exports/glances_restful/__init__.py:31` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[graphite]` | `host`, `port` ; `prefix`, `system_name` | `glances/exports/glances_graphite/__init__.py:36` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[timescaledb]` | `host`, `port`, `db` ; `user`, `password`, `hostname` | `glances/exports/glances_timescaledb/__init__.py:51-52` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[nats]` | `host` ; `prefix` | `glances/exports/glances_nats/__init__.py:31-34` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[duckdb]` | `database` ; `user`, `password`, `hostname` | `glances/exports/glances_duckdb/__init__.py:60-61` | ✅ porté | — | exporteur livré (`glances/exports/`). |
| `[clickhouse]` | `host`, `port`, `db`, `user`, `password` ; `hostname` | `glances/exports/glances_clickhouse/__init__.py:86-87` | ✅ porté | — | exporteur livré (`glances/exports/`). |

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
| ✅ porté | 177 |
| ⚠️ partiel | 14 |
| ❌ absent | 10 |
| 🚫 retiré (décision) | 10 |
| ❓ indéterminé | 0 |
| **Total** | **211 lignes sur 40 sous-tables** |

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
- ~~`[mem] available` : v5 affiche `available` inconditionnellement quand psutil le
  fournit ; v4 affichait `used` par défaut.~~ Plus une divergence : la clé est
  portée le 2026-10-05 (`used` par défaut, comme v4).
- `[alert] min_duration` → `[alerts] min_duration_seconds` : sémantique
  différente (rejet a posteriori vs. debounce), avertissement déjà présent
  conf:31-33.
- ~~La section `[hddtemp]` est morte **dans les deux branches** : v4 comme v5
  lisent `host`/`port` dans `[sensors]` — bug de documentation à corriger dans
  `conf/glances.conf`.~~ — **caduc** : hddtemp est retiré de la v5 (#3486).


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
| `A` | Show/hide AMPs (Application Monitoring Process) | `glances_curses.py:54` (`switch: disable_amps`) | ✅ porté | `glances/outputs/glances_curses.py:249` | portée (table `_HOTKEYS`). |
| `d` | Show/hide Disk I/O | `glances_curses.py:59` | ✅ porté | `glances/outputs/glances_curses.py:251` | portée (table `_HOTKEYS`). |
| `D` | Show/hide Docker/containers | `glances_curses.py:60` | ✅ porté | `glances/outputs/glances_curses.py:252` | portée (table `_HOTKEYS`). |
| `e` | Show/hide top process extended stats | `glances_curses.py:274` (`catch_other_actions` dict) → `_handle_process_extended`, `glances_curses.py:345-351` | 🚫 retiré (décision) | — | `ENTER` épingle le processus pour les stats étendues (`NEWS.rst`). |
| `f` | Show/hide filesystem + folders | `glances_curses.py:63` (`handler: _handle_fs_stats`) → `glances_curses.py:356-358` | ✅ porté | `glances/outputs/glances_curses.py:253` | portée (table `_HOTKEYS`). |
| `G` | Show/hide GPU | `glances_curses.py:66` | ✅ porté | `glances/outputs/glances_curses.py:254` | portée (table `_HOTKEYS`). |
| `I` | Show/hide IP module | `glances_curses.py:69` | ✅ porté | `glances/outputs/glances_curses.py:255` | portée (table `_HOTKEYS`). |
| `K` | Show/hide TCP connections | `glances_curses.py:72` | ✅ porté | `glances/outputs/glances_curses.py:256` | portée (table `_HOTKEYS`). |
| `l` | Show/hide alert/log messages | `glances_curses.py:73` | ✅ porté | `glances/outputs/glances_curses.py:257` | portée (table `_HOTKEYS`). |
| `n` | Show/hide network stats | `glances_curses.py:77` | ✅ porté | `glances/outputs/glances_curses.py:258` | portée (table `_HOTKEYS`). |
| `N` | Show/hide current time | `glances_curses.py:78` | ✅ porté | `glances/outputs/glances_curses.py:259` | portée (table `_HOTKEYS`). |
| `P` | Show/hide ports stats | `glances_curses.py:81` | ✅ porté | `glances/outputs/glances_curses.py:260` | portée (table `_HOTKEYS`). |
| `Q` | Show/hide IRQ module | `glances_curses.py:83` (`switch: enable_irq`, inverted-polarity flag) | ✅ porté | `glances/outputs/glances_curses.py:265` | portée (table `_HOTKEYS`). |
| `R` | Show/hide RAID plugin | `glances_curses.py:85` | ✅ porté | `glances/outputs/glances_curses.py:270` | portée (table `_HOTKEYS`). |
| `s` | Show/hide sensors | `glances_curses.py:86` | ✅ porté | `glances/outputs/glances_curses.py:271` | portée (table `_HOTKEYS`). |
| `V` | Show/hide VMS plugin | `glances_curses.py:92` | ✅ porté | `glances/outputs/glances_curses.py:272` | portée (table `_HOTKEYS`). |
| `W` | Show/hide Wifi module | `glances_curses.py:94` | ✅ porté | `glances/outputs/glances_curses.py:273` | portée (table `_HOTKEYS`). |
| `z` | Show/hide processes | `glances_curses.py:96` (`handler: _handle_disable_process`) → `glances_curses.py:382-387` | ✅ porté | `glances/outputs/glances_curses.py:278` | portée (table `_HOTKEYS`). |
| `7` | Show/hide NPU | `glances_curses.py:50` | ✅ porté | `glances/outputs/glances_curses.py:283` | portée (table `_HOTKEYS`). |
| `8` | Show/hide MPP | `glances_curses.py:51` | ✅ porté | `glances/outputs/glances_curses.py:284` | portée (table `_HOTKEYS`). |
| `2` | Show/hide left sidebar | `glances_curses.py:45` | ✅ porté | `glances/outputs/glances_curses.py:287` | portée (table `_HOTKEYS`). |
| `3` | Show/hide Quick Look | `glances_curses.py:46` | ✅ porté | `glances/outputs/glances_curses.py:288` | portée (table `_HOTKEYS`). |
| `4` | Full quicklook (hide cpu/npu/mpp/gpu/mem/memswap, keep quicklook+load) | `glances_curses.py:47` (`handler: _handle_quicklook`) → `enable_fullquicklook`/`disable_fullquicklook`, `glances_curses.py:447-456` | ✅ porté | `glances_curses_v5.py:159` (`_HOTKEYS['4']`), dispatch `glances_curses_v5.py:310-315`; sibling-hiding set `curses_renderer_v5.py:89` (`_FULL_QUICKLOOK_HIDDEN = {"cpu","npu","mpp","gpu","mem","memswap"}`), applied `curses_renderer_v5.py:1430` | ~~Exact same 6-plugin hidden set as v4~~ — **no longer true since 2026-09-22**: v5's `4` hides EVERY TOP sibling (`load` and `percpu` included), so the row holds quicklook alone. Deliberate divergence, recorded in `…decisions.md` §10 ("Reversed decision — full quicklook"). The key stays ✅ porté; only the hidden set differs. |
| `5` | Show/hide top menu (QuickLook, CPU, MEM, SWAP, LOAD) | `glances_curses.py:48` (`handler: _handle_top_menu`) → `disable_top`/`enable_top`, `glances_curses.py:437-445` | ✅ porté | `glances/outputs/glances_curses.py:289` | portée (table `_HOTKEYS`). |

---

### TOGGLE DATA TYPE

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `b` | Network I/O: bit/s ↔ byte/s | `glances_curses.py:55` | ✅ porté | `glances/outputs/glances_curses.py:293` | portée (table `_HOTKEYS`). |
| `B` | Disk I/O: count ↔ IOPS | `glances_curses.py:56` (`handler: _handle_diskio_iops`) → `glances_curses.py:389-393` | ✅ porté | `glances/outputs/glances_curses.py:295` | portée (table `_HOTKEYS`). |
| `L` | Disk I/O: bytes/s ↔ latency | `glances_curses.py:74` (`handler: _handle_diskio_latency`) → `glances_curses.py:395-399` | ✅ porté | `glances/outputs/glances_curses.py:296` | portée (table `_HOTKEYS`). |
| `F` | Filesystem: used ↔ free space | `glances_curses.py:64` | ✅ porté | `glances/outputs/glances_curses.py:302` | portée (table `_HOTKEYS`). |
| `S` | Quicklook: bar ↔ sparkline | `glances_curses.py:87` (`switch: sparkline`) | 🚫 retiré (décision) | — | sparkline retiré en 5.0. |
| `T` | Network I/O: separate ↔ combined | `glances_curses.py:89` | ✅ porté | `glances/outputs/glances_curses.py:298` | portée (table `_HOTKEYS`). |
| `U` | Network I/O: live ↔ cumulative | `glances_curses.py:91` | ✅ porté | `glances/outputs/glances_curses.py:299` | portée (table `_HOTKEYS`). |
| `0` | Load: Linux-style ↔ percentage (Irix mode) | `glances_curses.py:43` | ✅ porté | `glances/outputs/glances_curses.py:297` | portée (table `_HOTKEYS`). |
| `1` | CPU: aggregate ↔ per-CPU | `glances_curses.py:44` (`switch: percpu`) | ✅ porté | `glances_curses_v5.py:158` (`_HOTKEYS['1']`); mutual exclusion `glances_curses_v5.py:562-564` (`hidden_top = "cpu" if show_percpu else "percpu"`) | |
| `6` | GPU: individual ↔ mean | `glances_curses.py:49` (`switch: meangpu`) | ✅ porté | `glances/outputs/glances_curses.py:294` | portée (table `_HOTKEYS`). |
| `/` | Process names: short ↔ full | `glances_curses.py:52` (`switch: process_short_name`) | ✅ porté | `glances_curses_v5.py:160` (`_HOTKEYS['/']`); consumed `glances/plugins/processlist/render_curses_v5.py:391` | Consumed only by the `processlist` renderer, same scope as v4 (`glances/plugins/processlist/__init__.py:558` — `programlist` doesn't reference it in either version). |

---

### MISCELLANEOUS

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `ENTER` | Edit process filter pattern | `glances_curses.py:42` (`handler: _handle_enter`) → `glances_curses.py:328-329`; popup at `glances_curses.py:610-625` | ✅ porté | `glances/outputs/glances_curses.py:375` | `ENTER` épingle le processus (stats étendues) ; le filtre est sur `F4`. |
| `E` | Erase process filter | `glances_curses.py:62` (`handler: _handle_erase_filter`) → `glances_curses.py:353-354` | ✅ porté | `glances/outputs/glances_curses.py:307` | portée (table `_HOTKEYS`). |
| `g` | Generate history graphs (export) | `glances_curses.py:65` (`switch: generate_graph`) | ✅ porté | `glances/outputs/glances_curses.py:317` | portée (table `_HOTKEYS`). |
| `h` | Show/hide help screen | `glances_curses.py:67` (`switch: help_tag`) | ✅ porté | `glances_curses_v5.py:163` (`_HOTKEYS['h']`), dispatch `glances_curses_v5.py:306-309`; closes via `q`/ESC/`h`, `glances_curses_v5.py:343-345` | v5's overlay content is generated from the `_HOTKEYS` table itself (`glances_curses_v5.py:144-146,1196`), so it only ever lists v5's own (much smaller) key set — by construction it cannot drift from what v5 actually handles, but it also cannot show v4's full list. |
| `j` | Threads ↔ programs (process list aggregation) | `glances_curses.py:70` (`switch: programs`) | ✅ porté | `glances_curses_v5.py:161` (`_HOTKEYS['j']`); mutual exclusion `glances_curses_v5.py:565-568` (`hidden_right = "processlist" if programs else "programlist"`) | While the help overlay is open, `j`/`k` are repurposed for scroll-down/scroll-up (`glances_curses_v5.py:346,349`) instead of their normal action — by design (`_handle_help_key` intercepts all keys first, `glances_curses_v5.py:290-291`), not a bug. |
| `+` | Increase nice level of selected process | `glances_curses.py:97` (`handler: _handle_increase_nice`) → `glances_curses.py:360-361` | ✅ porté | `glances/outputs/glances_curses.py:328` | portée (table `_HOTKEYS`). |
| `-` | Decrease nice level of selected process | `glances_curses.py:98` (`handler: _handle_decrease_nice`) → `glances_curses.py:363-364` | ✅ porté | `glances/outputs/glances_curses.py:334` | portée (table `_HOTKEYS`). |
| `k` | Kill selected process | `glances_curses.py:275` (`catch_other_actions` dict) → `_handle_kill_process`, `glances_curses.py:366-367`; confirm popup `glances_curses.py:641-644` | ✅ porté | `glances/outputs/glances_curses.py:322` | portée (table `_HOTKEYS`). |
| `M` | Reset processes summary min/max | `glances_curses.py:76` (`switch: reset_minmax_tag`) | ✅ porté | `glances/outputs/glances_curses.py:312` | portée (table `_HOTKEYS`). |
| `q` | Quit | `glances_curses.py:287` (`catch_other_actions` dict, `ord('q')`) → `_handle_quit`, `glances_curses.py:417-425` | ✅ porté | `glances_curses_v5.py:164` (`_HOTKEYS['q']`), dispatch `glances_curses_v5.py:303-305` | |
| `r` | **Real v4 behaviour: show/hide SMART stats** (`switch: disable_smart`) | `glances_curses.py:84` | ✅ porté | `glances/outputs/glances_curses.py:269` | portée (table `_HOTKEYS`). |
| `w` | Delete finished warning log messages | `glances_curses.py:93` (`handler: _handle_clean_logs`) → `glances_curses.py:376-377` | ❌ absent | `glances_curses_v5.py:147-165` | |
| `x` | Delete finished warning+critical log messages | `glances_curses.py:95` (`handler: _handle_clean_critical_logs`) → `glances_curses.py:379-380` | ❌ absent | `glances_curses_v5.py:147-165` | |

---

### NAVIGATION (documented in `docs.rst`'s Interactive Commands list, not in the in-app help screen)

| Touche | Action v4 | v4 (file:line) | Statut v5 | Preuve v5 (file:line) | Note |
|---|---|---|---|---|---|
| `ESC` | Quit (also closes nothing else in v4 — no modal-close semantics) | `glances_curses.py:287` (`ord('\x1b')`) → `_handle_quit` | ✅ porté | `glances_curses_v5.py:293-294` (`if key == 27: return "quit"`) | In v5, ESC is context-sensitive: it quits normally, but closes the help overlay instead of quitting while the overlay is open (`glances_curses_v5.py:343-345`) — a v5-only modal-close behavior v4 doesn't have (v4's help screen is a `switch`, closed by pressing `h` again, not ESC). Not a regression since ESC-to-close is additive, but it is a behavioural difference worth naming: ⚠️ partiel would also be defensible here; recording as ✅ porté for the "ESC quits" core contract with this caveat noted. |
| `UP` (or ANSI code `65`) | Move process-list cursor up | `glances_curses.py:284` (`catch_other_actions` dict) → `_handle_cursor_up`, `glances_curses.py:409-411` | ✅ porté | `glances/outputs/glances_curses.py:390` | portée. |
| `DOWN` (or ANSI code `66`) | Move process-list cursor down | `glances_curses.py:285` → `_handle_cursor_down`, `glances_curses.py:413-415` | ✅ porté | `glances/outputs/glances_curses.py:397` | portée. |
| `LEFT` / `SHIFT-LEFT` | Scroll process name left / navigate sort left (swapped by `arrow_keys_sort` config) | `glances_curses.py:276-277,280-281` → `_handle_sort_left` (`glances_curses.py:401-403`) / `_handle_process_name_left` (`glances_curses.py:369-371`) | ✅ porté | `glances/outputs/glances_curses.py:446` | portée (`_arrow_bindings`, `--arrow-keys-sort`). |
| `RIGHT` / `SHIFT-RIGHT` | Scroll process name right / navigate sort right (swapped by `arrow_keys_sort` config) | `glances_curses.py:278-279,282-283` → `_handle_sort_right` (`glances_curses.py:405-407`) / `_handle_process_name_right` (`glances_curses.py:373-374`) | ✅ porté | `glances/outputs/glances_curses.py:446` | portée (`_arrow_bindings`). |
| `F5` / `Ctrl-R` (ASCII `18`) | Force-refresh (reset internal process cache) | `glances_curses.py:286` (`{curses.KEY_F5, 18}`) → `_handle_refresh`, `glances_curses.py:427-428` | ✅ porté | `glances/outputs/glances_curses.py:404` | portée. |

`Ctrl-C` is documented in `docs/cmds.rst:347` (`q|ESC|CTRL-C`) as a quit key, but it is not part of v4's curses
key-handling code at all — `_handle_quit`'s trigger set is only `{ord('\x1b'), ord('q')}` (`glances_curses.py:287`);
Ctrl-C works because it is the OS-level SIGINT → `KeyboardInterrupt`, unrelated to `__catch_key`. Excluded as a
row (not a curses hotkey in either version); ❓ indéterminé whether v5's thread/signal handling reproduces the
same SIGINT behaviour — I did not trace `main_v5.py`'s signal wiring, which is out of this section's scope
(curses key handling only).

---

### Summary

Recompte du 2026-11-15 sur les 62 lignes : ✅ porté = 58 · ⚠️ partiel = 0 · ❌ absent = 2
(`w`, `x` : effacer les alertes terminées) · 🚫 retiré (décision) = 2 (`e`, remplacée par `ENTER` ;
`S`, sparkline retiré). Le TUI v5 a une table de touches pilotée par les données
(`_HOTKEYS` et `_SPECIAL_HOTKEYS`, `glances/outputs/glances_curses.py`), d'où est aussi générée l'aide `h`.

Changements de sens par rapport à v4, tous dans `NEWS.rst` : `ENTER` épingle le processus
(stats étendues) et le filtre passe sur `F4` ; `ESC` ferme d'abord les surcouches.

**Constat v4 inchangé (pas un écart v5)** : la touche `r` affiche « Reset history » dans l'aide v4
alors que son code bascule `disable_smart` ; v5 suit le code.

---

## Suites proposées (2026-11-15)

La plupart des suites du 2026-09-10 sont faites (TUI interactif, options CLI, alias, famille `_log`,
exporteurs, browser). Reste, par ordre de valeur :

1. **Décider du sort des 11 `❌`** : porter ou retirer par décision écrite (`w`/`x`, `[alert] disable` et
   `min_interval`, `[processlist] sort_key`/`disable_stats`, actions par dossier et par
   capteur, `left_menu`, `webui_root_path`).
2. **Relire les 14 `⚠️`**, surtout `max_processes_display` côté TUI.
3. **Rouvrir une fois les `✅` de 2026-09-10** (non recomptés ici) pour mettre à jour leurs `file:line`
   après la suppression du suffixe `_v5`.
4. **Notes de version** : les changements de défaut sont dans `NEWS.rst` ; à relire avant le RC.
