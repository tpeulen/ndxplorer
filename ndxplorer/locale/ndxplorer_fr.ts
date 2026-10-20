<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fr">
    <context>
        <name>ndxplorer</name>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source> fps</source>
            <translation> ips</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>#</source>
            <translation>#</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>'es' is the 1/S = Ω + Σ·E fit and needs at least two FRET sub-populations; 'lifetime' uses the static FRET line and works on a single population, but needs a per-burst donor lifetime and a trustworthy τ_D(0); 'combined' is the precision-weighted mean; 'auto' takes the E-S fit and falls back to the lifetime. The two routes are independent, so their disagreement is itself a diagnostic.</source>
            <translation>'es' est l'ajustement 1/S = Ω + Σ·E et nécessite au moins deux sous-populations FRET ; 'lifetime' utilise la droite FRET statique et fonctionne sur une seule population, mais nécessite une durée de vie du donneur par burst et un τ_D(0) fiable ; 'combined' est la moyenne pondérée par la précision ; 'auto' prend l'ajustement E-S et se rabat sur la durée de vie. Les deux voies sont indépendantes, leur désaccord est donc en soi un diagnostic.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>'fit' determines them from the reference populations themselves — an acceptor-only burst has no donor, so what appears in the donor channel is background; a donor-only burst has no acceptor, so what appears under acceptor excitation is background; and the leakage line I_DA = α·I_DD + bg_da gives the third as its intercept. Use this when the background is not known, which is most of the time. It costs a second calibration pass: the populations have to exist before they can be read, and once the background is subtracted the classification is made again.

'measurement' uses the rates the Background step stored in this measurement's container, multiplied by each burst's duration — so a 4 ms burst carries four times the background of a 1 ms one, which a single number cannot express. Falls back to the window's constants if the container has no stored estimate.

'constants' uses the window's Bg / Br / By as they stand. 'none' sets them to zero.

This is the correction whose error is hardest to see: it moves the dim bursts and leaves the bright ones, which looks exactly like a real sub-population.</source>
            <translation>'fit' les détermine à partir des populations de référence elles-mêmes — un burst accepteur seul n'a pas de donneur, donc ce qui apparaît dans le canal donneur est du bruit de fond ; un burst donneur seul n'a pas d'accepteur, donc ce qui apparaît sous excitation de l'accepteur est du bruit de fond ; et la droite de fuite I_DA = α·I_DD + bg_da fournit le troisième comme ordonnée à l'origine. À utiliser quand le bruit de fond est inconnu, ce qui est le plus souvent le cas. Cela coûte une seconde passe d'étalonnage : les populations doivent exister avant de pouvoir être lues, et une fois le bruit de fond soustrait, la classification est refaite.

'measurement' utilise les taux que l'étape Bruit de fond a stockés dans le conteneur de cette mesure, multipliés par la durée de chaque burst — un burst de 4 ms porte donc quatre fois plus de bruit de fond qu'un burst de 1 ms, ce qu'un nombre unique ne peut pas exprimer. Se rabat sur les constantes de la fenêtre si le conteneur n'a pas d'estimation stockée.

'constants' utilise Bg / Br / By de la fenêtre tels quels. 'none' les met à zéro.

C'est la correction dont l'erreur est la plus difficile à voir : elle déplace les bursts faibles et laisse les brillants, ce qui ressemble exactement à une vraie sous-population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="416" />
            <source>(Parameters tab; right-click a vector &gt; Make scalar to go back to one value)</source>
            <translation>(onglet Paramètres ; clic droit sur un vecteur &gt; Convertir en scalaire pour revenir à une seule valeur)</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="142" />
            <source>({x}, {y}) is outside the plotted range</source>
            <translation>({x}, {y}) est en dehors de la plage tracée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>+</source>
            <translation>+</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="135" />
            <source>, replacing the previous clusters</source>
            <translation>, en remplaçant les clusters précédents</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>-1 uses all available cores, 0/1 disables parallelism.</source>
            <translation>-1 utilise tous les cœurs disponibles, 0/1 désactive le parallélisme.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>/</source>
            <translation>/</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>0 for scatter / a mirror; the lifetime of a reference dye otherwise.</source>
            <translation>0 pour une diffusion / un miroir ; sinon la durée de vie d'un colorant de référence.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="484" />
            <source>1-D histograms copied to the clipboard (tab separated).</source>
            <translation>Histogrammes 1D copiés dans le presse-papiers (séparés par tabulations).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="72" />
            <source>1. Open data: File &gt; Import (a burst-analysis folder, text files, an analysis file or a ChiSurf sampling), or drop a file or folder on the window.</source>
            <translation>1. Ouvrir des données : Fichier &gt; Importer (un dossier d'analyse de bursts, des fichiers texte, un fichier d'analyse ou un échantillonnage ChiSurf), ou déposer un fichier ou un dossier sur la fenêtre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>2 to plot directly, 3 for more room.</source>
            <translation>2 pour tracer directement, 3 pour plus de marge.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="474" />
            <source>2-D histogram copied to the clipboard (tab separated).</source>
            <translation>Histogramme 2D copié dans le presse-papiers (séparé par tabulations).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="74" />
            <source>2. Choose the x, y and z parameters in Plot controls; each has bins, a range (Auto), log and norm. Set stores a parameter's axis; Settings &gt; Save settings &gt; Axis settings writes them to a file.</source>
            <translation>2. Choisir les paramètres x, y et z dans les contrôles du graphique ; chacun a des bins, une plage (Auto), log et norm. Définir enregistre l'axe d'un paramètre ; Paramètres &gt; Enregistrer les paramètres &gt; Paramètres d'axe les écrit dans un fichier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>2D Plot</source>
            <translation>Graphique 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="77" />
            <source>3. Drag a rectangle on the 2-D map to gate: the Selection table lists the gates, which can be inverted, disabled and edited.</source>
            <translation>3. Tracer un rectangle sur la carte 2D pour gater : le tableau de sélection liste les gates, qui peuvent être inversés, désactivés et modifiés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="79" />
            <source>4. Parameters, Overlays, Equations and the analyses (clustering, Gaussian fit, informative projections) are in the tabs and the View menu.</source>
            <translation>4. Les paramètres, superpositions, équations et analyses (clustering, ajustement gaussien, projections informatives) se trouvent dans les onglets et le menu Affichage.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="81" />
            <source>5. File &gt; Make Report makes PNG/CSV/DOCX reports over many analysis folders from a report.yaml.</source>
            <translation>5. Fichier &gt; Créer un rapport génère des rapports PNG/CSV/DOCX sur de nombreux dossiers d'analyse à partir d'un report.yaml.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>&lt;b&gt;Separation&lt;/b&gt; (default) finds the views where the bursts fall into clearly separated islands: donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line. &lt;b&gt;Correlation&lt;/b&gt; finds parameters that move together. &lt;b&gt;Classes&lt;/b&gt; appears when there are gates or clusters and finds views that keep them apart.</source>
            <translation>&lt;b&gt;Separation&lt;/b&gt; (par défaut) trouve les vues où les bursts se répartissent en îlots nettement séparés : donneur seul, accepteur seul et espèces FRET dans E vs S, une population dynamique hors de la ligne FRET statique. &lt;b&gt;Correlation&lt;/b&gt; trouve les paramètres qui varient ensemble. &lt;b&gt;Classes&lt;/b&gt; apparaît lorsqu'il y a des gates ou des clusters et trouve les vues qui les distinguent.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <source>A load or a save running in the background.</source>
            <translation>Un chargement ou un enregistrement en cours en arrière-plan.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="301" />
            <location filename="ndxplorer/app/features/overlays.py" line="402" />
            <source>A parameter named '{name}' already exists.</source>
            <translation>Un paramètre nommé '{name}' existe déjà.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="299" />
            <source>A parameter needs a name.</source>
            <translation>Un paramètre doit avoir un nom.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="346" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="880" />
            <source>A stored calibration.</source>
            <translation>Un étalonnage enregistré.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="132" />
            <source>A vector (▸ gamma [2]) holds one value per population; open it for the elements.</source>
            <translation>Un vecteur (▸ gamma [2]) contient une valeur par population ; l'ouvrir pour voir les éléments.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="304" />
            <source>A vector needs its populations: how many, or their names.</source>
            <translation>Un vecteur a besoin de ses populations : leur nombre ou leurs noms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="306" />
            <source>A vector's name cannot end in [...].</source>
            <translation>Le nom d'un vecteur ne peut pas se terminer par [...].</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="83" />
            <source>About</source>
            <translation>À propos</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1091" />
            <source>About ndXplorer</source>
            <translation>À propos de ndXplorer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/text.view.json" line="0" />
            <source>Accept the entries and close the dialog.</source>
            <translation>Accepter les entrées et fermer la boîte de dialogue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Acceptor excited by the donor laser. Taken from the acceptor-only population, so it needs one.</source>
            <translation>Accepteur excité par le laser du donneur. Déterminé à partir de la population accepteur seul, il en faut donc une.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="736" />
            <source>Accurate FRET</source>
            <translation>Accurate FRET</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Accurate FRET efficiency of the population.</source>
            <translation>Efficacité FRET précise de la population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="207" />
            <source>Accurate FRET needs tttrlib's FRET calibration (tttrlib.auto_calibrate), which this tttrlib does not have.</source>
            <translation>Le FRET précis nécessite l'étalonnage FRET de tttrlib (tttrlib.auto_calibrate), que cette tttrlib n'a pas.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Add Curve</source>
            <translation>Ajouter une courbe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Add a Gaussian in the middle of the map.</source>
            <translation>Ajouter une gaussienne au centre de la carte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Add a new constant (name + value)</source>
            <translation>Ajouter une nouvelle constante (nom + valeur)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Add a new selection range to the selection list.</source>
            <translation>Ajouter une nouvelle plage de sélection à la liste de sélection.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Add accurate E / S / R_DA columns</source>
            <translation>Ajouter des colonnes E / S / R_DA précises</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Add an analysis folder (or a folder above several)</source>
            <translation>Ajouter un dossier d'analyse (ou un dossier contenant plusieurs)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Add an equation</source>
            <translation>Ajouter une équation</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="465" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="171" />
            <source>Add one or more Gaussians (click on the histogram) before fitting.</source>
            <translation>Ajoutez une ou plusieurs gaussiennes (clic sur l'histogramme) avant d'ajuster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Add or remove Gaussian components of the fit to the current histogram.</source>
            <translation>Ajouter ou supprimer des composantes gaussiennes de l'ajustement du histogramme actuel.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="372" />
            <location filename="ndxplorer/app/features/overlays.py" line="401" />
            <location filename="ndxplorer/app/features/overlays.py" line="413" />
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Add parameter</source>
            <translation>Ajouter un paramètre</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Add the chosen curve to the plot.</source>
            <translation>Ajouter la courbe choisie au graphique.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Add the painted area to the mask.</source>
            <translation>Ajouter la zone peinte au masque.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Add the painted category as a mask gate in the Selection table.</source>
            <translation>Ajouter la catégorie peinte comme gate de masque dans le tableau de sélection.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Added to the covariance diagonals, so no component collapses.</source>
            <translation>Ajouté aux diagonales de covariance pour qu'aucune composante ne s'effondre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1321" />
            <source>Added {first}…{last}. Pick them in the axis controls to plot.</source>
            <translation>{first}…{last} ajouté(s). Les choisir dans les contrôles d'axe pour les tracer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1743" />
            <source>Added {n} line(s) to the Overlays tab</source>
            <translation>{n} ligne(s) ajoutée(s) à l'onglet Overlays</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1740" />
            <source>Added {n} line(s) to the Overlays tab from {source}</source>
            <translation>{n} ligne(s) ajoutée(s) à l'onglet Overlays depuis {source}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Add…</source>
            <translation>Ajouter…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Advanced</source>
            <translation>Avancé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Advanced Options</source>
            <translation>Options avancées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>After</source>
            <translation>Après</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Aggressive Caching</source>
            <translation>Mise en cache agressive</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="91" />
            <location filename="ndxplorer/io/loading.py" line="99" />
            <source>All Files</source>
            <translation>Tous les fichiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="59" />
            <source>All bursts, equal weight</source>
            <translation>Tous les bursts, poids égal</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>All cores</source>
            <translation>Tous les cœurs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io_service.py" line="126" />
            <location filename="ndxplorer/app/features/io_service.py" line="191" />
            <location filename="ndxplorer/app/features/io_service.py" line="192" />
            <location filename="ndxplorer/app/features/phasor_reference.py" line="34" />
            <location filename="ndxplorer/app/features/settings.py" line="524" />
            <location filename="ndxplorer/app/features/settings.py" line="946" />
            <location filename="ndxplorer/io/loading.py" line="85" />
            <location filename="ndxplorer/io/loading.py" line="96" />
            <source>All files</source>
            <translation>Tous les fichiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="75" />
            <source>All files (*.selection.json)</source>
            <translation>Tous les fichiers (*.selection.json)</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="436" />
            <source>All of {lo}–{hi}{unit}</source>
            <translation>Tout de {lo}–{hi}{unit}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="691" />
            <source>All selected analysis folders already have a report. Nothing to generate.</source>
            <translation>Tous les dossiers d'analyse sélectionnés ont déjà un rapport. Rien à générer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="434" />
            <source>All {n} · {first}–{last}</source>
            <translation>Tous les {n} · {first}–{last}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="778" />
            <source>Also this view: {names}.</source>
            <translation>Aussi cette vue : {names}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>An analysis folder, or a folder above several</source>
            <translation>Un dossier d'analyse, ou un dossier contenant plusieurs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="27" />
            <source>Analysis file (*.zip, *.hdf)</source>
            <translation>Fichier d'analyse (*.zip, *.hdf)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Analysis folders (drop here):</source>
            <translation>Dossiers d'analyse (déposer ici) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="28" />
            <source>Analysis-Folder</source>
            <translation>Dossier d'analyse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Answer no and continue without it.</source>
            <translation>Répondre non et continuer sans.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Answer yes and continue.</source>
            <translation>Répondre oui et continuer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="113" />
            <source>Append as columns (add new columns, rows must match)</source>
            <translation>Ajouter comme colonnes (nouvelles colonnes, les lignes doivent correspondre)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="114" />
            <source>Append as rows (add new rows of existing columns)</source>
            <translation>Ajouter comme lignes (nouvelles lignes des colonnes existantes)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Apply</source>
            <translation>Appliquer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="628" />
            <source>Apply a saved FRET calibration to the current ndX session.</source>
            <translation>Appliquer un étalonnage FRET enregistré à la session ndX actuelle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Apply and close</source>
            <translation>Appliquer et fermer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Apply the computed reference calibration to the loaded data.</source>
            <translation>Appliquer l'étalonnage de référence calculé aux données chargées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="883" />
            <source>Apply this calibration to the window?</source>
            <translation>Appliquer cet étalonnage à la fenêtre ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Arrays held by the overlay store; edit cells to change parameter values.</source>
            <translation>Tableaux détenus par le stockage des superpositions ; modifier les cellules pour changer les valeurs des paramètres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Ask where to save, then write the figure.</source>
            <translation>Demander où enregistrer, puis écrire la figure.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Asked after the burst-ID (.bst) files were written: what to do with them.</source>
            <translation>Demandé après l'écriture des fichiers d'ID de burst (.bst) : que faire de ces fichiers.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Asked when a ChiSurf project holds more than one stored table (one per sampled fit): which one to open.</source>
            <translation>Demandé lorsqu'un projet ChiSurf contient plus d'un tableau enregistré (un par ajustement échantillonné) : lequel ouvrir.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Asked when data is already loaded and another file is opened: replace the table, or merge the new one into it.</source>
            <translation>Demandé lorsque des données sont déjà chargées et qu'un autre fichier est ouvert : remplacer le tableau ou y fusionner le nouveau.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1090" />
            <source>Author: Thomas-Otavio Peulen. License: {license}.</source>
            <translation>Auteur : Thomas-Otavio Peulen. Licence : {license}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Auto</source>
            <translation>Auto</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Auto-range the x axis to the data</source>
            <translation>Ajuster automatiquement l'axe x aux données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Auto-range the y axis to the data</source>
            <translation>Ajuster automatiquement l'axe y aux données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Auto-range the z axis to the data</source>
            <translation>Ajuster automatiquement l'axe z aux données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Available names that can be used in the expression; double-click to insert one.</source>
            <translation>Noms utilisables dans l'expression ; double-cliquer pour en insérer un.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Axes, bin counts, ranges and weighting for the marginal and 2-D histograms.</source>
            <translation>Axes, nombres de bins, plages et pondération des histogrammes marginaux et 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Axis</source>
            <translation>Axe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="252" />
            <location filename="ndxplorer/app/features/settings.py" line="1066" />
            <location filename="ndxplorer/app/features/settings.py" line="1070" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="77" />
            <source>Axis Control</source>
            <translation>Contrôle des axes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis Label Settings</source>
            <translation>Paramètres d'étiquettes d'axe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="911" />
            <source>Axis Mismatch</source>
            <translation>Axes incompatibles</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="989" />
            <source>Axis file</source>
            <translation>Fichier d'axes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1071" />
            <source>Axis label and font settings saved and applied successfully.</source>
            <translation>Paramètres d'étiquettes d'axe et de police enregistrés et appliqués.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis labels of the x marginal plot.</source>
            <translation>Étiquettes d'axe de l'histogramme marginal x.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis labels of the y marginal plot.</source>
            <translation>Étiquettes d'axe de l'histogramme marginal y.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis labels of the z marginal plot.</source>
            <translation>Étiquettes d'axe de l'histogramme marginal z.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="55" />
            <source>Axis settings</source>
            <translation>Paramètres des axes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="989" />
            <source>Axis settings file</source>
            <translation>Fichier de paramètres d'axe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility and enabling of the z marginal plot.</source>
            <translation>Visibilité des axes et activation de l'histogramme marginal z.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the 2D histogram plot.</source>
            <translation>Visibilité des axes du graphique d'histogramme 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the overlay plot.</source>
            <translation>Visibilité des axes du graphique de superposition.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the x marginal plot.</source>
            <translation>Visibilité des axes de l'histogramme marginal x.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the y marginal plot.</source>
            <translation>Visibilité des axes de l'histogramme marginal y.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>BID</source>
            <translation>BID</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="432" />
            <source>Back</source>
            <translation>Précédent</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Background</source>
            <translation>Bruit de fond</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="455" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="433" />
            <source>Background, fitted from the reference populations: {values}</source>
            <translation>Bruit de fond, ajusté à partir des populations de référence : {values}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="471" />
            <source>Background: none (set to zero)</source>
            <translation>Bruit de fond : aucun (mis à zéro)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="464" />
            <source>Background: per burst, from this measurement's own estimate ({columns})</source>
            <translation>Bruit de fond : par burst, d'après l'estimation propre à cette mesure ({columns})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="467" />
            <source>Background: the container has no stored estimate — the window's own constants were used</source>
            <translation>Bruit de fond : le conteneur ne contient pas d'estimation stockée — les constantes propres à la fenêtre ont été utilisées</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="458" />
            <source>Background: the reference populations were too small to fit one — the window's constants were used</source>
            <translation>Bruit de fond : les populations de référence étaient trop petites pour en ajuster un — les constantes de la fenêtre ont été utilisées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="436" />
            <source>Background: {source}</source>
            <translation>Bruit de fond : {source}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Backgrounds are an input to the calibration, not one of its factors — unless you ask it to fit them, which is what 'fit' does.</source>
            <translation>Les bruits de fond sont une entrée de l'étalonnage, pas l'un de ses facteurs — sauf si on lui demande de les ajuster, ce que fait 'fit'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Batch reports over analysis folders: a report.yaml names the plots, each folder gets PNGs, CSVs and a DOCX.</source>
            <translation>Rapports par lots sur des dossiers d'analyse : un fichier report.yaml nomme les graphiques, chaque dossier reçoit des PNG, des CSV et un DOCX.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Before</source>
            <translation>Avant</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="284" />
            <source>Bitmap {n} ({x}, {y})</source>
            <translation>Bitmap {n} ({x}, {y})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Bootstrap resamples</source>
            <translation>Rééchantillons bootstrap</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Bottom Axis</source>
            <translation>Axe inférieur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Bottom Axis Label</source>
            <translation>Étiquette de l'axe inférieur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Browse</source>
            <translation>Parcourir</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Browse generated images</source>
            <translation>Parcourir les images générées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Browse the images generated by the report.</source>
            <translation>Parcourir les images générées par le rapport.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Brush radius in pixels.</source>
            <translation>Rayon du pinceau en pixels.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Brush:</source>
            <translation>Pinceau :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="36" />
            <source>Burst IDs</source>
            <translation>ID de bursts</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="605" />
            <source>Burst IDs saved; recording them failed: {error}</source>
            <translation>ID de burst enregistrés ; leur consignation a échoué : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="87" />
            <source>Burst analysis folder</source>
            <translation>Dossier d'analyse de bursts</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Burst-table columns; tick to show a column and filter the list by name.</source>
            <translation>Colonnes du tableau des bursts ; cocher pour afficher une colonne et filtrer la liste par nom.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Bursts</source>
            <translation>Bursts</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Bursts drawn at random for scoring. The same sample serves every view, so views are compared on identical bursts.</source>
            <translation>Bursts tirés au hasard pour le score. Le même échantillon sert à toutes les vues, qui sont ainsi comparées sur des bursts identiques.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Bursts with fewer photons than this are left out of the Separation score.</source>
            <translation>Les bursts ayant moins de photons que cette valeur sont exclus du score de séparation.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="827" />
            <source>CSV Files</source>
            <translation>Fichiers CSV</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1358" />
            <source>CSV files</source>
            <translation>Fichiers CSV</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Cache more intermediate results for better performance at the cost of higher memory usage.</source>
            <translation>Mettre en cache davantage de résultats intermédiaires pour de meilleures performances, au prix d'une plus grande consommation de mémoire.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="99" />
            <source>Calibrate</source>
            <translation>Étalonner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="102" />
            <location filename="ndxplorer/app/features/accurate_fret/progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis.py" line="1339" />
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Cancel</source>
            <translation>Annuler</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Cancel the import</source>
            <translation>Annuler l'importation</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="741" />
            <source>Canceled</source>
            <translation>Annulé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="512" />
            <source>Cancelled or failed.</source>
            <translation>Annulé ou échoué.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="271" />
            <source>Cancelled.</source>
            <translation>Annulé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="510" />
            <location filename="ndxplorer/app/features/analysis.py" line="516" />
            <location filename="ndxplorer/app/features/io.py" line="257" />
            <source>Cancelling…</source>
            <translation>Annulation…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="331" />
            <source>Cannot rank: {error}</source>
            <translation>Classement impossible : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="601" />
            <source>Cannot show {name}</source>
            <translation>Impossible d'afficher {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Cat:</source>
            <translation>Cat. :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Category/class ID for drawing (1-255): the one the brush paints and Apply turns into a gate.</source>
            <translation>ID de catégorie/classe pour le dessin (1-255) : celle que peint le pinceau et que Appliquer transforme en gate.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Change working path</source>
            <translation>Changer le chemin de travail</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="864" />
            <source>Changes:</source>
            <translation>Modifications :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Channels of g, s:</source>
            <translation>Canaux de g, s :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="376" />
            <source>ChiSurf does not advertise a burst consumer named {key}; it offers {offered}</source>
            <translation>ChiSurf n'annonce aucun consommateur de bursts nommé {key} ; il propose : {offered}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="260" />
            <source>ChiSurf is not available: the lifetime route used the no-linker line E = 1 - tau/tau_D(0) instead of the static FRET line (tau_D(0) = {tau} ns)</source>
            <translation>ChiSurf n'est pas disponible : la voie durée de vie a utilisé la droite sans linker E = 1 - tau/tau_D(0) au lieu de la droite FRET statique (tau_D(0) = {tau} ns)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="101" />
            <source>ChiSurf project</source>
            <translation>Projet ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="31" />
            <source>ChiSurf project (*.cs.pto)</source>
            <translation>Projet ChiSurf (*.cs.pto)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="102" />
            <source>ChiSurf projects</source>
            <translation>Projets ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="95" />
            <source>ChiSurf sampling files</source>
            <translation>Fichiers d'échantillonnage ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="511" />
            <source>ChiSurf's fits are not listed: ChiSurf is not available here.</source>
            <translation>Les ajustements de ChiSurf ne sont pas listés : ChiSurf n'est pas disponible ici.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="30" />
            <source>ChiSurf-Sampling</source>
            <translation>ChiSurf-Sampling</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Choose IRF…</source>
            <translation>Choisir l'IRF…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="92" />
            <source>Choose an IRF (and a measurement), then Compute.</source>
            <translation>Choisir une IRF (et une mesure), puis Calculer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1211" />
            <source>Choose at least {n} columns to project.</source>
            <translation>Choisir au moins {n} colonnes à projeter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Choose measurement…</source>
            <translation>Choisir la mesure…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Choose the criterion used to rank pairs of parameters by how informative their 2D view of the bursts is.</source>
            <translation>Choisir le critère de classement des paires de paramètres selon l'intérêt informatif de leur vue 2D des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Choose what "informative" means</source>
            <translation>Définir ce que « informatif » signifie</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Choose what to do with the saved Burst IDs:</source>
            <translation>Choisir que faire des ID de burst enregistrés :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Choose which axis labels are shown on the plots.</source>
            <translation>Choisir les étiquettes d'axe affichées sur les graphiques.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Choose which columns are shown</source>
            <translation>Choisir les colonnes affichées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Choose which parameters the method sees. Strongly recommended: without a choice it falls back to the current x/y/z axes.</source>
            <translation>Choisir les paramètres que la méthode voit. Vivement recommandé : sans choix, elle se rabat sur les axes x/y/z actuels.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="651" />
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Classes</source>
            <translation>Classes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/selection.py" line="52" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Clear</source>
            <translation>Effacer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="773" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Clear Reports</source>
            <translation>Supprimer les rapports</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="500" />
            <source>Clear list</source>
            <translation>Vider la liste</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Clear the plots and the working path.</source>
            <translation>Effacer les graphiques et le chemin de travail.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="767" />
            <source>Cleared reports for {n} folder(s).</source>
            <translation>Rapports supprimés pour {n} dossier(s).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Click a row to see that plot</source>
            <translation>Cliquer sur une ligne pour voir ce graphique</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Clicks on the map add a Gaussian there.</source>
            <translation>Un clic sur la carte y ajoute une gaussienne.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Close</source>
            <translation>Fermer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Close the report tool</source>
            <translation>Fermer l'outil de rapport</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Close this dialog.</source>
            <translation>Fermer cette boîte de dialogue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Close without applying</source>
            <translation>Fermer sans appliquer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Close without exporting.</source>
            <translation>Fermer sans exporter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Close without saving</source>
            <translation>Fermer sans enregistrer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Close without writing any change back</source>
            <translation>Fermer sans réécrire les modifications</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Cluster</source>
            <translation>Cluster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="375" />
            <source>Cluster {n}</source>
            <translation>Cluster {n}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/writer.py" line="200" />
            <source>Clustering data saved successfully!</source>
            <translation>Données de clustering enregistrées avec succès !</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1385" />
            <source>Clustering data saved to {path}</source>
            <translation>Données de clustering enregistrées dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1265" />
            <source>Clustering using {method} completed successfully.</source>
            <translation>Clustering avec {method} terminé avec succès.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="280" />
            <source>Clusters</source>
            <translation>Clusters</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Clusters:</source>
            <translation>Clusters :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Color:</source>
            <translation>Couleur :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Colormap of the 2-D histogram.</source>
            <translation>Palette de couleurs de l'histogramme 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Colour by value</source>
            <translation>Colorer selon la valeur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Colour of the axis titles</source>
            <translation>Couleur des titres d'axe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Colour the 2-D histogram by log10 of the counts.</source>
            <translation>Colorer l'histogramme 2D selon le log10 des comptages.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Colour the 2-D map by cluster.</source>
            <translation>Colorer la carte 2D par cluster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Colour the map by the islands the Separation score found in the selected view (the view must be on the axes).</source>
            <translation>Colorer la carte selon les îlots trouvés par le score de séparation dans la vue sélectionnée (la vue doit être sur les axes).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Column</source>
            <translation>Colonne</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Column each point is weighted by when the histograms are filled</source>
            <translation>Colonne par laquelle chaque point est pondéré lors du remplissage des histogrammes</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Column the playback runs along. Picked from the data on load — the frame index of an image stack, otherwise the per-burst macro time — but any numeric column can be played back.</source>
            <translation>Colonne le long de laquelle la lecture s'effectue. Choisie à partir des données au chargement — l'indice d'image d'une pile d'images, sinon le temps macro par burst — mais toute colonne numérique peut être lue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays.py" line="1394" />
            <location filename="ndxplorer/core/equation_table.py" line="166" />
            <source>Columns</source>
            <translation>Colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Combine the data estimates with the optical model's excitation/emission probabilities, so the result is a posterior: data where the data speaks, optics where it does not.</source>
            <translation>Combiner les estimations issues des données avec les probabilités d'excitation/émission du modèle optique, de sorte que le résultat soit un a posteriori : les données là où elles parlent, l'optique là où elles ne parlent pas.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="83" />
            <source>Comma separated value files</source>
            <translation>Fichiers de valeurs séparées par des virgules</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Comma-separated t values: one marker each.</source>
            <translation>Valeurs de t séparées par des virgules : un marqueur chacune.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="616" />
            <source>Component parameter: centre x, y, widths σx, σy, correlation ρ and weight w.</source>
            <translation>Paramètres de la composante : centre x, y, largeurs σx, σy, corrélation ρ et poids w.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Components to keep. Two is usually enough to plot; more is useful when the first two explain little of the variance.</source>
            <translation>Composantes à conserver. Deux suffisent en général pour tracer ; davantage est utile quand les deux premières expliquent peu de variance.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Components:</source>
            <translation>Composantes :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Compute</source>
            <translation>Calculer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Compute a microtime (decay) histogram for the selected bursts.</source>
            <translation>Calculer un histogramme de micro-temps (déclin) pour les bursts sélectionnés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Compute microtime histogram</source>
            <translation>Calculer l'histogramme de micro-temps</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Compute the phasor reference calibration from the chosen reference.</source>
            <translation>Calculer l'étalonnage de référence phasor à partir de la référence choisie.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Configuration of the report (report.yaml); edit to change which figures are made.</source>
            <translation>Configuration du rapport (report.yaml) ; modifier pour changer les figures produites.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Configure performance settings for ndxplorer. These settings control histogram computation, memory usage, and optimization features. Changes take effect after restarting ndxplorer.</source>
            <translation>Configurer les paramètres de performance de ndxplorer. Ils contrôlent le calcul des histogrammes, l'utilisation de la mémoire et les optimisations. Les modifications prennent effet après le redémarrage de ndxplorer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Configure the EM and save it to your user settings.</source>
            <translation>Configurer l'EM et l'enregistrer dans les paramètres utilisateur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Confirm</source>
            <translation>Confirmer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Constant</source>
            <translation>Constante</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="56" />
            <location filename="ndxplorer/core/equation_table.py" line="165" />
            <source>Constants</source>
            <translation>Constantes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1022" />
            <source>Constants saved to {path}.</source>
            <translation>Constantes enregistrées dans {path}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="98" />
            <location filename="ndxplorer/analysis/vizrank.py" line="99" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="243" />
            <source>Continue</source>
            <translation>Reprendre</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Contrast</source>
            <translation>Contraste</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Controls for stepping through the data along one column.</source>
            <translation>Commandes pour parcourir les données pas à pas le long d'une colonne.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1255" />
            <location filename="ndxplorer/app/parameter_table.py" line="413" />
            <source>Copy</source>
            <translation>Copier</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="53" />
            <source>Copy 1D Histograms (CSV)</source>
            <translation>Copier les histogrammes 1D (CSV)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="53" />
            <source>Copy 2D Histogram (CSV)</source>
            <translation>Copier l'histogramme 2D (CSV)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="608" />
            <source>Copy Image Path</source>
            <translation>Copier le chemin de l'image</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="478" />
            <source>Copy Path(s)</source>
            <translation>Copier le(s) chemin(s)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="403" />
            <source>Copy values</source>
            <translation>Copier les valeurs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1256" />
            <source>Copy with headers</source>
            <translation>Copier avec les en-têtes</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="381" />
            <source>Cores only</source>
            <translation>Cœurs uniquement</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Cores only (default): label bursts clearly inside an island, 2 shot-noise sigmas above its valley to the others; the low-photon smear between species stays -1. Whole islands: label every burst in an island's catchment basin -- the watershed of the smoothed density the score uses; -1 stays on ridges between islands, in clumps too small to be islands, and for outliers or missing values.</source>
            <translation>Cœurs uniquement (par défaut) : étiqueter les bursts nettement à l'intérieur d'un îlot, à 2 sigmas de bruit de grenaille au-dessus de sa vallée vers les autres ; le halo à faibles photons entre les espèces reste à -1. Îlots entiers : étiqueter chaque burst du bassin versant d'un îlot -- la ligne de partage des eaux de la densité lissée utilisée par le score ; -1 reste sur les crêtes entre îlots, dans les amas trop petits pour être des îlots, et pour les valeurs aberrantes ou manquantes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Corrected FRET efficiency, computed from the counts. Ticking it switches to the multidimensional mixture over every ticked dimension, which separates FRET populations the stoichiometry alone lumps together. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Efficacité FRET corrigée, calculée à partir des comptages. La cocher passe au mélange multidimensionnel sur toutes les dimensions cochées, qui sépare des populations FRET que la stœchiométrie seule regroupe. Coût : le gating multidimensionnel est environ dix fois plus lent que le gating par stœchiométrie (25 s au lieu de 2.4 s sur la mesure cal1, 44 270 bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Corrected stoichiometry, computed from the counts, so every ALEX/PIE measurement has it. Ticked alone it is the stoichiometry gating the calibration always used (fast).</source>
            <translation>Stœchiométrie corrigée, calculée à partir des comptages, de sorte que toute mesure ALEX/PIE en dispose. Cochée seule, c'est le gating par stœchiométrie que l'étalonnage a toujours utilisé (rapide).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Correction factors</source>
            <translation>Facteurs de correction</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="650" />
            <source>Correlation</source>
            <translation>Corrélation</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="530" />
            <source>Could not link: {error}</source>
            <translation>Liaison impossible : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1127" />
            <source>Could not load:
{error}</source>
            <translation>Chargement impossible :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="59" />
            <source>Could not open {path}: {error}</source>
            <translation>Impossible d'ouvrir {path} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="119" />
            <source>Could not parse the configuration: {error}</source>
            <translation>Impossible d'analyser la configuration : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="234" />
            <source>Could not remove the sessions from {name}: {error}</source>
            <translation>Impossible de retirer les sessions de {name} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="578" />
            <source>Could not save the burst IDs: {error}</source>
            <translation>Impossible d'enregistrer les ID de burst : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="924" />
            <source>Could not save the language: {error}</source>
            <translation>Impossible d'enregistrer la langue : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1140" />
            <source>Could not save:
{error}</source>
            <translation>Enregistrement impossible :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="794" />
            <source>Could not save: {error}</source>
            <translation>Enregistrement impossible : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="556" />
            <source>Could not send to {target}: {error}</source>
            <translation>Impossible d'envoyer à {target} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="814" />
            <source>Could not store: {error}</source>
            <translation>Impossible d'enregistrer : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="285" />
            <location filename="ndxplorer/app/features/overlays.py" line="1354" />
            <location filename="ndxplorer/app/features/settings.py" line="1020" />
            <source>Could not write {path}:
{error}</source>
            <translation>Impossible d'écrire {path} :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>DPI (raster):</source>
            <translation>DPI (raster) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Data</source>
            <translation>Données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="441" />
            <location filename="ndxplorer/app/features/io.py" line="444" />
            <location filename="ndxplorer/app/features/io.py" line="482" />
            <location filename="ndxplorer/app/features/io.py" line="491" />
            <location filename="ndxplorer/app/features/io.py" line="767" />
            <location filename="ndxplorer/app/frame.py" line="380" />
            <source>Data Load Error</source>
            <translation>Erreur de chargement des données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="664" />
            <source>Data:</source>
            <translation>Données :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1581" />
            <source>Decomposing</source>
            <translation>Décomposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1055" />
            <source>Default axis settings have been updated.</source>
            <translation>Les paramètres d'axe par défaut ont été mis à jour.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Definitions evaluated first, in order, separated by ';' (omega = 2*pi*f*harmonic*1e-3; tau = tan(t)/omega); x and y may use them.</source>
            <translation>Définitions évaluées en premier, dans l'ordre, séparées par ';' (omega = 2*pi*f*harmonic*1e-3 ; tau = tan(t)/omega) ; x et y peuvent les utiliser.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <location filename="ndxplorer/app/features/selection.py" line="52" />
            <source>Delete</source>
            <translation>Supprimer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Delete the report folders of the selected (or all) analysis folders</source>
            <translation>Supprimer les dossiers de rapport des dossiers d'analyse sélectionnés (ou de tous)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="183" />
            <source>Density-based. Finds clusters of varying shape and leaves noise unlabelled.</source>
            <translation>Basé sur la densité. Trouve des clusters de formes variées et laisse le bruit sans étiquette.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Derived columns: each row computes an output column from an expression.</source>
            <translation>Colonnes dérivées : chaque ligne calcule une colonne de sortie à partir d'une expression.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Detection efficiency times quantum-yield ratio. From the 1/S = Ω + Σ·E fit across FRET sub-populations, or from the donor lifetime. Turn this off to keep a γ you determined on a reference sample.</source>
            <translation>Efficacité de détection multipliée par le rapport des rendements quantiques. Issu de l'ajustement 1/S = Ω + Σ·E sur les sous-populations FRET, ou de la durée de vie du donneur. Désactivez pour conserver un γ déterminé sur un échantillon de référence.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Determine</source>
            <translation>Déterminer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="619" />
            <source>Determine FRET correction factors from the loaded burst data.</source>
            <translation>Déterminer les facteurs de correction FRET à partir des données de bursts chargées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Discard every change made in this dialog</source>
            <translation>Annuler toutes les modifications faites dans ce dialogue</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Discard the changes and close the dialog.</source>
            <translation>Annuler les modifications et fermer la boîte de dialogue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Display options for the array table below.</source>
            <translation>Options d'affichage du tableau ci-dessous.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="75" />
            <source>Displayed data (y vs x)</source>
            <translation>Données affichées (y en fonction de x)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Distance in the original space.</source>
            <translation>Distance dans l'espace d'origine.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="325" />
            <source>Distances to the centres</source>
            <translation>Distances aux centres</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="663" />
            <source>Do the bursts of one label (a gate, the clusters) sit together in this view? Share of each burst's 10 nearest neighbours with its label, above chance.</source>
            <translation>Les bursts d'une étiquette (un gate, les clusters) sont-ils regroupés dans cette vue ? Part des 10 plus proches voisins de chaque burst portant son étiquette, au-dessus du hasard.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="84" />
            <source>Documentation and source: {url}</source>
            <translation>Documentation et code source : {url}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="438" />
            <location filename="ndxplorer/app/features/settings.py" line="741" />
            <source>Done</source>
            <translation>Terminé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Donor emission detected in the acceptor channel. Taken from the donor-only population, so it needs one.</source>
            <translation>Émission du donneur détectée dans le canal accepteur. Déterminée à partir de la population donneur seul, il en faut donc une.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Donor-only lifetime, which anchors the static FRET line. Only used by the lifetime route; a wrong value there shows up as γ disagreeing between the two routes.</source>
            <translation>Durée de vie du donneur seul, qui ancre la droite FRET statique. Utilisée uniquement par la voie durée de vie ; une valeur erronée se manifeste par un γ qui diffère entre les deux voies.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Double-click a name to insert it into the focused expression.</source>
            <translation>Double-cliquer sur un nom pour l'insérer dans l'expression active.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="44" />
            <source>Download .pto with session…</source>
            <translation>Télécharger le .pto avec la session…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="787" />
            <source>Downloaded {name}</source>
            <translation>{name} téléchargé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/frame.py" line="660" />
            <source>Drag to resize the x marginal.</source>
            <translation>Glisser pour redimensionner la marge X.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/frame.py" line="662" />
            <source>Drag to resize the y marginal.</source>
            <translation>Glisser pour redimensionner la marge Y.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/frame.py" line="709" />
            <source>Drag to resize the z marginal.</source>
            <translation>Glisser pour redimensionner la marge Z.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Draw</source>
            <translation>Dessiner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Draw Mask</source>
            <translation>Dessiner un masque</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Draw each Gaussian on the x and y marginals.</source>
            <translation>Tracer chaque gaussienne sur les marges x et y.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Draw or erase a mask on the 2D histogram to select bursts.</source>
            <translation>Dessiner ou effacer un masque sur l'histogramme 2D pour sélectionner des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Draw the x and y marginal histograms above and beside the 2-D density.</source>
            <translation>Dessiner les histogrammes marginaux x et y au-dessus et à côté de la densité 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Drop analysis folders here to include them in the report.</source>
            <translation>Déposer des dossiers d'analyse ici pour les inclure dans le rapport.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Drop folder here.</source>
            <translation>Déposer le dossier ici.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Dynamic z-selection: the z range gates the other plots</source>
            <translation>Sélection z dynamique : la plage z gate les autres graphiques</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>E</source>
            <translation>E</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>E efficiency</source>
            <translation>E efficacité</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>EM stops when the lower bound improves by less than this.</source>
            <translation>L'EM s'arrête lorsque la borne inférieure s'améliore de moins que cette valeur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Each marker's label, formatted with t, the parameters and the definitions ({t:g} ns); empty for none.</source>
            <translation>Étiquette de chaque marqueur, formatée avec t, les paramètres et les définitions ({t:g} ns) ; vide pour aucune.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Editable text of report.yaml.</source>
            <translation>Texte modifiable de report.yaml.</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="148" />
            <source>Elevation failed with exit code {code}. See log: {log}</source>
            <translation>L'élévation de privilèges a échoué avec le code de sortie {code}. Voir le journal : {log}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="406" />
            <source>Embedding {rows} rows in {n} dimensions</source>
            <translation>Plongement de {rows} lignes en {n} dimensions</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Enable</source>
            <translation>Activer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Enable All Labels</source>
            <translation>Activer toutes les étiquettes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Enable Z Plot</source>
            <translation>Activer le graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Enable drawing</source>
            <translation>Activer le dessin</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Enable/disable drawing on the 2-D plot. While on, the left button paints instead of dragging a rectangle gate.</source>
            <translation>Activer/désactiver le dessin sur le graphique 2D. Tant qu'il est actif, le bouton gauche peint au lieu de tracer un gate rectangulaire.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Enables the caching and pre-binning around the fill. The fill itself is always tttrlib and is not affected.</source>
            <translation>Active la mise en cache et le pré-binning autour du remplissage. Le remplissage lui-même passe toujours par tttrlib et n'est pas affecté.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Enter text to filter columns</source>
            <translation>Saisir un texte pour filtrer les colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Epochs:</source>
            <translation>Époques :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Equation:</source>
            <translation>Équation :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Equation: y =</source>
            <translation>Équation : y =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1113" />
            <location filename="ndxplorer/app/features/overlays.py" line="1126" />
            <location filename="ndxplorer/app/features/overlays.py" line="1139" />
            <location filename="ndxplorer/app/features/overlays.py" line="1642" />
            <location filename="ndxplorer/app/features/settings.py" line="1034" />
            <location filename="ndxplorer/app/menus.py" line="57" />
            <location filename="ndxplorer/app/menus.py" line="71" />
            <source>Equations</source>
            <translation>Équations</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1118" />
            <source>Equations applied</source>
            <translation>Équations appliquées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1034" />
            <source>Equations file</source>
            <translation>Fichier d'équations</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1146" />
            <source>Equations saved to {path}</source>
            <translation>Équations enregistrées dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Erase</source>
            <translation>Effacer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Erase the whole mask.</source>
            <translation>Effacer tout le masque.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="379" />
            <source>Error</source>
            <translation>Erreur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="722" />
            <source>Error for {folder}: {error}</source>
            <translation>Erreur pour {folder} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1067" />
            <source>Error saving axis label settings.
Details: {error}</source>
            <translation>Erreur lors de l'enregistrement des paramètres d'étiquettes d'axe.
Détails : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="272" />
            <location filename="ndxplorer/app/features/overlays.py" line="577" />
            <source>Error: {error}</source>
            <translation>Erreur : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Evaluate a coarse grid over the free parameters before the fit and start it at the best point. A least-squares run only goes downhill from where it starts, so a degenerate pair -- a constant that scales the data against a parameter that scales the curve -- otherwise strands it in the first dip. Costs a fixed number of steps.</source>
            <translation>Évaluer une grille grossière sur les paramètres libres avant l'ajustement et démarrer au meilleur point. Une exécution des moindres carrés ne fait que descendre depuis son point de départ ; une paire dégénérée -- une constante qui met les données à l'échelle contre un paramètre qui met la courbe à l'échelle -- la piège sinon dans le premier creux. Coûte un nombre fixe d'étapes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Every pair of parameters is a possible plot. This panel &lt;b&gt;scores all of them&lt;/b&gt; and lists them best first, so you look at the few that show something instead of paging through hundreds.&lt;br/&gt;&lt;br/&gt;Four steps.</source>
            <translation>Chaque paire de paramètres est un graphique possible. Ce panneau &lt;b&gt;les évalue tous&lt;/b&gt; et les liste du meilleur au moins bon, pour consulter les quelques-uns qui montrent quelque chose au lieu de parcourir des centaines de vues.&lt;br/&gt;&lt;br/&gt;Quatre étapes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Every point is assigned to one of exactly this many groups, whether or not that many populations exist.</source>
            <translation>Chaque point est affecté à l'un d'exactement ce nombre de groupes, qu'il existe ou non autant de populations.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Everything up to the current step, accumulating as playback advances.</source>
            <translation>Tout jusqu'à l'étape courante, en s'accumulant au fil de la lecture.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Existing parameters of other overlay curves; double-click one to link to it.</source>
            <translation>Paramètres existants d'autres courbes de superposition ; double-cliquer sur l'un d'eux pour le lier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="49" />
            <source>Exit</source>
            <translation>Quitter</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="57" />
            <source>Exit code {code}</source>
            <translation>Code de sortie {code}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Expert options; the defaults are suitable for most users.</source>
            <translation>Options expert ; les valeurs par défaut conviennent à la plupart des utilisateurs.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Export CSV…</source>
            <translation>Exporter en CSV…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Export a publication figure.</source>
            <translation>Exporter une figure de publication.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1353" />
            <location filename="ndxplorer/app/features/overlays.py" line="1358" />
            <source>Export as CSV</source>
            <translation>Exporter en CSV</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1258" />
            <source>Export as CSV…</source>
            <translation>Exporter en CSV…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="894" />
            <source>Export failed:
{error}</source>
            <translation>Échec de l'export :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="901" />
            <source>Export publication figure</source>
            <translation>Exporter la figure pour publication</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Export the current plot as a publication-quality figure.</source>
            <translation>Exporter le graphique actuel sous forme de figure de qualité publication.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Export the visible rows and columns as CSV</source>
            <translation>Exporter les lignes et colonnes visibles en CSV</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1356" />
            <source>Exported to {path}</source>
            <translation>Exporté vers {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Export…</source>
            <translation>Exporter…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Expression</source>
            <translation>Expression</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Expression evaluated per burst; may use other column names.</source>
            <translation>Expression évaluée par burst ; peut utiliser d'autres noms de colonnes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="618" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="621" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="622" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="626" />
            <source>FRET</source>
            <translation>FRET</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="103" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="174" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="771" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="778" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="850" />
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>FRET calibration</source>
            <translation>Étalonnage FRET</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="57" />
            <source>FRET calibration (*.fretcal.json);;All files (*)</source>
            <translation>Étalonnage FRET (*.fretcal.json);;Tous les fichiers (*)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="726" />
            <source>FRET calibration cancelled; the constants are unchanged</source>
            <translation>Étalonnage FRET annulé ; les constantes restent inchangées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="760" />
            <source>FRET calibration — applied</source>
            <translation>Étalonnage FRET — appliqué</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="878" />
            <source>FRET calibration — loaded</source>
            <translation>Étalonnage FRET — chargé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="260" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="618" />
            <location filename="ndxplorer/app/features/accurate_fret/progress.view.json" line="0" />
            <source>FRET calibration…</source>
            <translation>Étalonnage FRET…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>FRET populations</source>
            <translation>Populations FRET</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Factor</source>
            <translation>Facteur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="441" />
            <location filename="ndxplorer/app/features/io.py" line="480" />
            <location filename="ndxplorer/app/model.py" line="206" />
            <source>Failed to load data: {error}</source>
            <translation>Échec du chargement des données : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="896" />
            <source>Failed to load file:
{error}</source>
            <translation>Échec du chargement du fichier :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="823" />
            <source>Failed to save CSV:
{error}</source>
            <translation>Échec de l'enregistrement du CSV :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1052" />
            <source>Failed to save default axis settings:
{error}</source>
            <translation>Échec de l'enregistrement des paramètres d'axe par défaut :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="380" />
            <source>Failed to save settings: {error}</source>
            <translation>Échec de l'enregistrement des paramètres : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="878" />
            <source>Failed to save:
{error}</source>
            <translation>Échec de l'enregistrement :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="629" />
            <location filename="ndxplorer/app/menus.py" line="22" />
            <source>File</source>
            <translation>Fichier</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="869" />
            <source>File axes:
X: {file_x}
Y: {file_y}
Current axes:
X: {x}
Y: {y}

Gaussians were loaded regardless.</source>
            <translation>Axes du fichier :
X : {file_x}
Y : {file_y}
Axes actuels :
X : {x}
Y : {y}

Les gaussiennes ont été chargées malgré tout.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="517" />
            <source>File read, but failed to parse config (will still load text):
{error}

Load as-is?</source>
            <translation>Fichier lu, mais l'analyse de la configuration a échoué (le texte sera tout de même chargé) :
{error}

Charger tel quel ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1190" />
            <source>Files</source>
            <translation>Fichiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="663" />
            <source>Filled Function:</source>
            <translation>Fonction remplie :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="666" />
            <source>Filled:</source>
            <translation>Remplie :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="663" />
            <source>Filled: y =</source>
            <translation>Remplie : y =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1331" />
            <source>Filter this column</source>
            <translation>Filtrer cette colonne</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1263" />
            <source>Filter this column…</source>
            <translation>Filtrer cette colonne…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Filter:</source>
            <translation>Filtre :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="319" />
            <location filename="ndxplorer/app/features/playback_export.py" line="259" />
            <source>Find informative projections</source>
            <translation>Trouver les projections informatives</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="75" />
            <source>Find informative projections (z axis)…</source>
            <translation>Trouver des projections informatives (axe z)…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="264" />
            <source>Find informative projections - help</source>
            <translation>Trouver des projections informatives - aide</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="74" />
            <source>Find informative projections…</source>
            <translation>Trouver des projections informatives…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="320" />
            <location filename="ndxplorer/app/features/playback_export.py" line="260" />
            <source>Find informative z parameters</source>
            <translation>Trouver les paramètres z informatifs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="411" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Find structure</source>
            <translation>Trouver la structure</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="100" />
            <source>Find the donor-only / acceptor-only / FRET populations in the loaded bursts and determine the correction factors from them.</source>
            <translation>Trouver les populations donneur seul / accepteur seul / FRET dans les bursts chargés et en déterminer les facteurs de correction.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="333" />
            <location filename="ndxplorer/analysis/vizrank.py" line="100" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="244" />
            <source>Finished</source>
            <translation>Terminé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="269" />
            <location filename="ndxplorer/app/features/analysis.py" line="512" />
            <source>Finished.</source>
            <translation>Terminé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Fit</source>
            <translation>Ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="69" />
            <source>Fit Gaussians</source>
            <translation>Ajuster des gaussiennes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Fit and draw the Gaussians in log scale on both axes (positive values only); off fits in the axes' own scale.</source>
            <translation>Ajuster et tracer les gaussiennes en échelle logarithmique sur les deux axes (valeurs positives uniquement) ; désactivé, l'ajustement se fait dans l'échelle propre des axes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="850" />
            <source>Fit curve to data</source>
            <translation>Ajuster la courbe aux données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="778" />
            <location filename="ndxplorer/app/features/analysis.py" line="805" />
            <source>Fit failed</source>
            <translation>Échec de l'ajustement</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="54" />
            <source>Fit gate to the population here</source>
            <translation>Ajuster le gate à la population ici</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Fit the Gaussians to the gated points shown on the map.</source>
            <translation>Ajuster les gaussiennes aux points du gate affichés sur la carte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Fit this curve's free parameters to the displayed data (the 2-D distribution, or a marginal histogram)</source>
            <translation>Ajuster les paramètres libres de cette courbe aux données affichées (la distribution 2D ou un histogramme marginal)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Fit through:</source>
            <translation>Ajuster via :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Fit to:</source>
            <translation>Ajuster à :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="783" />
            <source>Fitted {n} Gaussian</source>
            <translation>{n} gaussienne ajustée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="810" />
            <source>Fitted {n} Gaussian per population ({populations})</source>
            <translation>{n} gaussienne ajustée par population ({populations})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="784" />
            <source>Fitted {n} Gaussians</source>
            <translation>{n} gaussiennes ajustées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="811" />
            <source>Fitted {n} Gaussians per population ({populations})</source>
            <translation>{n} gaussiennes ajustées par population ({populations})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Fix new means by default</source>
            <translation>Fixer les nouvelles moyennes par défaut</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Fixed</source>
            <translation>Fixe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Fixed: a fit leaves it where it is.</source>
            <translation>Fixe : un ajustement le laisse inchangé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Folder</source>
            <translation>Dossier</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="555" />
            <source>Folder for Burst IDs</source>
            <translation>Dossier pour les ID de burst</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1373" />
            <source>Folder for Clustering Data</source>
            <translation>Dossier des données de clustering</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io_service.py" line="161" />
            <source>Folders</source>
            <translation>Dossiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="860" />
            <source>Follow the operating system's language.</source>
            <translation>Suivre la langue du système d'exploitation.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Font Settings</source>
            <translation>Paramètres de police</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Font sizes and colours of the plot titles and axis labels.</source>
            <translation>Tailles et couleurs de police des titres de graphique et des étiquettes d'axe.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>For most users, the default settings provide optimal performance. Advanced users can fine-tune these settings for specific workloads.</source>
            <translation>Pour la plupart des utilisateurs, les paramètres par défaut offrent des performances optimales. Les utilisateurs avancés peuvent les affiner pour des charges de travail spécifiques.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="43" />
            <source>Forget session</source>
            <translation>Oublier la session</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Format:</source>
            <translation>Format :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Free parameters are optimised, fixed ones held. Constants and crosslinked parameters start fixed -- free them to fit them.</source>
            <translation>Les paramètres libres sont optimisés, les fixes sont maintenus. Les constantes et les paramètres liés démarrent fixes -- les libérer pour les ajuster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="630" />
            <source>From MMFDB…</source>
            <translation>Depuis MMFDB…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Full report</source>
            <translation>Rapport complet</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="171" />
            <source>Functions</source>
            <translation>Fonctions</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="290" />
            <location filename="ndxplorer/app/features/analysis.py" line="316" />
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>GMM Settings</source>
            <translation>Paramètres GMM</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="314" />
            <source>GMM settings saved to your ndX user folder.</source>
            <translation>Paramètres GMM enregistrés dans le dossier utilisateur ndX.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="535" />
            <source>Gate fitted to the population at ({x}, {y}): {n} points</source>
            <translation>Gate ajusté à la population en ({x}, {y}) : {n} points</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Gate the plot on the z-range slider</source>
            <translation>Appliquer au graphique un gate via le curseur de plage z</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="265" />
            <source>Gate: inside vs outside</source>
            <translation>Gate : à l'intérieur vs à l'extérieur</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="272" />
            <source>Gates: one population per gate</source>
            <translation>Gates : une population par gate</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Gates: range limits on parameters that select bursts; edit cells to change them.</source>
            <translation>Gates : limites de plage sur des paramètres qui sélectionnent des bursts ; modifier les cellules pour les changer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Gating dimensions</source>
            <translation>Dimensions de gating</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="378" />
            <source>Gating dimensions: {dims}</source>
            <translation>Dimensions de gating : {dims}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="865" />
            <location filename="ndxplorer/app/features/analysis.py" line="888" />
            <source>Gaussian Files (*.json *.csv);;All Files (*)</source>
            <translation>Fichiers gaussiennes (*.json *.csv);;Tous les fichiers (*)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="57" />
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Gaussian Fit</source>
            <translation>Ajustement gaussien</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Gaussian mixture</source>
            <translation>Mélange gaussien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Gaussians</source>
            <translation>Gaussiennes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>General Cache (MB):</source>
            <translation>Cache général (Mo) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Generate</source>
            <translation>Générer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Generate Reports</source>
            <translation>Générer les rapports</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Generate the report and follow its progress.</source>
            <translation>Générer le rapport et suivre sa progression.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="646" />
            <source>Generating reports...</source>
            <translation>Génération des rapports...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="644" />
            <source>Generating reports... {index}/{total}: {folder}</source>
            <translation>Génération des rapports... {index}/{total} : {folder}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="733" />
            <source>Generation canceled.</source>
            <translation>Génération annulée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="454" />
            <source>Give how many populations, or their names (HF, LF).</source>
            <translation>Indiquer le nombre de populations ou leurs noms (HF, LF).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Green channels:</source>
            <translation>Canaux verts :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="418" />
            <source>Guide {n}/{total}: {title}</source>
            <translation>Guide {n}/{total} : {title}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>HDBSCAN</source>
            <translation>HDBSCAN</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="295" />
            <source>HDBSCAN finished</source>
            <translation>HDBSCAN terminé</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="90" />
            <source>HDF5 files</source>
            <translation>Fichiers HDF5</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Half-width, in bins, of the window a clicked Gaussian's width is measured in.</source>
            <translation>Demi-largeur, en bins, de la fenêtre dans laquelle est mesurée la largeur d'une gaussienne cliquée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Has a report already</source>
            <translation>A déjà un rapport</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="442" />
            <source>Held fixed (not calibrated):</source>
            <translation>Maintenus fixes (non étalonnés) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="80" />
            <location filename="ndxplorer/app/menus.py" line="81" />
            <source>Help</source>
            <translation>Aide</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Hi</source>
            <translation>Sup.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Hide all</source>
            <translation>Tout masquer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Hide columns that contain no values</source>
            <translation>Masquer les colonnes sans valeurs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Hide empty</source>
            <translation>Masquer les vides</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Hide every column in the burst table.</source>
            <translation>Masquer chaque colonne du tableau des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1264" />
            <source>Hide this column</source>
            <translation>Masquer cette colonne</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Histogram</source>
            <translation>Histogramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Histogram Computation</source>
            <translation>Calcul des histogrammes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Histogram Threads:</source>
            <translation>Threads d'histogramme :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Histogram computation and caching settings, saved to the settings file.</source>
            <translation>Paramètres de calcul et de mise en cache des histogrammes, enregistrés dans le fichier de paramètres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="37" />
            <source>Histograms</source>
            <translation>Histogrammes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Hold the centre of a Gaussian added by a click on the map.</source>
            <translation>Maintenir le centre d'une gaussienne ajoutée par un clic sur la carte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>How</source>
            <translation>Comment</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>How bursts count in the Separation score. Low-photon bursts are wide (shot noise) and fill the valleys between FRET populations: weight each burst by its photons, or keep only bursts with at least Min photons. Needs a 'Number of Photons' column.</source>
            <translation>Comment les bursts comptent dans le score de séparation. Les bursts à faibles photons sont larges (bruit de grenaille) et comblent les vallées entre populations FRET : pondérer chaque burst par ses photons, ou ne garder que les bursts ayant au moins Min. photons. Nécessite une colonne 'Number of Photons'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>How conservative the density estimate is. Larger leaves more points unlabelled as noise.</source>
            <translation>Degré de prudence de l'estimation de densité. Plus grand, plus de points restent non étiquetés comme bruit.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="107" />
            <source>How do you want to merge the new data?</source>
            <translation>Comment fusionner les nouvelles données ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>How many (3: populations 0, 1, 2), or their names (HF, LF).</source>
            <translation>Combien (3 : populations 0, 1, 2) ou leurs noms (HF, LF).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="656" />
            <source>How many bursts fall into clearly separated islands: donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line. 0: one population; 0.5: two equal islands with empty space between; 0.67: three.</source>
            <translation>Combien de bursts tombent dans des îlots nettement séparés : espèces donneur seul, accepteur seul et FRET en E vs S, une population dynamique hors de la ligne FRET statique. 0 : une population ; 0,5 : deux îlots égaux séparés par un espace vide ; 0,67 : trois.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>How many slices the range is cut into. The width of one slice is the range divided by this, so a longer measurement gets wider slices and the playback lasts the same time either way. An index column (frames) starts at one step per value.</source>
            <translation>En combien de tranches la plage est découpée. La largeur d'une tranche est la plage divisée par cette valeur : une mesure plus longue a donc des tranches plus larges et la lecture dure le même temps. Une colonne d'indices (images) démarre à une étape par valeur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>How the UMAP embedding is initialised (e.g. spectral or random).</source>
            <translation>Mode d'initialisation de l'immersion UMAP (p. ex. spectrale ou aléatoire).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>How the donor-only, acceptor-only and FRET populations are found in the gating dimensions. 'HDBSCAN' (default) finds dense clusters of any shape and leaves sparse bursts unassigned, so a smeared or non-Gaussian population is not split into several components or merged with a neighbour; outliers are removed per dimension before the dimensions are scaled. 'Gaussian mixture' fits Gaussian components and picks their number by the BIC. On cal1 with S+E the mixture took 45 s and lost the donor-only class; HDBSCAN took 3 s. Only used when gating dimensions beyond S are chosen. Needs a tttrlib whose calibration has the population_method option; otherwise this choice is disabled and the Gaussian mixture is used.</source>
            <translation>Comment les populations donneur seul, accepteur seul et FRET sont trouvées dans les dimensions de gating. 'HDBSCAN' (par défaut) trouve des clusters denses de forme quelconque et laisse les bursts épars non assignés, si bien qu'une population étalée ou non gaussienne n'est ni scindée en plusieurs composantes ni fusionnée avec une voisine ; les valeurs aberrantes sont retirées par dimension avant la mise à l'échelle des dimensions. 'Mélange gaussien' ajuste des composantes gaussiennes et choisit leur nombre par le BIC. Sur cal1 avec S+E, le mélange a pris 45 s et perdu la classe donneur seul ; HDBSCAN a pris 3 s. Utilisé seulement si des dimensions de gating au-delà de S sont choisies. Nécessite une tttrlib dont l'étalonnage a l'option population_method ; sinon ce choix est désactivé et le mélange gaussien est utilisé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>How the gamma correction factor is obtained for the accurate FRET calibration.</source>
            <translation>Comment le facteur de correction gamma est obtenu pour l'étalonnage FRET précis.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="96" />
            <source>IRF / reference measurement</source>
            <translation>IRF / mesure de référence</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>IRF / reference:</source>
            <translation>IRF / référence :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="127" />
            <source>IRF{suffix}: {photons} photons, {percent} % flat background removed; the file's f_rep is {header} MHz (constant f_rep {f_rep})</source>
            <translation>IRF{suffix} : {photons} photons, {percent} % de bruit de fond plat retiré ; le f_rep du fichier est {header} MHz (f_rep constant {f_rep})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="398" />
            <source>Identifiable: no — per-population γ needs, for every FRET population, a donor lifetime that puts it on the static FRET line (0.05 &lt; E &lt; 0.95), and at least two populations</source>
            <translation>Identifiable : non — un γ par population exige, pour chaque population FRET, une durée de vie du donneur qui la place sur la droite FRET statique (0.05 &lt; E &lt; 0.95), et au moins deux populations</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="397" />
            <source>Identifiable: yes</source>
            <translation>Identifiable : oui</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>If checked histogram as are weighted by selected axis</source>
            <translation>Si coché, les histogrammes sont pondérés par l'axe sélectionné</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>If checked the axis is changed and no default scale is defined the axis scale is updated.</source>
            <translation>Si coché et que l'axe est modifié sans échelle par défaut définie, l'échelle de l'axe est mise à jour.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="629" />
            <location filename="ndxplorer/app/menus.py" line="23" />
            <source>Import</source>
            <translation>Importer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="24" />
            <source>Import Text files (*.csv,*.dat)</source>
            <translation>Importer des fichiers texte (*.csv,*.dat)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1096" />
            <source>In the browser the page loads the newest published build: reload the page.</source>
            <translation>Dans le navigateur, la page charge la dernière version publiée : recharger la page.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Include X/Y marginal histograms</source>
            <translation>Inclure les histogrammes marginaux X/Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Initial value of the new overlay parameter.</source>
            <translation>Valeur initiale du nouveau paramètre de superposition.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Initialisation:</source>
            <translation>Initialisation :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="231" />
            <source>Initializing UMAP computation...</source>
            <translation>Initialisation du calcul UMAP...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1339" />
            <source>Install</source>
            <translation>Installer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1333" />
            <source>Installation was cancelled or failed, so this method cannot run.</source>
            <translation>L'installation a été annulée ou a échoué : cette méthode ne peut pas s'exécuter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1103" />
            <source>Installed: ndXplorer {version}</source>
            <translation>Installé : ndXplorer {version}</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="332" />
            <source>Installing {packages} with {solver}…</source>
            <translation>Installation de {packages} avec {solver}…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1349" />
            <source>Installing {package}</source>
            <translation>Installation de {package}</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Integrate</source>
            <translation>Intégrer</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1073" />
            <source>Invalid Merge Mode</source>
            <translation>Mode de fusion non valide</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="677" />
            <source>Invalid config</source>
            <translation>Configuration invalide</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1074" />
            <source>Invalid mode: {mode}. Must be 'columns' or 'rows'.</source>
            <translation>Mode non valide : {mode}. Doit être 'columns' ou 'rows'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Invert</source>
            <translation>Inverser</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="312" />
            <source>K-means finished</source>
            <translation>K-means terminé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Keep the bursts outside the range instead of inside.</source>
            <translation>Conserver les bursts hors de la plage plutôt que dans la plage.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Keep this calibration: into the .pto measurement it was determined from, or a separate *.fretcal.json file.</source>
            <translation>Conserver cet étalonnage : dans la mesure .pto dont il est issu, ou dans un fichier *.fretcal.json séparé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Kind:</source>
            <translation>Type :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Label</source>
            <translation>Étiquette</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Label every burst of the table by the island of the view on the axes and write the labels as the clusters (Cluster Label and Cluster Probability, replacing K-means/HDBSCAN clusters) and as a column 'Island Label (x vs y)'. Islands are numbered by size, largest first. The probability is the island's share of the smoothed density at the burst: 1 deep inside, falling toward 1/2 at a ridge. Then the Cluster spin box, colour, gates and Save Burst IDs work on the islands.</source>
            <translation>Étiqueter chaque burst du tableau selon l'îlot de la vue sur les axes et écrire les étiquettes comme clusters (Cluster Label et Cluster Probability, remplaçant les clusters K-means/HDBSCAN) et comme colonne 'Island Label (x vs y)'. Les îlots sont numérotés par taille, le plus grand en premier. La probabilité est la part de l'îlot dans la densité lissée au niveau du burst : 1 en plein cœur, tombant vers 1/2 sur une crête. Ensuite, le champ Cluster, la couleur, les gates et Enregistrer les ID de bursts agissent sur les îlots.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Labels:</source>
            <translation>Étiquettes :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="857" />
            <location filename="ndxplorer/app/features/settings.py" line="923" />
            <source>Language</source>
            <translation>Langue</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Learning rate:</source>
            <translation>Taux d'apprentissage :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Leave out points with an infinite value on a plotted axis.</source>
            <translation>Exclure les points de valeur infinie sur un axe tracé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Leave out points with no value on a plotted axis.</source>
            <translation>Exclure les points sans valeur sur un axe tracé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Leave the figure background transparent.</source>
            <translation>Laisser l'arrière-plan de la figure transparent.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Left Axis</source>
            <translation>Axe gauche</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Left Axis Label</source>
            <translation>Étiquette de l'axe gauche</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Limit histograms to overlay selection, dynamic</source>
            <translation>Limiter les histogrammes à la sélection de superposition, dynamique</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="161" />
            <source>Linear decomposition. Reports which parameters carry the variance.</source>
            <translation>Décomposition linéaire. Indique quels paramètres portent la variance.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="530" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Link</source>
            <translation>Lier</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Link the new parameter to the selected existing parameter so they share one value.</source>
            <translation>Lier le nouveau paramètre au paramètre existant sélectionné pour qu'ils partagent une seule valeur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="488" />
            <source>Link {name}</source>
            <translation>Lier {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Linker σ (Å)</source>
            <translation>σ du linker (Å)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="416" />
            <source>Link…</source>
            <translation>Lier…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>List of analysis folders that the report is generated for.</source>
            <translation>Liste des dossiers d'analyse pour lesquels le rapport est généré.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>List of the overlay curves drawn over the plots, with their parameters.</source>
            <translation>Liste des courbes de superposition tracées sur les graphiques, avec leurs paramètres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <source>Live log of the UMAP embedding run (read only).</source>
            <translation>Journal en direct de l'exécution de l'intégration UMAP (lecture seule).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Lo</source>
            <translation>Inf.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Load</source>
            <translation>Charger</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="895" />
            <source>Load Error</source>
            <translation>Erreur de chargement</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="887" />
            <source>Load Gaussian Fits</source>
            <translation>Charger les ajustements gaussiens</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="899" />
            <source>Load Gaussians</source>
            <translation>Charger les gaussiennes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Load Gaussians from a .json or .csv file.</source>
            <translation>Charger des gaussiennes depuis un fichier .json ou .csv.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="300" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Load Mask</source>
            <translation>Charger le masque</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Load a mask from an integer TIFF (one label per bin, the map's binning).</source>
            <translation>Charger un masque depuis un TIFF d'entiers (une étiquette par bin, avec le binning de la carte).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Load a report.yaml (YAML or JSON)</source>
            <translation>Charger un fichier report.yaml (YAML ou JSON)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="829" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="843" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="882" />
            <source>Load calibration</source>
            <translation>Charger un étalonnage</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="626" />
            <source>Load calibration…</source>
            <translation>Charger un étalonnage…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Load gates from a file.</source>
            <translation>Charger des gates depuis un fichier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="53" />
            <source>Load settings</source>
            <translation>Charger les paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="845" />
            <source>Load the most recent one? No opens a file instead.</source>
            <translation>Charger le plus récent ? Non ouvre un fichier à la place.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="493" />
            <source>Loaded {rows} rows from {name}</source>
            <translation>{rows} lignes chargées depuis {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="474" />
            <source>Loading</source>
            <translation>Chargement</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="481" />
            <source>Loading failed: {error}</source>
            <translation>Échec du chargement : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="473" />
            <location filename="ndxplorer/app/features/io.py" line="474" />
            <source>Loading {names}…</source>
            <translation>Chargement de {names}…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Load…</source>
            <translation>Charger…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Local window (bins):</source>
            <translation>Fenêtre locale (bins) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Log Gauss</source>
            <translation>Gauss log</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="151" />
            <source>Log tail</source>
            <translation>Fin du journal</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Logarithmic axis</source>
            <translation>Axe logarithmique</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Lower bound of the gate on this parameter.</source>
            <translation>Borne inférieure du gate sur ce paramètre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Lower bound. −∞: none. Type a number to set it, ∞ (or inf) to remove it.</source>
            <translation>Borne inférieure. −∞ : aucune. Saisir un nombre pour la définir, ∞ (ou inf) pour la supprimer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Lower colour limit of the 2-D histogram.</source>
            <translation>Limite de couleur inférieure de l'histogramme 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="89" />
            <source>MFD HDF5 files</source>
            <translation>Fichiers HDF5 MFD</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="46" />
            <source>Make Report</source>
            <translation>Créer un rapport</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Make a report for every listed analysis folder that has none</source>
            <translation>Créer un rapport pour chaque dossier d'analyse listé qui n'en a pas</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="408" />
            <source>Make scalar</source>
            <translation>Convertir en scalaire</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="421" />
            <source>Make vector…</source>
            <translation>Convertir en vecteur…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="435" />
            <source>Make {name} a vector</source>
            <translation>Faire de {name} un vecteur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Marginals</source>
            <translation>Marges</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="332" />
            <source>Mask file failed: {error}</source>
            <translation>Échec du fichier de masque : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="292" />
            <source>Mask gate added: category {category}, {bins} bins</source>
            <translation>Gate de masque ajouté : catégorie {category}, {bins} bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="327" />
            <source>Mask loaded from {path}</source>
            <translation>Masque chargé depuis {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="330" />
            <source>Mask saved to {path}</source>
            <translation>Masque enregistré dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Max</source>
            <translation>Max</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Max iterations:</source>
            <translation>Itérations max. :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Maximum number of EM iterations of the Gaussian mixture fit.</source>
            <translation>Nombre maximal d'itérations EM de l'ajustement du mélange gaussien.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Mean fluorescence-weighted lifetime of the population in ns.</source>
            <translation>Durée de vie moyenne pondérée par la fluorescence de la population, en ns.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Mean inter-dye distance R in angstrom derived from the FRET efficiency.</source>
            <translation>Distance moyenne R entre les colorants en angströms, déduite de l'efficacité FRET.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Mean stoichiometry S of the population.</source>
            <translation>Stœchiométrie moyenne S de la population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="100" />
            <location filename="ndxplorer/app/features/session.py" line="255" />
            <source>Measurement</source>
            <translation>Mesure</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Measurement:</source>
            <translation>Mesure :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Memory &amp; Caching</source>
            <translation>Mémoire et cache</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Memory limit for general-purpose caching (selections, computations, etc.). Recommended range: 10-500 MB</source>
            <translation>Limite de mémoire pour le cache général (sélections, calculs, etc.). Plage recommandée : 10-500 Mo</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Merge</source>
            <translation>Fusionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Method:</source>
            <translation>Méthode :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Metric:</source>
            <translation>Métrique :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Min</source>
            <translation>Min</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Min photons</source>
            <translation>Min. photons</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Min. cluster size:</source>
            <translation>Taille min. des clusters :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Min. distance:</source>
            <translation>Distance min. :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Min. reference bursts</source>
            <translation>Bursts de référence min.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Min. samples:</source>
            <translation>Échantillons min. :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Minimum spacing of embedded points. Smaller = tighter clumps.</source>
            <translation>Espacement minimal des points intégrés. Plus petit = amas plus serrés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Mode</source>
            <translation>Mode</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="382" />
            <source>Mode: {mode}</source>
            <translation>Mode : {mode}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="387" />
            <source>Model selection: not run (no acceptor-excitation channel or no FRET population)</source>
            <translation>Sélection de modèle : non exécutée (pas de canal d'excitation de l'accepteur ou pas de population FRET)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="385" />
            <source>Model selection: not run — scalar factors only</source>
            <translation>Sélection de modèle : non exécutée — facteurs scalaires uniquement</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="393" />
            <source>Model selection: {selected} — BIC shared {bic_shared}, per population {bic_species}</source>
            <translation>Sélection de modèle : {selected} — BIC partagé {bic_shared}, par population {bic_species}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>NaN</source>
            <translation>NaN</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Name</source>
            <translation>Nom</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Name of the burst-table column.</source>
            <translation>Nom de la colonne du tableau des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Name of the column that the equation writes.</source>
            <translation>Nom de la colonne dans laquelle l'équation écrit.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Name of the new overlay parameter.</source>
            <translation>Nom du nouveau paramètre de superposition.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Name of the parameter or constant.</source>
            <translation>Nom du paramètre ou de la constante.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Names</source>
            <translation>Noms</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1160" />
            <source>Names &amp; functions</source>
            <translation>Noms et fonctions</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Names &amp; functions you can use</source>
            <translation>Noms et fonctions utilisables</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Navigation: Up/Down, PageUp/PageDown and Home/End move the selection; a click on a box toggles it.</source>
            <translation>Navigation : Haut/Bas, Page préc./suiv. et Début/Fin déplacent la sélection ; un clic sur une case la bascule.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Neighbours:</source>
            <translation>Voisins :</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1051" />
            <source>New Columns Found</source>
            <translation>Nouvelles colonnes trouvées</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="476" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="438" />
            <source>New columns: {columns}</source>
            <translation>Nouvelles colonnes : {columns}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1052" />
            <source>New data contains columns not in current data: {names}. Only rows of existing columns will be appended.</source>
            <translation>Les nouvelles données contiennent des colonnes absentes des données actuelles : {names}. Seules les lignes des colonnes existantes seront ajoutées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1031" />
            <source>New data has {new} rows, current has {current} rows. Not merging.</source>
            <translation>Les nouvelles données ont {new} lignes, les actuelles {current}. Fusion annulée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="438" />
            <source>Next</source>
            <translation>Suivant</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis.py" line="141" />
            <location filename="ndxplorer/app/features/analysis.py" line="1184" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>No</source>
            <translation>Non</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="621" />
            <source>No .bst files were found in the selected folder.</source>
            <translation>Aucun fichier .bst n'a été trouvé dans le dossier sélectionné.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="287" />
            <source>No .bur files in 'bi4_bur' or 'bur'.</source>
            <translation>Aucun fichier .bur dans 'bi4_bur' ou 'bur'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="757" />
            <source>No 2D histogram available. Fit is restricted to visible data; please update histogram first.</source>
            <translation>Aucun histogramme 2D disponible. L'ajustement est limité aux données visibles ; mettre d'abord à jour l'histogramme.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="506" />
            <location filename="ndxplorer/app/features/playback_export.py" line="877" />
            <source>No 2D histogram is available yet — load data and update the plot first.</source>
            <translation>Aucun histogramme 2D disponible pour l'instant — charger d'abord des données et actualiser le graphique.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="620" />
            <source>No BST Files Found</source>
            <translation>Aucun fichier BST trouvé</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="895" />
            <source>No CSV-like files found in zip: {name}</source>
            <translation>Aucun fichier de type CSV trouvé dans le ZIP : {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="631" />
            <source>No ChiSurf connection. Open ndX from ChiSurf, or start it with --chisurf-rpc host:port.</source>
            <translation>Pas de connexion ChiSurf. Ouvrez ndX depuis ChiSurf, ou lancez-le avec --chisurf-rpc host:port.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1366" />
            <source>No Clustering Data</source>
            <translation>Aucune donnée de clustering</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1058" />
            <source>No Common Columns</source>
            <translation>Aucune colonne commune</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1606" />
            <source>No Data</source>
            <translation>Aucune donnée</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="464" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="170" />
            <source>No Gaussians</source>
            <translation>Aucune gaussienne</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="825" />
            <source>No HDF5 files in zip: {name}</source>
            <translation>Aucun fichier HDF5 dans le ZIP : {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="465" />
            <location filename="ndxplorer/app/features/settings.py" line="684" />
            <source>No analysis folders found</source>
            <translation>Aucun dossier d'analyse trouvé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="758" />
            <source>No analysis folders to clear.</source>
            <translation>Aucun dossier d'analyse à vider.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="466" />
            <source>No analysis folders were found in the dropped directory/directories.</source>
            <translation>Aucun dossier d'analyse trouvé dans le ou les répertoires déposés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="475" />
            <location filename="ndxplorer/app/features/selection.py" line="485" />
            <source>No clipboard to copy to here.</source>
            <translation>Aucun presse-papiers disponible pour copier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1367" />
            <source>No clustering data available. Please apply clustering before saving.</source>
            <translation>Aucune donnée de clustering disponible. Appliquer un clustering avant d'enregistrer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="424" />
            <source>No column to play back</source>
            <translation>Aucune colonne à lire</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1215" />
            <source>No columns are selected, so only the current X, Y and Z axes will be used — which rarely groups the data well.

Choose columns now?</source>
            <translation>Aucune colonne n'est sélectionnée : seuls les axes X, Y et Z actuels seront utilisés, ce qui regroupe rarement bien les données.

Choisir des colonnes maintenant ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1295" />
            <source>No components could be computed from the selected columns.</source>
            <translation>Aucune composante n'a pu être calculée à partir des colonnes sélectionnées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="470" />
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="475" />
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="479" />
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="488" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="186" />
            <location filename="ndxplorer/app/features/analysis.py" line="1237" />
            <source>No data</source>
            <translation>Aucune donnée</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="268" />
            <source>No data available for clustering.</source>
            <translation>Aucune donnée disponible pour le clustering.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="470" />
            <source>No data available for fitting.</source>
            <translation>Aucune donnée disponible pour l'ajustement.</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="531" />
            <source>No data found in folder: {folder}</source>
            <translation>Aucune donnée trouvée dans le dossier : {folder}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="489" />
            <source>No data in {paths}</source>
            <translation>Aucune donnée dans {paths}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/model.py" line="209" />
            <source>No data in {path}</source>
            <translation>Aucune donnée dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="634" />
            <source>No data loaded.</source>
            <translation>Aucune donnée chargée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1606" />
            <source>No data loaded—nothing to show.</source>
            <translation>Aucune donnée chargée : rien à afficher.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="476" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="187" />
            <source>No data within the visible histogram range to fit.</source>
            <translation>Aucune donnée dans la plage visible de l'histogramme à ajuster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1190" />
            <source>No file service is available in this window.</source>
            <translation>Aucun service de fichiers n'est disponible dans cette fenêtre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="899" />
            <source>No file service to save with.</source>
            <translation>Aucun service de fichiers pour enregistrer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="803" />
            <source>No finite pairs, or a constant column.</source>
            <translation>Aucune paire finie, ou une colonne constante.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>No folder selected</source>
            <translation>Aucun dossier sélectionné</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="680" />
            <location filename="ndxplorer/app/features/settings.py" line="758" />
            <source>No folders</source>
            <translation>Aucun dossier</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="520" />
            <source>No gate: no data on the plot.</source>
            <translation>Pas de gate : aucune donnée dans le graphique.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="528" />
            <source>No gate: {reason}</source>
            <translation>Pas de gate : {reason}</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>No gating: the whole measurement at once.</source>
            <translation>Pas de gating : toute la mesure à la fois.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="756" />
            <source>No histogram</source>
            <translation>Aucun histogramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="596" />
            <source>No images found</source>
            <translation>Aucune image trouvée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="506" />
            <source>No other parameters are open to link to (a curve, the Gaussians or a fit).</source>
            <translation>Aucun autre paramètre n'est disponible pour la liaison (une courbe, les gaussiennes ou un ajustement).</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1058" />
            <source>No overlapping columns. Cannot append rows.</source>
            <translation>Aucune colonne commune. Impossible d'ajouter des lignes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="807" />
            <source>No overlay data available yet. Create/update overlays first.</source>
            <translation>Aucune donnée de superposition disponible. Créer/mettre à jour d'abord les superpositions.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="177" />
            <source>No populations</source>
            <translation>Aucune population</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="489" />
            <source>No positive data available on log-scaled axis for fitting.</source>
            <translation>Aucune donnée positive disponible sur l'axe logarithmique pour l'ajustement.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="770" />
            <source>No report folders were found to delete.</source>
            <translation>Aucun dossier de rapport à supprimer n'a été trouvé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="454" />
            <source>No row selected.</source>
            <translation>Aucune ligne sélectionnée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="641" />
            <source>No selection. Draw a gate first — the whole table would be sent.</source>
            <translation>Aucune sélection. Dessinez d'abord un gate — sinon toute la table serait envoyée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="143" />
            <source>No stored table {name}; the project holds: {names}</source>
            <translation>Aucun tableau enregistré {name} ; le projet contient : {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="56" />
            <source>No such project: {path}</source>
            <translation>Projet introuvable : {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="900" />
            <source>No valid Gaussian rows found in the selected file.</source>
            <translation>Aucune ligne gaussienne valide trouvée dans le fichier sélectionné.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="685" />
            <source>No valid analysis subfolders were found. Please check your selection.</source>
            <translation>Aucun sous-dossier d'analyse valide trouvé. Veuillez vérifier la sélection.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="811" />
            <source>No visible curves to save.</source>
            <translation>Aucune courbe visible à enregistrer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="375" />
            <source>Noise</source>
            <translation>Bruit</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="172" />
            <source>Non-linear projection to 2-3 dimensions for visual inspection.</source>
            <translation>Projection non linéaire en 2-3 dimensions pour inspection visuelle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1237" />
            <source>None of the chosen columns is in the table.</source>
            <translation>Aucune des colonnes choisies ne figure dans le tableau.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Normalized density</source>
            <translation>Densité normalisée</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Not a correction factor — it converts efficiency to distance. Off by default: it belongs to the dye pair and its environment, not to this measurement.</source>
            <translation>Ce n'est pas un facteur de correction — il convertit l'efficacité en distance. Désactivé par défaut : il appartient à la paire de fluorophores et à son environnement, pas à cette mesure.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="287" />
            <source>Not enough data points for HDBSCAN: need at least {n} (min. samples).</source>
            <translation>Pas assez de points de données pour HDBSCAN : au moins {n} requis (min. samples).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="284" />
            <source>Not enough data points for HDBSCAN: need at least {n}.</source>
            <translation>Pas assez de points de données pour HDBSCAN : au moins {n} requis.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="303" />
            <source>Not enough data points for K-means: need at least {n} (one per cluster).</source>
            <translation>Pas assez de points de données pour K-means : au moins {n} requis (un par cluster).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="404" />
            <source>Not enough data points for UMAP: need at least {n}.</source>
            <translation>Pas assez de points de données pour UMAP : au moins {n} requis.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="352" />
            <source>Not in the browser. ChiSurf's RPC needs a native socket; run ndX on the desktop to send a selection</source>
            <translation>Pas dans le navigateur. Le RPC de ChiSurf nécessite un socket natif ; exécuter ndX sur le bureau pour envoyer une sélection</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="356" />
            <source>Not stored automatically: {error}</source>
            <translation>Non enregistré automatiquement : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="863" />
            <source>Note: {note}</source>
            <translation>Remarque : {note}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="138" />
            <source>Nothing is painted. Enable drawing and paint on the 2-D plot first.</source>
            <translation>Rien n'est peint. Activer d'abord le dessin et peindre sur le graphique 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="769" />
            <source>Nothing to clear</source>
            <translation>Rien à supprimer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="690" />
            <source>Nothing to do</source>
            <translation>Rien à faire</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="864" />
            <source>Nothing would change.</source>
            <translation>Rien ne changerait.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Number of 1D bins</source>
            <translation>Nombre de bins 1D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Number of 2D bins</source>
            <translation>Nombre de bins 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Number of bursts in the population.</source>
            <translation>Nombre de bursts dans la population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Number of points:</source>
            <translation>Nombre de points :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Number of sigmas used for Gaussian burst selection (1.0 = 1σ).</source>
            <translation>Nombre de sigmas utilisé pour la sélection de bursts gaussienne (1.0 = 1σ).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/text.view.json" line="0" />
            <location filename="ndxplorer/app/frame.py" line="745" />
            <source>OK</source>
            <translation>OK</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Off</source>
            <translation>Désactivé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>On</source>
            <translation>Activé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="667" />
            <source>One population in {x} vs {y}: no islands to use as clusters.</source>
            <translation>Une population dans {x} vs {y} : aucun îlot utilisable comme cluster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="795" />
            <source>One population: no significant density valley over {n} sampled bursts.</source>
            <translation>Une seule population : aucune vallée de densité significative sur {n} bursts échantillonnés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>One slice at a time: the data inside the current playback window.</source>
            <translation>Une tranche à la fois : les données dans la fenêtre de lecture courante.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>One step back</source>
            <translation>Une étape en arrière</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>One step forward</source>
            <translation>Une étape en avant</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="441" />
            <source>One value of {name} per population; a burst takes its population's value, and a burst in no population the global one.</source>
            <translation>Une valeur de {name} par population ; un burst prend la valeur de sa population, et un burst sans population la valeur globale.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>One value per population, picked by a column of the burst table.</source>
            <translation>Une valeur par population, choisie par une colonne du tableau des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>One value shared by all bursts.</source>
            <translation>Une valeur partagée par tous les bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>One γ for all FRET populations, or one per population. A local environment can change a dye's quantum yield in one population, and with it that population's γ; β, α and δ stay shared.

'Off' writes one global factor set, as before — the per-population model is not tried.
'Auto' (default) fits both a shared and a per-population γ and keeps the per-population one only when it lowers the BIC.
'On' writes the per-population γ whenever it is identifiable, even when the BIC prefers the shared one.

Per-population γ is only identifiable with lifetimes: every FRET population needs a donor lifetime (the static FRET line pins its E), and there must be at least two populations. Without a donor lifetime column all three modes give the same scalar result. Written γ vectors appear in the Parameters tab; right-click &gt; Make scalar removes one again. The test itself is cheap; it is the gating dimensions below that cost time.</source>
            <translation>Un γ pour toutes les populations FRET, ou un par population. Un environnement local peut changer le rendement quantique d'un fluorophore dans une population, et donc le γ de cette population ; β, α et δ restent partagés.

'Désactivé' écrit un seul jeu de facteurs global, comme avant — le modèle par population n'est pas essayé.
'Auto' (par défaut) ajuste un γ partagé et un γ par population et ne garde ce dernier que s'il abaisse le BIC.
'Activé' écrit le γ par population dès qu'il est identifiable, même si le BIC préfère le partagé.

Le γ par population n'est identifiable qu'avec les durées de vie : chaque population FRET a besoin d'une durée de vie du donneur (la droite FRET statique fixe son E), et il faut au moins deux populations. Sans colonne de durée de vie du donneur, les trois modes donnent le même résultat scalaire. Les vecteurs γ écrits apparaissent dans l'onglet Paramètres ; clic droit &gt; Convertir en scalaire en supprime un. Le test lui-même est peu coûteux ; ce sont les dimensions de gating ci-dessous qui coûtent du temps.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="61" />
            <source>Only bursts with at least Min photons</source>
            <translation>Seulement les bursts avec au moins Min. photons</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Open</source>
            <translation>Ouvrir</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="86" />
            <source>Open CSV Files</source>
            <translation>Ouvrir des fichiers CSV</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="167" />
            <location filename="ndxplorer/io/loading.py" line="102" />
            <source>Open ChiSurf Project</source>
            <translation>Ouvrir un projet ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Open FCS Correlator Wizard to correlate BST files</source>
            <translation>Ouvrir l'assistant du corrélateur FCS pour corréler les fichiers BST</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="92" />
            <source>Open MFD HDF5 Files</source>
            <translation>Ouvrir des fichiers HDF5 MFD</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="167" />
            <location filename="ndxplorer/io/loading.py" line="100" />
            <source>Open PTO Container</source>
            <translation>Ouvrir un conteneur PTO</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="94" />
            <location filename="ndxplorer/io/loading.py" line="97" />
            <source>Open Sampling Files</source>
            <translation>Ouvrir des fichiers d'échantillonnage</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="88" />
            <source>Open SmFRET Files</source>
            <translation>Ouvrir des fichiers smFRET</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="632" />
            <source>Open a burst selection registered in MMFDB (ChiSurf's database; {reason}).</source>
            <translation>Ouvrir une sélection de bursts enregistrée dans MMFDB (la base de données de ChiSurf ; {reason}).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="32" />
            <source>Open a sampling chain stored in a ChiSurf project; asks which one when the project holds several.</source>
            <translation>Ouvrir une chaîne d'échantillonnage stockée dans un projet ChiSurf ; demande laquelle si le projet en contient plusieurs.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Open clustering dialog: find structure (PCA, UMAP, HDBSCAN, K-means) in chosen columns.</source>
            <translation>Ouvrir la boîte de dialogue de clustering : trouver une structure (PCA, UMAP, HDBSCAN, K-means) dans les colonnes choisies.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="523" />
            <source>Open config</source>
            <translation>Ouvrir la configuration</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1132" />
            <source>Open equations</source>
            <translation>Ouvrir des équations</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="893" />
            <source>Open from MMFDB</source>
            <translation>Ouvrir depuis MMFDB</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Open nothing.</source>
            <translation>Ne rien ouvrir.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="93" />
            <source>Open sampling folder</source>
            <translation>Ouvrir un dossier d'échantillonnage</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Open the FCS correlator wizard afterwards to correlate the burst photon files.</source>
            <translation>Ouvrir ensuite l'assistant du corrélateur FCS pour corréler les fichiers de photons des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Open the chosen table.</source>
            <translation>Ouvrir le tableau choisi.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="894" />
            <source>Opening a burst selection registered in MMFDB needs ChiSurf's MMFDB client: it works when ndX runs inside ChiSurf.</source>
            <translation>L'ouverture d'une sélection de bursts enregistrée dans MMFDB nécessite le client MMFDB de ChiSurf : cela fonctionne lorsque ndX s'exécute dans ChiSurf.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1549" />
            <location filename="ndxplorer/app/features/phasor_reference.py" line="218" />
            <source>Opening files needs the io feature.</source>
            <translation>L'ouverture de fichiers nécessite la fonctionnalité io.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="507" />
            <source>Opening {name} in napari...</source>
            <translation>Ouverture de {name} dans napari...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Optimisation epochs; Auto lets UMAP choose from the data size.</source>
            <translation>Époques d'optimisation ; Auto laisse UMAP les choisir selon la taille des données.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Optimise every free parameter against the selected data</source>
            <translation>Optimiser chaque paramètre libre par rapport aux données sélectionnées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Optional: the TTTR file the pixel table was made from; its flat background gives n_bg per pixel and frame.</source>
            <translation>Facultatif : le fichier TTTR dont le tableau de pixels est issu ; son bruit de fond plat donne n_bg par pixel et par image.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Options that speed up histogram computation for large burst tables.</source>
            <translation>Options accélérant le calcul des histogrammes pour les grands tableaux de bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Options that trade memory for speed by caching intermediate results.</source>
            <translation>Options échangeant de la mémoire contre de la vitesse en mettant en cache les résultats intermédiaires.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Output</source>
            <translation>Sortie</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Overlay Plot</source>
            <translation>Graphique de superposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Overlay curve that owns the parameter.</source>
            <translation>Courbe de superposition à laquelle appartient le paramètre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="44" />
            <location filename="ndxplorer/app/features/overlays.py" line="1641" />
            <location filename="ndxplorer/app/menus.py" line="67" />
            <source>Overlays</source>
            <translation>Superpositions</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Owner</source>
            <translation>Propriétaire</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1294" />
            <source>PCA failed</source>
            <translation>Échec de la PCA</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>PCA, UMAP, HDBSCAN and K-means over the columns you choose: projections add PC_n / UMAP_n columns, labellings add Cluster Label.</source>
            <translation>PCA, UMAP, HDBSCAN et K-means sur les colonnes choisies : les projections ajoutent des colonnes PC_n / UMAP_n, les étiquetages ajoutent Cluster Label.</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/publication_figure.py" line="28" />
            <source>PDF (vector)</source>
            <translation>PDF (vectoriel)</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/publication_figure.py" line="30" />
            <source>PNG (raster)</source>
            <translation>PNG (matriciel)</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/screenshots.py" line="25" />
            <source>PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp)</source>
            <translation>Image PNG (*.png);;Image JPEG (*.jpg *.jpeg);;Image BMP (*.bmp)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="98" />
            <source>PTO Measurement Containers</source>
            <translation>Conteneurs de mesure PTO</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="99" />
            <source>PTO files</source>
            <translation>Fichiers PTO</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Paint a region on the 2-D plot and apply it as a gate.</source>
            <translation>Peindre une région sur le graphique 2D et l'appliquer comme gate.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Paint the category, or erase back to unpainted.</source>
            <translation>Peindre la catégorie, ou effacer pour revenir à non peint.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Parallel jobs:</source>
            <translation>Tâches parallèles :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="313" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter</source>
            <translation>Paramètre</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Parameter name:</source>
            <translation>Nom du paramètre :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter on the x axis.</source>
            <translation>Paramètre sur l'axe x.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter on the y axis.</source>
            <translation>Paramètre sur l'axe y.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter on the z axis.</source>
            <translation>Paramètre sur l'axe z.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="44" />
            <location filename="ndxplorer/app/features/overlays.py" line="1640" />
            <location filename="ndxplorer/app/menus.py" line="65" />
            <source>Parameters</source>
            <translation>Paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="287" />
            <source>Parameters saved to {path}</source>
            <translation>Paramètres enregistrés dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="516" />
            <source>Parse warning</source>
            <translation>Avertissement d'analyse</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="193" />
            <source>Partitions every point into exactly k groups of similar spread.</source>
            <translation>Répartit chaque point en exactement k groupes de dispersion similaire.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1257" />
            <location filename="ndxplorer/app/parameter_table.py" line="414" />
            <source>Paste</source>
            <translation>Coller</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="405" />
            <location filename="ndxplorer/app/parameter_table.py" line="471" />
            <source>Paste values</source>
            <translation>Coller les valeurs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Path</source>
            <translation>Chemin</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="97" />
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Pause</source>
            <translation>Pause</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst acceptor anisotropy: separates populations whose acceptor is stuck. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Anisotropie de l'accepteur par burst : sépare les populations dont l'accepteur est bloqué. Coût : le gating multidimensionnel est environ dix fois plus lent que le gating par stœchiométrie (25 s au lieu de 2.4 s sur la mesure cal1, 44 270 bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst acceptor lifetime. Tracks the acceptor quantum yield of each population, the usual reason a population has its own γ. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Durée de vie de l'accepteur par burst. Suit le rendement quantique de l'accepteur de chaque population, la raison habituelle pour laquelle une population a son propre γ. Coût : le gating multidimensionnel est environ dix fois plus lent que le gating par stœchiométrie (25 s au lieu de 2.4 s sur la mesure cal1, 44 270 bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst donor anisotropy: separates populations whose donor is stuck. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Anisotropie du donneur par burst : sépare les populations dont le donneur est bloqué. Coût : le gating multidimensionnel est environ dix fois plus lent que le gating par stœchiométrie (25 s au lieu de 2.4 s sur la mesure cal1, 44 270 bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst donor lifetime. Separates species at equal E but different lifetime (dynamics, a changed quantum yield), and it is what makes population-wise γ identifiable. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Durée de vie du donneur par burst. Sépare des espèces de même E mais de durée de vie différente (dynamique, rendement quantique modifié), et c'est ce qui rend identifiable un γ par population. Coût : le gating multidimensionnel est environ dix fois plus lent que le gating par stœchiométrie (25 s au lieu de 2.4 s sur la mesure cal1, 44 270 bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="358" />
            <source>Performance Configuration</source>
            <translation>Configuration des performances</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="332" />
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="52" />
            <source>Performance Settings</source>
            <translation>Paramètres de performance</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="383" />
            <source>Performance settings have been saved.</source>
            <translation>Les paramètres de performance ont été enregistrés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="53" />
            <source>Phasor reference from IRF</source>
            <translation>Référence phasor depuis l'IRF</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="238" />
            <source>Phasor reference from IRF…</source>
            <translation>Référence phasor depuis l'IRF…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="154" />
            <source>Phasor reference: set {names}</source>
            <translation>Référence phasor : définir {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Pick a measurement of a reference dye of known lifetime as the phasor reference.</source>
            <translation>Choisir une mesure d'un colorant de référence de durée de vie connue comme référence phasor.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Pick the IRF measurement that serves as the phasor reference.</source>
            <translation>Choisir la mesure d'IRF qui sert de référence phasor.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>Picked by:</source>
            <translation>Choisi par :</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Play backward</source>
            <translation>Lire en arrière</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Play forward</source>
            <translation>Lire en avant</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Play the data back along one of its own columns: macro time for bursts, frame index for image stacks.</source>
            <translation>Lire les données le long d'une de leurs colonnes : temps macro pour les bursts, indice d'image pour les piles d'images.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Playback</source>
            <translation>Lecture</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="680" />
            <source>Please add analysis folders.</source>
            <translation>Veuillez ajouter des dossiers d'analyse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="823" />
            <source>Please select one or more Gaussian rows in the table.</source>
            <translation>Sélectionner une ou plusieurs lignes gaussiennes dans le tableau.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="42" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="64" />
            <source>Plot</source>
            <translation>Graphique</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="41" />
            <location filename="ndxplorer/app/menus.py" line="62" />
            <source>Plot controls</source>
            <translation>Contrôles du graphique</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="537" />
            <source>Plot {index}</source>
            <translation>Graphique {index}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Plot:</source>
            <translation>Graphique :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="361" />
            <source>Plots are drawn by emtk here; the Qt window's plot backend ({backend}) is kept in the settings for it.</source>
            <translation>Les graphiques sont dessinés ici par emtk ; le backend graphique de la fenêtre Qt ({backend}) est conservé dans les paramètres à cet effet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="614" />
            <location filename="ndxplorer/app/features/io.py" line="623" />
            <source>Plugin Not Available</source>
            <translation>Plugin non disponible</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="371" />
            <source>Points</source>
            <translation>Points</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Points an equation curve is drawn with.</source>
            <translation>Points avec lesquels une courbe d'équation est tracée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Points loaded.</source>
            <translation>Points chargés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Points shown (after the gates).</source>
            <translation>Points affichés (après les gates).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Population finder</source>
            <translation>Recherche de populations</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Population number.</source>
            <translation>Numéro de la population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="532" />
            <source>Population {n}</source>
            <translation>Population {n}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Population-wise factors</source>
            <translation>Facteurs par population</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="474" />
            <source>Population-wise factors:</source>
            <translation>Facteurs par population :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays.py" line="453" />
            <source>Populations</source>
            <translation>Populations</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="433" />
            <source>Populations of {name}</source>
            <translation>Populations de {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>Populations:</source>
            <translation>Populations :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="407" />
            <source>Populations…</source>
            <translation>Populations…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="269" />
            <source>Preparing the data</source>
            <translation>Préparation des données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Press &lt;b&gt;Start&lt;/b&gt;.</source>
            <translation>Appuyer sur &lt;b&gt;Start&lt;/b&gt;.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="206" />
            <source>Press Start to rank every view.</source>
            <translation>Appuyer sur Démarrer pour classer chaque vue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Preview of the selected generated image.</source>
            <translation>Aperçu de l'image générée sélectionnée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="47" />
            <source>Print window</source>
            <translation>Imprimer la fenêtre</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="206" />
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Process Burst IDs</source>
            <translation>Traiter les ID de burst</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <source>Progress</source>
            <translation>Progression</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Progress of the report generation.</source>
            <translation>Progression de la génération du rapport.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="555" />
            <location filename="ndxplorer/app/features/playback_export.py" line="876" />
            <location filename="ndxplorer/app/features/playback_export.py" line="893" />
            <location filename="ndxplorer/app/features/playback_export.py" line="899" />
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Publication export</source>
            <translation>Export pour publication</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Python expression or function that defines the overlay curve.</source>
            <translation>Expression ou fonction Python qui définit la courbe de superposition.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <source>Question</source>
            <translation>Question</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>R (Å)</source>
            <translation>R (Å)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Rank by</source>
            <translation>Classer par</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Ranked parameter pairs; click a row to show that view in the main plot.</source>
            <translation>Paires de paramètres classées ; cliquer sur une ligne pour afficher cette vue dans le graphique principal.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Ranked views - click one to show it</source>
            <translation>Vues classées - cliquer pour afficher</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Ranking</source>
            <translation>Classement</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="452" />
            <source>Ranking failed: {error}</source>
            <translation>Échec du classement : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Raster resolution. Ignored for vector formats.</source>
            <translation>Résolution raster. Ignorée pour les formats vectoriels.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Ratio of the two lasers' excitation flux and cross-sections. Comes from the same E-S fit as γ.</source>
            <translation>Rapport du flux d'excitation et des sections efficaces des deux lasers. Issu du même ajustement E-S que γ.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Read equations from a YAML file</source>
            <translation>Lire les équations depuis un fichier YAML</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="202" />
            <source>Read from the column '{column}'.</source>
            <translation>Lu depuis la colonne '{column}'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1114" />
            <source>Recompute failed:
{error}</source>
            <translation>Échec du recalcul :
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="262" />
            <source>Recompute failed: {error}</source>
            <translation>Échec du recalcul : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Red channels:</source>
            <translation>Canaux rouges :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Redraw the plots with these axes</source>
            <translation>Redessiner les graphiques avec ces axes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Redraw the plots.</source>
            <translation>Redessiner les graphiques.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Reference lifetime (ns):</source>
            <translation>Durée de vie de référence (ns) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Reg. covar:</source>
            <translation>Cov. de régul. :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Remove</source>
            <translation>Retirer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="500" />
            <source>Remove all folders from the list?</source>
            <translation>Retirer tous les dossiers de la liste ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Remove every Gaussian.</source>
            <translation>Supprimer toutes les gaussiennes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Remove every folder from the list</source>
            <translation>Retirer tous les dossiers de la liste</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Remove every gate.</source>
            <translation>Supprimer tous les gates.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Remove the curve.</source>
            <translation>Supprimer la courbe.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Remove the painted area from the mask.</source>
            <translation>Retirer la zone peinte du masque.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Remove the reference's flat background</source>
            <translation>Retirer le bruit de fond plat de la référence</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Remove the selected Gaussian (or the last).</source>
            <translation>Supprimer la gaussienne sélectionnée (ou la dernière).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Remove the selected equation</source>
            <translation>Supprimer l'équation sélectionnée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Remove the selected folder from the list</source>
            <translation>Retirer le dossier sélectionné de la liste</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="231" />
            <source>Removed {n} saved session(s) from {name}</source>
            <translation>{n} session(s) enregistrée(s) retirée(s) de {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="112" />
            <source>Replace existing data</source>
            <translation>Remplacer les données existantes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Replace: the new table replaces the one on screen. Columns: its columns are added beside these (the rows must match). Rows: its rows are appended under these, for the columns both have.</source>
            <translation>Remplacer : le nouveau tableau remplace celui à l'écran. Colonnes : ses colonnes sont ajoutées à côté de celles-ci (les lignes doivent correspondre). Lignes : ses lignes sont ajoutées sous celles-ci, pour les colonnes communes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/constants_group.py" line="236" />
            <source>Replaced population-wise {symbol} with shared {symbol} = {value}</source>
            <translation>{symbol} propre à chaque population remplacé par {symbol} commun = {value}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Report</source>
            <translation>Rapport</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Report YAML (report.yaml):</source>
            <translation>YAML du rapport (report.yaml) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="454" />
            <source>Report downloaded as {name}</source>
            <translation>Rapport téléchargé sous {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="460" />
            <source>Report written to {path}</source>
            <translation>Rapport écrit dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="766" />
            <source>Reports cleared</source>
            <translation>Rapports supprimés</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="733" />
            <source>Reports generated.</source>
            <translation>Rapports générés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Resamples used for the factor uncertainties, with the population assignment held fixed. 0 skips them. It is cheap — the classification, not the resampling, is what costs.</source>
            <translation>Rééchantillons utilisés pour les incertitudes des facteurs, l'assignation des populations restant fixe. 0 les saute. C'est peu coûteux — c'est la classification, pas le rééchantillonnage, qui coûte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="399" />
            <source>Reset</source>
            <translation>Réinitialiser</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="402" />
            <source>Reset Settings</source>
            <translation>Réinitialiser les paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Reset all performance settings to their default values</source>
            <translation>Rétablir tous les paramètres de performance à leurs valeurs par défaut</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="403" />
            <source>Reset all performance settings to their default values?</source>
            <translation>Réinitialiser tous les paramètres de performance à leurs valeurs par défaut ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Reset to Defaults</source>
            <translation>Rétablir les valeurs par défaut</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="78" />
            <source>Reset window layout</source>
            <translation>Réinitialiser la disposition de la fenêtre</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1266" />
            <source>Resize columns to contents</source>
            <translation>Ajuster les colonnes au contenu</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="242" />
            <source>Restart with new settings</source>
            <translation>Relancer avec de nouveaux paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="203" />
            <source>Restored the session saved {when} UTC</source>
            <translation>Session enregistrée le {when} UTC restaurée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="205" />
            <source>Restored the session saved {when} UTC; not restored: {notes}</source>
            <translation>Session enregistrée le {when} UTC restaurée ; non restauré : {notes}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="595" />
            <source>Restored {n} constants stored in {name}</source>
            <translation>{n} constantes enregistrées dans {name} restaurées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="42" />
            <source>Revert to saved session</source>
            <translation>Revenir à la session enregistrée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Right Axis</source>
            <translation>Axe droit</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Right Axis Label</source>
            <translation>Étiquette de l'axe droit</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Right-click a row to copy, paste, link, or make it a vector (one value per population).</source>
            <translation>Clic droit sur une ligne pour copier, coller, lier ou en faire un vecteur (une valeur par population).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Routing channels of the green detectors (empty: skip green).</source>
            <translation>Canaux de routage des détecteurs verts (vide : ignorer le vert).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Routing channels of the red detectors (empty: skip red).</source>
            <translation>Canaux de routage des détecteurs rouges (vide : ignorer le rouge).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Routing channels of the unlabelled g, s columns (empty: skip).</source>
            <translation>Canaux de routage des colonnes g, s non marquées (vide : ignorer).</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1030" />
            <source>Row Count Mismatch</source>
            <translation>Nombre de lignes différent</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1332" />
            <source>Rows whose '{column}' contains:</source>
            <translation>Lignes dont '{column}' contient :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Run it</source>
            <translation>Lancer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Run the method on the chosen columns.</source>
            <translation>Exécuter la méthode sur les colonnes choisies.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="160" />
            <source>Run {label} in the current ndX session.</source>
            <translation>Exécuter {label} dans la session ndX en cours.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="292" />
            <source>Running HDBSCAN</source>
            <translation>HDBSCAN en cours</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="308" />
            <source>Running K-means</source>
            <translation>K-means en cours</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="511" />
            <source>Running {method}…</source>
            <translation>Exécution de {method}…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>R₀ Förster radius</source>
            <translation>R₀ rayon de Förster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>S</source>
            <translation>S</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="379" />
            <source>S (stoichiometry gating)</source>
            <translation>S (gating par stœchiométrie)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>S stoichiometry</source>
            <translation>S stœchiométrie</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/publication_figure.py" line="29" />
            <source>SVG (vector)</source>
            <translation>SVG (vectoriel)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Sample</source>
            <translation>Échantillon</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="96" />
            <source>Sampling files</source>
            <translation>Fichiers d'échantillonnage</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <location filename="ndxplorer/app/features/io_service.py" line="199" />
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="35" />
            <source>Save</source>
            <translation>Enregistrer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="255" />
            <source>Save .pto with session</source>
            <translation>Enregistrer le .pto avec la session</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="577" />
            <source>Save Burst IDs</source>
            <translation>Enregistrer les ID de burst</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Save CSV</source>
            <translation>Enregistrer en CSV</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="878" />
            <location filename="ndxplorer/app/features/analysis.py" line="1383" />
            <source>Save Error</source>
            <translation>Erreur d'enregistrement</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="748" />
            <source>Save Final Combined Report</source>
            <translation>Enregistrer le rapport combiné final</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="864" />
            <source>Save Gaussian Fits</source>
            <translation>Enregistrer les ajustements gaussiens</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="859" />
            <source>Save Gaussians</source>
            <translation>Enregistrer les gaussiennes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="300" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Save Mask</source>
            <translation>Enregistrer le masque</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="827" />
            <source>Save Overlay Curves</source>
            <translation>Enregistrer les courbes de superposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="806" />
            <location filename="ndxplorer/app/features/overlays.py" line="811" />
            <location filename="ndxplorer/app/features/overlays.py" line="822" />
            <source>Save Overlays</source>
            <translation>Enregistrer les superpositions</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/screenshots.py" line="22" />
            <source>Save Screenshot</source>
            <translation>Enregistrer la capture d'écran</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Save a picture of the window.</source>
            <translation>Enregistrer une image de la fenêtre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Save and close.</source>
            <translation>Enregistrer et fermer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Save axis label settings to the settings folder</source>
            <translation>Enregistrer les paramètres d'étiquettes d'axe dans le dossier des paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="796" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="818" />
            <source>Save calibration</source>
            <translation>Enregistrer l'étalonnage</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="622" />
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Save calibration…</source>
            <translation>Enregistrer l'étalonnage…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="547" />
            <source>Save config</source>
            <translation>Enregistrer la configuration</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1019" />
            <location filename="ndxplorer/app/features/settings.py" line="1022" />
            <source>Save constants</source>
            <translation>Enregistrer les constantes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1148" />
            <source>Save equations</source>
            <translation>Enregistrer les équations</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="533" />
            <source>Save error</source>
            <translation>Erreur d'enregistrement</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/window.py" line="58" />
            <source>Save histograms</source>
            <translation>Enregistrer les histogrammes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="284" />
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Save parameters</source>
            <translation>Enregistrer les paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="462" />
            <source>Save report</source>
            <translation>Enregistrer le rapport</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Save report…</source>
            <translation>Enregistrer le rapport…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="160" />
            <location filename="ndxplorer/app/menus.py" line="41" />
            <source>Save session</source>
            <translation>Enregistrer la session</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="54" />
            <source>Save settings</source>
            <translation>Enregistrer les paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Save the Gaussians with the histogram and model (.json and .csv files).</source>
            <translation>Enregistrer les gaussiennes avec l'histogramme et le modèle (fichiers .json et .csv).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Save the burst IDs of the selected bursts.</source>
            <translation>Enregistrer les ID des bursts sélectionnés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Save the configuration as YAML or JSON</source>
            <translation>Enregistrer la configuration en YAML ou JSON</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Save the gates to a file.</source>
            <translation>Enregistrer les gates dans un fichier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Save the mask as an integer TIFF.</source>
            <translation>Enregistrer le masque en TIFF d'entiers.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Save the settings</source>
            <translation>Enregistrer les paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Save the settings and close</source>
            <translation>Enregistrer les paramètres et fermer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Save the settings to your ndX user folder without closing.</source>
            <translation>Enregistrer les paramètres dans le dossier utilisateur ndX sans fermer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Save visible overlay curves as CSV (curve, x, y)</source>
            <translation>Enregistrer les courbes de superposition visibles en CSV (courbe, x, y)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="880" />
            <source>Saved</source>
            <translation>Enregistré</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="880" />
            <source>Saved files:
{files}</source>
            <translation>Fichiers enregistrés :
{files}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="825" />
            <source>Saved overlay curves to {path}</source>
            <translation>Courbes de superposition enregistrées dans {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="353" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="793" />
            <source>Saved to {target}</source>
            <translation>Enregistré dans {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="860" />
            <source>Saved {when} ({where}: {target})</source>
            <translation>Enregistré {when} ({where} : {target})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Save…</source>
            <translation>Enregistrer…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="580" />
            <source>Saving Burst ID files...</source>
            <translation>Enregistrement des fichiers d'ID de burst...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="580" />
            <source>Saving Files</source>
            <translation>Enregistrement des fichiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/writer.py" line="169" />
            <source>Saving cluster labels...</source>
            <translation>Enregistrement des étiquettes de cluster...</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/writer.py" line="157" />
            <source>Saving clustering parameters...</source>
            <translation>Enregistrement des paramètres de clustering...</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/region_selection.py" line="210" />
            <source>Saving drawn regions, masks or Gaussian gates needs ChiSurf's region module (chisurf.core.roi), which is not installed here; interval gates alone can be saved.</source>
            <translation>L'enregistrement de régions dessinées, de masques ou de gates gaussiens nécessite le module de régions de ChiSurf (chisurf.core.roi), non installé ici ; seuls les gates d'intervalle peuvent être enregistrés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1539" />
            <source>Saving files needs the io feature.</source>
            <translation>L'enregistrement de fichiers nécessite la fonctionnalité io.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Scalar</source>
            <translation>Scalaire</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Scalar: one value for all bursts. Vector: one value per population.</source>
            <translation>Scalaire : une valeur pour tous les bursts. Vecteur : une valeur par population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Scale colours across all columns instead of per column</source>
            <translation>Mettre les couleurs à l'échelle sur toutes les colonnes plutôt que par colonne</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Scale each column to unit variance first. Leave this on unless the columns genuinely share a scale.</source>
            <translation>Mettre d'abord chaque colonne à variance unitaire. Laisser activé, sauf si les colonnes partagent réellement une échelle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Scan first</source>
            <translation>Balayer d'abord</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="281" />
            <location filename="ndxplorer/analysis/vizrank.py" line="313" />
            <location filename="ndxplorer/analysis/vizrank.py" line="349" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="183" />
            <source>Score</source>
            <translation>Score</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="137" />
            <source>Score views</source>
            <translation>Évaluer les vues</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="351" />
            <source>Scoring views…</source>
            <translation>Évaluation des vues…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Screenshot</source>
            <translation>Capture d'écran</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Select</source>
            <translation>Sélectionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="52" />
            <source>Select All</source>
            <translation>Tout sélectionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="174" />
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Select Columns for Clustering</source>
            <translation>Sélectionner les colonnes pour le clustering</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="822" />
            <source>Select Gaussian</source>
            <translation>Sélectionner une gaussienne</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1259" />
            <source>Select all</source>
            <translation>Tout sélectionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1076" />
            <source>Select an equation to see it here.</source>
            <translation>Sélectionner une équation pour la voir ici.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="482" />
            <source>Select analysis folder</source>
            <translation>Sélectionner le dossier d'analyse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1207" />
            <source>Select at least {n} columns.</source>
            <translation>Sélectionner au moins {n} colonnes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1210" />
            <source>Select columns for {method}</source>
            <translation>Sélectionner les colonnes pour {method}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Select columns to use for clustering:</source>
            <translation>Sélectionner les colonnes à utiliser pour le clustering :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1214" />
            <source>Select columns?</source>
            <translation>Sélectionner des colonnes ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="542" />
            <source>Select current path</source>
            <translation>Sélectionner le chemin actuel</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Select point</source>
            <translation>Sélectionner un point</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="480" />
            <source>Selected data contains no finite values for fitting.</source>
            <translation>Les données sélectionnées ne contiennent aucune valeur finie à ajuster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Selecting a row sets the axes of the main plot. &lt;b&gt;Islands&lt;/b&gt; says how many populations the view splits into, and the line under the table what the score means in numbers. Picking axes by hand in the plot selects the matching row here.</source>
            <translation>Sélectionner une ligne définit les axes du graphique principal. &lt;b&gt;Islands&lt;/b&gt; indique en combien de populations la vue se divise, et la ligne sous le tableau ce que signifie le score en chiffres. Choisir les axes à la main dans le graphique sélectionne ici la ligne correspondante.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Selection</source>
            <translation>Sélection</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="644" />
            <location filename="ndxplorer/app/features/io.py" line="662" />
            <source>Selection JSON</source>
            <translation>JSON de sélection</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Selection σ:</source>
            <translation>σ de sélection :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="55" />
            <source>Send selection to</source>
            <translation>Envoyer la sélection à</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="54" />
            <source>Send to Napari</source>
            <translation>Envoyer à Napari</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="496" />
            <source>Send to Napari: {reason}.</source>
            <translation>Envoyer à Napari : {reason}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="652" />
            <source>Sent {bursts} bursts from {files} file(s) to {target} (not recorded: no database product attached)</source>
            <translation>{bursts} bursts de {files} fichier(s) envoyés vers {target} (non enregistré : aucun produit de base de données attaché)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="658" />
            <source>Sent {bursts} bursts from {files} file(s) to {target} and recorded it</source>
            <translation>{bursts} bursts de {files} fichier(s) envoyés vers {target} et enregistrés</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="655" />
            <source>Sent {bursts} bursts from {files} file(s) to {target} — but the provenance record failed: {error}</source>
            <translation>{bursts} bursts de {files} fichier(s) envoyés vers {target} — mais l'enregistrement de la provenance a échoué : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="649" />
            <source>Separation</source>
            <translation>Séparation</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="156" />
            <source>Session not saved in {name}: {reason}</source>
            <translation>Session non enregistrée dans {name} : {reason}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="152" />
            <source>Session saved in {name}</source>
            <translation>Session enregistrée dans {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Set</source>
            <translation>Définir</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1051" />
            <location filename="ndxplorer/app/features/settings.py" line="1055" />
            <location filename="ndxplorer/app/menus.py" line="59" />
            <source>Set default axis</source>
            <translation>Définir l'axe par défaut</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="240" />
            <source>Set g_irf, s_irf (and n_bg) of the corrected phasor columns from an IRF and the measurement.</source>
            <translation>Définir g_irf, s_irf (et n_bg) des colonnes phasor corrigées à partir d'une IRF et de la mesure.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Set the colour limits from the data.</source>
            <translation>Définir les limites de couleur à partir des données.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings.py" line="857" />
            <location filename="ndxplorer/app/menus.py" line="51" />
            <source>Settings</source>
            <translation>Paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="382" />
            <source>Settings Applied</source>
            <translation>Paramètres appliqués</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="371" />
            <source>Settings are saved to: {path}</source>
            <translation>Les paramètres sont enregistrés dans : {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="400" />
            <source>Settings reset to defaults. Apply or OK saves them.</source>
            <translation>Paramètres réinitialisés par défaut. Appliquer ou OK les enregistre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Settings that steer convergence rather than the result's meaning.</source>
            <translation>Paramètres qui pilotent la convergence plutôt que la signification du résultat.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="139" />
            <source>Several stored tables; choose one of: {names}</source>
            <translation>Plusieurs tableaux enregistrés ; en choisir un parmi : {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Shade numeric cells by their value</source>
            <translation>Nuancer les cellules numériques selon leur valeur</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="172" />
            <source>Show a 2-D map first: the mask is loaded onto its bins.</source>
            <translation>Afficher d'abord une carte 2D : le masque est chargé sur ses bins.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Show all</source>
            <translation>Tout afficher</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show every axis title; untick to choose them one by one</source>
            <translation>Afficher tous les titres d'axe ; décocher pour les choisir un par un</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Show every column in the burst table.</source>
            <translation>Afficher chaque colonne du tableau des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Show islands on the map</source>
            <translation>Afficher les îlots sur la carte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="865" />
            <source>Show ndX in this language.</source>
            <translation>Afficher ndX dans cette langue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Show only the columns whose name contains this text.</source>
            <translation>Afficher uniquement les colonnes dont le nom contient ce texte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Show only this cluster; -1 shows all.</source>
            <translation>Afficher uniquement ce cluster ; -1 les affiche tous.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Show the curve on the plot.</source>
            <translation>Afficher la courbe sur le graphique.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Show the data table.</source>
            <translation>Afficher le tableau de données.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Show the projection in its own window.</source>
            <translation>Afficher la projection dans sa propre fenêtre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the 2D plot</source>
            <translation>Afficher/masquer l'axe inférieur du graphique 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the X plot</source>
            <translation>Afficher/masquer l'axe inférieur du graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the Y plot</source>
            <translation>Afficher/masquer l'axe inférieur du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the Z plot</source>
            <translation>Afficher/masquer l'axe inférieur du graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the overlay plot</source>
            <translation>Afficher/masquer l'axe inférieur du graphique de superposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the 2D plot</source>
            <translation>Afficher/masquer l'axe gauche du graphique 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the X plot</source>
            <translation>Afficher/masquer l'axe gauche du graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the Y plot</source>
            <translation>Afficher/masquer l'axe gauche du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the Z plot</source>
            <translation>Afficher/masquer l'axe gauche du graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the overlay plot</source>
            <translation>Afficher/masquer l'axe gauche du graphique de superposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the 2D plot</source>
            <translation>Afficher/masquer l'axe droit du graphique 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the X plot</source>
            <translation>Afficher/masquer l'axe droit du graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the Y plot</source>
            <translation>Afficher/masquer l'axe droit du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the overlay plot</source>
            <translation>Afficher/masquer l'axe droit du graphique de superposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the 2D plot</source>
            <translation>Afficher/masquer l'axe supérieur du graphique 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the X plot</source>
            <translation>Afficher/masquer l'axe supérieur du graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the Y plot</source>
            <translation>Afficher/masquer l'axe supérieur du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the overlay plot</source>
            <translation>Afficher/masquer l'axe supérieur du graphique de superposition</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Shown</source>
            <translation>Affichée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Size of the local neighbourhood. Larger = more global structure, smaller = more local detail.</source>
            <translation>Taille du voisinage local. Plus grand = plus de structure globale, plus petit = plus de détails locaux.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Smallest donor-only / acceptor-only population accepted when fitting a background. Below it that channel is left at whatever it had rather than guessed from a handful of bursts.</source>
            <translation>Plus petite population donneur seul / accepteur seul acceptée pour ajuster un bruit de fond. En dessous, ce canal garde sa valeur actuelle au lieu d'être deviné à partir de quelques bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Smallest group that counts as a cluster rather than noise.</source>
            <translation>Plus petit groupe comptant comme cluster plutôt que comme bruit.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Smallest weight a component keeps; 0 disables the floor.</source>
            <translation>Plus petit poids conservé par une composante ; 0 désactive le plancher.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="384" />
            <source>Some changes may require restarting ndX to take full effect.</source>
            <translation>Certaines modifications peuvent nécessiter un redémarrage de ndX pour prendre pleinement effet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="806" />
            <source>Spearman ρ = {rho}, p = {p} over {n} sampled bursts: the two move together, which says nothing about populations.</source>
            <translation>ρ de Spearman = {rho}, p = {p} sur {n} bursts échantillonnés : les deux varient ensemble, ce qui ne dit rien des populations.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Speed</source>
            <translation>Vitesse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Spread:</source>
            <translation>Dispersion :</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Stack</source>
            <translation>Pile</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Standard error from the bootstrap (population assignment held fixed).</source>
            <translation>Erreur standard issue du bootstrap (affectation des populations fixée).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Standardise columns</source>
            <translation>Standardiser les colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="94" />
            <location filename="ndxplorer/analysis/vizrank.py" line="95" />
            <location filename="ndxplorer/analysis/vizrank.py" line="96" />
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="244" />
            <source>Start</source>
            <translation>Démarrer</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Start the ranking, continue it, or restart it with new settings.</source>
            <translation>Démarrer le classement, le reprendre ou le relancer avec de nouveaux paramètres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="267" />
            <source>Starting…</source>
            <translation>Démarrage…</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Step</source>
            <translation>Étape</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Step through the data along one of its columns.</source>
            <translation>Parcourir les données pas à pas le long de l'une de leurs colonnes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Steps</source>
            <translation>Étapes</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Steps per second while playing. A redraw takes a few tens of milliseconds, so above roughly 30 the plot cannot keep up and steps are dropped rather than shown faster.</source>
            <translation>Étapes par seconde pendant la lecture. Un redessin prend quelques dizaines de millisecondes ; au-delà d'environ 30, le graphique ne suit plus et des étapes sont sautées plutôt qu'affichées plus vite.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Stop</source>
            <translation>Arrêter</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Stop after the folder being processed</source>
            <translation>S'arrêter après le dossier en cours de traitement</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Stop scoring; Start continues from here.</source>
            <translation>Arrêter le calcul des scores ; Démarrer reprend à partir d'ici.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/progress.view.json" line="0" />
            <source>Stop the calibration; the window keeps the constants it had.</source>
            <translation>Arrêter l'étalonnage ; la fenêtre conserve les constantes qu'elle avait.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Stop the fit after the step it is on.</source>
            <translation>Arrêter l'ajustement après l'étape en cours.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Stop the running method.</source>
            <translation>Arrêter la méthode en cours.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <source>Stop; what is finished stays</source>
            <translation>Arrêter ; ce qui est terminé est conservé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Store the calibration in the measurement</source>
            <translation>Enregistrer l'étalonnage dans la mesure</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="819" />
            <source>Store the calibration in the measurement?</source>
            <translation>Enregistrer l'étalonnage dans la mesure ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="624" />
            <source>Store the current FRET factors in the measurement or a calibration file.</source>
            <translation>Enregistrer les facteurs FRET actuels dans la mesure ou dans un fichier d'étalonnage.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="351" />
            <source>Stored in the measurement: {target}</source>
            <translation>Enregistré dans la mesure : {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="812" />
            <source>Stored in {target}</source>
            <translation>Enregistré dans {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Stored table</source>
            <translation>Tableau enregistré</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Subtract the flat background of the reference decay before computing the phasor reference.</source>
            <translation>Soustraire le bruit de fond plat du déclin de référence avant de calculer la référence phasor.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="858" />
            <source>System language</source>
            <translation>Langue du système</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="302" />
            <source>TIFF files</source>
            <translation>Fichiers TIFF</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>TTTR file (.ptu, .ht3, ...) of the instrument response: scatter, a mirror, or a dye of known lifetime.</source>
            <translation>Fichier TTTR (.ptu, .ht3, ...) de la réponse instrumentale : diffusion, miroir ou colorant de durée de vie connue.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="33" />
            <source>TTTR files</source>
            <translation>Fichiers TTTR</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1188" />
            <source>Table Editor</source>
            <translation>Éditeur de tableau</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Table of parameters (burst-table columns) with their per-parameter settings.</source>
            <translation>Tableau des paramètres (colonnes du tableau de bursts) avec leurs réglages par paramètre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Table:</source>
            <translation>Tableau :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Take from</source>
            <translation>Prendre depuis</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/text.view.json" line="0" />
            <source>Text</source>
            <translation>Texte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="462" />
            <source>Text (*.txt);;All files (*)</source>
            <translation>Texte (*.txt);;Tous les fichiers (*)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="84" />
            <source>Text files</source>
            <translation>Fichiers texte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/window.py" line="59" />
            <source>Text files (*.txt *.tsv)</source>
            <translation>Fichiers texte (*.txt *.tsv)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Text report of the accurate FRET calibration (read only).</source>
            <translation>Rapport texte de l'étalonnage FRET précis (lecture seule).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <source>Text to enter.</source>
            <translation>Texte à saisir.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="624" />
            <source>The FCS Correlator Wizard is a ChiSurf plugin and does not run in this window. Open the {n} .bst file(s) in {folder} with ChiSurf's FCS correlator.</source>
            <translation>L'assistant du corrélateur FCS est un plugin ChiSurf et ne s'exécute pas dans cette fenêtre. Ouvrir les {n} fichier(s) .bst de {folder} avec le corrélateur FCS de ChiSurf.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="615" />
            <source>The Microtime Histogram plugin (chisurf) is not available in this standalone build.</source>
            <translation>Le plugin Histogramme de micro-temps (ChiSurf) n'est pas disponible dans cette version autonome.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>The burst column whose value says which population a burst is in.</source>
            <translation>La colonne de bursts dont la valeur indique à quelle population appartient un burst.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>The calibration's whole text, as the Qt window's report shows it and as Save report writes it.</source>
            <translation>Le texte complet de l'étalonnage, tel que l'affiche le rapport de la fenêtre Qt et tel que l'écrit Enregistrer le rapport.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>The cloud fits the curve to the distribution itself: every populated bin pulls on it, weighted by what it counted, and a bin more than a couple of bins away stops pulling -- so the curve follows the populations and ignores the junk. Reducing each column to one point instead cannot describe a population: a blob reduces to a horizontal streak across its own columns.</source>
            <translation>Le nuage ajuste la courbe à la distribution elle-même : chaque bin peuplé l'attire, pondéré par ses comptages, et un bin éloigné de plus de quelques bins cesse de l'attirer -- la courbe suit ainsi les populations et ignore les parasites. Réduire chaque colonne à un point ne peut en revanche pas décrire une population : un blob devient une traînée horizontale sur ses propres colonnes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1383" />
            <source>The clustering data could not be written.</source>
            <translation>Les données de clustering n'ont pas pu être écrites.</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="122" />
            <source>The configuration must define a top-level 'plots' list.</source>
            <translation>La configuration doit définir une liste 'plots' de premier niveau.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="345" />
            <source>The correction factors were optimized against the loaded data.</source>
            <translation>Les facteurs de correction ont été optimisés sur les données chargées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>The curve to add: Custom Equation (type your own) or one of the curves in curve_equations.yaml.</source>
            <translation>La courbe à ajouter : équation personnalisée (saisir la sienne) ou l'une des courbes de curve_equations.yaml.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>The curve with the parameter values written in (select to copy).</source>
            <translation>La courbe avec les valeurs des paramètres insérées (sélectionner pour copier).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>The curve's colour.</source>
            <translation>Couleur de la courbe.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>The displayed data fits y(x) to the two-dimensional distribution (one point per populated x column); a marginal fits the curve to that axis's histogram of counts.</source>
            <translation>Les données affichées ajustent y(x) à la distribution bidimensionnelle (un point par colonne x peuplée) ; pour une marge, la courbe est ajustée à l'histogramme des comptages de cet axe.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>The full path of the selected folder</source>
            <translation>Le chemin complet du dossier sélectionné</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The gates in force. Edit a bound in place; the Delete key removes a row.</source>
            <translation>Les gates en vigueur. Modifier une borne directement ; la touche Suppr supprime une ligne.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>The generated images of the selected folder</source>
            <translation>Les images générées du dossier sélectionné</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="219" />
            <source>The help text is not installed.</source>
            <translation>Le texte d'aide n'est pas installé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>The labels a view should keep apart: the gate in the Selection table, each gate as its own population, the clusters, or a z parameter that holds labels. Parameters a gate is defined on are left out.</source>
            <translation>Les étiquettes qu'une vue doit séparer : le gate du tableau de sélection, chaque gate comme population distincte, les clusters, ou un paramètre z contenant des étiquettes. Les paramètres sur lesquels un gate est défini sont omis.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="200" />
            <source>The map changed: the painted mask was cleared and drawing stopped.</source>
            <translation>La carte a changé : le masque peint a été effacé et le dessin arrêté.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="142" />
            <source>The mask has no bins of any category.</source>
            <translation>Le masque ne contient aucun bin d'aucune catégorie.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="143" />
            <source>The mask has no bins of category {category}.</source>
            <translation>Le masque ne contient aucun bin de la catégorie {category}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="176" />
            <source>The mask is {mask_x} x {mask_y} bins; the map is {map_x} x {map_y}.</source>
            <translation>Le masque fait {mask_x} x {mask_y} bins ; la carte {map_x} x {map_y}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="824" />
            <source>The mean {classes} of each burst's {k} nearest neighbours predicts its own with R² = {r2}; weighted by the {share} of sampled rows that have values.</source>
            <translation>La moyenne de {classes} des {k} plus proches voisins de chaque burst prédit la sienne avec R² = {r2} ; pondérée par la part {share} des lignes échantillonnées qui ont des valeurs.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>The parameter this one follows (right-click to link or unlink). Shown while one is linked.</source>
            <translation>Le paramètre que celui-ci suit (clic droit pour lier ou délier). Affiché tant qu'un paramètre est lié.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>The sampling chain to open: the fit it belongs to, with its number of draws and parameters.</source>
            <translation>La chaîne d'échantillonnage à ouvrir : l'ajustement auquel elle appartient, avec son nombre de tirages et de paramètres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="191" />
            <source>The score; the bar is its share of the range.</source>
            <translation>Le score ; la barre représente sa part de la plage.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="161" />
            <source>The session could not be saved in {name}: {error}</source>
            <translation>La session n'a pas pu être enregistrée dans {name} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="316" />
            <source>The settings could not be saved.</source>
            <translation>Les paramètres n'ont pas pu être enregistrés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>The table fills while it computes, best rows at the top. &lt;b&gt;Pause&lt;/b&gt; stops it and &lt;b&gt;Start&lt;/b&gt; continues; closing the panel pauses too.</source>
            <translation>Le tableau se remplit pendant le calcul, les meilleures lignes en haut. &lt;b&gt;Pause&lt;/b&gt; l'arrête et &lt;b&gt;Start&lt;/b&gt; le reprend ; fermer le panneau le met aussi en pause.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The third axis: its own marginal, and a range slider that gates the plot.</source>
            <translation>Le troisième axe : sa propre marge et un curseur de plage qui applique un gate au graphique.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>The value. Double-click to type one; a linked parameter shows its master's.</source>
            <translation>La valeur. Double-clic pour en saisir une ; un paramètre lié affiche celle de son maître.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>The working folder: where files are opened from.</source>
            <translation>Le dossier de travail : emplacement d'ouverture des fichiers.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The x parameter's name above the X plot</source>
            <translation>Nom du paramètre x au-dessus du graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The y parameter's name above the Y plot</source>
            <translation>Nom du paramètre y au-dessus du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The y parameter's name right of the Y plot</source>
            <translation>Nom du paramètre y à droite du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The z axis has no 2D bins</source>
            <translation>L'axe z n'a pas de bins 2D</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The z marginal; drag the region to set the z range, and its bottom edge to resize it.</source>
            <translation>La marge z ; faire glisser la région pour définir la plage z, et son bord inférieur pour la redimensionner.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The z parameter's name left of the Z plot</source>
            <translation>Nom du paramètre z à gauche du graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The z parameter's name under the Z plot</source>
            <translation>Nom du paramètre z sous le graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="196" />
            <source>The {axis} parameter of the view; hover a shortened name for the whole of it.</source>
            <translation>Le paramètre {axis} de la vue ; survoler un nom abrégé pour le voir en entier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1101" />
            <source>Then restart ndXplorer.</source>
            <translation>Puis redémarrer ndXplorer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="859" />
            <source>There are no Gaussian rows to save.</source>
            <translation>Il n'y a aucune ligne gaussienne à enregistrer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="643" />
            <source>This ChiSurf advertises no burst analyses. It may be an older version, or the burst services are not loaded.</source>
            <translation>Ce ChiSurf n'annonce aucune analyse de bursts. Il s'agit peut-être d'une version plus ancienne, ou les services de bursts ne sont pas chargés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="844" />
            <source>This measurement carries {n} stored calibration(s).</source>
            <translation>Cette mesure contient {n} étalonnage(s) enregistré(s).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="220" />
            <source>This measurement holds no saved session</source>
            <translation>Cette mesure ne contient aucune session enregistrée</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="637" />
            <source>This table has no burst provenance: {missing} missing. Sending needs the photon intervals each burst came from.</source>
            <translation>Cette table n'a pas de provenance des bursts : {missing} manquant. L'envoi nécessite les intervalles de photons dont provient chaque burst.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="404" />
            <source>This will clear your custom configuration.</source>
            <translation>Cela effacera la configuration personnalisée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="774" />
            <source>This will permanently delete report folders for {n} analysis folder(s). Continue?</source>
            <translation>Cela supprimera définitivement les dossiers de rapport de {n} dossier(s) d'analyse. Continuer ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="379" />
            <source>This window cannot show context menus yet.</source>
            <translation>Cette fenêtre ne peut pas encore afficher de menus contextuels.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="771" />
            <source>This window carries no constants to save.</source>
            <translation>Cette fenêtre ne contient aucune constante à enregistrer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Threads UMAP may use; -1 uses all cores.</source>
            <translation>Threads que UMAP peut utiliser ; -1 utilise tous les cœurs.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Tick every column in the list.</source>
            <translation>Cocher toutes les colonnes de la liste.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Tick the axes each plot shows. Apply or OK redraws the plots; Save also writes the axis titles and their colour to the settings folder.</source>
            <translation>Cocher les axes affichés par chaque graphique. Appliquer ou OK redessine les graphiques ; Enregistrer écrit aussi les titres des axes et leur couleur dans le dossier des paramètres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Tick the burst-table columns to include in the analysis.</source>
            <translation>Cocher les colonnes du tableau de bursts à inclure dans l'analyse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Tick to apply this gate to the selection.</source>
            <translation>Cocher pour appliquer ce gate à la sélection.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Tick to include this column in the analysis.</source>
            <translation>Cocher pour inclure cette colonne dans l'analyse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Tick to show this column in the burst table.</source>
            <translation>Cocher pour afficher cette colonne dans le tableau des bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Title color</source>
            <translation>Couleur du titre</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Tolerance (tol):</source>
            <translation>Tolérance (tol) :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Top Axis</source>
            <translation>Axe supérieur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Top Axis Label</source>
            <translation>Étiquette de l'axe supérieur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Transparent background</source>
            <translation>Arrière-plan transparent</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Turn the selected Gaussian (or the only one) into an elliptical gate at Selection σ.</source>
            <translation>Transformer la gaussienne sélectionnée (ou la seule) en gate elliptique au σ de sélection.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="73" />
            <source>UMAP</source>
            <translation>UMAP</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="977" />
            <location filename="ndxplorer/app/features/analysis.py" line="1254" />
            <location filename="ndxplorer/app/features/analysis.py" line="1516" />
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <source>UMAP Computation Progress</source>
            <translation>Progression du calcul UMAP</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="333" />
            <location filename="ndxplorer/app/features/analysis.py" line="353" />
            <source>UMAP Projection</source>
            <translation>Projection UMAP</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="352" />
            <source>UMAP Projection (3D)</source>
            <translation>Projection UMAP (3D)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="417" />
            <source>UMAP finished</source>
            <translation>UMAP terminé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>UMAP learning rate of the embedding optimisation; larger values move points faster.</source>
            <translation>Taux d'apprentissage UMAP de l'optimisation de l'intégration ; des valeurs plus grandes déplacent les points plus vite.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>UMAP spread; sets how widely the embedded points are scattered.</source>
            <translation>Dispersion UMAP ; définit l'étalement des points intégrés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="197" />
            <source>Unavailable: this measurement has no {need}.</source>
            <translation>Indisponible : cette mesure n'a pas de {need}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="206" />
            <source>Unavailable: {reason}.</source>
            <translation>Indisponible : {reason}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="418" />
            <source>Unlink</source>
            <translation>Délier</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Untick every column in the list.</source>
            <translation>Décocher toutes les colonnes de la liste.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1102" />
            <location filename="ndxplorer/app/menus.py" line="84" />
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Update</source>
            <translation>Mettre à jour</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Update default axis range. To save current default axis settings use the Settings-&gt;Save Menu.</source>
            <translation>Mettre à jour la plage d'axe par défaut. Pour enregistrer les paramètres d'axe par défaut actuels, utiliser le menu Paramètres-&gt;Enregistrer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1098" />
            <source>Update with the package manager that installed ndXplorer:</source>
            <translation>Mettre à jour avec le gestionnaire de paquets qui a installé ndXplorer :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Upper bound of the gate on this parameter.</source>
            <translation>Borne supérieure du gate sur ce paramètre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Upper bound. ∞: none. Type a number to set it, ∞ (or inf) to remove it.</source>
            <translation>Borne supérieure. ∞ : aucune. Saisir un nombre pour la définir, ∞ (ou inf) pour la supprimer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Upper colour limit of the 2-D histogram.</source>
            <translation>Limite de couleur supérieure de l'histogramme 2D.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Use</source>
            <translation>Utiliser</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Use Fast Histogram Optimizations</source>
            <translation>Utiliser les optimisations rapides d'histogramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Use Parallel Computation</source>
            <translation>Utiliser le calcul parallèle</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Use islands as clusters</source>
            <translation>Utiliser les îlots comme clusters</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Use light-path priors</source>
            <translation>Utiliser des a priori du trajet optique</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Use multiple CPU cores for histogram computation when available.</source>
            <translation>Utiliser plusieurs cœurs de processeur pour le calcul des histogrammes, si disponibles.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Validate all equations and recompute the derived columns</source>
            <translation>Valider toutes les équations et recalculer les colonnes dérivées</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Value</source>
            <translation>Valeur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Value after the calibration.</source>
            <translation>Valeur après l'étalonnage.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Value before the calibration.</source>
            <translation>Valeur avant l'étalonnage.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="391" />
            <source>Value for '{name}':</source>
            <translation>Valeur pour '{name}' :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Value of the correction factor.</source>
            <translation>Valeur du facteur de correction.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Values in settings file override environment variables.</source>
            <translation>Les valeurs du fichier de paramètres remplacent les variables d'environnement.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Vector</source>
            <translation>Vecteur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Vector (PDF/SVG) is resolution-independent and best for print; PNG is a high-resolution raster.</source>
            <translation>Le vectoriel (PDF/SVG) est indépendant de la résolution et idéal pour l'impression ; PNG est un raster haute résolution.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="419" />
            <source>Vector constants written: none — scalar factors only</source>
            <translation>Constantes vectorielles écrites : aucune — facteurs scalaires uniquement</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="415" />
            <source>Vector constants written: {vectors}</source>
            <translation>Constantes vectorielles écrites : {vectors}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Verbose:</source>
            <translation>Verbosité :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Verbosity of the Gaussian mixture fit log (0 is silent).</source>
            <translation>Verbosité du journal de l'ajustement du mélange gaussien (0 est silencieux).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="61" />
            <source>View</source>
            <translation>Affichage</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="60" />
            <source>Weight by photons</source>
            <translation>Pondérer par les photons</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Weight floor:</source>
            <translation>Poids plancher :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>What makes a view informative. Separation (default): how many bursts fall into clearly separated islands -- donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line; one population scores 0 however correlated. Correlation: parameters that move together (related measurements, not populations). Classes (only with gates or clusters): views that keep the labelled bursts apart.</source>
            <translation>Ce qui rend une vue informative. Séparation (par défaut) : combien de bursts tombent dans des îlots nettement séparés -- espèces donneur seul, accepteur seul et FRET en E vs S, une population dynamique hors de la ligne FRET statique ; une seule population obtient 0 quelle que soit sa corrélation. Corrélation : paramètres qui varient ensemble (mesures liées, et non populations). Classes (seulement avec des gates ou des clusters) : vues qui séparent les bursts étiquetés.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>What the populations are told apart by. S alone is the stoichiometry gating (fast, the default); any other ticked dimension switches to the multidimensional mixture over all ticked ones, about ten times slower (25 s instead of 2.4 s on cal1). Dimensions this measurement has no column for are disabled; their tooltip says which column is missing.</source>
            <translation>Ce qui distingue les populations. S seul est le gating par stœchiométrie (rapide, par défaut) ; toute autre dimension cochée passe au mélange multidimensionnel sur toutes les dimensions cochées, environ dix fois plus lent (25 s au lieu de 2.4 s sur cal1). Les dimensions pour lesquelles cette mesure n'a pas de colonne sont désactivées ; leur infobulle indique la colonne manquante.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>What this panel does</source>
            <translation>Ce que fait ce panneau</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>When it finishes</source>
            <translation>À la fin</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Where the curve ends (t1); it is traced with the tab's number of points.</source>
            <translation>Où la courbe se termine (t1) ; elle est tracée avec le nombre de points de l'onglet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Where the curve starts (t0).</source>
            <translation>Où la courbe commence (t0).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Where the result is kept. The measurement container is the default: it already holds the photons, the burst table and the background estimate, and a calibration determined from them belongs in the same file.</source>
            <translation>Où le résultat est conservé. Le conteneur de la mesure est le choix par défaut : il contient déjà les photons, la table des bursts et l'estimation du bruit de fond, et un étalonnage déterminé à partir d'eux appartient au même fichier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Where:</source>
            <translation>Où :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Whether each FRET population got its own γ: the mode, the model the BIC selected (shared or per population) with both BICs, whether the per-population model was identifiable, and the vector constants written. A written vector is an expandable row of the Parameters tab; right-click &gt; Make scalar turns it back into one value.</source>
            <translation>Indique si chaque population FRET a reçu son propre γ : le mode, le modèle retenu par le BIC (commun ou par population) avec les deux BIC, si le modèle par population était identifiable, et les constantes vectorielles écrites. Un vecteur écrit est une ligne dépliable de l'onglet Paramètres ; clic droit &gt; Make scalar le ramène à une seule valeur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Whether the correction factors may differ between the FRET populations, and what the populations are told apart by. A population-wise γ is written as a vector constant (γ[FRET 1], γ[FRET 2]…) that the Parameters tab lists as an expandable row; to go back to one value, right-click it there and choose Make scalar.</source>
            <translation>Si les facteurs de correction peuvent différer entre les populations FRET, et ce qui distingue les populations. Un γ par population est écrit comme une constante vectorielle (γ[FRET 1], γ[FRET 2]…) que l'onglet Paramètres liste comme une ligne dépliable ; pour revenir à une seule valeur, faites-y un clic droit et choisissez Convertir en scalaire.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Whether the factor was written into the window, or held at the value it had (the options' Determine toggles).</source>
            <translation>Indique si le facteur a été écrit dans la fenêtre ou conservé à sa valeur antérieure (les bascules Determine des options).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Which axes and axis titles the plots show, and the titles' colour.</source>
            <translation>Axes et titres d'axes affichés par les graphiques, et couleur des titres.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Which correction factors this calibration is allowed to change. The others keep the value the window already has.</source>
            <translation>Quels facteurs de correction cet étalonnage peut modifier. Les autres gardent la valeur que la fenêtre a déjà.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Which question to ask of the chosen columns.</source>
            <translation>Quelle question poser aux colonnes choisies.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Which slice is on screen. Drag to scrub through the measurement; double-click to type a step. Hovering shows the slice and how many points survive it.</source>
            <translation>Quelle tranche est affichée. Faire glisser pour parcourir la mesure ; double-clic pour saisir une étape. Le survol indique la tranche et le nombre de points qui y subsistent.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="381" />
            <source>Whole islands</source>
            <translation>Îlots entiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Width (standard deviation) of the FRET efficiency distribution of the population.</source>
            <translation>Largeur (écart type) de la distribution d'efficacité FRET de la population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Width of the dye-linker distance distribution, which sets the curvature of the static FRET line.</source>
            <translation>Largeur de la distribution des distances fluorophore-linker, qui fixe la courbure de la droite FRET statique.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Window</source>
            <translation>Fenêtre</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Window: one slice at a time — what the sample looked like then. Integrate: everything up to the current step, accumulating, so a population that only appears late is visible as it arrives. Stack: no gating, the whole measurement at once.</source>
            <translation>Fenêtre : une tranche à la fois — l'aspect de l'échantillon à ce moment-là. Intégrer : tout jusqu'à l'étape courante, en s'accumulant, de sorte qu'une population n'apparaissant que tard est visible à son arrivée. Pile : pas de gating, toute la mesure à la fois.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Write the changes back to the data and redraw</source>
            <translation>Réécrire les modifications dans les données et redessiner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Write the cluster assignment to a folder.</source>
            <translation>Écrire l'affectation des clusters dans un dossier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Write the corrected per-burst columns under new names. Not redundant with applying the constants: ndX's own efficiency equation has no direct-excitation term, so constants alone cannot make its native column accurate. Its own columns are left untouched.</source>
            <translation>Écrire les colonnes corrigées par burst sous de nouveaux noms. Pas redondant avec l'application des constantes : l'équation d'efficacité propre à ndX n'a pas de terme d'excitation directe, donc les constantes seules ne peuvent pas rendre sa colonne native précise. Ses propres colonnes ne sont pas modifiées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Write the equations to a YAML file</source>
            <translation>Écrire les équations dans un fichier YAML</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Write the report text to a file.</source>
            <translation>Écrire le texte du rapport dans un fichier.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Writes the factors, their uncertainties and the report into the .pto container the bursts came from. Each save is kept as its own object, so an earlier calibration is still there afterwards. With no container, the report window offers a file instead.</source>
            <translation>Écrit les facteurs, leurs incertitudes et le rapport dans le conteneur .pto d'où proviennent les bursts. Chaque enregistrement est conservé comme objet distinct, de sorte qu'un étalonnage antérieur reste disponible ensuite. Sans conteneur, la fenêtre de rapport propose un fichier à la place.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Written</source>
            <translation>Écrit</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>X Plot</source>
            <translation>Graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>X Plot Labels</source>
            <translation>Étiquettes du graphique X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>X axis maximum value</source>
            <translation>Valeur maximale de l'axe X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>X axis minimum value</source>
            <translation>Valeur minimale de l'axe X</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="76" />
            <source>X marginal histogram</source>
            <translation>Distribution marginale en X</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Y Plot</source>
            <translation>Graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Y Plot Labels</source>
            <translation>Étiquettes du graphique Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Y axis maximum value</source>
            <translation>Valeur maximale de l'axe Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Y axis minimum value</source>
            <translation>Valeur minimale de l'axe Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="77" />
            <source>Y marginal histogram</source>
            <translation>Distribution marginale en Y</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis.py" line="140" />
            <location filename="ndxplorer/app/features/analysis.py" line="1183" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Yes</source>
            <translation>Oui</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="820" />
            <source>Yes keeps it beside the photons and the burst table. No writes a separate file instead.</source>
            <translation>Oui la conserve à côté des photons et du tableau de bursts. Non écrit à la place un fichier distinct.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Z Plot</source>
            <translation>Graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Z Plot Labels</source>
            <translation>Étiquettes du graphique Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Z axis maximum value</source>
            <translation>Valeur maximale de l'axe Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Z axis minimum value</source>
            <translation>Valeur minimale de l'axe Z</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="90" />
            <source>ZIP files</source>
            <translation>Fichiers ZIP</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="57" />
            <source>acceptor anisotropy column (e.g. 'r Scatter (yellow)' or 'r Scatter (red)')</source>
            <translation>colonne d'anisotropie de l'accepteur (p. ex. 'r Scatter (yellow)' ou 'r Scatter (red)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="55" />
            <source>acceptor lifetime column (e.g. 'Tau (yellow)' or 'Tau (red)')</source>
            <translation>colonne de durée de vie de l'accepteur (p. ex. 'Tau (yellow)' ou 'Tau (red)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>add</source>
            <translation>ajouter</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="816" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1057" />
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="189" />
            <source>all parameters are fixed</source>
            <translation>tous les paramètres sont fixés</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>auto</source>
            <translation>auto</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="375" />
            <source>auto (the BIC decides)</source>
            <translation>auto (le BIC décide)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="144" />
            <source>background{suffix}: {percent} % of the photons, over {rows} pixels x frames</source>
            <translation>bruit de fond{suffix} : {percent} % des photons, sur {rows} pixels x images</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="182" />
            <source>burst table lacks provenance column(s) {missing}; the selection cannot be resolved to TTTR photon intervals</source>
            <translation>la table des bursts n'a pas de colonne(s) de provenance {missing} ; la sélection ne peut pas être résolue en intervalles de photons TTTR</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="739" />
            <source>calibration failed</source>
            <translation>échec de l'étalonnage</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="677" />
            <source>cannot compile the function: {error}</source>
            <translation>impossible de compiler la fonction : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1215" />
            <source>cannot evaluate equation: {error}</source>
            <translation>impossible d'évaluer l'équation : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="922" />
            <source>cannot fit: {error}</source>
            <translation>ajustement impossible : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/mask_helpers.py" line="74" />
            <source>cannot write an empty mask (shape {shape}) to {path}: a TIFF needs at least one pixel</source>
            <translation>impossible d'écrire un masque vide (forme {shape}) dans {path} : un TIFF nécessite au moins un pixel</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>clear</source>
            <translation>effacer</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="280" />
            <source>cluster</source>
            <translation>cluster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>colour</source>
            <translation>couleur</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="238" />
            <source>column for it</source>
            <translation>colonne correspondante</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="301" />
            <source>column mask does not match the bin edges</source>
            <translation>le masque de colonnes ne correspond pas aux bords de bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>combined</source>
            <translation>combined</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>constants</source>
            <translation>constants</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1797" />
            <source>constants (a calibration stored after the session holds newer ones)</source>
            <translation>constantes (un étalonnage enregistré après la session en contient de plus récentes)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/container.py" line="49" />
            <source>could not commit {path}: {error}</source>
            <translation>impossible de valider {path} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="215" />
            <source>could not identify the {role} column among {columns}…; pass it explicitly</source>
            <translation>impossible d'identifier la colonne {role} parmi {columns}… ; indiquez-la explicitement</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/container.py" line="45" />
            <source>could not open {path}: {error}</source>
            <translation>impossible d'ouvrir {path} : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_background.py" line="179" />
            <source>could not read a background from {container}</source>
            <translation>impossible de lire un bruit de fond depuis {container}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="286" />
            <source>could not write into the container ({reason})</source>
            <translation>impossible d'écrire dans le conteneur ({reason})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="358" />
            <source>curve has no equation to fit</source>
            <translation>la courbe n'a pas d'équation à ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1125" />
            <source>curve has no function to fit</source>
            <translation>la courbe n'a pas de fonction à ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1127" />
            <source>curve has no parameters to fit</source>
            <translation>la courbe n'a pas de paramètres à ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>del</source>
            <translation>suppr.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="56" />
            <source>donor anisotropy column (e.g. 'r Scatter (green)')</source>
            <translation>colonne d'anisotropie du donneur (p. ex. 'r Scatter (green)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="54" />
            <source>donor lifetime column (e.g. 'Tau (green)')</source>
            <translation>colonne de durée de vie du donneur (p. ex. 'Tau (green)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="196" />
            <source>donor-excitation channel counts</source>
            <translation>taux de comptage du canal d'excitation du donneur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>dynamic z-selection</source>
            <translation>sélection z dynamique</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_graph.py" line="136" />
            <source>empty expression</source>
            <translation>expression vide</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1208" />
            <source>equation has no free parameters</source>
            <translation>l'équation n'a pas de paramètres libres</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>es</source>
            <translation>es</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="340" />
            <source>failed: {error}</source>
            <translation>échec : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="215" />
            <source>finished</source>
            <translation>terminé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>fit</source>
            <translation>fit</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="509" />
            <source>fit failed</source>
            <translation>échec de l'ajustement</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="836" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1090" />
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="198" />
            <location filename="ndxplorer/app/features/overlays.py" line="990" />
            <source>fit failed: {error}</source>
            <translation>échec de l'ajustement : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="934" />
            <source>fitting — the data is re-derived at every step… step {n}</source>
            <translation>ajustement en cours — les données sont recalculées à chaque étape… étape {n}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="936" />
            <source>fitting… step {n}</source>
            <translation>ajustement en cours… étape {n}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="140" />
            <source>gate {name}</source>
            <translation>gate {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="237" />
            <source>gating dimension {dim} left out: this table has no {need}</source>
            <translation>dimension de gating {dim} omise : cette table n'a pas de {need}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="381" />
            <source>held</source>
            <translation>maintenu</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="380" />
            <source>held at {value}</source>
            <translation>maintenu à {value}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="119" />
            <source>histogram does not match its bin edges</source>
            <translation>l'histogramme ne correspond pas à ses bords de bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>inf</source>
            <translation>inf</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="266" />
            <source>inside vs outside the gate</source>
            <translation>à l'intérieur vs à l'extérieur du gate</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="339" />
            <source>installed</source>
            <translation>installé</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="50" />
            <source>invalid</source>
            <translation>non valide</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="154" />
            <source>it is open for writing in another program</source>
            <translation>elle est ouverte en écriture dans un autre programme</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>lifetime</source>
            <translation>lifetime</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>load</source>
            <translation>charger</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>log #</source>
            <translation>log #</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/mask_helpers.py" line="90" />
            <source>mask holds a negative class label ({label}); class labels are unsigned and 0 is background</source>
            <translation>le masque contient une étiquette de classe négative ({label}) ; les étiquettes de classe sont non signées et 0 est le fond</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/mask_helpers.py" line="95" />
            <source>mask holds class label {label}, above the 65535 a 16-bit TIFF can carry; relabel the classes consecutively</source>
            <translation>le masque contient l'étiquette de classe {label}, au-delà des 65535 qu'un TIFF 16 bits peut porter ; renuméroter les classes de façon consécutive</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>measurement</source>
            <translation>measurement</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="48" />
            <source>missing output name</source>
            <translation>nom de sortie manquant</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>nDXplorer parameters -- a freed one moves the data, which is re-derived from the equations at every step.</source>
            <translation>Paramètres nDXplorer -- un paramètre libéré déplace les données, qui sont recalculées à partir des équations à chaque étape.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="135" />
            <source>n_bg: the table is not a pixel table (no x pixel, y pixel); set n_bg or edit the f_bg equation</source>
            <translation>n_bg : le tableau n'est pas un tableau de pixels (pas de pixel x, pixel y) ; définir n_bg ou modifier l'équation f_bg</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="371" />
            <source>napari is not installed</source>
            <translation>napari n'est pas installé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="414" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>ndX Report Tool</source>
            <translation>Outil de rapport ndX</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>ndX constants</source>
            <translation>Constantes ndX</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="431" />
            <source>ndX constants:</source>
            <translation>Constantes ndX :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="945" />
            <source>ndX settings</source>
            <translation>Paramètres ndX</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="944" />
            <source>ndX settings file</source>
            <translation>Fichier de paramètres ndX</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1087" />
            <source>ndXplorer -- interactive exploration of multidimensional data (single-molecule fluorescence, sampling, any table).</source>
            <translation>ndXplorer -- exploration interactive de données multidimensionnelles (fluorescence de molécules uniques, échantillonnage, tout tableau).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1083" />
            <source>ndXplorer Help</source>
            <translation>Aide de ndXplorer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="69" />
            <source>ndXplorer shows a table of measurements -- bursts, pixels, samples -- as histograms you can gate.</source>
            <translation>ndXplorer affiche un tableau de mesures -- bursts, pixels, échantillons -- sous forme d'histogrammes que l'on peut gater.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1131" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1197" />
            <source>need at least 3 matching data points</source>
            <translation>au moins 3 points de données correspondants sont nécessaires</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="392" />
            <source>no 2-D histogram displayed ({error})</source>
            <translation>aucun histogramme 2D affiché ({error})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="111" />
            <source>no 2-D histogram to fit</source>
            <translation>aucun histogramme 2D à ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="394" />
            <source>no ChiSurf RPC connection — launch ndX with --chisurf-rpc host:port, or open it from ChiSurf, to use analysis bridges</source>
            <translation>aucune connexion RPC ChiSurf — lancez ndX avec --chisurf-rpc host:port, ou ouvrez-le depuis ChiSurf, pour utiliser les passerelles d'analyse</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="415" />
            <source>no columnar HDF5 table in the file</source>
            <translation>aucun tableau HDF5 en colonnes dans le fichier</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="291" />
            <source>no container for this window and no path given</source>
            <translation>aucun conteneur pour cette fenêtre et aucun chemin indiqué</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="373" />
            <source>no histogram</source>
            <translation>aucun histogramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="162" />
            <source>no mask to save</source>
            <translation>aucun masque à enregistrer</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="505" />
            <source>no parameter {name}</source>
            <translation>aucun paramètre {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="187" />
            <source>no points near the click; click where the population is</source>
            <translation>aucun point près du clic ; cliquer là où se trouve la population</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="160" />
            <source>no points on this plane</source>
            <translation>aucun point sur ce plan</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="409" />
            <source>no sampled states in the file</source>
            <translation>aucun état échantillonné dans le fichier</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="454" />
            <source>no table to rank</source>
            <translation>aucun tableau à classer</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="414" />
            <source>no {target} histogram displayed ({error})</source>
            <translation>aucun histogramme {target} affiché ({error})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="377" />
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>none</source>
            <translation>aucun</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="367" />
            <source>not in the browser</source>
            <translation>pas dans le navigateur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="115" />
            <source>not installed</source>
            <translation>non installé</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="545" />
            <source>nothing to histogram</source>
            <translation>rien à mettre en histogramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="375" />
            <source>off (one global factor set)</source>
            <translation>désactivé (un seul jeu de facteurs global)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="376" />
            <source>on (per population whenever identifiable)</source>
            <translation>activé (par population dès que identifiable)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="55" />
            <source>only inside ChiSurf</source>
            <translation>uniquement dans ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="210" />
            <source>only {n} point(s) in the population at the click</source>
            <translation>seulement {n} point(s) dans la population au clic</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="360" />
            <source>ordering parameters</source>
            <translation>tri des paramètres</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="297" />
            <source>pass 1 of 2 (backgrounds): </source>
            <translation>passe 1 sur 2 (bruits de fond) : </translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="307" />
            <source>pass 2 of 2: </source>
            <translation>passe 2 sur 2 : </translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="213" />
            <source>paused</source>
            <translation>en pause</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="390" />
            <source>per population</source>
            <translation>par population</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="392" />
            <source>per population (forced; the BIC preferred shared)</source>
            <translation>par population (forcé ; le BIC préférait partagé)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="722" />
            <source>playback column</source>
            <translation>colonne de lecture</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="729" />
            <source>playback {key} ({error})</source>
            <translation>lecture {key} ({error})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="248" />
            <source>population finder {method} not available ({reason}); the Gaussian mixture was used</source>
            <translation>recherche de populations {method} indisponible ({reason}) ; le mélange gaussien a été utilisé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="270" />
            <source>population {label} has no displayed data</source>
            <translation>la population {label} n'a pas de données affichées</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="381" />
            <source>populations found by HDBSCAN</source>
            <translation>populations trouvées par HDBSCAN</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="737" />
            <source>python-docx is not installed: PNGs and CSVs were written, no DOCX.</source>
            <translation>python-docx n'est pas installé : les PNG et CSV ont été écrits, pas de DOCX.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>r_A acceptor anisotropy</source>
            <translation>r_A anisotropie de l'accepteur</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>r_D donor anisotropy</source>
            <translation>r_D anisotropie du donneur</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="507" />
            <source>reduced χ² = {chi2r}</source>
            <translation>χ² réduit = {chi2r}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="575" />
            <source>refusing to load {name} out of a data file</source>
            <translation>refus de charger {name} depuis un fichier de données</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>save</source>
            <translation>enregistrer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="194" />
            <source>saved on another table</source>
            <translation>enregistrée sur un autre tableau</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="195" />
            <source>saved on {saved} rows, {now} now</source>
            <translation>enregistrée sur {saved} lignes, {now} maintenant</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>select</source>
            <translation>sélectionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="449" />
            <source>selection is empty — no bursts to send to {target}</source>
            <translation>la sélection est vide — aucun burst à envoyer vers {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="604" />
            <source>selection is empty — nothing to send</source>
            <translation>la sélection est vide — rien à envoyer</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="390" />
            <source>shared</source>
            <translation>partagé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="835" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1081" />
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="197" />
            <source>stopped</source>
            <translation>arrêté</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_graph.py" line="140" />
            <source>syntax error: {error}</source>
            <translation>erreur de syntaxe : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>t from</source>
            <translation>t de</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>t values:</source>
            <translation>Valeurs de t :</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_background.py" line="174" />
            <source>the bursts carry no container, so no measured background</source>
            <translation>les bursts n'ont pas de conteneur, donc pas de bruit de fond mesuré</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="460" />
            <source>the chosen classes are no longer available</source>
            <translation>les classes choisies ne sont plus disponibles</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="157" />
            <source>the click is not on a log axis's positive range</source>
            <translation>le clic n'est pas dans la plage positive d'un axe logarithmique</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="83" />
            <source>the cloud (every populated bin)</source>
            <translation>le nuage (chaque bin peuplé)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="383" />
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="441" />
            <source>the curve has no parameters to fit</source>
            <translation>la courbe n'a pas de paramètres à ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="136" />
            <source>the data has no population column '{column}'</source>
            <translation>les données n'ont pas de colonne de population '{column}'</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="197" />
            <source>the data has no population column '{column}' to fit the populations by</source>
            <translation>les données n'ont pas de colonne de population '{column}' pour ajuster les populations</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="273" />
            <source>the gate a burst falls in</source>
            <translation>le gate dans lequel tombe un burst</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="85" />
            <source>the mean of each column</source>
            <translation>la moyenne de chaque colonne</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_background.py" line="182" />
            <source>the measurement stores no background</source>
            <translation>la mesure ne stocke pas de bruit de fond</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="151" />
            <source>the plotted range is empty (or not positive on a log axis)</source>
            <translation>la plage tracée est vide (ou non positive sur un axe logarithmique)</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="217" />
            <source>the points are collinear: no ellipse describes them</source>
            <translation>les points sont colinéaires : aucune ellipse ne les décrit</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="84" />
            <source>the population of each column</source>
            <translation>la population de chaque colonne</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="415" />
            <source>this file is not a ChiSurf FRET calibration</source>
            <translation>ce fichier n'est pas un étalonnage FRET de ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="452" />
            <source>this measurement carries no stored calibration</source>
            <translation>cette mesure ne contient aucun étalonnage enregistré</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="445" />
            <source>this measurement would have given {value}</source>
            <translation>cette mesure aurait donné {value}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="72" />
            <source>this tttrlib's calibration has no population_method option (only the Gaussian mixture)</source>
            <translation>l'étalonnage de cette tttrlib n'a pas d'option population_method (seulement le mélange gaussien)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="238" />
            <source>this window cannot split its data by population</source>
            <translation>cette fenêtre ne peut pas séparer ses données par population</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>to</source>
            <translation>à</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="295" />
            <source>too few points to fit in population {label} (need 3)</source>
            <translation>trop peu de points à ajuster dans la population {label} (3 nécessaires)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="297" />
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="400" />
            <source>too few populated columns to fit (need 3)</source>
            <translation>trop peu de colonnes peuplées pour ajuster (3 nécessaires)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="279" />
            <source>too little displayed data in population {label}</source>
            <translation>trop peu de données affichées dans la population {label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="445" />
            <source>too little displayed data to fit</source>
            <translation>trop peu de données affichées pour ajuster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="117" />
            <location filename="ndxplorer/app/features/settings.py" line="1094" />
            <source>unknown</source>
            <translation>inconnu</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="155" />
            <source>unknown error</source>
            <translation>erreur inconnue</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_graph.py" line="170" />
            <source>unknown name(s): {names}</source>
            <translation>nom(s) inconnu(s) : {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>weight</source>
            <translation>poids</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="379" />
            <source>written</source>
            <translation>écrit</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="509" />
            <source>x and y differ in length</source>
            <translation>x et y n'ont pas la même longueur</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>x as a function of t; every name that is not t, a definition or a maths function is a parameter.</source>
            <translation>x en fonction de t ; tout nom qui n'est pas t, une définition ou une fonction mathématique est un paramètre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>x(t) =</source>
            <translation>x(t) =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>x:</source>
            <translation>x :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>y as a function of t.</source>
            <translation>y en fonction de t.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>y as a function of x; every other name is a parameter.</source>
            <translation>y en fonction de x ; tout autre nom est un paramètre.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>y(t) =</source>
            <translation>y(t) =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>y:</source>
            <translation>y :</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>z axis</source>
            <translation>axe z</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="54" />
            <source>z parameter: {name}</source>
            <translation>paramètre z : {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>z range</source>
            <translation>plage z</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="114" />
            <source>{channel}: channels are numbers, e.g. 0 1</source>
            <translation>{channel} : les canaux sont des nombres, par ex. 0 1</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="788" />
            <source>{count} islands holding {shares} of the {n} sampled bursts; {inside} % sit clearly inside one (not on a bridge or in a tail). Score {score}: the chance that two bursts are in two different, clearly separated populations.</source>
            <translation>{count} îlots contenant {shares} des {n} bursts échantillonnés ; {inside} % se trouvent nettement à l'intérieur de l'un d'eux (ni sur un pont ni dans une queue). Score {score} : la probabilité que deux bursts appartiennent à deux populations différentes nettement séparées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="803" />
            <source>{current} of {total} points</source>
            <translation>{current} points sur {total}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="566" />
            <source>{done} / {total} files</source>
            <translation>{done} / {total} fichiers</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="211" />
            <source>{done} scored</source>
            <translation>{done} évaluées</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="208" />
            <source>{done}/{total} scored ({percent} %)</source>
            <translation>{done}/{total} évaluées ({percent} %)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io_service.py" line="190" />
            <source>{ext} files</source>
            <translation>Fichiers {ext}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>{filled_label}</source>
            <translation>{filled_label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="171" />
            <source>{gate} (drawn regions need ChiSurf's region module)</source>
            <translation>{gate} (les régions dessinées nécessitent le module de régions de ChiSurf)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="176" />
            <source>{gate} (unknown kind {kind!r})</source>
            <translation>{gate} (type inconnu {kind!r})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <source>{label}</source>
            <translation>{label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1268" />
            <source>{method} failed</source>
            <translation>Échec de {method}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="406" />
            <source>{method} failed: {error}</source>
            <translation>{method} a échoué : {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1357" />
            <source>{method} installed</source>
            <translation>{method} installé</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="138" />
            <source>{method} is not available in the browser: {package} needs numba's compiled code, which the browser cannot run. Use PCA for a projection here, or the desktop app for {method}.</source>
            <translation>{method} n'est pas disponible dans le navigateur : {package} nécessite le code compilé de numba, que le navigateur ne peut pas exécuter. Utiliser PCA pour une projection ici, ou l'application de bureau pour {method}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1206" />
            <source>{method} needs more columns</source>
            <translation>{method} nécessite plus de colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="149" />
            <source>{method} needs {package}, which is not installed.</source>
            <translation>{method} nécessite {package}, qui n'est pas installé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="143" />
            <source>{method} needs {package}, which this page did not load.</source>
            <translation>{method} nécessite {package}, que cette page n'a pas chargé.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1332" />
            <location filename="ndxplorer/app/features/analysis.py" line="1335" />
            <source>{method} not installed</source>
            <translation>{method} non installé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1328" />
            <source>{method} unavailable</source>
            <translation>{method} indisponible</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="186" />
            <source>{name} ({rows} draws, {params} parameters)</source>
            <translation>{name} ({rows} tirages, {params} paramètres)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="183" />
            <source>{name} ({rows} rows, {columns} columns)</source>
            <translation>{name} ({rows} lignes, {columns} colonnes)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="472" />
            <source>{name} has {n} populations; the clipboard holds {count} number(s).</source>
            <translation>{name} a {n} populations ; le presse-papiers contient {count} nombre(s).</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/pto_reader.py" line="142" />
            <source>{name} holds no burst or image table: convert the photons with a burst search first, or point ndX at the analysis folder if one was written.</source>
            <translation>{name} ne contient aucun tableau de bursts ou d'images : convertir d'abord les photons par une recherche de bursts, ou indiquer à ndX le dossier d'analyse s'il en existe un.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="816" />
            <source>{name} holds no columnar HDF5 table (one 1-D dataset per column, at the root or under /results)</source>
            <translation>{name} ne contient aucun tableau HDF5 en colonnes (un jeu de données 1D par colonne, à la racine ou sous /results)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="445" />
            <location filename="ndxplorer/io/project_reader.py" line="135" />
            <source>{name} holds no stored sampling chain</source>
            <translation>{name} ne contient aucune chaîne d'échantillonnage enregistrée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="178" />
            <source>{name} holds {n} stored tables. Which one?</source>
            <translation>{name} contient {n} tableaux enregistrés. Lequel ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="176" />
            <source>{name} holds {n} tables. Which one?</source>
            <translation>{name} contient {n} tableaux. Lequel ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="414" />
            <source>{name} is not a ChiSurf FRET calibration</source>
            <translation>{name} n'est pas un étalonnage FRET de ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="508" />
            <source>{name} will follow the parameter you pick (double-click, or select and Link).</source>
            <translation>{name} suivra le paramètre choisi (double-clic, ou sélectionner puis Lier).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="444" />
            <source>{name}: kept {value}</source>
            <translation>{name} : {value} conservé</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="206" />
            <source>{name}: one value per population, picked per burst by the column '{column}' or mixed by the assignment probabilities. Right-click for the vector's menu.</source>
            <translation>{name} : une valeur par population, choisie par burst via la colonne '{column}' ou mélangée selon les probabilités d'affectation. Clic droit pour le menu du vecteur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="209" />
            <source>{name}: one value per population, picked per burst by the column '{column}'. Right-click for the vector's menu.</source>
            <translation>{name} : une valeur par population, choisie par burst via la colonne '{column}'. Clic droit pour le menu du vecteur.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="217" />
            <source>{name}: population {label}</source>
            <translation>{name} : population {label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="213" />
            <source>{name}: the value of a burst in no population.</source>
            <translation>{name} : la valeur d'un burst n'appartenant à aucune population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1378" />
            <source>{n} column(s) written</source>
            <translation>{n} colonne(s) écrite(s)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="217" />
            <source>{n} failed</source>
            <translation>{n} échouées</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="274" />
            <source>{n} finite rows</source>
            <translation>{n} lignes finies</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="734" />
            <source>{n} folder(s).</source>
            <translation>{n} dossier(s).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="128" />
            <source>{n} islands of {x} vs {y} written as clusters 0–{last}; {labelled} % of bursts labelled, {rest} % on ridges/outliers (−1)</source>
            <translation>{n} îlots de {x} vs {y} écrits comme clusters 0–{last} ; {labelled} % des bursts étiquetés, {rest} % sur des crêtes/valeurs aberrantes (−1)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="131" />
            <source>{n} islands of {x} vs {y} written as clusters 0–{last}; {labelled} % of bursts labelled, {rest} % outside the cores (−1)</source>
            <translation>{n} îlots de {x} vs {y} écrits comme clusters 0–{last} ; {labelled} % des bursts étiquetés, {rest} % en dehors des cœurs (−1)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="485" />
            <source>{n} parameters left out or merged</source>
            <translation>{n} paramètres omis ou fusionnés</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="694" />
            <source>{n} tabulated points</source>
            <translation>{n} points tabulés</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="693" />
            <source>{n} tabulated points from {source}</source>
            <translation>{n} points tabulés depuis {source}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="146" />
            <source>{package} could not be imported, although it ships with the application. The installation is likely broken.</source>
            <translation>{package} n'a pas pu être importé, bien qu'il soit fourni avec l'application. L'installation est probablement défectueuse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1358" />
            <source>{package} was installed but could not be imported yet.
Please restart the application and try again.</source>
            <translation>{package} a été installé mais ne peut pas encore être importé.
Redémarrer l'application et réessayer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/phasor_reference.py" line="132" />
            <source>{path}: channels {channels} hold no instrument response ({percent} % of the photons are flat background)</source>
            <translation>{path} : les canaux {channels} ne contiennent pas de réponse instrumentale ({percent} % des photons sont un fond plat)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/phasor_reference.py" line="122" />
            <source>{path}: fewer than 10 photons in channels {channels}</source>
            <translation>{path} : moins de 10 photons dans les canaux {channels}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1336" />
            <source>{reason}

{blurb}

Install {package} now (conda, conda-forge)?</source>
            <translation>{reason}

{blurb}

Installer {package} maintenant (conda, conda-forge) ?</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="177" />
            <source>{reason}: the population-wise Gaussians cannot tell the bursts apart.</source>
            <translation>{reason} : les gaussiennes par population ne peuvent pas distinguer les bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="480" />
            <source>{rows} of {total} bursts sampled</source>
            <translation>{rows} bursts sur {total} échantillonnés</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="439" />
            <source>{rows} rows fitted, {dropped} dropped as non-finite; {share}% of the variance retained.</source>
            <translation>{rows} lignes ajustées, {dropped} écartées car non finies ; {share} % de la variance conservée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="442" />
            <source>{rows} rows fitted; {share}% of the variance retained.</source>
            <translation>{rows} lignes ajustées ; {share} % de la variance conservée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="816" />
            <source>{share} of each burst's {k} nearest neighbours share its class ({classes}); κ = {kappa} above chance, over {valid} of {n} sampled rows.</source>
            <translation>{share} des {k} plus proches voisins de chaque burst partagent sa classe ({classes}) ; κ = {kappa} au-dessus du hasard, sur {valid} des {n} lignes échantillonnées.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="435" />
            <source>{share}% of variance: {drivers}</source>
            <translation>{share} % de la variance : {drivers}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1230" />
            <source>{shown} / {total} rows × {columns} columns</source>
            <translation>{shown} / {total} lignes × {columns} colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="444" />
            <source>{step} · index {index}</source>
            <translation>{step} · indice {index}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>{title}</source>
            <translation>{title}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="62" />
            <source>{total} equation(s), all valid</source>
            <translation>{total} équation(s), toutes valides</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="61" />
            <source>{total} equation(s), {bad} with problems</source>
            <translation>{total} équation(s), {bad} avec des problèmes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1232" />
            <source>{total} rows × {columns} columns</source>
            <translation>{total} lignes × {columns} colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>{value_label}</source>
            <translation>{value_label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="96" />
            <source>{what} (no column {columns})</source>
            <translation>{what} (pas de colonne {columns})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="663" />
            <source>{x} vs {y} was not ranked by Separation: show a ranked view first.</source>
            <translation>{x} vs {y} n'a pas été classé par Separation : afficher d'abord une vue classée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="660" />
            <source>|Spearman rho| of the pair: parameters that measure related things (E and a lifetime, a rate and its count), not populations. Parameters that are the same quantity are ranked once.</source>
            <translation>|rho de Spearman| de la paire : paramètres qui mesurent des grandeurs liées (E et une durée de vie, un taux et son comptage), et non des populations. Les paramètres représentant la même grandeur ne sont classés qu'une fois.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>±</source>
            <translation>±</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>α leakage</source>
            <translation>α fuite</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>α leakage, δ direct excitation, γ detection/QY ratio, β excitation flux ratio (Hellenkamp et al. 2018); R₀ the Förster radius.</source>
            <translation>α fuite spectrale, δ excitation directe, γ rapport détection/RQ, β rapport des flux d'excitation (Hellenkamp et al. 2018) ; R₀ le rayon de Förster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>β excitation flux</source>
            <translation>β flux d'excitation</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>γ detection / QY</source>
            <translation>γ détection / RQ</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>γ from</source>
            <translation>γ depuis</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="402" />
            <source>γ is held fixed: no per-population γ was written</source>
            <translation>γ est maintenu fixe : aucun γ par population n'a été écrit</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>δ direct excitation</source>
            <translation>δ excitation directe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>σE</source>
            <translation>σE</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>τ_A acceptor lifetime</source>
            <translation>τ_A durée de vie de l'accepteur</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>τ_D donor lifetime</source>
            <translation>τ_D durée de vie du donneur</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>τ_D(0) (ns)</source>
            <translation>τ_D(0) (ns)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>τf (ns)</source>
            <translation>τf (ns)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>↺ Reset</source>
            <translation>↺ Réinitialiser</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>−</source>
            <translation>−</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>∥ One scale</source>
            <translation>∥ Une échelle</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>■</source>
            <translation>■</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="516" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>■ Cancel</source>
            <translation>■ Annuler</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="466" />
            <source>▦ Columns</source>
            <translation>▦ Colonnes</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="465" />
            <source>▦ Columns ({count})</source>
            <translation>▦ Colonnes ({count})</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>▶</source>
            <translation>▶</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>▶ Run</source>
            <translation>▶ Exécuter</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>▶▶</source>
            <translation>▶▶</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>◀</source>
            <translation>◀</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>◀◀</source>
            <translation>◀◀</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>☐ Deselect All</source>
            <translation>☐ Tout désélectionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>☑ Columns…</source>
            <translation>☑ Colonnes…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>☑ Select All</source>
            <translation>☑ Tout sélectionner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>✓</source>
            <translation>✓</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>✓ Apply</source>
            <translation>✓ Appliquer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>✓ valid; ✗ the problem is shown under the table when the row is selected.</source>
            <translation>✓ valide ; ✗ le problème s'affiche sous le tableau lorsque la ligne est sélectionnée.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>✕ Cancel</source>
            <translation>✕ Annuler</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="72" />
            <source>Custom Equation</source>
            <translation>Équation personnalisée</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="585" />
            <source>Result from {target}</source>
            <translation>Résultat de {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/model.py" line="377" />
            <source>{name} has no positive values: a log scale is not possible</source>
            <translation>{name} n’a aucune valeur positive : une échelle logarithmique est impossible</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/model.py" line="373" />
            <source>{name}: log scale, range set to its positive values ({lo:.4g} to {hi:.4g})</source>
            <translation>{name} : échelle logarithmique, plage réglée sur ses valeurs positives ({lo:.4g} à {hi:.4g})</translation>
        </message>
    </context>
</TS>
