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
  - [ ] B1 — les `__init__.py` de paquets v4 chargés par chaque import v5
    (avant la suppression du code v4)
  - [ ] constats « avant 5.0.0b1 » du plan de correction : M1 ✅, M2 ✅,
    M4 ✅ (`sh -c` documenté, décision du mainteneur), M3 ✅, M7 ✅, M8 ✅, M10 ✅, B-4, B-13, tests
    CVE-2026-33641 et GHSA-mcm7
  - [ ] constats « avant 5.0.0 » (M5, M6, M9, M11, constats bas, I-1, I-3)
- [ ] **Les 42 tests GAP** de `glances-v5-v4-tests-migration.md` : pour chacun,
  correction en v5 ou retrait par décision écrite (§9 : « not silently dropped »).
  - [ ] mem : bornes `used`/`percent` en conteneur (LXC, cgroup v2), ARC ZFS,
    `[mem] available`
  - [ ] network / diskio : tri naturel par alias ou nom
  - [ ] fs : pas de seuils sur les montages en lecture seule (#3143)
  - [ ] gpu : `stop()` appelle l'`exit()` des backends (`nvmlShutdown`)
  - [ ] containers : titre « served by <engine> »
  - [ ] connections : compteurs par état (`SYN_SENT`, `SYN_RECV`…)
  - [ ] processlist : colonne CPU#
  - [ ] stdout-json : entrée `_errors` pour un plugin en échec
  - [ ] REST : `/<plugin>/<field>`, `/<plugin>/<pk>/value/<v>`,
    `/<plugin>/<field>/<pk>`, `/<plugin>/top/<n>`, `/config/<section>/<key>`,
    compression gzip
  - [ ] WebUI : `/?refresh=N` règle la cadence
  - [ ] plugins externes (`-P`, `plugin_dir`)
  - [ ] vérification de mise à jour : à porter avec le correctif CVE-2026-46607
    (cache JSON, jamais pickle) ou à retirer par décision
- [ ] **Validation des performances** : pas de régression de la latence de
  rafraîchissement par rapport à v4 (mesure documentée).

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
