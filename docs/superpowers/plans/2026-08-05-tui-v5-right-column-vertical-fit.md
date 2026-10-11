# TUI v5 — Dynamicité verticale de la colonne de droite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La colonne droite de la TUI v5 (vms, containers, processcount, amps, processlist/programlist, alert) s'adapte à la hauteur du terminal : elle se rogne selon un ordre de sacrifice explicite quand la place manque, et la processlist absorbe tout le surplus quand il y en a.

**Architecture :** Un solveur pur (`plan_right_column`) calcule un budget de lignes par plugin à partir de la hauteur disponible et des effectifs réels ; ce budget est injecté dans `view["row_budget"]` et consommé par chaque renderer. Symétrique exacte du mécanisme horizontal déjà en place (`_fit_proclist_width` → `view["proclist_width"]`).

**Tech Stack :** Python 3.9+, `curses`, `pytest`. Aucune dépendance nouvelle.

**Spec de référence :** `docs/superpowers/specs/2026-08-05-tui-v5-right-column-vertical-fit-design.md`

## Global Constraints

- **Branche : `develop-v5`.** Ne jamais commiter, pusher ni ouvrir de PR — chaque tâche se termine par un `git add`, rien de plus. Aucun trailer `Co-Authored-By`.
- **Ne pas toucher `NEWS.rst`** pendant le développement.
- **Non-régression absolue** : sans clé `row_budget` dans `view` (export, tests headless, appels directs aux renderers), la sortie de chaque renderer doit être identique au bit près à celle d'aujourd'hui. `_MAX_ROWS = 20` reste en place comme valeur de repli.
- **Valeurs nominales** (constantes de module, aucune clé de configuration) : workloads `10`, alertes `10`, processus `20`. Croissance : workloads plafonnés à `20`, processus illimités.
- **Budget = lignes de DONNÉES**, ligne d'en-tête du bloc exclue. Exception documentée : `amps` n'a pas de ligne d'en-tête, son budget compte toutes ses lignes, marqueur inclus.
- **Colonne gauche hors périmètre** : `_paint_sidebar` continue de la clipper comme aujourd'hui.
- Style : `from __future__ import annotations` en tête de chaque module touché (déjà présent partout), docstrings en anglais, commentaires en anglais.
- Suite de tests : `python -m pytest tests/ -q` doit rester verte (1889+ tests au dernier point connu).
- En fin de plan : `make pre-commit` (≈23 hooks ; gitleaks scanne l'index, donc restager avant de relancer).

---

## Structure des fichiers

| Fichier | Responsabilité | Tâches |
|---|---|---|
| `glances/outputs/curses_renderer_v5.py` | `PluginBlock.data_count`, solveur `plan_right_column`, helper `row_budget`, budget du bloc `alert` | 1, 2, 3, 5 |
| `glances/outputs/glances_curses_v5.py` | `_body_geometry`, `_fit_right_column`, câblage de `max_y` | 7 |
| `glances/plugins/processlist/render_curses_v5.py` | consommation du budget | 3 |
| `glances/plugins/programlist/render_curses_v5.py` | consommation du budget | 3 |
| `glances/plugins/containers/render_curses_v5.py` | budget + compteur d'en-tête | 4 |
| `glances/plugins/vms/render_curses_v5.py` | budget + compteur d'en-tête | 4 |
| `glances/plugins/amps/render_curses_v5.py` | budget + ligne marqueur | 6 |

Tests : un fichier de test existant par fichier source touché — aucun nouveau fichier de test.

---

### Task 1: `PluginBlock.data_count` — exposer les effectifs réels

Le solveur est analytique : il a besoin du nombre d'éléments **disponibles**, or un bloc déjà tronqué ne le révèle pas. `build_frame` attache l'information au bloc.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` (dataclass `PluginBlock` ~ligne 150 ; `build_frame` ~lignes 731-798)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consomme : rien.
- Produit : `PluginBlock.data_count: int | None` — nombre d'éléments dans `payload["data"]` pour les plugins collection, `len(alerts_history)` pour le bloc `alert` synthétisé, `None` pour les plugins scalaires.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_curses_renderer_v5.py` :

```python
def test_data_count_is_none_for_scalar_plugin():
    """A scalar plugin has no `data` list — data_count stays None."""
    frame = build_frame(
        store_snapshot={"uptime": {"seconds": 42}},
        fields_by_plugin={"uptime": {"seconds": {"unit": "second", "label": "Uptime"}}},
        registry=[("uptime", False)],
        alerts_history=[],
    )
    blocks = [b for b in frame.header + frame.top + frame.left + frame.right if b.name == "uptime"]
    assert blocks, "uptime block missing"
    assert blocks[0].data_count is None


def test_data_count_counts_collection_items():
    """A collection plugin exposes its FULL item count, even when the
    renderer truncates the rows it emits."""
    data = [{"name": f"c{i}", "status": "running"} for i in range(25)]
    frame = build_frame(
        store_snapshot={"containers": {"data": data, "_levels": {}, "disable_stats": []}},
        fields_by_plugin={"containers": {}},
        registry=[("containers", True)],
        alerts_history=[],
    )
    blocks = [b for b in frame.right if b.name == "containers"]
    assert blocks, "containers block missing"
    assert blocks[0].data_count == 25


def test_data_count_on_alert_block_is_history_length():
    """The synthesized alert block carries the history length."""
    history = [
        {"ts": "2026-08-05T10:00:00+00:00", "plugin": "cpu", "key": None,
         "field": "total", "level": "warning", "previous_level": "ok"}
        for _ in range(17)
    ]
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=history,
    )
    alert_blocks = [b for b in frame.right if b.name == "alert"]
    assert alert_blocks[0].data_count == 17
```

Vérifier que `build_frame` est déjà importé en tête du fichier de test ; sinon ajouter l'import depuis `glances.outputs.curses_renderer_v5`.

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k data_count -v`
Expected: FAIL — `AttributeError: 'PluginBlock' object has no attribute 'data_count'`

- [ ] **Step 3: Ajouter le champ à la dataclass**

Dans `glances/outputs/curses_renderer_v5.py`, dataclass `PluginBlock` :

```python
@dataclass
class PluginBlock:
    """A plugin's multi-line output as a self-contained block.

    The painter places blocks: TOP-slot blocks side-by-side on row 0,
    LEFT/RIGHT-slot blocks stacked vertically below the top row.
    """

    name: str
    rows: list[Row] = field(default_factory=list)
    # Number of items available in the payload BEFORE the renderer applied
    # any row budget — the RIGHT-column solver needs the real count, which a
    # truncated block no longer reveals. None for scalar plugins.
    data_count: int | None = None
```

- [ ] **Step 4: Renseigner le champ dans `build_frame`**

Dans `build_frame`, remplacer la construction du bloc :

```python
        block = PluginBlock(name=plugin_name, rows=rows)
```

par :

```python
        raw_data = payload.get("data") if isinstance(payload, dict) else None
        block = PluginBlock(
            name=plugin_name,
            rows=rows,
            data_count=len(raw_data) if isinstance(raw_data, list) else None,
        )
```

Et pour le bloc `alert` synthétisé en fin de fonction :

```python
    frame.right.append(
        PluginBlock(
            name="alert",
            rows=render_alert_block(alerts_history, limit=alerts_limit, is_initializing=alerts_initializing),
            data_count=len(alerts_history),
        )
    )
```

- [ ] **Step 5: Lancer les tests**

Run: `python -m pytest tests/test_curses_renderer_v5.py -v`
Expected: PASS, y compris tous les tests préexistants du fichier.

- [ ] **Step 6: Stager**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 2: Le solveur `plan_right_column`

Fonction pure, sans dépendance curses. C'est le cœur du design : elle traduit une hauteur disponible en budget par plugin.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` (nouvelle section après `render_alert_block`)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consomme : rien (fonction pure).
- Produit :
  - `plan_right_column(*, body_height: int, static_heights: dict[str, int], amps_height: int, n_vms: int, n_containers: int, n_processes: int, n_alerts: int) -> dict[str, int]`
    → dict `{"vms": int, "containers": int, "processlist": int, "programlist": int, "alert": int}`, plus `"amps": int` uniquement quand le palier `j` s'est déclenché.
  - `_split_workloads(quota: int, n_vms: int, n_containers: int) -> tuple[int, int]`
  - Constantes `_NOMINAL_WORKLOADS = 10`, `_NOMINAL_ALERTS = 10`, `_NOMINAL_PROCESSES = 20`, `_MAX_WORKLOADS = 20`.

- [ ] **Step 1: Écrire les tests du découpage max-min**

Ajouter à `tests/test_curses_renderer_v5.py` :

```python
from glances.outputs.curses_renderer_v5 import _split_workloads, plan_right_column


def test_split_workloads_leftover_goes_to_the_other_block():
    """3 VMs + 20 containers, budget 10 → les 3 VMs tiennent, containers prend le reste."""
    assert _split_workloads(10, 3, 20) == (3, 7)


def test_split_workloads_equal_demand_splits_evenly():
    assert _split_workloads(10, 12, 12) == (5, 5)


def test_split_workloads_single_block_takes_everything():
    assert _split_workloads(10, 0, 30) == (0, 10)
    assert _split_workloads(10, 30, 0) == (10, 0)


def test_split_workloads_never_exceeds_demand():
    assert _split_workloads(10, 2, 3) == (2, 3)


def test_split_workloads_odd_leftover_goes_to_vms_first():
    """Biais documenté : le reliquat impair est proposé d'abord à `vms`
    (ordre de RIGHT_SLOT)."""
    assert _split_workloads(5, 10, 10) == (3, 2)


def test_split_workloads_zero_quota_hides_both():
    assert _split_workloads(0, 5, 5) == (0, 0)
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k split_workloads -v`
Expected: FAIL — `ImportError: cannot import name '_split_workloads'`

- [ ] **Step 3: Implémenter `_split_workloads`**

Dans `glances/outputs/curses_renderer_v5.py`, après `render_alert_block` :

```python
# ------------------------------------------------- RIGHT column vertical budget
#
# The RIGHT column adapts to the terminal height the way the TOP row adapts to
# its width. `plan_right_column` is pure: it turns an available height into a
# per-plugin row budget, published as `view["row_budget"]` and consumed by the
# renderers. See docs/superpowers/specs/2026-08-05-tui-v5-right-column-vertical-fit-design.md

# Nominal budgets, in DATA rows (the block's own header row is not counted).
# These reproduce the historical behaviour: 20 processes, 10 alerts.
_NOMINAL_WORKLOADS = 10
_NOMINAL_ALERTS = 10
_NOMINAL_PROCESSES = 20
# Growth ceiling for the shared vms+containers budget on a tall terminal.
_MAX_WORKLOADS = 20


def _split_workloads(quota: int, n_vms: int, n_containers: int) -> tuple[int, int]:
    """Split the shared workload budget between `vms` and `containers`.

    Max-min fairness: each block first gets an equal share, then whatever a
    block does not use is handed to the other one. A sparsely populated block
    is therefore never squeezed out by a crowded one (2 VMs + 30 containers
    shows both VMs). An odd leftover is offered to `vms` first, matching the
    RIGHT_SLOT order.
    """
    share = quota // 2
    vms = min(n_vms, share)
    containers = min(n_containers, share)
    leftover = quota - vms - containers
    if leftover > 0:
        take = min(leftover, n_vms - vms)
        vms += take
        leftover -= take
    if leftover > 0:
        containers += min(leftover, n_containers - containers)
    return (vms, containers)
```

- [ ] **Step 4: Lancer les tests du découpage**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k split_workloads -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Écrire les tests du solveur**

Ajouter à `tests/test_curses_renderer_v5.py`. Le helper fixe un décor réaliste et ne fait varier que `body_height`, ce qui permet de tester la cascade palier par palier :

```python
def _plan(body_height, **overrides):
    """Solveur avec un décor réaliste : 1 ligne processcount, pas d'AMP,
    4 VMs, 30 containers, 400 processus, 40 alertes."""
    kwargs = {
        "body_height": body_height,
        "static_heights": {"processcount": 1},
        "amps_height": 0,
        "n_vms": 4,
        "n_containers": 30,
        "n_processes": 400,
        "n_alerts": 40,
    }
    kwargs.update(overrides)
    return plan_right_column(**kwargs)


def _cost(plan, *, n_vms=4, n_containers=30, n_processes=400, n_alerts=40,
          static=1, amps=0):
    """Hauteur réellement occupée par un plan — miroir de _paint_sidebar :
    somme des hauteurs des blocs visibles + une ligne vide entre blocs."""
    heights = []
    if n_vms and plan["vms"]:
        heights.append(1 + min(n_vms, plan["vms"]))
    if n_containers and plan["containers"]:
        heights.append(1 + min(n_containers, plan["containers"]))
    if static:
        heights.append(static)
    amps_rows = plan.get("amps", amps)
    if amps_rows:
        heights.append(amps_rows)
    if n_processes:
        heights.append(1 + min(n_processes, plan["processlist"]))
    heights.append(1 + min(n_alerts, plan["alert"]))
    return sum(heights) + max(0, len(heights) - 1)


def test_plan_nominal_on_a_comfortable_terminal():
    """Assez de place → valeurs nominales, sauf les processus qui absorbent
    le surplus (palier de croissance B)."""
    plan = _plan(50)
    assert plan["vms"] + plan["containers"] == 10
    assert plan["alert"] == 10
    assert plan["processlist"] >= _NOMINAL_PROCESSES


def test_plan_processes_absorb_all_the_surplus():
    """Le seul bloc élastique remplit le terminal, sans le dépasser."""
    plan = _plan(60)
    assert _cost(plan) <= 60
    grown = dict(plan, processlist=plan["processlist"] + 1)
    assert _cost(grown) > 60, "une ligne de plus aurait encore tenu"


def test_plan_workloads_grow_before_processes():
    """Palier A avant B : sur un terminal haut les workloads regagnent de la
    place avant que la processlist n'avale tout."""
    plan = _plan(90)
    assert plan["vms"] + plan["containers"] == _MAX_WORKLOADS


def test_plan_workloads_never_exceed_the_growth_ceiling():
    plan = _plan(400)
    assert plan["vms"] + plan["containers"] == _MAX_WORKLOADS


def _first_height_where(predicate):
    """Plus grande hauteur (en descendant) où `predicate(plan)` devient vrai.

    Balayer plutôt que coder en dur une hauteur rend les tests robustes au
    décor : c'est bien l'ORDRE des paliers qui est vérifié, pas une valeur
    arithmétique fragile.
    """
    for height in range(80, 0, -1):
        if predicate(_plan(height)):
            return height
    return None


def test_plan_shrink_ladder_follows_the_documented_order():
    """Les paliers a→k se déclenchent dans l'ordre du spec, jamais l'inverse."""
    steps = {
        "a": lambda p: p["vms"] + p["containers"] <= 5,
        "b": lambda p: p["alert"] <= 5,
        "c": lambda p: p["processlist"] <= 10,
        "d": lambda p: p["vms"] + p["containers"] <= 3,
        "e": lambda p: p["alert"] <= 3,
        "f": lambda p: p["processlist"] <= 5,
        "g": lambda p: p["vms"] + p["containers"] == 0,
        "h": lambda p: p["alert"] == 0,
        "i": lambda p: p["processlist"] <= 3,
        "k": lambda p: p["processlist"] <= 1,
    }
    heights = {name: _first_height_where(pred) for name, pred in steps.items()}
    assert all(h is not None for h in heights.values()), heights
    ordered = [heights[name] for name in "abcdefghik"]
    # Hauteurs décroissantes : un palier ne peut pas se déclencher avant celui
    # qui le précède dans la cascade.
    assert ordered == sorted(ordered, reverse=True), heights


def test_plan_step_a_shrinks_workloads_alone():
    """Juste sous le seuil nominal, SEULS les workloads reculent."""
    height = _first_height_where(lambda p: p["vms"] + p["containers"] < 10)
    plan = _plan(height)
    assert plan["vms"] + plan["containers"] == 5
    assert plan["alert"] == 10
    assert plan["processlist"] == 20


def test_plan_cascade_is_monotonic():
    """Réduire la hauteur ne peut jamais augmenter un quota, et le plan tient
    toujours dans la hauteur disponible tant qu'on n'a pas épuisé la cascade."""
    previous = None
    for height in range(60, 14, -1):
        plan = _plan(height)
        assert _cost(plan) <= height, f"plan déborde à body_height={height}"
        if previous is not None:
            assert plan["vms"] + plan["containers"] <= previous["workloads"]
            assert plan["alert"] <= previous["alert"]
            assert plan["processlist"] <= previous["processlist"]
        previous = {
            "workloads": plan["vms"] + plan["containers"],
            "alert": plan["alert"],
            "processlist": plan["processlist"],
        }


def test_plan_step_g_hides_workloads_entirely():
    plan = _plan(12)
    assert plan["vms"] == 0
    assert plan["containers"] == 0


def test_plan_step_h_leaves_alert_header_only():
    plan = _plan(10)
    assert plan["alert"] == 0


def test_plan_keeps_five_processes_until_the_alert_block_is_a_header():
    """Le plancher 5 processus est plus fort que les alertes : il ne tombe
    qu'une fois workloads masqués (g) et alertes réduites à l'en-tête (h)."""
    plan = _plan(11)
    assert plan["processlist"] >= 5


def test_plan_breaks_the_process_floor_only_at_the_very_end():
    plan = _plan(7)
    assert plan["processlist"] < 5
    assert plan["processlist"] >= 1


def test_plan_never_returns_zero_processes():
    plan = _plan(1)
    assert plan["processlist"] == 1


def test_plan_step_j_truncates_amps_before_the_last_process_step():
    """Un AMP bavard est rogné plutôt que de faire disparaître la
    processlist."""
    plan = _plan(14, amps_height=30, n_vms=0, n_containers=0)
    assert plan.get("amps") is not None
    assert plan["amps"] < 30
    assert plan["processlist"] >= 1


def test_plan_leaves_amps_untouched_when_they_fit():
    plan = _plan(60, amps_height=3)
    assert "amps" not in plan


def test_plan_absent_blocks_free_room_for_processes():
    """Sans containers ni VMs, les paliers a/d/g sont des no-op : la place
    qu'ils auraient prise revient à la processlist."""
    with_workloads = _plan(40)
    without = _plan(40, n_vms=0, n_containers=0)
    assert without["vms"] == 0
    assert without["containers"] == 0
    assert without["processlist"] > with_workloads["processlist"]


def test_plan_programlist_mirrors_processlist():
    """Les deux vues sont mutuellement exclusives et partagent le budget."""
    plan = _plan(40)
    assert plan["programlist"] == plan["processlist"]


def test_plan_on_a_degenerate_height_does_not_crash():
    for height in (0, -5):
        plan = plan_right_column(
            body_height=height,
            static_heights={},
            amps_height=0,
            n_vms=0,
            n_containers=0,
            n_processes=10,
            n_alerts=0,
        )
        assert plan["processlist"] >= 1
```

- [ ] **Step 6: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k plan_ -v`
Expected: FAIL — `ImportError: cannot import name 'plan_right_column'`

- [ ] **Step 7: Implémenter le solveur**

À la suite de `_split_workloads` :

```python
# Shrink ladder, applied in order until the layout fits (design §4.4).
# `None` marks the special "truncate amps to whatever is left" step.
_SHRINK_STEPS: tuple[tuple[str, int | None], ...] = (
    ("workloads", 5),  # a
    ("alerts", 5),  # b
    ("processes", 10),  # c
    ("workloads", 3),  # d
    ("alerts", 3),  # e
    ("processes", 5),  # f
    ("workloads", 0),  # g — block hidden entirely
    ("alerts", 0),  # h — header only
    ("processes", 3),  # i
    ("amps", None),  # j — truncated to what remains, "+N lines" marker
    ("processes", 1),  # k — beyond this, curses clips
)


def plan_right_column(
    *,
    body_height: int,
    static_heights: dict[str, int],
    amps_height: int,
    n_vms: int,
    n_containers: int,
    n_processes: int,
    n_alerts: int,
) -> dict[str, int]:
    """Return the RIGHT column row budget for the available `body_height`.

    Pure and analytic — no frame rebuild is needed to evaluate a candidate
    layout, because every elastic block costs exactly one line per data row
    plus one header row.

    Args:
        body_height: rows available below the top row separator.
        static_heights: heights of the non-elastic RIGHT blocks that are
            present (currently only `processcount`, always 1 row).
        amps_height: natural height of the amps block, 0 when absent.
        n_vms / n_containers / n_processes / n_alerts: item counts available
            in the payloads (`PluginBlock.data_count`).

    Returns:
        `{plugin: max data rows}`. `amps` is present only when the ladder had
        to truncate it (step j); its budget counts ALL its rows, marker
        included.
    """
    state = {
        "workloads": _NOMINAL_WORKLOADS,
        "alerts": _NOMINAL_ALERTS,
        "processes": _NOMINAL_PROCESSES,
        "amps": amps_height,
    }

    def cost(candidate: dict[str, int]) -> int:
        """Rows occupied by `candidate` — mirrors `_paint_sidebar`: the sum of
        the visible block heights plus one blank line between blocks."""
        vms_q, containers_q = _split_workloads(candidate["workloads"], n_vms, n_containers)
        heights: list[int] = []
        if n_vms and vms_q:
            heights.append(1 + vms_q)
        if n_containers and containers_q:
            heights.append(1 + containers_q)
        heights.extend(h for h in static_heights.values() if h)
        if candidate["amps"]:
            heights.append(candidate["amps"])
        if n_processes:
            heights.append(1 + min(n_processes, candidate["processes"]))
        # The alert block is always emitted, if only as a header line.
        heights.append(1 + min(n_alerts, candidate["alerts"]))
        return sum(heights) + max(0, len(heights) - 1)

    if cost(state) <= body_height:
        # Growth: workloads first (step A), then processes absorb the rest
        # (step B). One row at a time so the result provably fills the
        # terminal without overflowing it.
        while state["workloads"] < _MAX_WORKLOADS and cost({**state, "workloads": state["workloads"] + 1}) <= body_height:
            state["workloads"] += 1
        while state["processes"] < n_processes and cost({**state, "processes": state["processes"] + 1}) <= body_height:
            state["processes"] += 1
    else:
        for key, value in _SHRINK_STEPS:
            if key == "amps":
                if not state["amps"]:
                    continue
                # Truncate to what remains, keeping at least the marker line.
                deficit = cost(state) - body_height
                state["amps"] = max(1, state["amps"] - deficit)
            else:
                if value >= state[key]:
                    continue
                state[key] = value
            if cost(state) <= body_height:
                break

    vms_q, containers_q = _split_workloads(state["workloads"], n_vms, n_containers)
    budget = {
        "vms": vms_q,
        "containers": containers_q,
        "processlist": state["processes"],
        "programlist": state["processes"],
        "alert": state["alerts"],
    }
    if state["amps"] != amps_height:
        budget["amps"] = state["amps"]
    return budget
```

- [ ] **Step 8: Lancer les tests du solveur**

Run: `python -m pytest tests/test_curses_renderer_v5.py -v`
Expected: PASS. Si `test_plan_cascade_is_monotonic` échoue à une hauteur donnée, c'est que la cascade laisse un plan qui déborde — corriger le solveur, pas le test.

- [ ] **Step 9: Stager**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 3: Helper `row_budget` + consommation par processlist et programlist

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` (helper)
- Modify: `glances/plugins/processlist/render_curses_v5.py:407`
- Modify: `glances/plugins/programlist/render_curses_v5.py:109`
- Test: `tests/test_plugin_processlist_render_curses_v5.py`, `tests/test_plugin_programlist_render_curses_v5.py`

**Interfaces:**
- Consomme : rien de Task 1/2 (le helper lit `view`, il ne dépend pas du solveur).
- Produit : `row_budget(view: dict[str, Any] | None, plugin_name: str, default: int | None) -> int | None` — nombre max de lignes de données, `default` quand `view["row_budget"]` est absent ou n'a pas la clé.

- [ ] **Step 1: Écrire les tests**

Dans `tests/test_plugin_processlist_render_curses_v5.py` — le fichier fournit déjà le helper `_proc(**overrides)` (ligne 47) et la fixture `fields()` (ligne 29), à réutiliser tels quels :

```python
def _many_procs(n):
    return {"data": [_proc(pid=1000 + i, name=f"proc{i}") for i in range(n)], "_levels": {}}


def test_row_budget_caps_the_number_of_processes(fields):
    rows = render(_many_procs(50), fields, view={"row_budget": {"processlist": 7}})
    assert len(rows) == 1 + 7  # en-tête + 7 processus


def test_row_budget_above_the_default_shows_more_than_twenty(fields):
    """La règle principale : sur un terminal haut on dépasse _MAX_ROWS."""
    rows = render(_many_procs(50), fields, view={"row_budget": {"processlist": 45}})
    assert len(rows) == 1 + 45


def test_without_row_budget_the_default_cap_still_applies(fields):
    """Non-régression : sans budget, la sortie est celle d'aujourd'hui."""
    rows = render(_many_procs(50), fields)
    assert len(rows) == 1 + 20
```

Dans `tests/test_plugin_programlist_render_curses_v5.py`, le même triplet avec la clé `"programlist"`, le helper `_program(**overrides)` (ligne 34) et la fixture `fields()` (ligne 56) :

```python
def _many_programs(n):
    return {"data": [_program(name=f"prog{i}") for i in range(n)], "_levels": {}}


def test_row_budget_caps_the_number_of_programs(fields):
    rows = render(_many_programs(50), fields, view={"row_budget": {"programlist": 7}})
    assert len(rows) == 1 + 7


def test_row_budget_above_the_default_shows_more_than_twenty(fields):
    rows = render(_many_programs(50), fields, view={"row_budget": {"programlist": 45}})
    assert len(rows) == 1 + 45


def test_without_row_budget_the_default_cap_still_applies(fields):
    rows = render(_many_programs(50), fields)
    assert len(rows) == 1 + 20
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_plugin_processlist_render_curses_v5.py tests/test_plugin_programlist_render_curses_v5.py -k row_budget -v`
Expected: FAIL — les deux premiers tests renvoient 21 lignes (le budget est ignoré).

- [ ] **Step 3: Implémenter le helper**

Dans `glances/outputs/curses_renderer_v5.py`, juste après les constantes `_NOMINAL_*` :

```python
def row_budget(view: dict[str, Any] | None, plugin_name: str, default: int | None) -> int | None:
    """Max number of DATA rows `plugin_name` may emit this cycle.

    Reads `view["row_budget"]`, published by the TUI's vertical fit pass.
    Returns `default` when the view carries no budget (export, tests, direct
    renderer calls) so those paths keep their historical output.
    """
    budget = (view or {}).get("row_budget")
    if not isinstance(budget, dict):
        return default
    value = budget.get(plugin_name)
    return value if isinstance(value, int) else default
```

- [ ] **Step 4: Consommer le budget dans processlist**

Dans `glances/plugins/processlist/render_curses_v5.py`, ajouter `row_budget` à l'import existant :

```python
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, row_budget
```

puis remplacer la boucle (ligne ~407) :

```python
    for item in items[:_MAX_ROWS]:
```

par :

```python
    # `_MAX_ROWS` is the nominal fallback; the TUI publishes a height-driven
    # budget in `view["row_budget"]` which may be lower (short terminal) or
    # higher (tall terminal — the list fills the screen).
    for item in items[: row_budget(view, "processlist", _MAX_ROWS)]:
```

- [ ] **Step 5: Consommer le budget dans programlist**

Dans `glances/plugins/programlist/render_curses_v5.py`, ajouter `row_budget` à l'import depuis `glances.outputs.curses_renderer_v5` (l'import existant vient de `glances.plugins.processlist.render_curses_v5` pour les helpers de cellule ; ajouter une ligne d'import distincte pour `row_budget` si nécessaire), puis remplacer la boucle (ligne ~109) :

```python
    for item in items[: row_budget(view, "programlist", _MAX_ROWS)]:
```

- [ ] **Step 6: Lancer les tests**

Run: `python -m pytest tests/test_plugin_processlist_render_curses_v5.py tests/test_plugin_programlist_render_curses_v5.py -v`
Expected: PASS, tests préexistants inclus (notamment `test_no_width_keeps_all_columns`).

- [ ] **Step 7: Stager**

```bash
git add glances/outputs/curses_renderer_v5.py glances/plugins/processlist/render_curses_v5.py glances/plugins/programlist/render_curses_v5.py tests/test_plugin_processlist_render_curses_v5.py tests/test_plugin_programlist_render_curses_v5.py
```

---

### Task 4: Budget et compteur de troncature pour containers et vms

**Files:**
- Modify: `glances/plugins/containers/render_curses_v5.py` (`_build_header_row`, `render`)
- Modify: `glances/plugins/vms/render_curses_v5.py` (`_build_header_row`, `render`)
- Test: `tests/test_plugin_containers_render_curses_v5.py`, `tests/test_plugin_vms_render_curses_v5.py`

**Interfaces:**
- Consomme : `row_budget(view, plugin_name, default)` (Task 3).
- Produit : rien pour les tâches suivantes.

Règles :
- `budget == 0` → `render` retourne `[]` (bloc entièrement masqué, palier `g`).
- La largeur de la colonne nom (`name_w`) reste calculée sur **la liste complète**, pour que la colonne ne saute pas de largeur quand le budget change. Elle est ensuite élargie si le compteur est plus long.
- `show_engine` / `show_pod` / `show_load` restent calculés sur la liste complète, même raison.

- [ ] **Step 1: Écrire les tests containers**

Dans `tests/test_plugin_containers_render_curses_v5.py` :

```python
def _many(n):
    return [
        {"name": f"ctr{i}", "status": "running", "cpu_percent": 1.0,
         "memory_usage_no_cache": 1024, "memory_limit": 4096}
        for i in range(n)
    ]


def test_row_budget_truncates_the_container_list():
    rows = render(_payload(_many(25)), {}, view={"row_budget": {"containers": 7}})
    assert len(rows) == 1 + 7


def test_truncated_list_shows_a_counter_in_the_name_header():
    rows = render(_payload(_many(25)), {}, view={"row_budget": {"containers": 7}})
    assert "CONTAINER 7/25" in _texts(rows[0])


def test_untruncated_list_keeps_the_bare_header_label():
    rows = render(_payload(_many(5)), {}, view={"row_budget": {"containers": 10}})
    header = _texts(rows[0])
    assert "CONTAINER" in header
    assert "/" not in header.split("Status")[0]


def test_zero_budget_hides_the_block_entirely():
    assert render(_payload(_many(25)), {}, view={"row_budget": {"containers": 0}}) == []


def test_without_row_budget_all_containers_are_rendered():
    """Non-régression : appel direct sans view → sortie inchangée."""
    rows = render(_payload(_many(25)), {})
    assert len(rows) == 1 + 25


def test_counter_widens_the_name_column_so_data_rows_stay_aligned():
    """Un compteur plus long que le nom le plus long ne doit pas décaler les
    colonnes suivantes : la cellule de nom garde la même largeur en en-tête
    et en données."""
    data = [{"name": "a", "status": "running"} for _ in range(25)]
    rows = render(_payload(data), {}, view={"row_budget": {"containers": 7}})
    assert rows[0].cells[0].text.startswith("CONTAINER 7/25")
    assert len(rows[0].cells[0].text) == len(rows[1].cells[0].text)
```

- [ ] **Step 2: Écrire les tests vms**

Dans `tests/test_plugin_vms_render_curses_v5.py` — le fichier fournit `_payload(items, max_name_size=20)`, `_vm(**over)` et `_flat(rows)` (lignes 18-26). Même jeu de six tests, avec la clé `"vms"` et le libellé `Name` :

```python
def _many_vms(n):
    return [_vm(name=f"vm{i}") for i in range(n)]


def test_row_budget_truncates_the_vm_list():
    rows = render(_payload(_many_vms(12)), {}, view={"row_budget": {"vms": 3}})
    assert len(rows) == 1 + 3


def test_truncated_list_shows_a_counter_in_the_name_header():
    rows = render(_payload(_many_vms(12)), {}, view={"row_budget": {"vms": 3}})
    assert "Name 3/12" in _flat(rows[0])


def test_untruncated_list_keeps_the_bare_header_label():
    rows = render(_payload(_many_vms(2)), {}, view={"row_budget": {"vms": 10}})
    assert "/" not in _flat(rows[0]).split("Status")[0]


def test_zero_budget_hides_the_block_entirely():
    assert render(_payload(_many_vms(12)), {}, view={"row_budget": {"vms": 0}}) == []


def test_without_row_budget_all_vms_are_rendered():
    rows = render(_payload(_many_vms(12)), {})
    assert len(rows) == 1 + 12


def test_counter_widens_the_name_column_so_data_rows_stay_aligned():
    rows = render(_payload([_vm(name="a") for _ in range(12)]), {}, view={"row_budget": {"vms": 3}})
    name_index = 0  # pas de colonne Engine avec un seul moteur
    assert len(rows[0].cells[name_index].text) == len(rows[1].cells[name_index].text)
```

- [ ] **Step 3: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_plugin_containers_render_curses_v5.py tests/test_plugin_vms_render_curses_v5.py -k "budget or counter or truncat or hides" -v`
Expected: FAIL — le budget est ignoré, toutes les lignes sont rendues.

- [ ] **Step 4: Implémenter dans containers**

Dans `glances/plugins/containers/render_curses_v5.py`, ajouter `row_budget` à l'import depuis `glances.outputs.curses_renderer_v5`.

`_build_header_row` prend un libellé de colonne nom paramétrable :

```python
def _build_header_row(
    disable: set[str], *, show_engine: bool, show_pod: bool, name_w: int, sort_key: str | None,
    name_label: str = "CONTAINER",
) -> Row:
```

et dans son corps :

```python
    if "name" not in disable:
        h.append(hdr(name_label, name_w, ljust=True))
```

Dans `render`, après le calcul de `name_w` (ligne ~186) :

```python
    total = len(items)
    budget = row_budget(view, "containers", None)
    if isinstance(budget, int):
        if budget <= 0:
            # Step g of the vertical cascade: the block is dropped entirely.
            return []
        items = items[:budget]
    truncated = len(items) < total
    # The counter replaces the bare label when the list is cut. `name_w` stays
    # computed on the FULL list so the column does not jump width from one
    # cycle to the next, and is only widened when the counter needs it.
    name_label = f"CONTAINER {len(items)}/{total}" if truncated else "CONTAINER"
    name_w = max(name_w, len(name_label))
```

⚠️ `show_engine`, `show_pod` et `name_w` sont calculés **avant** la troncature, sur `items` complet — ne pas déplacer ces lignes après le slice.

Enfin passer le libellé :

```python
    header = _build_header_row(
        disable, show_engine=show_engine, show_pod=show_pod, name_w=name_w,
        sort_key=sort_key, name_label=name_label,
    )
```

- [ ] **Step 5: Implémenter dans vms**

Même schéma dans `glances/plugins/vms/render_curses_v5.py` :

```python
def _build_header_row(
    *, show_engine: bool, engine_w: int, name_w: int, show_load: bool, sort_key: str | None,
    name_label: str = "Name",
) -> Row:
```

```python
    cells.append(_header(name_label, name_w, ljust=True, sort_key=sort_key))
```

Dans `render`, après le calcul de `name_w` / `engine_w` / `show_load` (ligne ~134) :

```python
    total = len(items)
    budget = row_budget(view, "vms", None)
    if isinstance(budget, int):
        if budget <= 0:
            return []
        items = items[:budget]
    truncated = len(items) < total
    name_label = f"Name {len(items)}/{total}" if truncated else "Name"
    name_w = max(name_w, len(name_label))
```

⚠️ **Piège du soulignement de tri, à corriger dans les DEUX plugins.** Le soulignement de la colonne triée est résolu par une table indexée sur le libellé : `_HEADER_SORT_FIELD = {"Name": "name", ...}` côté vms (ligne 49) et `_HEADER_SORT_KEY = {"CONTAINER": "name", ...}` côté containers (ligne 28). Avec un libellé devenu `"Name 3/12"` / `"CONTAINER 7/25"`, la clé ne matche plus et le soulignement **disparaît silencieusement** dès que la liste est tronquée.

Côté vms, remplacer dans `_build_header_row` :

```python
    cells.append(_header(name_label, name_w, ljust=True, sort_key=sort_key))
```

par :

```python
    # The sort underline is resolved on the CANONICAL label: `name_label` may
    # carry a truncation counter ("Name 3/12"), which is not a table key.
    name_underline = bool(sort_key) and _HEADER_SORT_FIELD.get("Name") == sort_key
    cells.append(
        Cell(text=name_label.ljust(name_w), color=ColorRole.HEADER, bold=True, underline=name_underline)
    )
```

Côté containers, dans `_build_header_row`, remplacer :

```python
    if "name" not in disable:
        h.append(hdr(name_label, name_w, ljust=True))
```

par :

```python
    if "name" not in disable:
        name_underline = bool(sort_key) and _HEADER_SORT_KEY.get("CONTAINER") == sort_key
        h.append(
            Cell(text=f"{name_label:<{name_w}}", color=ColorRole.HEADER, bold=True, underline=name_underline)
        )
```

- [ ] **Step 6: Ajouter le test de non-régression du soulignement**

Dans chacun des deux fichiers de test :

Containers (`_HEADER_SORT_KEY["CONTAINER"] == "name"`) :

```python
def test_sort_underline_survives_the_truncation_counter():
    rows = render(
        _payload(_many(25)), {},
        view={"row_budget": {"containers": 7}, "sort_key": "name"},
    )
    assert rows[0].cells[0].underline is True
```

vms (`_HEADER_SORT_FIELD["Name"] == "name"`) :

```python
def test_sort_underline_survives_the_truncation_counter():
    rows = render(
        _payload(_many_vms(12)), {},
        view={"row_budget": {"vms": 3}, "sort_key": "name"},
    )
    assert rows[0].cells[0].underline is True
```

- [ ] **Step 7: Lancer les tests**

Run: `python -m pytest tests/test_plugin_containers_render_curses_v5.py tests/test_plugin_vms_render_curses_v5.py -v`
Expected: PASS, tests préexistants inclus.

- [ ] **Step 8: Stager**

```bash
git add glances/plugins/containers/render_curses_v5.py glances/plugins/vms/render_curses_v5.py tests/test_plugin_containers_render_curses_v5.py tests/test_plugin_vms_render_curses_v5.py
```

---

### Task 5: Budget du bloc alert

Le bloc `alert` n'est pas un renderer de plugin : il est synthétisé par `build_frame` via `render_alert_block(history, limit=…)`. Le budget passe donc par l'argument `limit`.

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` (`render_alert_block` ~ligne 562, `build_frame`)
- Test: `tests/test_curses_renderer_v5.py`

**Interfaces:**
- Consomme : `row_budget` (Task 3).
- Produit : rien.

- [ ] **Step 1: Écrire les tests**

```python
def _alert_history(n):
    return [
        {"ts": f"2026-08-05T10:{i:02d}:00+00:00", "plugin": "cpu", "key": None,
         "field": "total", "level": "warning", "previous_level": "ok"}
        for i in range(n)
    ]


def test_alert_limit_zero_renders_the_header_only():
    """Piège : `history[-0:]` renvoie TOUT l'historique. Le palier h doit
    court-circuiter explicitement."""
    rows = render_alert_block(_alert_history(27), limit=0)
    assert len(rows) == 1
    assert "27 total" in "".join(c.text for c in rows[0].cells)


def test_alert_limit_is_read_from_the_row_budget():
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=_alert_history(27),
        view={"row_budget": {"alert": 4}},
    )
    alert_block = [b for b in frame.right if b.name == "alert"][0]
    assert len(alert_block.rows) == 1 + 4


def test_alert_without_row_budget_keeps_the_default_limit():
    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={},
        registry=[],
        alerts_history=_alert_history(27),
    )
    alert_block = [b for b in frame.right if b.name == "alert"][0]
    assert len(alert_block.rows) == 1 + 10
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k alert_limit -v`
Expected: FAIL — `test_alert_limit_zero_renders_the_header_only` renvoie 28 lignes (le slice `[-0:]`), et le budget n'est pas lu.

- [ ] **Step 3: Court-circuiter `limit=0` dans `render_alert_block`**

Dans `render_alert_block`, remplacer :

```python
    recent = list(reversed(history[-limit:]))
```

par :

```python
    # `history[-0:]` returns the WHOLE list — the cascade's "header only" step
    # (limit == 0) must short-circuit rather than rely on the slice.
    recent = list(reversed(history[-limit:])) if limit > 0 else []
```

- [ ] **Step 4: Lire le budget dans `build_frame`**

Dans `build_frame`, remplacer l'appel final :

```python
            rows=render_alert_block(alerts_history, limit=alerts_limit, is_initializing=alerts_initializing),
```

par :

```python
            rows=render_alert_block(
                alerts_history,
                limit=row_budget(view, "alert", alerts_limit),
                is_initializing=alerts_initializing,
            ),
```

- [ ] **Step 5: Lancer les tests**

Run: `python -m pytest tests/test_curses_renderer_v5.py -v`
Expected: PASS

- [ ] **Step 6: Stager**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 6: Budget et marqueur pour amps

**Files:**
- Modify: `glances/plugins/amps/render_curses_v5.py`
- Test: `tests/test_plugin_amps_render_curses_v5.py`

**Interfaces:**
- Consomme : `row_budget` (Task 3).
- Produit : rien.

Rappel du contrat : `amps` n'a pas de ligne d'en-tête ; son budget compte **toutes** ses lignes, marqueur inclus. Budget `N` ⇒ `N − 1` lignes de contenu + 1 ligne `… +K lines`.

- [ ] **Step 1: Écrire les tests**

```python
def _verbose_amp(n_lines):
    return {
        "data": [
            {"name": "myamp", "regex": None, "count": None,
             "result": "\n".join(f"line {i}" for i in range(n_lines))}
        ],
        "_levels": {},
    }


def test_amps_without_budget_render_every_line():
    """Non-régression : la garantie « toutes les lignes AMPs » par défaut."""
    rows = render(_verbose_amp(30), {})
    assert len(rows) == 30


def test_amps_budget_truncates_and_appends_a_marker():
    rows = render(_verbose_amp(30), {}, view={"row_budget": {"amps": 5}})
    assert len(rows) == 5
    last = "".join(c.text for c in rows[-1].cells)
    assert "+26 lines" in last  # 30 rendues - 4 conservées


def test_amps_budget_larger_than_the_content_is_a_no_op():
    rows = render(_verbose_amp(3), {}, view={"row_budget": {"amps": 10}})
    assert len(rows) == 3
    assert "+" not in "".join(c.text for c in rows[-1].cells)


def test_amps_budget_of_one_is_the_marker_alone():
    rows = render(_verbose_amp(30), {}, view={"row_budget": {"amps": 1}})
    assert len(rows) == 1
    assert "+30 lines" in "".join(c.text for c in rows[0].cells)
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_plugin_amps_render_curses_v5.py -k budget -v`
Expected: FAIL — 30 lignes rendues quel que soit le budget.

- [ ] **Step 3: Implémenter**

Dans `glances/plugins/amps/render_curses_v5.py`, ajouter `row_budget` à l'import depuis `glances.outputs.curses_renderer_v5`, puis remplacer le `return rows` final par :

```python
    budget = row_budget(view, "amps", None)
    if isinstance(budget, int) and 0 < budget < len(rows):
        # Last step of the vertical cascade: a verbose AMP must not push the
        # process list off the screen. The marker consumes the last budgeted
        # line, so `budget` rows are emitted in total.
        hidden = len(rows) - (budget - 1)
        rows = rows[: budget - 1]
        rows.append(Row(cells=[Cell(text=f"… +{hidden} lines", color=ColorRole.HEADER)]))
    return rows
```

Vérifier que `Cell`, `Row` et `ColorRole` sont bien tous importés dans le module (ils le sont pour `Cell` et `Row` ; ajouter `ColorRole` s'il manque).

- [ ] **Step 4: Lancer les tests**

Run: `python -m pytest tests/test_plugin_amps_render_curses_v5.py -v`
Expected: PASS

- [ ] **Step 5: Stager**

```bash
git add glances/plugins/amps/render_curses_v5.py tests/test_plugin_amps_render_curses_v5.py
```

---

### Task 7: Câblage — `_body_geometry` et `_fit_right_column`

C'est ici que la hauteur du terminal entre dans le pipeline de rendu.

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py` (`_repaint` ~ligne 494, `_build_fitted_frame` ~ligne 570, `_build_view` ~ligne 680, `_paint` ~ligne 707)
- Test: `tests/test_curses_v5.py`

**Interfaces:**
- Consomme : `plan_right_column` (Task 2), `PluginBlock.data_count` (Task 1).
- Produit :
  - `TuiV5._body_geometry(frame: Frame, max_y: int) -> tuple[int, int]` — `(body_y0, body_height)`.
  - `TuiV5._fit_right_column(view: dict, frame: Frame, max_y: int) -> Frame`.
  - `_build_fitted_frame(max_x: int, max_y: int | None = None) -> Frame` (le défaut `None` garde les appels de test existants valides).

- [ ] **Step 1: Écrire les tests**

Dans `tests/test_curses_v5.py` :

```python
def _tui_with(store, alerts, config, registry, fields):
    from glances.outputs import glances_curses_v5 as tui_mod

    return tui_mod.TuiV5(
        store=store, alerts=alerts, config=config,
        registry=registry, fields_by_plugin=fields, refresh_interval=0.01,
    )


def test_body_geometry_matches_what_paint_computes(fake_store, fake_alerts, fake_config):
    """Le fitter et le painter doivent partager EXACTEMENT la même géométrie."""
    from glances.outputs.curses_renderer_v5 import Cell, Frame, PluginBlock, Row

    tui = _tui_with(fake_store, fake_alerts, fake_config, [], {})
    frame = Frame()
    frame.header.append(PluginBlock(name="system", rows=[Row(cells=[Cell(text="host")])]))
    frame.top.append(PluginBlock(name="cpu", rows=[Row(cells=[Cell(text="CPU")]) for _ in range(4)]))

    body_y0, body_height = tui._body_geometry(frame, 40)
    # header(1) + sep(1) + top(4) + sep(1)
    assert body_y0 == 7
    assert body_height == 33


def test_body_geometry_without_header_or_top(fake_store, fake_alerts, fake_config):
    from glances.outputs.curses_renderer_v5 import Frame

    tui = _tui_with(fake_store, fake_alerts, fake_config, [], {})
    assert tui._body_geometry(Frame(), 24) == (0, 24)


def test_tall_terminal_shows_more_than_twenty_processes(fake_alerts, fake_config):
    """Règle principale : la processlist remplit le terminal en hauteur."""
    from unittest.mock import MagicMock

    procs = [
        {"pid": 100 + i, "name": f"p{i}", "cmdline": [f"p{i}"], "cpu_percent": 1.0,
         "memory_percent": 1.0, "username": "root", "num_threads": 1, "nice": 0,
         "status": "S", "memory_info": {"vms": 1024, "rss": 512}}
        for i in range(300)
    ]
    store = MagicMock()
    store.as_dict.return_value = {"processlist": {"data": procs, "_levels": {}}}

    tui = _tui_with(store, fake_alerts, fake_config, [("processlist", True)], {"processlist": {}})
    frame = tui._build_fitted_frame(200, 80)
    block = [b for b in frame.right if b.name == "processlist"][0]
    assert block.height > 21


def test_short_terminal_keeps_the_alert_block_visible(fake_alerts, fake_config):
    """Régression corrigée : le bloc alert ne doit plus être écrasé."""
    from unittest.mock import MagicMock

    procs = [
        {"pid": 100 + i, "name": f"p{i}", "cmdline": [f"p{i}"], "cpu_percent": 1.0,
         "memory_percent": 1.0, "username": "root", "num_threads": 1, "nice": 0,
         "status": "S", "memory_info": {"vms": 1024, "rss": 512}}
        for i in range(300)
    ]
    store = MagicMock()
    store.as_dict.return_value = {"processlist": {"data": procs, "_levels": {}}}
    fake_alerts.get_history.return_value = [
        {"ts": f"2026-08-05T10:{i:02d}:00+00:00", "plugin": "cpu", "key": None,
         "field": "total", "level": "warning", "previous_level": "ok"}
        for i in range(20)
    ]

    tui = _tui_with(store, fake_alerts, fake_config, [("processlist", True)], {"processlist": {}})
    frame = tui._build_fitted_frame(200, 24)
    _, body_height = tui._body_geometry(frame, 24)

    total = sum(b.height for b in frame.right if b.rows)
    total += max(0, len([b for b in frame.right if b.rows]) - 1)
    assert total <= body_height, "la colonne droite déborde du corps"
    assert any(b.name == "alert" and b.rows for b in frame.right)


def test_right_column_never_overflows_across_heights(fake_alerts, fake_config):
    """Invariant : quelle que soit la hauteur, le plan tient dans le corps."""
    from unittest.mock import MagicMock

    procs = [
        {"pid": 100 + i, "name": f"p{i}", "cmdline": [f"p{i}"], "cpu_percent": 1.0,
         "memory_percent": 1.0, "username": "root", "num_threads": 1, "nice": 0,
         "status": "S", "memory_info": {"vms": 1024, "rss": 512}}
        for i in range(300)
    ]
    containers = [
        {"name": f"ctr{i}", "status": "running", "cpu_percent": 1.0,
         "memory_usage_no_cache": 1024, "memory_limit": 4096}
        for i in range(25)
    ]
    store = MagicMock()
    store.as_dict.return_value = {
        "processlist": {"data": procs, "_levels": {}},
        "containers": {"data": containers, "_levels": {}, "disable_stats": []},
    }
    fake_alerts.get_history.return_value = []

    tui = _tui_with(
        store, fake_alerts, fake_config,
        [("processlist", True), ("containers", True)],
        {"processlist": {}, "containers": {}},
    )
    for max_y in range(12, 81):
        frame = tui._build_fitted_frame(200, max_y)
        _, body_height = tui._body_geometry(frame, max_y)
        visible = [b for b in frame.right if b.rows]
        total = sum(b.height for b in visible) + max(0, len(visible) - 1)
        assert total <= body_height, f"débordement à max_y={max_y}: {total} > {body_height}"
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `python -m pytest tests/test_curses_v5.py -k "body_geometry or tall_terminal or short_terminal or never_overflows" -v`
Expected: FAIL — `AttributeError: 'TuiV5' object has no attribute '_body_geometry'`

- [ ] **Step 3: Extraire `_body_geometry` de `_paint`**

Ajouter la méthode dans `glances_curses_v5.py`, juste avant `_paint` :

```python
    def _body_geometry(self, frame: Frame, max_y: int) -> tuple[int, int]:
        """Return ``(body_y0, body_height)`` — the region below the top row.

        Single source of truth shared by the painter and by the vertical fit
        pass: the RIGHT column budget is computed against the very same
        height the painter will honour.
        """
        header_height = max((b.height for b in frame.header), default=0)
        y = header_height + (1 if header_height else 0)
        top_height = max((b.height for b in frame.top), default=0)
        y += top_height + (1 if top_height else 0)
        return (y, max(0, max_y - y))
```

Puis réécrire `_paint` pour l'utiliser (les hauteurs peintes sont identiques à celles mesurées : `_paint_header` et `_paint_top_row` renvoient déjà le max des hauteurs de blocs) :

```python
    def _paint(self, stdscr, frame: Frame) -> None:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # 0. Header line (system flush-left, uptime flush-right).
        header_height = self._paint_header(stdscr, frame.header, 0, max_x)

        # 0b. Separator between the header and the top row (v4 parity).
        top_y0 = header_height
        if header_height > 0 and top_y0 < max_y:
            self._paint_separator(stdscr, top_y0, 0, max_x)
            top_y0 += 1

        # 1. Top row, below the header (and its separator).
        top_height = self._paint_top_row(stdscr, frame.top, top_y0, max_x)

        # 2. Separator under the top row (if any top content was painted).
        if top_height > 0 and top_y0 + top_height < max_y:
            self._paint_separator(stdscr, top_y0 + top_height, 0, max_x)

        # 3. Below the top row: left + right sidebars side-by-side. The
        # geometry comes from `_body_geometry` so the painter and the vertical
        # fit pass can never disagree on the available height.
        body_y0, body_height = self._body_geometry(frame, max_y)
        if body_height > 0:
            left_width = self._sidebar_split(frame, max_x)
            right_x = left_width + self._SIDEBAR_SEPARATOR_GAP
            right_width = max(0, max_x - right_x)

            self._paint_sidebar(stdscr, frame.left, body_y0, 0, left_width, body_height)
            self._paint_sidebar(stdscr, frame.right, body_y0, right_x, right_width, body_height)
```

- [ ] **Step 4: Lancer les tests de géométrie**

Run: `python -m pytest tests/test_curses_v5.py -k body_geometry -v`
Expected: PASS. Lancer aussi tout le fichier pour confirmer qu'aucun test de peinture existant ne casse :
`python -m pytest tests/test_curses_v5.py -v`

- [ ] **Step 5: Stager l'extraction**

```bash
git add glances/outputs/glances_curses_v5.py tests/test_curses_v5.py
```

- [ ] **Step 6: Ajouter le budget nominal à `_build_view`**

Pour que le premier frame de chaque cycle ne rende pas 300 processus et 200 containers qui seront jetés, `_build_view` publie d'emblée un budget de coût borné, que le solveur corrigera. Ajouter la constante près de `_QUICKLOOK_COMPACT_WIDTH` :

```python
    # Pre-fit row budget: a cost bound only. The vertical fit pass replaces it
    # with the exact, height-driven budget — but without it the first frame of
    # every cycle would render every process and every container just to throw
    # the rows away.
    _PREFIT_ROW_BUDGET = {
        "vms": 10,
        "containers": 10,
        "processlist": 20,
        "programlist": 20,
        "alert": 10,
    }
```

et, en fin de `_build_view` :

```python
        view["row_budget"] = dict(self._PREFIT_ROW_BUDGET)
        return view
```

- [ ] **Step 7: Implémenter `_fit_right_column`**

Ajouter l'import en tête du module :

```python
from glances.outputs.curses_renderer_v5 import (
    ...,
    plan_right_column,
)
```

Puis la méthode, juste après `_fit_proclist_width` :

```python
    # RIGHT-column blocks whose height the vertical budget controls. Anything
    # else in the column (currently `processcount`) is non-elastic.
    _ELASTIC_RIGHT = frozenset({"vms", "containers", "processlist", "programlist", "alert", "amps"})

    def _fit_right_column(self, view: dict[str, Any], frame: Frame, max_y: int) -> Frame:
        """Give each RIGHT-column block the number of rows the terminal height
        allows, then rebuild once if that changes anything.

        Mirrors ``_fit_proclist_width`` on the vertical axis: the plan is
        computed by the pure ``plan_right_column`` solver from the real item
        counts (``PluginBlock.data_count``), so a single rebuild settles it.
        """
        _, body_height = self._body_geometry(frame, max_y)
        if body_height <= 0:
            return frame

        by_name = {b.name: b for b in frame.right}

        def count(name: str) -> int:
            block = by_name.get(name)
            return block.data_count or 0 if block else 0

        # processlist and programlist are mutually exclusive — exactly one is
        # in the frame at any time (see `_frame_for_view`).
        n_processes = count("processlist") or count("programlist")
        plan = plan_right_column(
            body_height=body_height,
            static_heights={b.name: b.height for b in frame.right if b.name not in self._ELASTIC_RIGHT},
            amps_height=by_name["amps"].height if "amps" in by_name else 0,
            n_vms=count("vms"),
            n_containers=count("containers"),
            n_processes=n_processes,
            n_alerts=count("alert"),
        )

        current = view.get("row_budget") or {}
        # Compare the EFFECTIVE row counts, not the raw quotas: a quota above
        # the item count renders exactly the same block, and rebuilding for
        # that would cost one extra frame on every single cycle.
        def effective(budget: dict[str, int], name: str) -> int:
            available = count(name) if name != "amps" else (by_name["amps"].height if "amps" in by_name else 0)
            quota = budget.get(name)
            return available if quota is None else min(available, quota)

        names = set(plan) | set(current)
        if all(effective(plan, n) == effective(current, n) for n in names):
            return frame

        view["row_budget"] = plan
        return self._frame_for_view(view)
```

- [ ] **Step 8: Câbler `max_y` dans le pipeline**

`_repaint` :

```python
        else:
            max_y, max_x = stdscr.getmaxyx()
            frame = self._build_fitted_frame(max_x, max_y)
            self._paint(stdscr, frame)
```

`_build_fitted_frame` — nouvelle signature et nouvelle étape finale, sur les **deux** chemins de retour :

```python
    def _build_fitted_frame(self, max_x: int, max_y: int | None = None) -> Frame:
        view = self._build_view(max_x)
        frame = self._frame_for_view(view)
        if self._full_quicklook or self._top_fits(frame, max_x):
            frame = self._fit_header(view, frame, max_x)
            frame = self._fit_proclist_width(view, frame, max_x)
            return frame if max_y is None else self._fit_right_column(view, frame, max_y)
        for key, val in _DEGRADE_STEPS:
            view[key] = val
            frame = self._frame_for_view(view)
            if self._top_fits(frame, max_x):
                break
        frame = self._fit_header(view, frame, max_x)
        frame = self._fit_proclist_width(view, frame, max_x)
        return frame if max_y is None else self._fit_right_column(view, frame, max_y)
```

⚠️ L'ordre est impératif : le fit vertical vient **après** le fit horizontal, car `body_height` dépend de la hauteur de la top row, elle-même figée par la cascade de dégradation horizontale.

- [ ] **Step 9: Lancer les tests d'intégration**

Run: `python -m pytest tests/test_curses_v5.py -v`
Expected: PASS. `test_right_column_never_overflows_across_heights` est l'invariant qui compte : s'il échoue à une hauteur donnée, le solveur et le painter ne sont pas d'accord sur le coût d'un agencement — corriger `cost()` dans `plan_right_column`, pas le test.

- [ ] **Step 10: Stager**

```bash
git add glances/outputs/glances_curses_v5.py tests/test_curses_v5.py
```

---

### Task 8: Validation globale

**Files:**
- Aucun fichier source modifié — vérification seule (sauf correctif révélé par la suite).

- [ ] **Step 1: Lancer la suite complète**

Run: `python -m pytest tests/ -q`
Expected: 0 échec. Toute régression provient nécessairement d'un test qui figeait l'ancien comportement (par exemple un test attendant exactement 20 processus ou tous les containers) — dans ce cas, mettre le test à jour en documentant en commentaire que la valeur est désormais pilotée par la hauteur, et vérifier que le changement est bien intentionnel au regard du spec.

- [ ] **Step 2: Vérifier l'absence de code mort**

Run: `grep -rn "row_budget\|plan_right_column\|data_count\|_body_geometry\|_fit_right_column" glances/ --include=*.py`
Expected: chaque symbole défini a au moins un appelant hors tests. `_MAX_ROWS` doit rester référencé (valeur de repli).

- [ ] **Step 3: Pre-commit**

Run: `make pre-commit`
Expected: tous les hooks passent. gitleaks scanne l'index — restager (`git add -u`) avant de relancer si un hook a reformaté un fichier.

- [ ] **Step 4: Stager l'état final**

```bash
git add -u
git status --short
```

- [ ] **Step 5: Smoke test manuel — à la charge du mainteneur**

Le seul juge de paix. Lancer le serveur v5 et sa TUI :

```bash
python -m glances.main_v5
```

Vérifier, en redimensionnant la fenêtre en continu :

1. Terminal haut (≥ 60 lignes) : plus de 20 processus, la liste descend jusqu'en bas sans laisser de bande vide.
2. Terminal court (24 lignes) : le bloc `ALERT` reste visible, au moins 5 processus restent affichés.
3. Terminal très court (< 16 lignes) : dégradation progressive, jamais de bloc à moitié peint ni de trace curses.
4. Avec containers/VMs : compteur `CONTAINER n/N` présent uniquement quand la liste est coupée, colonnes alignées.
5. Avec un AMP verbeux (`[amp_test]` avec un script qui produit 30 lignes) : les AMPs restent entiers tant qu'il y a la place, et la processlist ne disparaît jamais.
6. Bascule `j` (programlist) et `1` (percpu) : le budget se recalcule sans clignotement.

**Ne pas commiter.** Laisser l'arbre stagé pour le mainteneur.
