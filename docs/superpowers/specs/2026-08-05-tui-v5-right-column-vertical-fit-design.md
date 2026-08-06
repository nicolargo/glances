# TUI v5 — Dynamicité verticale de la colonne de droite

- **Date** : 2026-08-05
- **Branche** : `develop-v5`
- **Statut** : design validé, prêt pour le plan d'implémentation
- **Périmètre** : colonne droite de la TUI v5 uniquement (`RIGHT_SLOT`). La
  colonne gauche, le header et la top row sont inchangés.

---

## 1. Problème

La colonne droite de la TUI v5 empile ses blocs et laisse curses clipper ce qui
dépasse (`glances/outputs/glances_curses_v5.py:862`, `_paint_sidebar`). Trois
conséquences :

1. **Le bloc `alert` disparaît** dès que la colonne est chargée : il est le
   dernier de `RIGHT_SLOT`, donc le premier sacrifié par le clipping.
2. **La processlist est figée à 20 lignes** (`_MAX_ROWS`,
   `glances/plugins/processlist/render_curses_v5.py:64`) quelle que soit la
   hauteur du terminal : 20 processus sur un écran de 24 lignes comme sur un
   écran de 80.
3. **`containers`, `vms` et `amps` ne sont pas bornés du tout** : 30 containers
   écrasent tout ce qui suit.

L'axe horizontal a déjà sa réponse — la cascade de dégradation `_DEGRADE_STEPS`
et l'injection de `view["proclist_width"]`. L'axe vertical n'a rien.

v4 traitait partiellement le problème, pour la seule processlist :
`max_y = hauteur_écran − Σ(hauteurs des plugins situés APRÈS elle) − 2`
(`glances/outputs/glances_curses.py:960`).

## 2. Objectif

La colonne droite s'adapte à la hauteur disponible dans les deux sens :
elle se rogne proprement, selon un ordre de sacrifice explicite, quand la place
manque ; elle s'étend quand il y a du surplus.

## 3. Règles métier validées

| # | Règle | Décision |
|---|---|---|
| R1 | AMPs | Toutes les lignes affichées. Rognés **uniquement** au dernier palier de la cascade, pour garantir qu'il reste toujours au moins un processus visible. |
| R2 | Workloads (`vms` + `containers`) | Budget **commun** — pas 10 chacun. Nominal 10 lignes, extensible à 20 sur écran haut. Compteur de troncature dans l'en-tête. |
| R3 | Alertes | Nominal 10, les plus récentes en tête. Aucun marqueur (le compteur est déjà dans `ALERT (n ongoing / n total)`). Le mécanisme existe déjà (`alerts_limit`) ; seule sa valeur devient dynamique. |
| R4 | Processus | Bloc élastique : absorbe tout le surplus. Plancher **5**, rompu seulement aux paliers `i` et `k`. |
| R5 | Répartition vms/containers | Équité max-min : part égale, puis le reliquat inutilisé est reversé à l'autre. |

## 4. Architecture

### 4.1 Approche retenue

Le budget est **calculé au build et injecté dans `view`**, symétrique exacte de
`_fit_proclist_width` → `view["proclist_width"]`.

Les deux alternatives ont été écartées :

- **Troncature au paint** (`_paint_sidebar` coupe les `rows`) : la processlist
  resterait plafonnée à 20 lignes — on ne peut que couper, jamais étendre —, ce
  qui rend R4 inatteignable. Et le compteur `CONTAINER 7/20` est impossible : le
  painter ne manipule que des `Cell` opaques, sans sémantique.
- **Hybride** (budget au build pour la processlist, troncature au paint pour le
  reste) : deux mécanismes pour un seul problème, marqueur toujours impossible.

### 4.2 Géométrie

`_build_fitted_frame(max_x)` ne reçoit aujourd'hui que la largeur ; `_repaint`
(`glances_curses_v5.py:494`) jette `max_y`. Et la hauteur du corps n'est connue
qu'après la peinture du header et de la top row, c'est-à-dire dans `_paint`.

Changements :

1. Extraire de `_paint` une fonction pure :

   ```python
   def _body_geometry(frame: Frame, max_y: int) -> tuple[int, int]:
       """(body_y0, body_height) — géométrie du corps sous la top row."""
   ```

   ```
   body_y0     = header_height + (1 si header) + top_height + (1 si top)
   body_height = max(0, max_y - body_y0)
   ```

   `_paint` l'appelle au lieu de recalculer inline : une seule définition de la
   géométrie, partagée par le fitter et le painter.

2. `_repaint` transmet `max_y` : `_build_fitted_frame(max_x, max_y)`.

3. `_build_fitted_frame` gagne une 4ᵉ étape, **après** le fit de largeur —
   l'ordre compte, `body_height` dépend de la hauteur de la top row, elle-même
   figée par la cascade horizontale :

   ```
   _fit_top_row         (existant, cascade a→f)
   _fit_header          (existant)
   _fit_proclist_width  (existant)
   _fit_right_column    (NOUVEAU) → 0 ou 1 rebuild
   ```

**Absence de rétroaction** : le budget vertical ne modifie que le nombre de
lignes des blocs de droite. `_sidebar_split` ne dépend que de `frame.left`, et
`proclist_width` en découle — la largeur est donc déjà figée quand le vertical
se résout. Une seule passe, jamais d'oscillation.

### 4.3 Mesure des effectifs

Le solveur est analytique, pas itératif : il lui faut les effectifs réels, or un
bloc déjà tronqué ne les révèle pas.

`build_frame` attache donc à chaque `PluginBlock` un champ générique :

```python
@dataclass
class PluginBlock:
    name: str
    rows: list[Row] = field(default_factory=list)
    data_count: int | None = None   # len(payload["data"]) pour les collections
```

Renseigné par `build_frame` pour les plugins collection, et explicitement pour
le bloc `alert` synthétisé (`len(history)`). **Aucun renderer à modifier** : le
calcul vit dans la couche qui manipule déjà les payloads.

### 4.4 Le solveur

Fonction **pure**, sans dépendance curses, dans `curses_renderer_v5.py` :

```python
def plan_right_column(
    *,
    body_height: int,
    static_heights: dict[str, int],   # blocs non élastiques présents, ex. {"processcount": 1}
    amps_height: int,                 # 0 si le bloc amps est absent
    n_vms: int,
    n_containers: int,
    n_processes: int,
    n_alerts: int,
) -> dict[str, int]:
```

Les séparateurs **ne sont pas pré-calculés** par l'appelant : leur nombre dépend
du jeu de blocs visibles, qui dépend lui-même du quota (le palier `g` masque les
workloads et supprime donc un séparateur). Le solveur les recompte à chaque
palier évalué.

**Coût d'un agencement** — `_paint_sidebar` insère une ligne vide entre deux
blocs :

```
total = Σ hauteur(bloc visible) + (nb_blocs_visibles − 1)

hauteur(containers)   = 1 + min(n, quota)     # 0 si quota == 0 → bloc absent
hauteur(vms)          = 1 + min(n, quota)     # 0 si quota == 0 → bloc absent
hauteur(processlist)  = 1 + min(n, quota)
hauteur(alert)        = 1 + min(n, quota)     # 1 si quota == 0 → en-tête seul
hauteur(processcount) = 1                     # jamais rogné
hauteur(amps)         = naturelle, sauf palier j
```

**État nominal** — reproduit exactement le comportement actuel :

```
workloads 10 · alertes 10 · processus 20
```

**Paliers de croissance**, appliqués tant qu'il reste du surplus :

| | Palier | Effet |
|---|---|---|
| A | workloads 10 → 20 | |
| B | processus 20 → ∞ | absorbe tout le reste |

**Paliers de réduction**, appliqués dans l'ordre jusqu'à ce que l'agencement
tienne dans `body_height` :

| | Palier | | | Palier |
|---|---|---|---|---|
| a | workloads 10 → 5 | | g | workloads 3 → 0 *(bloc masqué)* |
| b | alertes 10 → 5 | | h | alertes 3 → 0 *(en-tête seul)* |
| c | processus 20 → 10 | | i | processus 5 → 3 |
| d | workloads 5 → 3 | | j | amps → reste, marqueur `+N` |
| e | alertes 5 → 3 | | k | processus 3 → 1 |
| f | processus 10 → 5 | | | *au-delà : curses clippe* |

Un palier visant un bloc absent est un no-op : on passe au suivant sans
consommer de « tour ».

**Répartition du quota workloads** (R5, équité max-min) :

```
part = quota // 2
attribué(vms)        = min(n_vms, part)
attribué(containers) = min(n_containers, part)
reliquat = quota − attribué(vms) − attribué(containers)
   → reversé au bloc qui en veut encore (les deux si le reliquat le permet)
```

Exemples :

```
3 vms + 20 containers, quota 10  →  vms 3,  containers 7
12 vms + 12 containers, quota 10 →  vms 5,  containers 5
0 vms + 30 containers, quota 10  →  containers 10
```

**Sortie** — un dict plat `plugin → nb max de lignes de données` (hors ligne
d'en-tête) :

```python
{"vms": 3, "containers": 7, "processlist": 34, "programlist": 34, "alert": 10}
```

Une clé absente signifie « aucune contrainte ». `amps` n'apparaît qu'au palier
`j`.

### 4.5 Contrat des renderers

Canal unique et générique : `view["row_budget"]`. Helper partagé dans
`curses_renderer_v5.py` pour que chaque renderer ne change que d'une ligne :

```python
def row_budget(view: dict | None, plugin_name: str, default: int | None) -> int | None:
    """Nb max de lignes de données pour `plugin_name`, `default` si non contraint."""
```

| Renderer | Changement | Sémantique de `0` |
|---|---|---|
| `processlist` | `items[:_MAX_ROWS]` → `items[:row_budget(view, "processlist", _MAX_ROWS)]` (`render_curses_v5.py:407`) | n/a — plancher 1 |
| `programlist` | idem, `_MAX_ROWS` local (`render_curses_v5.py:109`) | n/a — plancher 1 |
| `containers` | tronque `items` + compteur d'en-tête | retourne `[]` → bloc absent |
| `vms` | tronque `items` + compteur d'en-tête | retourne `[]` → bloc absent |
| `amps` | tronque + ligne marqueur | n/a |
| `alert` | pas un renderer de plugin : `build_frame` lit le budget et le passe en `limit=` à `render_alert_block` | en-tête seul |

`_MAX_ROWS = 20` reste en place comme valeur nominale de repli : sans
`row_budget` (export, tests headless), la sortie est identique à aujourd'hui au
bit près.

**Piège à désamorcer** : `render_alert_block` fait `history[-limit:]`
(`curses_renderer_v5.py:562`). Avec `limit=0`, `history[-0:]` renvoie **tout
l'historique**. Le palier `h` doit court-circuiter explicitement, pas se
reposer sur le slice.

### 4.6 Marqueur de troncature

**Workloads** — compteur dans l'en-tête de la colonne nom, présent uniquement
quand la liste est tronquée :

```
CONTAINER 7/20   Status  Uptime   CPU%     MEM/MAX
Name 3/12        Status  Uptime   CPU%   …            ← bloc vms
```

`name_w = max(name_w, len(label))` quand le compteur est présent, sinon toutes
les colonnes suivantes se décalent. Non tronqué → libellé nu (`CONTAINER`,
`Name`), sortie inchangée.

**AMPs**, palier `j` uniquement — ligne marqueur consommant la dernière ligne du
budget. Le budget `amps` compte **toutes** les lignes du bloc, marqueur inclus :
un budget de `N` laisse donc `N − 1` lignes de contenu.

```
… +12 lines
```

**Alertes** — aucun marqueur : `ALERT (2 ongoing / 27 total)` porte déjà
l'information.

**Processus** — aucun marqueur : le bloc `processcount` (`TASKS 412 (1523 thr)`)
porte déjà le total, et v4 n'en a jamais eu.

## 5. Tests

**Solveur pur** (`tests/test_curses_renderer_v5.py`, aucun curses) :

- nominal atteint dès que la hauteur le permet ;
- **un test par palier `a`→`k`**, déclenché en réduisant `body_height` d'une
  ligne à la fois → vérifie l'ordre exact de la cascade ;
- paliers de croissance `A` et `B` ;
- répartition max-min : `(3, 20, 10) → (3, 7)`, `(12, 12, 10) → (5, 5)`,
  un seul bloc présent → prend tout ;
- no-op sur bloc absent (pas de « tour » consommé).

**Cohérence géométrie ↔ painter** — l'invariant qui compte : *le frame planifié
ne dépasse jamais `body_height`*. Test sur `stdscr` factice, balayage des
hauteurs 10 → 80.

**Non-régression renderers** — `row_budget` absent ⇒ sortie identique à
aujourd'hui (même verrou que `test_no_width_keeps_all_columns`).

**Cas piégeux** — `limit=0` sur `render_alert_block` ⇒ 1 ligne, pas l'historique
complet.

**Intégration** — `_build_fitted_frame` sur 80×24 (cascade) et 200×80
(croissance), store synthétique.

**Smoke test manuel** — juge de paix final, à la charge du mainteneur :
`python -m glances.main_v5` sur un terminal redimensionné en continu, avec et
sans containers/vms/AMPs.

## 6. Hors périmètre

- Colonne gauche : inchangée (elle continue de clipper comme aujourd'hui).
- Aucune clé de configuration ajoutée — les valeurs nominales (10 / 10 / 20)
  restent des constantes de module. À reconsidérer seulement si un utilisateur
  le demande.
- `NEWS.rst` : non touché pendant le développement.

## 7. Points à retenir pour le changelog de release

- Sur terminal haut, la TUI affiche désormais **plus de 20 processus** et
  **plus de 10 workloads** — les anciens plafonds deviennent des valeurs
  nominales.
- Sur terminal court, les blocs sont rognés selon un ordre explicite au lieu que
  `alert` disparaisse silencieusement.
- Nouveau compteur `CONTAINER n/N` / `Name n/N` dans l'en-tête des blocs
  tronqués.
