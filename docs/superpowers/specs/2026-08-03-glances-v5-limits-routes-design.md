# Glances v5 — Routes `/limits` (REST + correction MCP)

**Date :** 2026-08-03
**Branche :** `develop-v5`
**Phase :** 2 — complétion de la surface REST
**Statut :** design validé, prêt pour la planification

---

## 1. Problème

v4 expose `/api/4/all/limits` et `/api/4/<plugin>/limits`. La surface REST v5
n'a pas d'équivalent, et le manque n'est enregistré nulle part : ni dans
l'inventaire des routes livrées (architecture §4.6), ni dans la liste des
routes différées. La fonctionnalité a été portée côté MCP et perdue côté REST.

Second problème, révélé par l'analyse : `McpPluginView.get_limits()`
(`glances/outputs/mcp_adapter_v5.py:116`) agrège les `default_thresholds` du
schéma de champ **sans lire la configuration**. La ressource MCP
`glances://limits` annonce donc les valeurs codées en dur même quand
l'opérateur a surchargé un seuil dans `glances.conf`. Le §11.3 la marque ✅ à
tort.

Une seule cause racine — aucune méthode ne résout les seuils effectifs hors du
chemin de calcul des niveaux — et donc un seul correctif.

## 2. Objectifs

1. Exposer `/api/5/all/limits` et `/api/5/<plugin>/limits`, retournant les
   seuils **effectifs** (configuration superposée aux défauts du schéma).
2. Corriger `glances://limits` en le faisant consommer la même source.
3. Fermer par construction la classe de vulnérabilité confirmée sur v4 le
   2026-08-03 (dump de section de configuration via `/limits`).

## 3. Hors périmètre

- L'historique des seuils, et toute route `/history` — pas de buffer en v5.
- L'écriture des seuils (`PUT`/`POST`) — la surface REST v5 est en lecture
  seule tant que la décision sur les routes mutatives (#3548) n'est pas prise.
- Le correctif v4 des endpoints `/limits` et `/config` — traité séparément,
  voir §11.

---

## 4. Architecture

### 4.1 `GlancesPluginBase.get_limits()`

Nouvelle méthode **publique** sur `glances/plugins/plugin/base_v5.py`. Le nom
est libre (aucune collision dans la classe de base ni dans un `model_v5.py`).

La logique de résolution reste dans le plugin ; la route est un passe-plat.
Respect du découpage en couches : la couche I/O ne calcule pas de seuil.

**Calcul à la demande, sans cache.** `_precompute_plugin_thresholds()` est
déjà appelé à chaque cycle par `_derived_parameters` (`base_v5.py:449`), mais
mémoriser son résultat serait un piège : le cache est vide au cycle 0 alors
que les seuils, eux, sont parfaitement connus dès le démarrage — ils viennent
de la configuration et du schéma, pas de psutil. La route est peu sollicitée
et les lectures de configuration sont des accès dictionnaire.

**Propriété qui en découle :** `/limits` n'a pas de sémantique cycle 0.
Contrairement à `/api/5/<plugin>` qui renvoie `200 null` avant la première
collecte (architecture §4.6), `/limits` répond correctement immédiatement.

### 4.2 Source des seuils

`get_limits()` s'appuie sur `_precompute_plugin_thresholds()`
(`base_v5.py:482`), qui retourne pour chaque champ surveillé :

- `{field_name: {"thresholds": {...}}}` — champ numérique
- `{field_name: {"mapping": {...}}}` — champ catégoriel

Détail subtil déjà traité par cette méthode et à préserver : la **clé de
configuration** d'un champ peut différer de son **nom de champ**, via
`threshold_field` (`_threshold_key()`, `base_v5.py:472`). Exemple : le plugin
`containers` stocke la valeur sous `cpu_percent` mais lit ses seuils dans
`[containers] cpu_*`. La sortie est indexée par **nom de champ** — ce que le
client voit dans le payload de stats — tandis que la lecture se fait par clé
de configuration.

### 4.3 Bloc `_per_item`

`_scan_pk_override_fields()` (`base_v5.py:513`) retourne l'ensemble des champs
surveillés portant au moins une clé `<pk>_<field>_<level>` dans la section.
Il est **vide dans le cas courant** : le bloc `_per_item` ne coûte alors rien.

Quand il est non vide, la construction itère les items **présents dans le
store** et résout par `read_thresholds(..., pk_value=item[self._primary_key])`
— exactement le chemin qu'emprunte `_compute_levels_for_item`. Seules les
entrées qui diffèrent du niveau plugin sont retenues.

**Limite assumée :** une surcharge configurée pour un item absent au moment de
l'appel (interface réseau down, conteneur arrêté) n'apparaît pas dans
`_per_item`.

Alternative écartée : reconstruire les valeurs de clé primaire en parsant les
clés `<pk>_<field>_<level>`. Le découpage est ambigu dès que la valeur de pk
contient un underscore, et la liste obtenue ne serait corrélée à aucun item
réel. Le compromis retenu privilégie la justesse de ce qui est retourné sur
l'exhaustivité de ce qui est configuré.

### 4.4 Bloc `_categorical`

Deux plugins déclarent `threshold_type: "categorical"` : `processlist` et
`programlist`, sur les champs `status` et `nice`. Ils pilotent `_levels` au
même titre que les seuils numériques, mais leur forme est inversée — niveau →
ensemble de valeurs, au lieu de niveau → nombre. Les isoler sous
`_categorical` préserve la forme numérique plate au premier niveau.

`amps` et `ports` évoquent le sujet en commentaire mais **surchargent
`_derived_parameters()`** et n'empruntent pas le chemin catégoriel de la
classe de base : ils ne produisent pas de bloc `_categorical`.

Les deux champs concernés sont **opt-in et sans défauts** (`status_ok=R,W,P,I`
à écrire explicitement dans `[processlist]`). Sur un déploiement non
configuré, `_categorical` est donc toujours absent — ce qui rend la règle
« absent quand vide » du §5.1 d'autant plus importante à respecter.

v4 n'avait aucun équivalent : c'est un ajout net de la surface v5.

### 4.5 Sûreté du namespace

Les deux clés préfixées ne peuvent entrer en collision avec un nom de champ :
`_remove_parameters()` (`base_v5.py:674`) supprime toute clé `_*` des stats,
donc aucun champ déclaré ne commence par un underscore.

### 4.6 Limitation connue — plugins hors du chemin `_watched_fields`

`get_limits()` ne parcourt que `_precompute_plugin_thresholds()`, alimenté par
`_watched_fields`. Six plugins — `sensors`, `wifi`, `folders`, `raid`, `ports`,
`amps` — **surchargent `_derived_parameters()`** et calculent `_levels` en
dehors de ce chemin (voir déjà §4.4 pour `amps`/`ports` côté catégoriel). Pour
ces six plugins, `get_limits()` renvoie `{}` même quand des seuils opérateur
sont actifs et pilotent réellement les couleurs affichées.

C'est une limitation documentée, pas un bug de cette spec : corriger cela
supposerait un point d'extension par plugin (`get_limits()` surchargeable),
ce qui est un suivi délibéré, hors périmètre de cette itération (§3).

---

## 5. Contrat des routes

```
GET /api/5/all/limits        → {plugin: <payload>, ...}
GET /api/5/<plugin>/limits   → <payload>
```

| Cas | Réponse |
|---|---|
| Plugin enregistré, champs surveillés | `200` + payload |
| Plugin enregistré, aucun champ surveillé (`now`, `version`) | `200 {}` |
| Plugin non enregistré | `404` |
| Nom réservé (`all`, `config`, `token`…) sur la route dynamique | `404` |
| Avant le premier cycle du scheduler | `200` + payload complet |

`/all/limits` **omet** les plugins dont les limites sont vides — cohérent avec
`getAllLimitsAsDict()` existant.

Authentification : politique per-config, comme toutes les routes `/api/5/*`.
Aucune exemption, aucune entrée dans `UNAUTH_PATHS`.

### 5.1 Payload

```jsonc
{
  "bytes_recv": {"careful": 70.0, "warning": 80.0, "critical": 90.0},
  "bytes_sent": {"careful": 70.0, "warning": 80.0, "critical": 90.0},

  "_per_item": {
    "wlan0": {"bytes_recv": {"careful": 40.0, "warning": 60.0}}
  },

  "_categorical": {
    "status": {"ok": ["I", "R", "S"], "critical": ["D", "Z"]}
  }
}
```

(Le bloc `_categorical` illustré ici vient de `processlist` ; il ne coexiste
pas avec les champs réseau du même exemple — les trois blocs sont réunis pour
montrer la forme complète.)

`_per_item` et `_categorical` sont **absents** quand vides, jamais présents à
`{}`.

### 5.2 Ordre de déclaration — contrainte bloquante

FastAPI résout les routes dans l'ordre de déclaration. `/all/limits` doit être
enregistrée **avant** `/{plugin_name}/limits`, faute de quoi le handler
dynamique capture `all` comme nom de plugin.

`_RESERVED_NAMES` (`routes_v5.py:57`) contient déjà `all` et `_resolve_plugin()`
lève un 404 dessus — mais c'est une ceinture, pas la bretelle. L'ordre reste la
protection primaire, et le test associé (§8) le verrouille.

---

## 6. Correction MCP

`McpPluginView` reçoit aujourd'hui `schema=plugin._fields` sans référence au
plugin, ce qui l'empêche structurellement de résoudre la configuration.

Modification :

1. Ajouter un paramètre `plugin: GlancesPluginBase | None = None` au
   constructeur de `McpPluginView`.
2. Le renseigner sur les deux sites de construction avec un plugin réel :
   `mcp_adapter_v5.py:174` (`getAllLimitsAsDict`) et `:199` (`get_plugin`).
3. `get_limits()` délègue à `self._plugin.get_limits()`, et retourne `{}`
   quand `_plugin is None`.

`getAllLimitsAsDict()` se corrige seul : il itère déjà sur `view.get_limits()`.
Le plugin synthétique `alert` n'a pas de plugin réel — comportement inchangé.

Résultat : REST et MCP partagent une source de vérité unique.

---

## 7. Invariant de sécurité

`/limits` n'expose que trois catégories de données :

1. des **noms de champs** issus de `fields_description` — contrôlés par le code ;
2. des **noms de niveaux** — `careful`, `warning`, `critical` ;
3. les **valeurs** des clés de configuration de forme `<field>_<level>`,
   `<pk>_<field>_<level>` ou `<level>`.

L'espace de clés lu est **clos et contrôlé par le code**. Aucune clé de
configuration arbitraire ne peut atteindre le payload : ni `*_action`, ni
`*_log`, ni `refresh`, ni `disable`.

C'est l'écart déterminant avec v4, dont `load_limits()`
(`glances/plugins/plugin/model.py:737-746`) recopie la section entière et dont
les routes `/limits` la restituent sans sanitisation — fuite confirmée
empiriquement le 2026-08-03.

**Cet invariant est une contrainte de conception, pas une observation.** Toute
évolution ultérieure qui élargirait `/limits` vers un dump de section de
configuration réintroduirait la vulnérabilité et doit être refusée en revue.

Corollaire : aucune redaction n'est nécessaire sur ces routes, et aucune ne
doit être ajoutée — elle donnerait l'illusion trompeuse que le payload peut
contenir un secret.

---

## 8. Tests

### 8.1 `get_limits()` — unitaires

- surcharge de configuration prioritaire sur `default_thresholds`
- fallback sur `default_thresholds` quand la section ne configure rien
- superposition partielle : un seul niveau surchargé, les autres au défaut
- `threshold_field` : lecture par clé de configuration, sortie par nom de champ
- plugin sans champ surveillé → `{}`
- `_per_item` absent quand aucune surcharge `<pk>_*` n'est configurée
- `_per_item` présent et correct quand une surcharge existe pour un item du store
- `_categorical` sérialisable en JSON et **trié** (payload déterministe)
- `_categorical` absent pour un plugin purement numérique

### 8.2 Routes

- `/api/5/all/limits` n'est pas capturée par `/{plugin_name}/limits`
- `404` sur plugin inconnu
- `404` sur nom réservé (`/api/5/config/limits`)
- réponse complète **avant** le premier cycle du scheduler
- `/all/limits` omet les plugins sans seuils
- politique d'authentification per-config appliquée

### 8.3 MCP — non-régression

- `glances://limits` reflète une surcharge de configuration (test qui échoue
  sur le code actuel : c'est le verrou du bug corrigé en §6)
- `glances://limits/{plugin}` idem sur un plugin isolé
- plugin synthétique `alert` → `{}`

---

## 9. Pièges d'implémentation

1. **`read_thresholds_categorical()` retourne `dict[str, set[str]]`**
   (`thresholds_v5.py:206`). Les `set` ne sont pas sérialisables en JSON —
   FastAPI lèvera à la sérialisation. Conversion en listes **triées**
   obligatoire ; le tri rend le payload déterministe, donc testable.

2. **`_precompute_plugin_thresholds()` mélange deux formes** dans son
   dictionnaire de sortie : `{"thresholds": …}` et `{"mapping": …}`.
   `get_limits()` doit dispatcher sur la présence de ces clés, pas sur
   `schema.get("threshold_type")` — les deux sont cohérents aujourd'hui, mais
   la clé de sortie est la source de vérité de cette méthode.

3. **`_per_item` ne doit pas re-résoudre les champs hors surcharge.** Le
   court-circuit par `_scan_pk_override_fields()` est ce qui évite de rejouer
   `read_thresholds` pour 500+ process. Le contourner ferait de `/limits` une
   route coûteuse sur `processlist`.

---

## 10. Documentation à mettre à jour

- architecture §4.6 — ajouter les deux routes au tableau d'inventaire
- architecture §11.3 — corriger le statut de `glances://limits` (✅ actuel
  erroné) et le remettre à ✅ une fois §6 livré
- `docs/api/restful.rst` est **auto-généré** depuis le chemin de code v4
  (`make docs`) — ne jamais l'éditer à la main ; il n'y a rien à y ajouter
  pour cette spec.

## 11. Dépendance externe

Le correctif v4 des fuites `/limits` et `/config` est **indépendant** de cette
spec et ne la bloque pas. Il fait l'objet d'un rapport séparé, à traiter comme
correctif 4.5.x. Le seul lien : `glances/config_v5.py::as_dict_secure()` doit
recevoir la même extension de regex que son homologue v4 (ajout de `action` au
motif de clés sensibles) — cette modification concerne `/api/5/config`, pas les
routes de cette spec.
