# Glances v5 — checklist de fusion `develop-v5 → develop`

**Date :** 2026-10-04 · **Branche :** `develop-v5` (`ad68ac2`) · **Référence :** `develop` (`a86a6e7`)

Ce qui reste à faire **sur `develop-v5`** avant la fusion, tiré de la Phase 4 de
`glances-v5-architecture-decisions.md` (§4.8, §9, §10) et de l'état de la branche
au 2026-10-04. Rien ici ne se fait sur `develop`, sauf la section 6.

État de départ : `develop-v5` a 80 commits d'avance sur `develop` et 0 de retard
(aucun conflit attendu). La CI est verte sur `ad68ac2`. Phase 3 terminée, les
108 tests PORT et les 9 scripts d'export sont portés.

## 1. Bloquants (§4.8, §9)

- [x] **Audit de sécurité complet** sur `develop-v5` (2026-10-04) :
  `glances-v5-security-audit.md`. Aucune faille critique ou haute ;
  1 bloquant structurel, 11 constats moyens. Reste à corriger :
  - [ ] B1 — les `__init__.py` de paquets v4 chargés par chaque import v5,
    en deux temps pour garder la fusion hebdomadaire `develop → develop-v5` :
    - [x] avant la bascule : `tests/test_v4_boundary_v5.py` fige les imports
      de la v5 hors d'elle-même ; plan dans `glances-v5-cutover-plan.md`
    - [ ] le jour de la bascule : appliquer le plan (après le dernier merge)
  - [x] constats « avant 5.0.0b1 » du plan de correction : M1 ✅, M2 ✅,
    M4 ✅ (`sh -c` documenté, décision du mainteneur), M3 ✅, M7 ✅, M8 ✅, M10 ✅, B-4 ✅, B-13 ✅,
    tests CVE-2026-33641 et GHSA-mcm7 ✅
  - [ ] constats « avant 5.0.0 » (M5, M6, M9, M11, constats bas, I-1, I-3)
- [x] **Les 42 tests GAP** de `glances-v5-v4-tests-migration.md` (2026-10-05) :
  chacun corrigé en v5 avec son test, ou retiré par décision écrite (section
  « GAP — traités le 2026-10-05 » du document de migration).
- [x] **Validation des performances** (2026-10-06) : pas de régression de
  latence (cycle ×2,3, API ×1,7, démarrage ×4 plus rapides, −25 % de mémoire) ;
  CPU plus élevé par conception (collecte continue) et parce que la v5
  respecte le `refresh` que la v4 sautait (`glances-v5-performance.md`).
  - [ ] à refaire sur une machine représentative avant `5.0.0`

## 2. Décisions de bascule (à écrire au §10)

- [ ] La commande `glances` lance la v5 (`pyproject.toml` : aujourd'hui
  `glances = "glances:main"` est la v4, `glances-v5` la v5).
- [ ] Sort du code v4 et des tests v4 COVERED / OBSOLETE : supprimés sur
  `develop-v5` avant la fusion (recommandé : ce qui est fusionné est ce qui a
  été testé) ou juste après.
- [ ] Les tests SHARED qui importent du v4 au niveau du module sont déplacés
  dans un fichier sans v4 (ex. `TestSecurePopen*` → `tests/test_secure_popen.py`).
- [ ] Le suffixe `_v5` des modules : gardé ou renommé.

## 3. Version et packaging

- [ ] Une seule source de version : `glances/__init__.py` reçoit
  `__version__ = "5.0.0b1"` et `__apiversion__ = "5"` ; les imports de
  `glances.version_v5` sont redirigés, le module est supprimé.
- [ ] Dockerfiles (`alpine`, `ubuntu`) : `python -m glances` lance la v5.
- [ ] Snap et Helm pointent sur la v5.
- [ ] Workflow de publication de la bêta PyPI depuis `develop`
  (« deferred » dans `.claude/skills/SKILL-ci-cd.md`).
- [ ] `weekly_merge_develop_to_v5.yml` désactivé, `develop-v5` retiré de `ci.yml`
  (dans le commit de fusion).

## 4. Documentation

- [ ] `NEWS.rst` : section 5.0.0 avec toutes les ruptures marquées « for the
  5.0.0 release notes » dans le document d'architecture :
  - [ ] clés de seuils renommées, `bytes_recv_*`/`bytes_sent_*` en ratio [0,1]
  - [ ] modèle de données `/api/5`, XML-RPC supprimé
  - [ ] fonctions retirées : `--cached-time`, `mmm` (`_min`/`_max`/`_mean`),
    flèches de tendance, `--trace-malloc`, `--enable-process-extended`,
    `--api-doc` (sens v4), SNMP, substitution backtick dans la config
  - [ ] templates `--fetch` v4 cassés
  - [ ] touche `4` : quicklook seul, pleine largeur
  - [ ] gestion des processus : F4 ouvre le filtre, ENTRÉE épingle
  - [ ] retirés le 2026-10-05 : vérification de mise à jour PyPI
    (`--disable-check-update`), plugins externes (`-P`, `plugin_dir`),
    `/api/5/config/<section>[/<key>]` ; titre « CONTAINERS N (served by …) »
  - [ ] routes fines `/api/5` : comparaison en texte, 404 sur champ inconnu
    (v4 : `200 null`), `top`/`value`/item en 404 sur un plugin non collection
  - [ ] `/api/5/config` sans mot de passe : seulement les clés de la WebUI (M1) ;
    serveur en loopback : seuls les Host loopback (M2, reverse proxy local →
    `webui_allowed_hosts`) ; graphes par défaut dans `~/.local/share/glances/graphs`
- [ ] `make docs` sur une machine représentative : `docs/api/restful.rst`
  (encore en `/api/4`) et `docs/api/python.rst`.
- [ ] Man page, `README.rst`, `docs/quickstart.rst`, `docs/cmds.rst`,
  `docs/config.rst` relus pour la v5.
- [ ] `conf/glances.conf` et `docker-compose/glances.conf` : plus aucune clé
  v4 ignorée par la v5.
- [ ] `glances-v5-v4-parity-inventory.md` (2026-09-10) recompté : il affiche
  encore 153 `❌ absent`, dont beaucoup livrés depuis.

## 5. Restes dans le code

- [ ] `percpu` lit `[percpu] max_cpu_display`
  (`plugins/percpu/render_curses_v5.py:49`, `_DEFAULT_MAX_CPU_DISPLAY = 4`).
- [ ] Les deux `TODO(G2+)` de `plugins/network/render_curses_v5.py`.

## 6. Le jour de la fusion (hors `develop-v5`)

- [ ] CI verte sur la tête de `develop-v5`, `make pre-commit` propre.
- [ ] Créer `support/glancesv4` depuis `develop`.
- [ ] Fusionner `develop-v5 → develop`, arrêter le weekly merge.
- [ ] Publier `5.0.0b1` depuis `develop`.
