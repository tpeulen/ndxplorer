# Trouver des projections informatives

Une table de bursts à quarante paramètres contient 780 graphiques à deux
paramètres. Ce panneau (**Affichage ▸ Trouver des projections informatives…**,
juste sous *UMAP* ; l'entrée *(axe z)* en dessous classe le troisième axe) les
note tous, en arrière-plan, et les liste du meilleur au moins bon. **Cliquez
sur une ligne et ndX affiche ce graphique.** Choisir les axes à la main dans le
graphique sélectionne la ligne correspondante : vous voyez ainsi le rang de
votre propre choix.

La table se remplit pendant le calcul. **Pause** l'arrête et **Démarrer**
reprend là où il s'est arrêté ; fermer le panneau le met aussi en pause, et le
rouvrir reprend. À la fin, la meilleure ligne est sélectionnée et affichée. La
ligne sous la table dit, en chiffres, ce que signifie la note de la ligne
sélectionnée.

## Classer par

**Séparation** (par défaut) — dans quelle vue les bursts se répartissent-ils en
populations nettement séparées ? C'est la question du smFRET : espèces
donneur seul, accepteur seul et FRET qui s'écartent en E contre S, une
population dynamique hors de la ligne FRET statique en E contre τ ou dans le
graphique de variance. Aucune étiquette n'est nécessaire.

Les bursts de la vue sont regroupés en classes et lissés ; chaque pic de
densité entouré d'une vallée est une **île**. Une vallée compte lorsqu'elle est
plus profonde que le bruit de grenaille de l'histogramme et que le côté le plus
petit contient au moins 3 % des bursts — une queue ou un amas de valeurs
aberrantes n'est donc pas une population. La note est la **probabilité que deux
bursts tirés au hasard se trouvent dans deux îles différentes et nettement
séparées** : seuls comptent les bursts au cœur d'une île (pas ceux sur un pont
entre deux populations, dans une queue ou dans le bruit), et une vallée peu
profonde compte moins qu'un espace vide. 0 correspond à une population — aussi
allongée, asymétrique ou corrélée soit-elle —, 0,5 à deux îles égales séparées
par un espace vide, 0,18 à une île de 10 % à côté d'un amas de 90 %, 0,67 à
trois îles égales. La colonne **Îles** indique leur nombre.

Avant de noter une paire, les paramètres qui ne peuvent pas distinguer les
molécules sont mis de côté : les indicateurs (moins de 20 valeurs), l'horloge
d'acquisition (premier photon, macro-temps) et les repliements d'un autre
paramètre (`(1-E)*E` de E). Les paramètres qui sont la même grandeur —
*Proximity ratio* et *FRET efficiency*, un taux et son comptage — sont classés
une seule fois ; la ligne nomme les autres. Chaque axe est lu comme le
graphique le dessine (un axe logarithmique en décades), sans les valeurs
sentinelles d'ajustement (`-1` là où un canal n'a pas été ajusté, une borne qui
retient beaucoup de bursts) ni les valeurs aberrantes, et l'axe est mis à
l'échelle par son étendue robuste, afin qu'un paramètre ne gagne pas grâce à
ses unités.

**Bursts** — les bursts pauvres en photons sont larges (bruit de grenaille) et
comblent les vallées entre populations. *Pondérer par les photons* compte
chaque burst selon ses photons ; *Seulement les bursts avec au moins Photons
min.* écarte les plus faibles. Les deux nécessitent une colonne *Number of
Photons*.

**Afficher les îles sur la carte** colore la carte selon les îles trouvées dans
la vue sur les axes (application emtk).

**Utiliser les îles comme clusters** attribue à chaque burst de la table l'île
de la vue sur les axes et écrit les étiquettes comme clusters (`Cluster Label`,
qui remplace les clusters K-means/HDBSCAN) et comme colonne
`Island Label (x vs y)`. Les îles sont numérotées selon le nombre de leurs
bursts, la plus grande en premier. La zone de sélection Cluster, *couleur*, les
gates, l'enregistrement des Burst IDs et l'axe de population des paramètres
vectoriels travaillent alors sur les îles. **Étiquette** à côté du bouton
indique quels bursts en reçoivent une :

- *Îles entières* (par défaut) : chaque burst dans le bassin versant de l'île --
  la ligne de partage des eaux de la densité lissée que segmente la note de
  séparation --, y compris la traînée pauvre en photons entre les espèces. -1
  seulement pour les bursts sur la crête entre deux îles (l'île y détient moins
  de 2/3 de la densité lissée, une bande d'environ une demi-largeur de noyau),
  dans un amas trop petit pour être une île (moins de 3 % des bursts ; il n'est
  pas fusionné avec un voisin), et pour les valeurs aberrantes ou manquantes.
  Sur le fichier ALEX cal1 (S contre PR), cela étiquette 94 % des bursts.
- *Cœurs seulement* : uniquement les bursts nettement à l'intérieur d'une île, à
  2 sigmas de bruit de grenaille au-dessus de sa vallée vers les autres ; les
  ponts, les queues et la traînée restent à -1 (37 % des bursts de cal1
  étiquetés).

`Cluster Probability` est la part de l'île dans la densité lissée au niveau du
burst : 1 au fond d'une île, décroissant vers 1/2 sur une crête, 0 pour -1. La
ligne d'état indique combien de bursts ont été étiquetés.

**Corrélation** — quels paramètres varient ensemble (Spearman |ρ|, signe
affiché) ? Elle trouve des mesures liées — E et une durée de vie, un taux et son
comptage —, pas des populations ; les mêmes règles de mise de côté
s'appliquent, afin que les paramètres dupliqués n'envahissent pas le haut du
classement.

**Classes** — proposé lorsqu'il existe des étiquettes : le gate de la table de
sélection (intérieur contre extérieur), une population par gate, les clusters de
*Cluster*, ou un paramètre z qui contient des étiquettes. Les bursts d'une même
classe sont-ils voisins dans cette vue ? Pour chaque burst, les 10 bursts les
plus proches à l'écran sont recherchés et la part de la même classe est
comptée, au-delà du hasard (κ). Les paramètres sur lesquels un gate est défini,
et ceux qui en sont calculés, ne sont pas classés par rapport à ce gate.

## Réglages

**Échantillon** — bursts tirés au hasard pour la notation. Le même échantillon
sert à toutes les lignes, de sorte que les lignes comparent ce qui est
comparable. Le haut du classement change rarement au-delà de quelques milliers.

Modifier un réglage met le classement en pause, et le **Démarrer** suivant
reclasse avec les nouveaux réglages. Modifier la table, les gates ou l'étendue
d'un axe invalide les lignes ; choisir à nouveau **Affichage ▸ Trouver des
projections informatives…** lance un nouveau classement.

## Pour aller plus loin

- [Interactive multidimensional exploration](docs/concepts/multidimensional_exploration.md)
- [Exploring & fitting multidimensional data (ndX)](docs/guides/46_ndxplorer.md)
- Edelsbrunner, Letscher & Zomorodian, *Topological persistence and
  simplification* (la règle de l'aîné qui associe chaque pic de densité à sa
  vallée) —
  [10.1007/s00454-002-2885-2](https://doi.org/10.1007/s00454-002-2885-2)
