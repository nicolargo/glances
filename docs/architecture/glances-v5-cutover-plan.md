# Glances v5 — plan de bascule de `develop-v5` vers `develop`

**Date :** 2026-10-05 · **Branche :** `develop-v5` · **Origine :** audit de
sécurité, constat B1 (`glances-v5-security-audit.md`) ; checklist de fusion §2.

## Pourquoi un plan, et pas une correction tout de suite

Le code v5 passe encore par le code v4. Le corriger demande de vider ou de
déplacer des fichiers que `develop` modifie chaque semaine : sur les 90
jours précédant le 2026-10-05, 39 commits de `develop` touchent un
`glances/plugins/*/__init__.py`, 11 un `glances/exports/*/__init__.py`,
8 les modules empruntés (`ports`, `sensors`, `smart`, `config.py`) et 3
`glances/__init__.py`. Faite sur `develop-v5` avant la bascule, la
correction transformerait la fusion hebdomadaire `develop → develop-v5` en
conflits « modifié / supprimé » à reporter à la main, et casserait la v4 qui
tourne encore sur cette branche.

B1 est donc coupé en deux :

1. **Avant la bascule (fait le 2026-10-05)** : aucun fichier v4 n'est touché.
   `tests/test_v4_boundary_v5.py` fige ce que la v5 importe hors d'elle-même
   (`SHARED`, partagé et conservé ; `BORROWED`, emprunté et à déplacer) : la
   liste ne peut plus que diminuer.
2. **Le jour de la bascule** : les étapes ci-dessous, appliquées dans l'ordre,
   après le dernier merge `develop → develop-v5`.

## État au 2026-10-05

### Ce que la v5 importe directement hors d'elle-même

| Module | Statut | Pourquoi |
|---|---|---|
| `glances.globals`, `glances.logger`, `glances.processes`, `glances.filter`, `glances.timer`, `glances.secure` | partagé | moteur commun |
| `glances.folder_list`, `glances.ports_list`, `glances.web_list` | partagé | listes de `folders` et `ports` |
| `glances.amps.amp` (et `glances.amps.<nom>`) | partagé | AMP (G6C) |
| `glances.outputs.glances_bars`, `glances_unicode`, `glances_mcp` | partagé | TUI, MCP |
| `glances.plugins.*.engines.*`, `*.cards.*`, `sensors.sensor.*` | partagé | pilotes |
| `glances.plugins`, `glances.exports`, `glances.outputs` | partagé | paquets vides |
| `glances` (racine) | **emprunté** | `psutil_version_info` (`psutilversion/model_v5.py`) ; son `__init__.py` importe `glances.main`, la CLI v4 |
| `glances.plugins.ports` | **emprunté** | `ThreadScanner` (`ports/model_v5.py`) |
| `glances.plugins.sensors` | **emprunté** | `GlancesGrabSensors`, `sensors_definition` (`sensors/model_v5.py`) |
| `glances.plugins.smart` | **emprunté** | `get_smart_data`, `import_error_tag`, `LARGE_VALUE_KEYS` (`smart/model_v5.py`, `smart/render_curses_v5.py`) ; le module importe `glances.main` (`disable`) |

### Ce que les modules partagés tirent encore de la v4

| Module partagé | Dépendance v4 |
|---|---|
| `glances.web_list`, `plugins/containers/engines/{docker,lxd,podman}.py` | `glances.config.secure_option` |
| `plugins/sensors/sensor/glances_{batpercent,hddtemp}.py` | héritent de `glances.plugins.plugin.model.GlancesPluginModel` |

### L'effet « paquet parent »

Importer `glances.plugins.<x>.model_v5` exécute d'abord
`glances/plugins/<x>/__init__.py`, le plugin v4, pour les 34 plugins portés
(et `glances/exports/glances_<x>/__init__.py`, l'exporteur v4, pour les
24 exporteurs). Toute la pile v4 est chargée à chaque démarrage, et
`plugins/load/__init__.py` exécute un `CorePlugin()` v4 à l'import.

## État final visé

- L'actuelle `develop` devient `support/glancesv4` (correctifs v4 seulement).
- `develop-v5` est fusionnée dans `develop`, puis supprimée.
- `develop` ne contient plus de code mort de Glances v4.
- Plus aucun nom de fichier, de module ou de classe ne porte `_v5` / `V5`.
- Documentation, README, Makefile, packaging et CI décrivent la v5.

Constats de l'inventaire du 2026-10-10 qui conditionnent le plan :
`develop-v5` a 120 commits d'avance sur `develop` et 0 de retard (fusion
sans conflit) ; 270 fichiers suivis portent `_v5` (dont 140 tests) ; 49 de
leurs noms sans suffixe sont déjà pris par un fichier v4 (`config.py`,
`main.py`, `webserver.py`, `glances_curses.py`, `index.html`, 36 tests…), d'où
« supprimer la v4 avant de renommer » ; 372 occurrences de `_v5` et 178 noms de
classes `…V5` dans le code ; `weekly_merge_develop_to_v5.yml` est présent sur
`develop`, la branche par défaut, d'où les planifications partent ; l'image
Docker lance `-m glances` avec `GLANCES_OPT=-w` (accepté par la v5) mais la v5
écoute par défaut sur `127.0.0.1`.

## Décisions (mainteneur, 2026-10-10)

| # | Décision |
|---|---|
| D1 | `glances-v5` est retiré : `glances` lance la v5. |
| D2 | Version `5.0.0b1`, `__apiversion__ = "5"` ; l'API reste en `/api/5`. |
| D3 | Les noms de classes `…V5` (`GlancesConfigV5`, `StatsStoreV5`, `TuiV5`…) perdent leur suffixe, dans le même commit que les fichiers. |
| D4 | WebUI : `glances5.js` → `glances.js`, `browser5.js` → `browser.js`, `css/v5.css` → `css/glances.css`, `js/v5/` remonte dans `js/`. |
| D5 | `docs/architecture` et `docs/superpowers` restent comme historique daté ; seuls les documents vivants sont mis à jour. |
| D6 | Le nettoyage se fait sur une branche `cutover/v5` issue de `develop-v5`, puis une PR vers `develop` fusionnée avec un commit de fusion (pas de squash). |
| D7 | Docker : le conteneur écoute sur `0.0.0.0` ; une bêta ne publie pas `latest`. |
| D8 | Windows, macOS et FreeBSD lancent la suite v5 hors tests propres à Linux (TUI curses, `/proc`). |

## 1. Gel et dernière synchronisation

1. Annoncer le gel : plus de fusion sur `develop` sauf correctif bloquant.
2. Dernier merge `develop → develop-v5` (workflow lancé à la main, ou
   `git merge origin/develop`) ; CI verte sur `develop-v5`.
3. Désactiver `weekly_merge_develop_to_v5` dans l'interface GitHub
   (Actions → Disable workflow) : planifié, il tourne depuis `develop`.
4. Recenser les PR ouvertes vers `develop` : celles qui portent sur la v4
   seront redirigées vers `support/glancesv4` (étape 2).

## 2. Créer `support/glancesv4`

```console
$ git fetch origin
$ git push origin origin/develop:refs/heads/support/glancesv4
```

Un commit d'adaptation sur `support/glancesv4` :

- `ci.yml` : déclencheurs sur `support/glancesv4` (au lieu de `develop` /
  `develop-v5`) ; suppression de `weekly_merge_develop_to_v5.yml` ;
- `build_docker.yml` : plus d'image `dev` depuis cette branche, seulement
  les tags `v4.*` ;
- snap : `source-branch` si le snap v4 continue d'être construit ;
- README et CONTRIBUTING : branche de correctifs v4 uniquement.

Côté GitHub : recopier les protections de `develop` ; rediriger les PR v4 ;
créer une version « v4 » sur ReadTheDocs liée à cette branche.

## 3. Branche `cutover/v5`, un commit vérifié par étape

```console
$ git switch -c cutover/v5 origin/develop-v5
```

Chaque étape se termine par la suite de tests, `make pre-commit` et un commit.

### C1. Sortir les emprunts au code v4 (B1)

| Quoi | Vers | Puis |
|---|---|---|
| `ThreadScanner` (`plugins/ports/__init__.py:249`) | `glances/plugins/ports/scanner.py` | `ports/model_v5.py` l'importe de là |
| `GlancesGrabSensors`, `sensors_definition` (`plugins/sensors/__init__.py:26, 325`) | `glances/plugins/sensors/grab.py` | `sensors/model_v5.py` idem |
| `get_smart_data`, `import_error_tag`, `LARGE_VALUE_KEYS` et les `convert_*` / `_process_*` dont ils dépendent (`plugins/smart/__init__.py:37-186`) | `glances/plugins/smart/data.py` | `smart/model_v5.py`, `smart/render_curses_v5.py` ; la dépendance à `glances.main.disable` disparaît |
| `secure_option` et ses deux regex (`glances/config.py:27-52`) | `glances/secure.py` | `web_list.py` et les trois moteurs de conteneurs l'importent de là |
| `BatpercentPlugin`, `HddtempPlugin` héritent de `GlancesPluginModel` | classes autonomes (seuls `update()` et les stats servent à `GlancesGrabSensors`) | — |

Vérification : `BORROWED` de `tests/test_v4_boundary_v5.py` est vide, hors
la racine `glances` (étape C2).

### C2. Une seule version, une seule entrée (D1, D2)

- `glances/__init__.py` : plus d'import de `glances.main` ;
  `__version__ = "5.0.0b1"`, `__apiversion__ = "5"`, `psutil_version_info`
  et le contrôle de version de psutil restent ; `main()` appelle la v5.
- `glances/version_v5.py` supprimé, ses imports redirigés ; vérifier
  `glances/__main__.py`.
- `pyproject.toml` : seulement `glances = "glances:main"`.

Vérification : `python -m glances -V`, `glances -s`, `glances --stdout cpu`.

### C3. Supprimer le code v4

- `glances/` : `actions.py`, `amps_list.py`, `api.py`, `attribute.py`,
  `client.py`, `client_browser.py`, `config.py`, `cpu_percent.py`,
  `event.py`, `events_list.py`, `gpu_percent.py`, `history.py`,
  `jwt_utils.py`, `main.py`, `outdated.py`, `password.py`,
  `password_list.py`, `server.py`, `servers_list.py`,
  `servers_list_dynamic.py`, `servers_list_static.py`, `snmp.py`,
  `standalone.py`, `stats.py`, `stats_client.py`, `stats_client_snmp.py`,
  `stats_server.py`, `thresholds.py`, `webserver.py` (`stats_streamer.py`
  reste : les moteurs de conteneurs l'utilisent).
- `glances/outputs/` : `glances_curses.py`, `glances_curses_browser.py`,
  `glances_restful_api.py`, `glances_stdout*.py`,
  `glances_json_serializer.py`, `glances_sparklines.py`, et
  `glances_colors.py` si aucun module v5 ne l'atteint.
- Plugins : les 34 `plugins/<x>/__init__.py` vidés (en-tête de licence
  seul) ; `plugins/alert/`, `plugins/help/`, `plugins/plugin/model.py` et
  `dag.py` supprimés. Les sous-modules partagés (`engines/`, `cards/`,
  `sensor/`, `fs/zfs.py`, et ceux de C1) restent.
- Exporteurs : les 24 `exports/glances_<x>/__init__.py` vidés ;
  `exports/export.py` et `export_asyncio.py` supprimés.
- WebUI v4 : composants hors `js/v5/`, `js/app.js`, `js/browser.js`,
  `js/uiconfig.json`, `public/glances.js` et `public/browser.js`,
  `templates/index.html` et `browser.html`, le bloc `v4Config` de
  `webpack.config.js`, `generate_webui_conf.py` s'il ne sert qu'à la v4, et
  les dépendances npm devenues inutiles.
- Tests : tests v4 COVERED et OBSOLETE de `glances-v5-v4-tests-migration.md`
  et scripts `tests/test_export_*.sh` v4 supprimés ; tests SHARED qui
  importent du v4 déplacés (`TestSecurePopen*` vers
  `tests/test_secure_popen.py`, par exemple).

La suppression de `config.py` emporte la substitution backtick
(CVE-2026-33641), celle d'`outdated.py` le cache pickle (CVE-2026-46607).

Vérification : suite complète ; `git grep` des modules supprimés vide.

### C4. Retirer `_v5` (D3, D4)

Renommages par `git mv` (l'historique reste lisible avec `git log --follow`) :

| Avant | Après |
|---|---|
| `glances/xxx_v5.py`, `glances/outputs/xxx_v5.py` | `xxx.py` |
| `plugins/<x>/model_v5.py`, `render_curses_v5.py` | `model.py`, `render_curses.py` |
| `plugins/plugin/base_v5.py`, `thresholds_v5.py` | `base.py`, `thresholds.py` |
| `exports/glances_<x>/export_v5.py`, `exports/export_base_v5.py` | `export.py`, `export_base.py` |
| `glances/actions_v5/` | `glances/actions/` |
| `tests/test_*_v5.py`, `tests/test_export_*_v5.sh` | `tests/test_*.py`, `tests/test_export_*.sh` |
| `static/js/v5/*`, `js/app_v5.js`, `js/browser_v5.js` | `static/js/*`, `js/app.js`, `js/browser.js` |
| `static/templates/index_v5.html`, `browser_v5.html` | `index.html`, `browser.html` |
| `static/css/v5.css`, `public/glances5.js`, `public/browser5.js` | `css/glances.css`, `public/glances.js`, `public/browser.js` |

Puis :

- les chaînes de découverte (`model_v5`, `render_curses_v5`, `export_v5`,
  `actions_v5` dans la découverte des plugins, exporteurs, rendus et actions) ;
- les imports, les chemins statiques et templates du serveur web, les
  entrées webpack ; les classes `…V5` (D3) ;
- `make webui` pour reconstruire le bundle ;
- `tests/test_v4_boundary_v5.py` remplacé par un test « aucun import d'un
  module supprimé ».

Vérification : `git ls-files | grep -i v5` et
`git grep -n "_v5\|V5\b" -- glances tests` sont vides.

### C5. Makefile

- `run-v5*` → `run*` (remplacent les cibles v4), `test-v5` → `test`,
  `test-exports-v5` → `test-exports`, `set-password-v5` → `set-password`,
  `webui-v5` fusionnée dans `webui` (un seul bundle) ;
- `bench-v4-v5` ne reste que sur `support/glancesv4` ;
- la cible `docs` appelle les générateurs renommés ; vérifier `run.py` et
  `run-venv.py` ;
- `make requirements` pour régénérer les fichiers épinglés.

### C6. CI (D8)

- `ci.yml` : déclencheurs sur `develop` seulement ;
- `test.yml` : un job Linux qui lance toute la suite (`python -m pytest
  tests/`) et les tests JS ; jobs Windows, macOS et FreeBSD sur la suite
  v5 hors tests propres à Linux ;
- `weekly_merge_develop_to_v5.yml` supprimé ;
- `webui.yml` : nouveaux chemins et noms de bundles ; `build.yml`,
  `build_docker.yml` (l'image `dev` depuis `develop` devient la v5),
  `quality.yml`, `cyber.yml` : chemins ;
- nouveau : publication PyPI des pré-versions sur les tags `v5.*` (le point
  « deferred » de `.claude/skills/SKILL-ci-cd.md`) ;
- optionnel : les scripts `test_export_*.sh` sous Docker, en manuel ou par
  semaine.

### C7. Packaging (D7)

- Dockerfiles et `docker-compose/` : écoute sur `0.0.0.0`
  (`bind_address` dans `docker-compose/glances.conf`, ou `-B 0.0.0.0`) ;
  `docker-compose.yml` garde `-w --enable-mcp --enable-plugin smart`, mais le
  commentaire « `--password` » renvoie à `[outputs] password` et
  `--set-password` ;
- `MANIFEST.in` et `package-data` : nouveaux noms des fichiers statiques ;
- snap : commande, plugs, branche source.

Vérification : wheel installée dans un venv vierge (`glances -V`, `-s`,
`--stdout`) ; images `alpine` et `ubuntu` construites et lancées.

### C8. Documentation (D5)

- `NEWS.rst` : section 5.0.0 avec toutes les ruptures de la checklist §4 ;
- `README.rst`, `README-pypi.rst` ;
- `docs/` : `quickstart.rst`, `install.rst`, `cmds.rst` (options retirées,
  ajoutées, renommées), `config.rst` (mot de passe, rate limiting,
  `webui_allowed_hosts`, TLS, `/config` public), `docker.rst` (écoute, mot de
  passe), `fetch.rst` (anciens templates cassés), `aoa/*`, `gw/*` ;
- générés par `make docs` sur une machine représentative :
  `docs/api/restful.rst`, `python.rst`, `openapi.json`, et la page de
  manuel `docs/man/glances.1` ;
- `conf/glances.conf`, `docker-compose/glances.conf` : plus de clé que seule
  la v4 lit ;
- `CONTRIBUTING.md` (où envoyer une PR v4 ou v5), `CLAUDE.md`,
  `.claude/skills/*` (modèle de branches de `SKILL-ci-cd.md`, chemins),
  `.claude/docs/*` ;
- `docs/architecture` : la checklist et ce plan passent en « fait » ; le
  reste demeure en archive.

### C9. Contrôle final de la branche

Suite complète et tests JS, `make pre-commit`, `make docs` (Sphinx sans
avertissement), `make webui`, wheel installée proprement, images Docker, et le
benchmark contre `support/glancesv4` comme garde-fou.

## 4. La fusion

1. PR `cutover/v5` → `develop` ; CI verte, relecture ; fusion par commit de
   fusion (D6).
2. Suppression de `develop-v5` (après redirection de ses PR restantes vers
   `develop`) et de `cutover/v5` :
   ```console
   $ git push origin --delete develop-v5 cutover/v5
   ```
3. Vérifier que `develop` n'a plus de workflow planifié de fusion et que sa
   CI est verte.

## 5. Après la fusion

1. Tag `v5.0.0b1` sur `develop` : PyPI (pré-version), Docker (tag
   `5.0.0b1`, pas `latest`), Snap (canal beta), note de version GitHub.
2. ReadTheDocs : `latest` sur la v5, une version « v4 » sur
   `support/glancesv4`.
3. Reporter sur `support/glancesv4` les correctifs de l'audit qui concernent
   la v4 (liste dans `glances-v5-security-audit.md`), et le défaut v4 qui
   saute des rafraîchissements (`glances-v5-performance.md`).
4. Labels `v4` / `v5` sur les issues ; la version demandée dans le modèle
   d'issue.
5. Avant `5.0.0` : constats de sécurité restants (M5, M6, M9, M11, bas) et
   mesure de performance sur une machine représentative.
