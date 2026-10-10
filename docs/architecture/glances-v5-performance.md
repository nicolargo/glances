# Glances v5 — mesure de performance v4 / v5

**Date :** 2026-10-06 · **Branche :** `develop-v5` (`0632920`) · **Exigence :**
checklist de fusion §1, « pas de régression de la latence de rafraîchissement
par rapport à v4 ».

## Résultat

**Pas de régression de latence.** Un cycle complet de collecte est 2,3 fois
plus rapide en v5, l'API répond 1,6 à 1,8 fois plus vite et le serveur
démarre 4 fois plus vite, avec 25 % de mémoire en moins.

**La consommation CPU est plus élevée, pour deux raisons connues et non pour
un surcoût par rafraîchissement.** Le coût d'un rafraîchissement est le même
(environ 0,025 à 0,028 seconde de CPU dans les deux versions) :

1. un serveur v4 ne collecte que quand on l'interroge, un serveur v5 collecte
   en continu (décision de conception, `--cached-time` retiré, §10) : au repos
   le serveur v5 consomme 1,6 % d'un cœur contre 0,2 % ;
2. la v4 saute des rafraîchissements : avec `refresh=2`, elle a reconstruit
   la liste des processus 6 fois en 20 s, la v5 10 fois. Le minuteur de
   chaque plugin v4 dure exactement l'intervalle de la boucle et n'est
   souvent pas encore écoulé quand elle repasse. La v5 rafraîchit au rythme
   configuré : elle fait plus de travail parce qu'elle fait ce qui est
   demandé.

Dès qu'un client lit le serveur (une WebUI ouverte), l'écart tombe à
0,4 point de pourcentage d'un cœur (2,1 % contre 1,7 %).

**Mode repos (2026-10-10).** En mode serveur sans module d'export, le
scheduler ralentit les plugins d'un facteur `[global] idle_refresh_factor`
(défaut 5, `1` désactive) après 30 s sans requête cliente authentifiée (hors
`/status`, `/healthz`, `/api/5/token`). La requête suivante les réveille
aussitôt. Mesure rapide sur une VM de 4 cœurs : 1,6 % → 0,5 % d'un cœur au
repos. Contrepartie : l'historique est moins dense et les alertes plus lentes
tant qu'aucun client n'est connecté. À refaire avec `bench_v4_v5.py` (la
fenêtre « repos » de 10 s de chauffe est avant le seuil de 30 s : utiliser
`--warmup 35`).

## Mesures

Machine : VM Linux, 4 vCPU, 15,7 Go, Python 3.11.15, psutil 7.2.2 ; même
`conf/glances.conf` pour les deux versions ; médiane de 3 exécutions (les
trois exécutions sont stables : écart inférieur à 0,1 point pour le CPU).

| Mesure | v4 | v5 | v5 / v4 |
|---|---:|---:|---:|
| Plugins actifs | 28 | 26 | — |
| Cycle complet forcé, médiane (ms) | 83,3 | 36,2 | 0,43 |
| Cycle complet forcé, p95 (ms) | 108,5 | 54,4 | 0,50 |
| Démarrage jusqu'à `/status` (s) | 3,01 | 0,73 | 0,24 |
| Serveur au repos, CPU (% d'un cœur) | 0,2 | 1,6 | voir (1) |
| Serveur lu toutes les 2 s, CPU (% d'un cœur) | 1,7 | 2,1 | 1,20 |
| Serveur, RSS (Mio) | 95 | 72 | 0,75 |
| `--quiet`, CPU (% d'un cœur) | 0,7 | 1,4 | voir (2) |
| `--quiet`, RSS (Mio) | 60 | 61 | 1,02 |
| `GET /all`, médiane (ms) | 8,8 | 5,0 | 0,56 |
| `GET /all`, p95 (ms) | 11,5 | 6,5 | 0,57 |
| `GET /all`, taille (Kio) | 90 | 98 | 1,09 |
| `GET /cpu`, médiane (ms) | 2,0 | 1,2 | 0,61 |
| `GET /cpu`, p95 (ms) | 2,8 | 1,7 | 0,61 |

- **Cycle complet forcé** : une mise à jour de chaque plugin actif, chronométrée
  dans le processus (v4 : `GlancesStats.update()` avec tous les minuteurs
  expirés ; v5 : `AsyncScheduler.run_cycle()`, plugins en parallèle).
- **Serveur** : v4 `-w --disable-webui`, v5 `-s --disable-webui
  --disable-autodiscover`, sur 127.0.0.1 ; fenêtres de 60 s après 10 s de
  chauffe ; 200 requêtes séquentielles par route.
- **`/all` plus gros de 9 %** : le modèle de données v5 (champs `_levels`
  notamment). La réponse est désormais compressée en gzip quand le client
  l'accepte (GAP traité le 2026-10-05), ce que la mesure n'exploite pas.

## Limites

- Une seule machine, une VM peu chargée (peu de processus, pas de conteneurs,
  pas de GPU) : les plugins qui coûtent cher en production (processlist sur
  des milliers de processus, containers) y pèsent peu. À refaire sur une
  machine représentative avant `5.0.0`.
- Les 28 et 26 plugins ne sont pas les mêmes listes (périmètres v4 et v5
  différents, plugins `alert` et `help` absents en v5) : le cycle complet
  compare des ensembles proches, pas identiques.

## Reproduire

```console
$ python tests/perf/bench_v4_v5.py --runs 3 --markdown
```

Options : `--config`, `--cycles`, `--idle` (fenêtres en secondes),
`--warmup`, `--requests`. Sans `--markdown`, le rapport est en JSON. La
mesure du nombre de mises à jour de la liste des processus (6 contre 10 en
20 s) a été faite en enveloppant `GlancesProcesses.update` le temps de
`--quiet --stop-after 10` dans chaque version.
