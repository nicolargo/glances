# Glances v5 — plan de bascule (B1 : sortir la v5 du code v4)

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

## Le jour de la bascule

**Préalables** (checklist §6) : CI verte sur `develop-v5` ; `support/glancesv4`
créée depuis `develop` ; dernier merge `develop → develop-v5` fait ;
`weekly_merge_develop_to_v5.yml` désactivé. Plus aucun merge ne viendra de
`develop`.

Chaque étape est un commit, vérifié avant de passer à la suivante.

### 1. Sortir les emprunts des modules v4

| Quoi | Vers | Puis |
|---|---|---|
| `ThreadScanner` (`plugins/ports/__init__.py:249`) | `glances/plugins/ports/scanner.py` | `ports/model_v5.py` l'importe de là |
| `GlancesGrabSensors`, `sensors_definition` (`plugins/sensors/__init__.py:26, 325`) | `glances/plugins/sensors/grab.py` | `sensors/model_v5.py` idem |
| `get_smart_data`, `import_error_tag`, `LARGE_VALUE_KEYS` et les `convert_*` / `_process_*` dont ils dépendent (`plugins/smart/__init__.py:37-186`) | `glances/plugins/smart/data.py` | `smart/model_v5.py`, `smart/render_curses_v5.py` ; la dépendance à `glances.main.disable` disparaît (la v5 a son propre `disable`) |
| `secure_option` et ses deux regex (`glances/config.py:27-52`) | `glances/secure.py` | `web_list.py` et les trois moteurs de conteneurs l'importent de là |
| `BatpercentPlugin`, `HddtempPlugin` héritent de `GlancesPluginModel` | classes autonomes (seuls `update()` et les stats sont utilisés par `GlancesGrabSensors`) | — |

Vérification : la suite v5 passe ; dans `tests/test_v4_boundary_v5.py`,
`glances.plugins.ports`, `sensors` et `smart` sortent de `BORROWED`.

### 2. Vider les plugins et exporteurs v4

- Les 34 `glances/plugins/<x>/__init__.py` des plugins portés deviennent des
  fichiers vides (en-tête de licence seul). Les sous-modules partagés
  (`engines/`, `cards/`, `sensor/`, `fs/zfs.py`, les nouveaux `scanner.py`,
  `grab.py`, `data.py`) restent.
- Supprimés : `plugins/alert/`, `plugins/help/` (sans portage v5) et le
  modèle v4 de `plugins/plugin/` (`model.py`, et `dag.py` que seul
  `glances_restful_api.py` utilise) ; `plugins/plugin/base_v5.py` reste.
- Les 24 `glances/exports/glances_<x>/__init__.py` deviennent vides ;
  `glances/exports/export.py` et `export_asyncio.py` sont supprimés.

Vérification : importer chaque module `*_v5` ne charge plus aucun
`glances.plugins.plugin.model`, `glances.exports.export` ni
`glances.thresholds` (`sys.modules`) ; la suite v5 passe.

### 3. Une seule version, une seule entrée

- `glances/__init__.py` : plus d'import de `glances.main` ;
  `__version__ = "5.0.0b1"`, `__apiversion__ = "5"`, `psutil_version_info`
  et le contrôle de version de psutil restent ; `main()` appelle
  `glances.main_v5.main`. `glances/version_v5.py` est supprimé et ses
  imports redirigés (checklist §3).
- `pyproject.toml` : `glances = "glances:main"` lance la v5 ; décider du
  sort de `glances-v5` (alias ou retrait) — décision de la checklist §2.

Vérification : `glances -V`, `glances -s`, `glances --stdout cpu`,
`python -m glances` ; `tests/test_version_v5.py`.

### 4. Supprimer le code v4

Candidats, à confirmer un par un par la suite de tests (un module supprimé à
tort casse un import, donc un test) :

- `glances/` : `actions.py`, `amps_list.py`, `api.py`, `attribute.py`,
  `client.py`, `client_browser.py`, `config.py` (après l'étape 1),
  `cpu_percent.py`, `event.py`, `events_list.py`, `gpu_percent.py`,
  `history.py`, `jwt_utils.py`, `main.py`, `password.py`,
  `password_list.py`, `server.py`, `servers_list.py`,
  `servers_list_dynamic.py`, `servers_list_static.py`, `snmp.py`,
  `standalone.py`, `stats.py`, `stats_client.py`, `stats_client_snmp.py`,
  `stats_server.py`, `thresholds.py`, `webserver.py`.
- `glances/outputs/` : `glances_curses.py`, `glances_curses_browser.py`,
  `glances_restful_api.py`, `glances_sparklines.py`, `glances_stdout*.py`,
  `glances_json_serializer.py`, `glances_colors.py` (vérifier qu'aucun
  module v5 ne les atteint).
- `glances/outdated.py` : la vérification de mise à jour n'est pas portée ;
  sa suppression suit la décision sur le GAP correspondant (CVE-2026-46607).
- Le code mort v4 ainsi libéré : `config.py` emporte la substitution backtick
  (CVE-2026-33641), qui n'est plus livrée.
- WebUI v4 (`glances/outputs/static/js/` hors `v5/`, son bundle) : à
  trancher avec la bascule de la WebUI.
- Tests : les tests v4 COVERED et OBSOLETE de
  `glances-v5-v4-tests-migration.md` sont supprimés ; les tests SHARED qui
  importent du v4 au niveau du module sont déplacés (par exemple
  `TestSecurePopen*` de `test_actions_sanitize.py` vers
  `tests/test_secure_popen.py`).

Vérification : la suite complète passe ; `tests/test_v4_boundary_v5.py` n'a
plus d'entrée `BORROWED` ; `make pre-commit` est propre.

### 5. Après

- Décider du suffixe `_v5` (checklist §2) : un renommage, s'il a lieu, vient
  en dernier, une fois le reste vert.
- `ci.yml` : retirer `develop-v5` ; `test.yml` : les tests v5 deviennent
  la suite principale.
- Reporter sur `support/glancesv4` les correctifs de l'audit qui concernent
  aussi la v4 (liste dans le rapport d'audit).
