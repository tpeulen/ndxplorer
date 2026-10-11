<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="de">
    <context>
        <name>ndxplorer</name>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source> fps</source>
            <translation> fps</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>#</source>
            <translation>#</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>'es' is the 1/S = Ω + Σ·E fit and needs at least two FRET sub-populations; 'lifetime' uses the static FRET line and works on a single population, but needs a per-burst donor lifetime and a trustworthy τ_D(0); 'combined' is the precision-weighted mean; 'auto' takes the E-S fit and falls back to the lifetime. The two routes are independent, so their disagreement is itself a diagnostic.</source>
            <translation>'es' ist der Fit 1/S = Ω + Σ·E und braucht mindestens zwei FRET-Subpopulationen; 'lifetime' nutzt die statische FRET-Linie und funktioniert mit einer einzelnen Population, braucht aber eine Donor-Lebensdauer pro Burst und ein verlässliches τ_D(0); 'combined' ist der präzisionsgewichtete Mittelwert; 'auto' nimmt den E-S-Fit und fällt auf die Lebensdauer zurück. Die beiden Routen sind unabhängig, daher ist ihre Abweichung selbst ein Diagnosewert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>'fit' determines them from the reference populations themselves — an acceptor-only burst has no donor, so what appears in the donor channel is background; a donor-only burst has no acceptor, so what appears under acceptor excitation is background; and the leakage line I_DA = α·I_DD + bg_da gives the third as its intercept. Use this when the background is not known, which is most of the time. It costs a second calibration pass: the populations have to exist before they can be read, and once the background is subtracted the classification is made again.

'measurement' uses the rates the Background step stored in this measurement's container, multiplied by each burst's duration — so a 4 ms burst carries four times the background of a 1 ms one, which a single number cannot express. Falls back to the window's constants if the container has no stored estimate.

'constants' uses the window's Bg / Br / By as they stand. 'none' sets them to zero.

This is the correction whose error is hardest to see: it moves the dim bursts and leaves the bright ones, which looks exactly like a real sub-population.</source>
            <translation>'fit' bestimmt sie aus den Referenzpopulationen selbst — ein Akzeptor-only-Burst hat keinen Donor, daher ist alles im Donorkanal Hintergrund; ein Donor-only-Burst hat keinen Akzeptor, daher ist alles unter Akzeptoranregung Hintergrund; und die Leckagegerade I_DA = α·I_DD + bg_da liefert den dritten als Achsenabschnitt. Verwenden, wenn der Hintergrund unbekannt ist, was meistens der Fall ist. Das kostet einen zweiten Kalibrierdurchgang: Die Populationen müssen existieren, bevor sie gelesen werden können, und nach Abzug des Hintergrunds wird die Klassifizierung erneut vorgenommen.

'measurement' nutzt die Raten, die der Schritt Hintergrund im Container dieser Messung gespeichert hat, multipliziert mit der Dauer jedes Bursts — ein 4-ms-Burst trägt also viermal so viel Hintergrund wie ein 1-ms-Burst, was eine einzelne Zahl nicht ausdrücken kann. Fällt auf die Konstanten des Fensters zurück, wenn der Container keine gespeicherte Schätzung hat.

'constants' nutzt Bg / Br / By des Fensters unverändert. 'none' setzt sie auf null.

Dies ist die Korrektur, deren Fehler am schwersten zu erkennen ist: Sie verschiebt die schwachen Bursts und lässt die hellen unberührt, was genau wie eine echte Subpopulation aussieht.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="416" />
            <source>(Parameters tab; right-click a vector &gt; Make scalar to go back to one value)</source>
            <translation>(Reiter Parameter; Rechtsklick auf einen Vektor &gt; In Skalar umwandeln, um zu einem Wert zurückzukehren)</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="142" />
            <source>({x}, {y}) is outside the plotted range</source>
            <translation>({x}, {y}) liegt außerhalb des dargestellten Bereichs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>+</source>
            <translation>+</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="135" />
            <source>, replacing the previous clusters</source>
            <translation>, wobei die vorherigen Cluster ersetzt wurden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>-1 uses all available cores, 0/1 disables parallelism.</source>
            <translation>-1 nutzt alle verfügbaren Kerne, 0/1 deaktiviert Parallelisierung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>/</source>
            <translation>/</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>0 for scatter / a mirror; the lifetime of a reference dye otherwise.</source>
            <translation>0 für Streuung / einen Spiegel; sonst die Lebensdauer eines Referenzfarbstoffs.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="484" />
            <source>1-D histograms copied to the clipboard (tab separated).</source>
            <translation>1D-Histogramme in die Zwischenablage kopiert (tabulatorgetrennt).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="72" />
            <source>1. Open data: File &gt; Import (a burst-analysis folder, text files, an analysis file or a ChiSurf sampling), or drop a file or folder on the window.</source>
            <translation>1. Daten öffnen: Datei &gt; Importieren (ein Burst-Analyseordner, Textdateien, eine Analysedatei oder ein ChiSurf-Sampling) oder eine Datei bzw. einen Ordner auf das Fenster ziehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>2 to plot directly, 3 for more room.</source>
            <translation>2 zum direkten Darstellen, 3 für mehr Spielraum.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="474" />
            <source>2-D histogram copied to the clipboard (tab separated).</source>
            <translation>2D-Histogramm in die Zwischenablage kopiert (tabulatorgetrennt).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="74" />
            <source>2. Choose the x, y and z parameters in Plot controls; each has bins, a range (Auto), log and norm. Set stores a parameter's axis; Settings &gt; Save settings &gt; Axis settings writes them to a file.</source>
            <translation>2. Die Parameter x, y und z in den Plot-Steuerelementen wählen; jeder hat Bins, einen Bereich (Auto), log und norm. Setzen speichert die Achse eines Parameters; Einstellungen &gt; Einstellungen speichern &gt; Achseneinstellungen schreibt sie in eine Datei.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>2D Plot</source>
            <translation>2D-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="77" />
            <source>3. Drag a rectangle on the 2-D map to gate: the Selection table lists the gates, which can be inverted, disabled and edited.</source>
            <translation>3. Ein Rechteck auf der 2D-Karte aufziehen, um zu gaten: Die Auswahltabelle listet die Gates, die sich invertieren, deaktivieren und bearbeiten lassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="79" />
            <source>4. Parameters, Overlays, Equations and the analyses (clustering, Gaussian fit, informative projections) are in the tabs and the View menu.</source>
            <translation>4. Parameter, Overlays, Gleichungen und die Analysen (Clustering, Gauß-Fit, informative Projektionen) befinden sich in den Tabs und im Menü Ansicht.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="81" />
            <source>5. File &gt; Make Report makes PNG/CSV/DOCX reports over many analysis folders from a report.yaml.</source>
            <translation>5. Datei &gt; Bericht erstellen erzeugt PNG-/CSV-/DOCX-Berichte über viele Analyseordner aus einer report.yaml.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>&lt;b&gt;Separation&lt;/b&gt; (default) finds the views where the bursts fall into clearly separated islands: donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line. &lt;b&gt;Correlation&lt;/b&gt; finds parameters that move together. &lt;b&gt;Classes&lt;/b&gt; appears when there are gates or clusters and finds views that keep them apart.</source>
            <translation>&lt;b&gt;Separation&lt;/b&gt; (Standard) findet die Ansichten, in denen die Bursts in klar getrennte Inseln fallen: Donor-only, Akzeptor-only und FRET-Spezies in E vs S, eine dynamische Population abseits der statischen FRET-Linie. &lt;b&gt;Correlation&lt;/b&gt; findet Parameter, die sich gemeinsam bewegen. &lt;b&gt;Classes&lt;/b&gt; erscheint, wenn es Gates oder Cluster gibt, und findet Ansichten, die sie auseinanderhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <source>A load or a save running in the background.</source>
            <translation>Ein Ladevorgang oder Speichervorgang im Hintergrund.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="301" />
            <location filename="ndxplorer/app/features/overlays.py" line="402" />
            <source>A parameter named '{name}' already exists.</source>
            <translation>Ein Parameter namens '{name}' existiert bereits.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="299" />
            <source>A parameter needs a name.</source>
            <translation>Ein Parameter braucht einen Namen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="346" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="880" />
            <source>A stored calibration.</source>
            <translation>Eine gespeicherte Kalibrierung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="132" />
            <source>A vector (▸ gamma [2]) holds one value per population; open it for the elements.</source>
            <translation>Ein Vektor (▸ gamma [2]) enthält einen Wert je Population; öffnen, um die Elemente zu sehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="304" />
            <source>A vector needs its populations: how many, or their names.</source>
            <translation>Ein Vektor braucht seine Populationen: wie viele oder ihre Namen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="306" />
            <source>A vector's name cannot end in [...].</source>
            <translation>Der Name eines Vektors darf nicht auf [...] enden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="83" />
            <source>About</source>
            <translation>Über</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1091" />
            <source>About ndXplorer</source>
            <translation>Über ndXplorer</translation>
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
            <translation>Die Einträge übernehmen und den Dialog schließen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Acceptor excited by the donor laser. Taken from the acceptor-only population, so it needs one.</source>
            <translation>Akzeptor, vom Donor-Laser angeregt. Wird aus der Akzeptor-only-Population bestimmt und braucht daher eine.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="736" />
            <source>Accurate FRET</source>
            <translation>Accurate FRET</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Accurate FRET efficiency of the population.</source>
            <translation>Genaue FRET-Effizienz der Population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="207" />
            <source>Accurate FRET needs tttrlib's FRET calibration (tttrlib.auto_calibrate), which this tttrlib does not have.</source>
            <translation>Genaues FRET benötigt die FRET-Kalibrierung von tttrlib (tttrlib.auto_calibrate), die diese tttrlib nicht hat.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Add Curve</source>
            <translation>Kurve hinzufügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Add a Gaussian in the middle of the map.</source>
            <translation>Eine Gauß-Funktion in der Mitte der Karte hinzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Add a new constant (name + value)</source>
            <translation>Neue Konstante hinzufügen (Name + Wert)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Add a new selection range to the selection list.</source>
            <translation>Einen neuen Auswahlbereich zur Auswahlliste hinzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Add accurate E / S / R_DA columns</source>
            <translation>Genaue E-/S-/R_DA-Spalten hinzufügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Add an analysis folder (or a folder above several)</source>
            <translation>Analyseordner hinzufügen (oder einen Ordner über mehreren)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Add an equation</source>
            <translation>Gleichung hinzufügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="465" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="171" />
            <source>Add one or more Gaussians (click on the histogram) before fitting.</source>
            <translation>Vor dem Anpassen eine oder mehrere Gauß-Kurven hinzufügen (Klick auf das Histogramm).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Add or remove Gaussian components of the fit to the current histogram.</source>
            <translation>Gauß-Komponenten des Fits an das aktuelle Histogramm hinzufügen oder entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="372" />
            <location filename="ndxplorer/app/features/overlays.py" line="401" />
            <location filename="ndxplorer/app/features/overlays.py" line="413" />
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Add parameter</source>
            <translation>Parameter hinzufügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Add the chosen curve to the plot.</source>
            <translation>Die gewählte Kurve zum Diagramm hinzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Add the painted area to the mask.</source>
            <translation>Die bemalte Fläche zur Maske hinzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Add the painted category as a mask gate in the Selection table.</source>
            <translation>Die bemalte Kategorie als Masken-Gate in der Auswahltabelle hinzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Added to the covariance diagonals, so no component collapses.</source>
            <translation>Wird zu den Kovarianzdiagonalen addiert, damit keine Komponente kollabiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1321" />
            <source>Added {first}…{last}. Pick them in the axis controls to plot.</source>
            <translation>{first}…{last} hinzugefügt. In den Achsenreglern auswählen, um sie darzustellen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1743" />
            <source>Added {n} line(s) to the Overlays tab</source>
            <translation>{n} Linie(n) zum Tab Overlays hinzugefügt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1740" />
            <source>Added {n} line(s) to the Overlays tab from {source}</source>
            <translation>{n} Linie(n) aus {source} zum Tab Overlays hinzugefügt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Add…</source>
            <translation>Hinzufügen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Advanced</source>
            <translation>Erweitert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Advanced Options</source>
            <translation>Erweiterte Optionen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>After</source>
            <translation>Nachher</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Aggressive Caching</source>
            <translation>Aggressives Caching</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="91" />
            <location filename="ndxplorer/io/loading.py" line="99" />
            <source>All Files</source>
            <translation>Alle Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="59" />
            <source>All bursts, equal weight</source>
            <translation>Alle Bursts, gleiches Gewicht</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>All cores</source>
            <translation>Alle Kerne</translation>
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
            <translation>Alle Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="75" />
            <source>All files (*.selection.json)</source>
            <translation>Alle Dateien (*.selection.json)</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="436" />
            <source>All of {lo}–{hi}{unit}</source>
            <translation>Alles von {lo}–{hi}{unit}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="691" />
            <source>All selected analysis folders already have a report. Nothing to generate.</source>
            <translation>Alle ausgewählten Analyseordner haben bereits einen Bericht. Nichts zu erzeugen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="434" />
            <source>All {n} · {first}–{last}</source>
            <translation>Alle {n} · {first}–{last}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="778" />
            <source>Also this view: {names}.</source>
            <translation>Auch diese Ansicht: {names}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>An analysis folder, or a folder above several</source>
            <translation>Ein Analyseordner oder ein Ordner über mehreren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="27" />
            <source>Analysis file (*.zip, *.hdf)</source>
            <translation>Analysedatei (*.zip, *.hdf)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Analysis folders (drop here):</source>
            <translation>Analyseordner (hier ablegen):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="28" />
            <source>Analysis-Folder</source>
            <translation>Analyseordner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Answer no and continue without it.</source>
            <translation>Nein antworten und ohne fortfahren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Answer yes and continue.</source>
            <translation>Ja antworten und fortfahren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="113" />
            <source>Append as columns (add new columns, rows must match)</source>
            <translation>Als Spalten anhängen (neue Spalten hinzufügen, Zeilen müssen übereinstimmen)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="114" />
            <source>Append as rows (add new rows of existing columns)</source>
            <translation>Als Zeilen anhängen (neue Zeilen bestehender Spalten hinzufügen)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Apply</source>
            <translation>Anwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="628" />
            <source>Apply a saved FRET calibration to the current ndX session.</source>
            <translation>Eine gespeicherte FRET-Kalibrierung auf die aktuelle ndX-Sitzung anwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Apply and close</source>
            <translation>Anwenden und schließen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Apply the computed reference calibration to the loaded data.</source>
            <translation>Die berechnete Referenzkalibrierung auf die geladenen Daten anwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="883" />
            <source>Apply this calibration to the window?</source>
            <translation>Diese Kalibrierung auf das Fenster anwenden?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Arrays held by the overlay store; edit cells to change parameter values.</source>
            <translation>Vom Overlay-Speicher gehaltene Arrays; Zellen bearbeiten, um Parameterwerte zu ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Ask where to save, then write the figure.</source>
            <translation>Nach dem Speicherort fragen, dann die Abbildung schreiben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Asked after the burst-ID (.bst) files were written: what to do with them.</source>
            <translation>Wird gefragt, nachdem die Burst-ID-Dateien (.bst) geschrieben wurden: was damit geschehen soll.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Asked when a ChiSurf project holds more than one stored table (one per sampled fit): which one to open.</source>
            <translation>Wird gefragt, wenn ein ChiSurf-Projekt mehr als eine gespeicherte Tabelle enthält (eine je gesampltem Fit): welche geöffnet werden soll.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Asked when data is already loaded and another file is opened: replace the table, or merge the new one into it.</source>
            <translation>Wird gefragt, wenn bereits Daten geladen sind und eine weitere Datei geöffnet wird: die Tabelle ersetzen oder die neue zusammenführen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1090" />
            <source>Author: Thomas-Otavio Peulen. License: GPL-2.1.</source>
            <translation>Autor: Thomas-Otavio Peulen. Lizenz: GPL-2.1.</translation>
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
            <translation>X-Achse automatisch an die Daten anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Auto-range the y axis to the data</source>
            <translation>Y-Achse automatisch an die Daten anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Auto-range the z axis to the data</source>
            <translation>Z-Achse automatisch an die Daten anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Available names that can be used in the expression; double-click to insert one.</source>
            <translation>Im Ausdruck verwendbare Namen; Doppelklick zum Einfügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Axes, bin counts, ranges and weighting for the marginal and 2-D histograms.</source>
            <translation>Achsen, Bin-Anzahlen, Bereiche und Gewichtung für die Rand- und 2D-Histogramme.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Axis</source>
            <translation>Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="252" />
            <location filename="ndxplorer/app/features/settings.py" line="1066" />
            <location filename="ndxplorer/app/features/settings.py" line="1070" />
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="77" />
            <source>Axis Control</source>
            <translation>Achsensteuerung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis Label Settings</source>
            <translation>Achsenbeschriftungs-Einstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="911" />
            <source>Axis Mismatch</source>
            <translation>Achsen passen nicht</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="989" />
            <source>Axis file</source>
            <translation>Achsendatei</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1071" />
            <source>Axis label and font settings saved and applied successfully.</source>
            <translation>Einstellungen für Achsenbeschriftung und Schrift gespeichert und angewendet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis labels of the x marginal plot.</source>
            <translation>Achsenbeschriftungen des x-Randhistogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis labels of the y marginal plot.</source>
            <translation>Achsenbeschriftungen des y-Randhistogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis labels of the z marginal plot.</source>
            <translation>Achsenbeschriftungen des z-Randhistogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="55" />
            <source>Axis settings</source>
            <translation>Achseneinstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="989" />
            <source>Axis settings file</source>
            <translation>Achseneinstellungsdatei</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility and enabling of the z marginal plot.</source>
            <translation>Sichtbarkeit der Achsen und Aktivierung des z-Randhistogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the 2D histogram plot.</source>
            <translation>Sichtbarkeit der Achsen des 2D-Histogramm-Diagramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the overlay plot.</source>
            <translation>Sichtbarkeit der Achsen des Overlay-Diagramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the x marginal plot.</source>
            <translation>Sichtbarkeit der Achsen des x-Randhistogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Axis visibility of the y marginal plot.</source>
            <translation>Sichtbarkeit der Achsen des y-Randhistogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>BID</source>
            <translation>BID</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="432" />
            <source>Back</source>
            <translation>Zurück</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Background</source>
            <translation>Hintergrund</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="455" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="433" />
            <source>Background, fitted from the reference populations: {values}</source>
            <translation>Hintergrund, aus den Referenzpopulationen angepasst: {values}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="471" />
            <source>Background: none (set to zero)</source>
            <translation>Hintergrund: keiner (auf null gesetzt)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="464" />
            <source>Background: per burst, from this measurement's own estimate ({columns})</source>
            <translation>Hintergrund: pro Burst, aus der eigenen Schätzung dieser Messung ({columns})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="467" />
            <source>Background: the container has no stored estimate — the window's own constants were used</source>
            <translation>Hintergrund: Der Container enthält keine gespeicherte Schätzung — die eigenen Konstanten des Fensters wurden verwendet</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="458" />
            <source>Background: the reference populations were too small to fit one — the window's constants were used</source>
            <translation>Hintergrund: Die Referenzpopulationen waren zu klein für eine Anpassung — die Konstanten des Fensters wurden verwendet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="436" />
            <source>Background: {source}</source>
            <translation>Hintergrund: {source}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Backgrounds are an input to the calibration, not one of its factors — unless you ask it to fit them, which is what 'fit' does.</source>
            <translation>Hintergründe sind eine Eingabe der Kalibrierung, keiner ihrer Faktoren — es sei denn, man lässt sie anpassen, was 'fit' tut.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Batch reports over analysis folders: a report.yaml names the plots, each folder gets PNGs, CSVs and a DOCX.</source>
            <translation>Stapelberichte über Analyseordner: Eine report.yaml benennt die Diagramme, jeder Ordner erhält PNGs, CSVs und eine DOCX.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Before</source>
            <translation>Vorher</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="284" />
            <source>Bitmap {n} ({x}, {y})</source>
            <translation>Bitmap {n} ({x}, {y})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Bootstrap resamples</source>
            <translation>Bootstrap-Stichproben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Bottom Axis</source>
            <translation>Untere Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Bottom Axis Label</source>
            <translation>Untere Achsenbeschriftung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Browse</source>
            <translation>Durchsuchen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Browse generated images</source>
            <translation>Erzeugte Bilder durchsuchen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Browse the images generated by the report.</source>
            <translation>Die vom Bericht erzeugten Bilder durchsehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Brush radius in pixels.</source>
            <translation>Pinselradius in Pixeln.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Brush:</source>
            <translation>Pinsel:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="36" />
            <source>Burst IDs</source>
            <translation>Burst-IDs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="605" />
            <source>Burst IDs saved; recording them failed: {error}</source>
            <translation>Burst-IDs gespeichert; ihre Aufzeichnung ist fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="87" />
            <source>Burst analysis folder</source>
            <translation>Burst-Analyseordner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Burst-table columns; tick to show a column and filter the list by name.</source>
            <translation>Spalten der Burst-Tabelle; ankreuzen, um eine Spalte anzuzeigen, und die Liste nach Namen filtern.</translation>
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
            <translation>Zufällig für das Scoring gezogene Bursts. Dieselbe Stichprobe dient allen Ansichten, sodass Ansichten an identischen Bursts verglichen werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Bursts with fewer photons than this are left out of the Separation score.</source>
            <translation>Bursts mit weniger Photonen als diesem Wert werden aus dem Trennungs-Score ausgelassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="827" />
            <source>CSV Files</source>
            <translation>CSV-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1358" />
            <source>CSV files</source>
            <translation>CSV-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Cache more intermediate results for better performance at the cost of higher memory usage.</source>
            <translation>Mehr Zwischenergebnisse zwischenspeichern für bessere Leistung auf Kosten höheren Speicherbedarfs.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="99" />
            <source>Calibrate</source>
            <translation>Kalibrieren</translation>
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
            <translation>Abbrechen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Cancel the import</source>
            <translation>Import abbrechen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="741" />
            <source>Canceled</source>
            <translation>Abgebrochen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="512" />
            <source>Cancelled or failed.</source>
            <translation>Abgebrochen oder fehlgeschlagen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="271" />
            <source>Cancelled.</source>
            <translation>Abgebrochen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="510" />
            <location filename="ndxplorer/app/features/analysis.py" line="516" />
            <location filename="ndxplorer/app/features/io.py" line="257" />
            <source>Cancelling…</source>
            <translation>Abbruch läuft…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="331" />
            <source>Cannot rank: {error}</source>
            <translation>Ranking nicht möglich: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="601" />
            <source>Cannot show {name}</source>
            <translation>{name} kann nicht angezeigt werden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Cat:</source>
            <translation>Kat.:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Category/class ID for drawing (1-255): the one the brush paints and Apply turns into a gate.</source>
            <translation>Kategorie-/Klassen-ID zum Zeichnen (1-255): die der Pinsel malt und die Anwenden zu einem Gate macht.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Change working path</source>
            <translation>Arbeitspfad ändern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="864" />
            <source>Changes:</source>
            <translation>Änderungen:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Channels of g, s:</source>
            <translation>Kanäle von g, s:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="376" />
            <source>ChiSurf does not advertise a burst consumer named {key}; it offers {offered}</source>
            <translation>ChiSurf bietet keinen Burst-Verbraucher namens {key}; angeboten wird: {offered}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="260" />
            <source>ChiSurf is not available: the lifetime route used the no-linker line E = 1 - tau/tau_D(0) instead of the static FRET line (tau_D(0) = {tau} ns)</source>
            <translation>ChiSurf ist nicht verfügbar: Die Lebensdauer-Route verwendete die Linker-freie Linie E = 1 - tau/tau_D(0) statt der statischen FRET-Linie (tau_D(0) = {tau} ns)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="101" />
            <source>ChiSurf project</source>
            <translation>ChiSurf-Projekt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="31" />
            <source>ChiSurf project (*.cs.pto)</source>
            <translation>ChiSurf-Projekt (*.cs.pto)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="102" />
            <source>ChiSurf projects</source>
            <translation>ChiSurf-Projekte</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="95" />
            <source>ChiSurf sampling files</source>
            <translation>ChiSurf-Sampling-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="511" />
            <source>ChiSurf's fits are not listed: ChiSurf is not available here.</source>
            <translation>Die Fits von ChiSurf werden nicht aufgelistet: ChiSurf ist hier nicht verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="30" />
            <source>ChiSurf-Sampling</source>
            <translation>ChiSurf-Sampling</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Choose IRF…</source>
            <translation>IRF wählen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="92" />
            <source>Choose an IRF (and a measurement), then Compute.</source>
            <translation>Eine IRF (und eine Messung) wählen, dann Berechnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1211" />
            <source>Choose at least {n} columns to project.</source>
            <translation>Mindestens {n} Spalten zur Projektion wählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Choose measurement…</source>
            <translation>Messung wählen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Choose the criterion used to rank pairs of parameters by how informative their 2D view of the bursts is.</source>
            <translation>Kriterium wählen, nach dem Parameterpaare danach gerankt werden, wie informativ ihre 2D-Ansicht der Bursts ist.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Choose what "informative" means</source>
            <translation>Festlegen, was "informativ" bedeutet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Choose what to do with the saved Burst IDs:</source>
            <translation>Auswählen, was mit den gespeicherten Burst-IDs geschehen soll:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Choose which axis labels are shown on the plots.</source>
            <translation>Auswählen, welche Achsenbeschriftungen in den Diagrammen angezeigt werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Choose which columns are shown</source>
            <translation>Wählen, welche Spalten angezeigt werden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Choose which parameters the method sees. Strongly recommended: without a choice it falls back to the current x/y/z axes.</source>
            <translation>Auswählen, welche Parameter die Methode sieht. Dringend empfohlen: ohne Auswahl greift sie auf die aktuellen x/y/z-Achsen zurück.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="651" />
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Classes</source>
            <translation>Klassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/selection.py" line="52" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Clear</source>
            <translation>Leeren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="773" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Clear Reports</source>
            <translation>Berichte löschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="500" />
            <source>Clear list</source>
            <translation>Liste leeren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Clear the plots and the working path.</source>
            <translation>Diagramme und Arbeitspfad leeren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="767" />
            <source>Cleared reports for {n} folder(s).</source>
            <translation>Berichte für {n} Ordner gelöscht.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Click a row to see that plot</source>
            <translation>Auf eine Zeile klicken, um dieses Diagramm zu sehen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Clicks on the map add a Gaussian there.</source>
            <translation>Klicks auf die Karte fügen dort eine Gauß-Funktion hinzu.</translation>
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
            <translation>Schließen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Close the report tool</source>
            <translation>Berichtswerkzeug schließen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Close this dialog.</source>
            <translation>Diesen Dialog schließen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Close without applying</source>
            <translation>Schließen ohne Anwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Close without exporting.</source>
            <translation>Schließen ohne Export.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Close without saving</source>
            <translation>Schließen ohne Speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Close without writing any change back</source>
            <translation>Schließen, ohne Änderungen zurückzuschreiben</translation>
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
            <translation>Clustering-Daten erfolgreich gespeichert!</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1385" />
            <source>Clustering data saved to {path}</source>
            <translation>Clustering-Daten gespeichert unter {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1265" />
            <source>Clustering using {method} completed successfully.</source>
            <translation>Clustering mit {method} erfolgreich abgeschlossen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="280" />
            <source>Clusters</source>
            <translation>Cluster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Clusters:</source>
            <translation>Cluster:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Color:</source>
            <translation>Farbe:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Colormap of the 2-D histogram.</source>
            <translation>Farbskala des 2D-Histogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Colour by value</source>
            <translation>Nach Wert einfärben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Colour of the axis titles</source>
            <translation>Farbe der Achsentitel</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Colour the 2-D histogram by log10 of the counts.</source>
            <translation>2D-Histogramm nach log10 der Zählwerte einfärben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Colour the 2-D map by cluster.</source>
            <translation>2D-Karte nach Cluster einfärben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Colour the map by the islands the Separation score found in the selected view (the view must be on the axes).</source>
            <translation>Die Karte nach den Inseln einfärben, die der Trennungs-Score in der gewählten Ansicht fand (die Ansicht muss auf den Achsen liegen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Column</source>
            <translation>Spalte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Column each point is weighted by when the histograms are filled</source>
            <translation>Spalte, mit der jeder Punkt beim Füllen der Histogramme gewichtet wird</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Column the playback runs along. Picked from the data on load — the frame index of an image stack, otherwise the per-burst macro time — but any numeric column can be played back.</source>
            <translation>Spalte, entlang der abgespielt wird. Wird beim Laden aus den Daten gewählt — der Frame-Index eines Bildstapels, sonst die Makrozeit pro Burst — aber jede numerische Spalte kann abgespielt werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays.py" line="1394" />
            <location filename="ndxplorer/core/equation_table.py" line="166" />
            <source>Columns</source>
            <translation>Spalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Combine the data estimates with the optical model's excitation/emission probabilities, so the result is a posterior: data where the data speaks, optics where it does not.</source>
            <translation>Die Datenschätzungen mit den Anregungs-/Emissionswahrscheinlichkeiten des optischen Modells kombinieren, sodass das Ergebnis ein Posterior ist: Daten, wo die Daten aussagekräftig sind, Optik, wo nicht.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="83" />
            <source>Comma separated value files</source>
            <translation>Dateien mit kommagetrennten Werten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Comma-separated t values: one marker each.</source>
            <translation>Kommagetrennte t-Werte: je eine Markierung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="616" />
            <source>Component parameter: centre x, y, widths σx, σy, correlation ρ and weight w.</source>
            <translation>Komponentenparameter: Zentrum x, y, Breiten σx, σy, Korrelation ρ und Gewicht w.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Components to keep. Two is usually enough to plot; more is useful when the first two explain little of the variance.</source>
            <translation>Zu behaltende Komponenten. Zwei reichen meist zum Darstellen; mehr ist nützlich, wenn die ersten beiden wenig Varianz erklären.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Components:</source>
            <translation>Komponenten:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Compute</source>
            <translation>Berechnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Compute a microtime (decay) histogram for the selected bursts.</source>
            <translation>Ein Mikrozeit-Histogramm (Zerfall) für die gewählten Bursts berechnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Compute microtime histogram</source>
            <translation>Mikrozeit-Histogramm berechnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Compute the phasor reference calibration from the chosen reference.</source>
            <translation>Die Phasor-Referenzkalibrierung aus der gewählten Referenz berechnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Configuration of the report (report.yaml); edit to change which figures are made.</source>
            <translation>Konfiguration des Berichts (report.yaml); bearbeiten, um zu ändern, welche Abbildungen erstellt werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Configure performance settings for ndxplorer. These settings control histogram computation, memory usage, and optimization features. Changes take effect after restarting ndxplorer.</source>
            <translation>Leistungseinstellungen für ndxplorer konfigurieren. Diese Einstellungen steuern Histogrammberechnung, Speichernutzung und Optimierungen. Änderungen wirken nach einem Neustart von ndxplorer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Configure the EM and save it to your user settings.</source>
            <translation>Den EM konfigurieren und in den Benutzereinstellungen speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Confirm</source>
            <translation>Bestätigen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Constant</source>
            <translation>Konstante</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="56" />
            <location filename="ndxplorer/core/equation_table.py" line="165" />
            <source>Constants</source>
            <translation>Konstanten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1022" />
            <source>Constants saved to {path}.</source>
            <translation>Konstanten gespeichert in {path}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="98" />
            <location filename="ndxplorer/analysis/vizrank.py" line="99" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="243" />
            <source>Continue</source>
            <translation>Fortsetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Contrast</source>
            <translation>Kontrast</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Controls for stepping through the data along one column.</source>
            <translation>Steuerung zum schrittweisen Durchlaufen der Daten entlang einer Spalte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1255" />
            <location filename="ndxplorer/app/parameter_table.py" line="413" />
            <source>Copy</source>
            <translation>Kopieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="53" />
            <source>Copy 1D Histograms (CSV)</source>
            <translation>1D-Histogramme kopieren (CSV)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="53" />
            <source>Copy 2D Histogram (CSV)</source>
            <translation>2D-Histogramm kopieren (CSV)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="608" />
            <source>Copy Image Path</source>
            <translation>Bildpfad kopieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="478" />
            <source>Copy Path(s)</source>
            <translation>Pfad(e) kopieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="403" />
            <source>Copy values</source>
            <translation>Werte kopieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1256" />
            <source>Copy with headers</source>
            <translation>Mit Kopfzeilen kopieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="381" />
            <source>Cores only</source>
            <translation>Nur Kerne</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Cores only (default): label bursts clearly inside an island, 2 shot-noise sigmas above its valley to the others; the low-photon smear between species stays -1. Whole islands: label every burst in an island's catchment basin -- the watershed of the smoothed density the score uses; -1 stays on ridges between islands, in clumps too small to be islands, and for outliers or missing values.</source>
            <translation>Nur Kerne (Standard): Bursts klar innerhalb einer Insel labeln, 2 Schrotrauschen-Sigma über ihrem Tal zu den anderen; der photonenarme Schleier zwischen den Spezies bleibt -1. Ganze Inseln: jeden Burst im Einzugsgebiet einer Insel labeln -- die Wasserscheide der geglätteten Dichte, die der Score verwendet; -1 bleibt auf Graten zwischen Inseln, in zu kleinen Klumpen für Inseln und für Ausreißer oder fehlende Werte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Corrected FRET efficiency, computed from the counts. Ticking it switches to the multidimensional mixture over every ticked dimension, which separates FRET populations the stoichiometry alone lumps together. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Korrigierte FRET-Effizienz, aus den Zählraten berechnet. Aktivieren wechselt zur mehrdimensionalen Mischung über alle aktivierten Dimensionen, die FRET-Populationen trennt, die die Stöchiometrie allein zusammenfasst. Kosten: Das mehrdimensionale Gating ist etwa zehnmal langsamer als das Stöchiometrie-Gating (25 s statt 2.4 s bei der Messung cal1, 44 270 Bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Corrected stoichiometry, computed from the counts, so every ALEX/PIE measurement has it. Ticked alone it is the stoichiometry gating the calibration always used (fast).</source>
            <translation>Korrigierte Stöchiometrie, aus den Zählraten berechnet, sodass jede ALEX/PIE-Messung sie hat. Allein aktiviert ist es das Stöchiometrie-Gating, das die Kalibrierung immer verwendet hat (schnell).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Correction factors</source>
            <translation>Korrekturfaktoren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="650" />
            <source>Correlation</source>
            <translation>Korrelation</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="530" />
            <source>Could not link: {error}</source>
            <translation>Verknüpfen nicht möglich: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1127" />
            <source>Could not load:
{error}</source>
            <translation>Laden nicht möglich:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="59" />
            <source>Could not open {path}: {error}</source>
            <translation>{path} konnte nicht geöffnet werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="119" />
            <source>Could not parse the configuration: {error}</source>
            <translation>Die Konfiguration konnte nicht gelesen werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="234" />
            <source>Could not remove the sessions from {name}: {error}</source>
            <translation>Die Sitzungen konnten nicht aus {name} entfernt werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="578" />
            <source>Could not save the burst IDs: {error}</source>
            <translation>Burst-IDs konnten nicht gespeichert werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="924" />
            <source>Could not save the language: {error}</source>
            <translation>Die Sprache konnte nicht gespeichert werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1140" />
            <source>Could not save:
{error}</source>
            <translation>Speichern nicht möglich:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="794" />
            <source>Could not save: {error}</source>
            <translation>Speichern nicht möglich: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="556" />
            <source>Could not send to {target}: {error}</source>
            <translation>Senden an {target} nicht möglich: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="814" />
            <source>Could not store: {error}</source>
            <translation>Speichern nicht möglich: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="285" />
            <location filename="ndxplorer/app/features/overlays.py" line="1354" />
            <location filename="ndxplorer/app/features/settings.py" line="1020" />
            <source>Could not write {path}:
{error}</source>
            <translation>{path} konnte nicht geschrieben werden:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>DPI (raster):</source>
            <translation>DPI (Raster):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Data</source>
            <translation>Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="441" />
            <location filename="ndxplorer/app/features/io.py" line="444" />
            <location filename="ndxplorer/app/features/io.py" line="482" />
            <location filename="ndxplorer/app/features/io.py" line="491" />
            <location filename="ndxplorer/app/features/io.py" line="767" />
            <location filename="ndxplorer/app/frame.py" line="380" />
            <source>Data Load Error</source>
            <translation>Fehler beim Laden der Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="664" />
            <source>Data:</source>
            <translation>Daten:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1581" />
            <source>Decomposing</source>
            <translation>Zerlegung läuft</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1055" />
            <source>Default axis settings have been updated.</source>
            <translation>Die Standardachseneinstellungen wurden aktualisiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Definitions evaluated first, in order, separated by ';' (omega = 2*pi*f*harmonic*1e-3; tau = tan(t)/omega); x and y may use them.</source>
            <translation>Zuerst ausgewertete Definitionen, der Reihe nach, durch ';' getrennt (omega = 2*pi*f*harmonic*1e-3; tau = tan(t)/omega); x und y dürfen sie verwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <location filename="ndxplorer/app/features/selection.py" line="52" />
            <source>Delete</source>
            <translation>Löschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Delete the report folders of the selected (or all) analysis folders</source>
            <translation>Die Berichtsordner der ausgewählten (oder aller) Analyseordner löschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="183" />
            <source>Density-based. Finds clusters of varying shape and leaves noise unlabelled.</source>
            <translation>Dichtebasiert. Findet Cluster unterschiedlicher Form und lässt Rauschen ohne Label.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Derived columns: each row computes an output column from an expression.</source>
            <translation>Abgeleitete Spalten: Jede Zeile berechnet eine Ausgabespalte aus einem Ausdruck.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Detection efficiency times quantum-yield ratio. From the 1/S = Ω + Σ·E fit across FRET sub-populations, or from the donor lifetime. Turn this off to keep a γ you determined on a reference sample.</source>
            <translation>Detektionseffizienz mal Quantenausbeuteverhältnis. Aus dem Fit 1/S = Ω + Σ·E über FRET-Subpopulationen oder aus der Donor-Lebensdauer. Ausschalten, um ein an einer Referenzprobe bestimmtes γ beizubehalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Determine</source>
            <translation>Bestimmen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="619" />
            <source>Determine FRET correction factors from the loaded burst data.</source>
            <translation>FRET-Korrekturfaktoren aus den geladenen Burst-Daten bestimmen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Discard every change made in this dialog</source>
            <translation>Alle in diesem Dialog vorgenommenen Änderungen verwerfen</translation>
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
            <translation>Änderungen verwerfen und den Dialog schließen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Display options for the array table below.</source>
            <translation>Anzeigeoptionen für die Array-Tabelle unten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="75" />
            <source>Displayed data (y vs x)</source>
            <translation>Angezeigte Daten (y über x)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Distance in the original space.</source>
            <translation>Abstand im ursprünglichen Raum.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="325" />
            <source>Distances to the centres</source>
            <translation>Abstände zu den Zentren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="663" />
            <source>Do the bursts of one label (a gate, the clusters) sit together in this view? Share of each burst's 10 nearest neighbours with its label, above chance.</source>
            <translation>Liegen die Bursts eines Labels (ein Gate, die Cluster) in dieser Ansicht beieinander? Anteil der 10 nächsten Nachbarn jedes Bursts mit seinem Label, über dem Zufall.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="84" />
            <source>Documentation and source: {url}</source>
            <translation>Dokumentation und Quellcode: {url}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="438" />
            <location filename="ndxplorer/app/features/settings.py" line="741" />
            <source>Done</source>
            <translation>Fertig</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Donor emission detected in the acceptor channel. Taken from the donor-only population, so it needs one.</source>
            <translation>Im Akzeptorkanal detektierte Donoremission. Wird aus der Donor-only-Population bestimmt und braucht daher eine.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Donor-only lifetime, which anchors the static FRET line. Only used by the lifetime route; a wrong value there shows up as γ disagreeing between the two routes.</source>
            <translation>Donor-only-Lebensdauer, die die statische FRET-Linie verankert. Wird nur von der Lebensdauer-Route verwendet; ein falscher Wert zeigt sich darin, dass γ der beiden Routen nicht übereinstimmt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Double-click a name to insert it into the focused expression.</source>
            <translation>Doppelklick auf einen Namen, um ihn in den fokussierten Ausdruck einzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="44" />
            <source>Download .pto with session…</source>
            <translation>.pto mit Sitzung herunterladen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="787" />
            <source>Downloaded {name}</source>
            <translation>{name} heruntergeladen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/frame.py" line="660" />
            <source>Drag to resize the x marginal.</source>
            <translation>Ziehen, um die X-Randverteilung in der Größe zu ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/frame.py" line="662" />
            <source>Drag to resize the y marginal.</source>
            <translation>Ziehen, um die Y-Randverteilung in der Größe zu ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/frame.py" line="709" />
            <source>Drag to resize the z marginal.</source>
            <translation>Ziehen, um die Z-Randverteilung in der Größe zu ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Draw</source>
            <translation>Zeichnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Draw Mask</source>
            <translation>Maske zeichnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Draw each Gaussian on the x and y marginals.</source>
            <translation>Jede Gauß-Funktion in den x- und y-Randverteilungen zeichnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Draw or erase a mask on the 2D histogram to select bursts.</source>
            <translation>Eine Maske im 2D-Histogramm zeichnen oder löschen, um Bursts auszuwählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Draw the x and y marginal histograms above and beside the 2-D density.</source>
            <translation>Die x- und y-Randhistogramme über und neben der 2D-Dichte zeichnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Drop analysis folders here to include them in the report.</source>
            <translation>Analyseordner hier ablegen, um sie in den Bericht aufzunehmen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Drop folder here.</source>
            <translation>Ordner hier ablegen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Dynamic z-selection: the z range gates the other plots</source>
            <translation>Dynamische z-Auswahl: Der z-Bereich gated die anderen Diagramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>E</source>
            <translation>E</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>E efficiency</source>
            <translation>E-Effizienz</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>EM stops when the lower bound improves by less than this.</source>
            <translation>Der EM stoppt, wenn sich die untere Schranke um weniger als diesen Wert verbessert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Each marker's label, formatted with t, the parameters and the definitions ({t:g} ns); empty for none.</source>
            <translation>Beschriftung jeder Markierung, formatiert mit t, den Parametern und den Definitionen ({t:g} ns); leer für keine.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Editable text of report.yaml.</source>
            <translation>Bearbeitbarer Text der report.yaml.</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="148" />
            <source>Elevation failed with exit code {code}. See log: {log}</source>
            <translation>Rechteerhöhung fehlgeschlagen mit Exit-Code {code}. Siehe Protokoll: {log}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="406" />
            <source>Embedding {rows} rows in {n} dimensions</source>
            <translation>{rows} Zeilen werden in {n} Dimensionen eingebettet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Enable</source>
            <translation>Aktivieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Enable All Labels</source>
            <translation>Alle Beschriftungen aktivieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Enable Z Plot</source>
            <translation>Z-Diagramm aktivieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Enable drawing</source>
            <translation>Zeichnen aktivieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Enable/disable drawing on the 2-D plot. While on, the left button paints instead of dragging a rectangle gate.</source>
            <translation>Zeichnen im 2D-Diagramm aktivieren/deaktivieren. Solange aktiv, malt die linke Taste, statt ein Rechteck-Gate aufzuziehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Enables the caching and pre-binning around the fill. The fill itself is always tttrlib and is not affected.</source>
            <translation>Aktiviert das Caching und die Vorab-Klasseneinteilung rund um das Füllen. Das Füllen selbst läuft immer über tttrlib und bleibt unberührt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Enter text to filter columns</source>
            <translation>Text zum Filtern der Spalten eingeben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Epochs:</source>
            <translation>Epochen:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Equation:</source>
            <translation>Gleichung:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Equation: y =</source>
            <translation>Gleichung: y =</translation>
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
            <translation>Gleichungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1118" />
            <source>Equations applied</source>
            <translation>Gleichungen angewendet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1034" />
            <source>Equations file</source>
            <translation>Gleichungsdatei</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1146" />
            <source>Equations saved to {path}</source>
            <translation>Gleichungen gespeichert unter {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Erase</source>
            <translation>Löschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Erase the whole mask.</source>
            <translation>Die gesamte Maske löschen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="379" />
            <source>Error</source>
            <translation>Fehler</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="722" />
            <source>Error for {folder}: {error}</source>
            <translation>Fehler bei {folder}: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1067" />
            <source>Error saving axis label settings.
Details: {error}</source>
            <translation>Fehler beim Speichern der Achsenbeschriftungs-Einstellungen.
Details: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="272" />
            <location filename="ndxplorer/app/features/overlays.py" line="577" />
            <source>Error: {error}</source>
            <translation>Fehler: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Evaluate a coarse grid over the free parameters before the fit and start it at the best point. A least-squares run only goes downhill from where it starts, so a degenerate pair -- a constant that scales the data against a parameter that scales the curve -- otherwise strands it in the first dip. Costs a fixed number of steps.</source>
            <translation>Vor dem Fit ein grobes Raster über die freien Parameter auswerten und am besten Punkt starten. Ein Kleinste-Quadrate-Lauf geht nur bergab vom Startpunkt aus; ein entartetes Paar -- eine Konstante, die die Daten skaliert, gegen einen Parameter, der die Kurve skaliert -- hält ihn sonst im ersten Tal fest. Kostet eine feste Anzahl von Schritten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Every pair of parameters is a possible plot. This panel &lt;b&gt;scores all of them&lt;/b&gt; and lists them best first, so you look at the few that show something instead of paging through hundreds.&lt;br/&gt;&lt;br/&gt;Four steps.</source>
            <translation>Jedes Parameterpaar ist ein mögliches Diagramm. Dieser Bereich &lt;b&gt;bewertet alle&lt;/b&gt; und listet sie nach Güte, sodass man die wenigen ansieht, die etwas zeigen, statt durch Hunderte zu blättern.&lt;br/&gt;&lt;br/&gt;Vier Schritte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Every point is assigned to one of exactly this many groups, whether or not that many populations exist.</source>
            <translation>Jeder Punkt wird genau einer von so vielen Gruppen zugeordnet, unabhängig davon, ob es so viele Populationen gibt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Everything up to the current step, accumulating as playback advances.</source>
            <translation>Alles bis zum aktuellen Schritt, mit fortschreitender Wiedergabe akkumulierend.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Existing parameters of other overlay curves; double-click one to link to it.</source>
            <translation>Vorhandene Parameter anderer Overlay-Kurven; Doppelklick auf einen, um darauf zu verknüpfen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="49" />
            <source>Exit</source>
            <translation>Beenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="57" />
            <source>Exit code {code}</source>
            <translation>Exit-Code {code}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Expert options; the defaults are suitable for most users.</source>
            <translation>Expertenoptionen; die Standardwerte passen für die meisten Anwender.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Export CSV…</source>
            <translation>CSV exportieren…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Export a publication figure.</source>
            <translation>Abbildung für Publikation exportieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1353" />
            <location filename="ndxplorer/app/features/overlays.py" line="1358" />
            <source>Export as CSV</source>
            <translation>Als CSV exportieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1258" />
            <source>Export as CSV…</source>
            <translation>Als CSV exportieren…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="894" />
            <source>Export failed:
{error}</source>
            <translation>Export fehlgeschlagen:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="901" />
            <source>Export publication figure</source>
            <translation>Abbildung für Publikation exportieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Export the current plot as a publication-quality figure.</source>
            <translation>Das aktuelle Diagramm als Abbildung in Publikationsqualität exportieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Export the visible rows and columns as CSV</source>
            <translation>Die sichtbaren Zeilen und Spalten als CSV exportieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1356" />
            <source>Exported to {path}</source>
            <translation>Exportiert nach {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Export…</source>
            <translation>Exportieren…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Expression</source>
            <translation>Ausdruck</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Expression evaluated per burst; may use other column names.</source>
            <translation>Pro Burst ausgewerteter Ausdruck; kann andere Spaltennamen verwenden.</translation>
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
            <translation>FRET-Kalibrierung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="57" />
            <source>FRET calibration (*.fretcal.json);;All files (*)</source>
            <translation>FRET-Kalibrierung (*.fretcal.json);;Alle Dateien (*)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="726" />
            <source>FRET calibration cancelled; the constants are unchanged</source>
            <translation>FRET-Kalibrierung abgebrochen; die Konstanten bleiben unverändert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="760" />
            <source>FRET calibration — applied</source>
            <translation>FRET-Kalibrierung — angewendet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="878" />
            <source>FRET calibration — loaded</source>
            <translation>FRET-Kalibrierung — geladen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="260" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="618" />
            <location filename="ndxplorer/app/features/accurate_fret/progress.view.json" line="0" />
            <source>FRET calibration…</source>
            <translation>FRET-Kalibrierung…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>FRET populations</source>
            <translation>FRET-Populationen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Factor</source>
            <translation>Faktor</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="441" />
            <location filename="ndxplorer/app/features/io.py" line="480" />
            <location filename="ndxplorer/app/model.py" line="206" />
            <source>Failed to load data: {error}</source>
            <translation>Daten konnten nicht geladen werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="896" />
            <source>Failed to load file:
{error}</source>
            <translation>Datei konnte nicht geladen werden:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="823" />
            <source>Failed to save CSV:
{error}</source>
            <translation>CSV konnte nicht gespeichert werden:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1052" />
            <source>Failed to save default axis settings:
{error}</source>
            <translation>Standardachseneinstellungen konnten nicht gespeichert werden:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="380" />
            <source>Failed to save settings: {error}</source>
            <translation>Einstellungen konnten nicht gespeichert werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="878" />
            <source>Failed to save:
{error}</source>
            <translation>Speichern fehlgeschlagen:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="629" />
            <location filename="ndxplorer/app/menus.py" line="22" />
            <source>File</source>
            <translation>Datei</translation>
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
            <translation>Achsen der Datei:
X: {file_x}
Y: {file_y}
Aktuelle Achsen:
X: {x}
Y: {y}

Die Gauß-Kurven wurden trotzdem geladen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="517" />
            <source>File read, but failed to parse config (will still load text):
{error}

Load as-is?</source>
            <translation>Datei gelesen, aber die Konfiguration konnte nicht geparst werden (Text wird trotzdem geladen):
{error}

Trotzdem laden?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1190" />
            <source>Files</source>
            <translation>Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="663" />
            <source>Filled Function:</source>
            <translation>Gefüllte Funktion:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="666" />
            <source>Filled:</source>
            <translation>Gefüllt:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="663" />
            <source>Filled: y =</source>
            <translation>Gefüllt: y =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1331" />
            <source>Filter this column</source>
            <translation>Diese Spalte filtern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1263" />
            <source>Filter this column…</source>
            <translation>Diese Spalte filtern…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Filter:</source>
            <translation>Filter:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="319" />
            <location filename="ndxplorer/app/features/playback_export.py" line="259" />
            <source>Find informative projections</source>
            <translation>Informative Projektionen finden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="75" />
            <source>Find informative projections (z axis)…</source>
            <translation>Informative Projektionen finden (z-Achse)…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="264" />
            <source>Find informative projections - help</source>
            <translation>Informative Projektionen finden - Hilfe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="74" />
            <source>Find informative projections…</source>
            <translation>Informative Projektionen finden…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="320" />
            <location filename="ndxplorer/app/features/playback_export.py" line="260" />
            <source>Find informative z parameters</source>
            <translation>Informative z-Parameter finden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="411" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Find structure</source>
            <translation>Struktur finden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="100" />
            <source>Find the donor-only / acceptor-only / FRET populations in the loaded bursts and determine the correction factors from them.</source>
            <translation>Die Donor-only-/Akzeptor-only-/FRET-Populationen in den geladenen Bursts finden und daraus die Korrekturfaktoren bestimmen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="333" />
            <location filename="ndxplorer/analysis/vizrank.py" line="100" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="244" />
            <source>Finished</source>
            <translation>Abgeschlossen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="269" />
            <location filename="ndxplorer/app/features/analysis.py" line="512" />
            <source>Finished.</source>
            <translation>Fertig.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Fit</source>
            <translation>Fit</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="69" />
            <source>Fit Gaussians</source>
            <translation>Gauß-Funktionen anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Fit and draw the Gaussians in log scale on both axes (positive values only); off fits in the axes' own scale.</source>
            <translation>Die Gauß-Funktionen auf beiden Achsen im logarithmischen Maßstab anpassen und zeichnen (nur positive Werte); aus passt im eigenen Maßstab der Achsen an.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="850" />
            <source>Fit curve to data</source>
            <translation>Kurve an Daten anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="778" />
            <location filename="ndxplorer/app/features/analysis.py" line="805" />
            <source>Fit failed</source>
            <translation>Fit fehlgeschlagen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="54" />
            <source>Fit gate to the population here</source>
            <translation>Gate hier an die Population anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Fit the Gaussians to the gated points shown on the map.</source>
            <translation>Die Gauß-Funktionen an die auf der Karte gezeigten Gate-Punkte anpassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Fit this curve's free parameters to the displayed data (the 2-D distribution, or a marginal histogram)</source>
            <translation>Die freien Parameter dieser Kurve an die angezeigten Daten anpassen (die 2D-Verteilung oder ein Randhistogramm)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Fit through:</source>
            <translation>Anpassen durch:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Fit to:</source>
            <translation>Anpassen an:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="783" />
            <source>Fitted {n} Gaussian</source>
            <translation>{n} Gauß-Funktion angepasst</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="810" />
            <source>Fitted {n} Gaussian per population ({populations})</source>
            <translation>{n} Gauß-Funktion pro Population angepasst ({populations})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="784" />
            <source>Fitted {n} Gaussians</source>
            <translation>{n} Gauß-Funktionen angepasst</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="811" />
            <source>Fitted {n} Gaussians per population ({populations})</source>
            <translation>{n} Gauß-Funktionen pro Population angepasst ({populations})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Fix new means by default</source>
            <translation>Neue Mittelwerte standardmäßig fixieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Fixed</source>
            <translation>Fest</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Fixed: a fit leaves it where it is.</source>
            <translation>Fest: Ein Fit lässt den Wert unverändert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Folder</source>
            <translation>Ordner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="555" />
            <source>Folder for Burst IDs</source>
            <translation>Ordner für Burst-IDs</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1373" />
            <source>Folder for Clustering Data</source>
            <translation>Ordner für Clustering-Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io_service.py" line="161" />
            <source>Folders</source>
            <translation>Ordner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="860" />
            <source>Follow the operating system's language.</source>
            <translation>Der Sprache des Betriebssystems folgen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Font Settings</source>
            <translation>Schrifteinstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Font sizes and colours of the plot titles and axis labels.</source>
            <translation>Schriftgrößen und Farben der Diagrammtitel und Achsenbeschriftungen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>For most users, the default settings provide optimal performance. Advanced users can fine-tune these settings for specific workloads.</source>
            <translation>Für die meisten Anwender bieten die Standardeinstellungen optimale Leistung. Fortgeschrittene können diese Einstellungen für bestimmte Arbeitslasten feinabstimmen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="43" />
            <source>Forget session</source>
            <translation>Sitzung verwerfen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Format:</source>
            <translation>Format:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Free parameters are optimised, fixed ones held. Constants and crosslinked parameters start fixed -- free them to fit them.</source>
            <translation>Freie Parameter werden optimiert, feste bleiben gehalten. Konstanten und verknüpfte Parameter starten fest -- zum Anpassen freigeben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="630" />
            <source>From MMFDB…</source>
            <translation>Aus MMFDB…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Full report</source>
            <translation>Vollständiger Bericht</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="171" />
            <source>Functions</source>
            <translation>Funktionen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="290" />
            <location filename="ndxplorer/app/features/analysis.py" line="316" />
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>GMM Settings</source>
            <translation>GMM-Einstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="314" />
            <source>GMM settings saved to your ndX user folder.</source>
            <translation>GMM-Einstellungen im ndX-Benutzerordner gespeichert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="535" />
            <source>Gate fitted to the population at ({x}, {y}): {n} points</source>
            <translation>Gate an die Population bei ({x}, {y}) angepasst: {n} Punkte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Gate the plot on the z-range slider</source>
            <translation>Das Diagramm mit dem z-Bereichsregler gaten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="265" />
            <source>Gate: inside vs outside</source>
            <translation>Gate: innerhalb vs. außerhalb</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="272" />
            <source>Gates: one population per gate</source>
            <translation>Gates: ein Population pro Gate</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Gates: range limits on parameters that select bursts; edit cells to change them.</source>
            <translation>Gates: Bereichsgrenzen auf Parametern, die Bursts auswählen; Zellen bearbeiten zum Ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Gating dimensions</source>
            <translation>Gating-Dimensionen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="378" />
            <source>Gating dimensions: {dims}</source>
            <translation>Gating-Dimensionen: {dims}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="865" />
            <location filename="ndxplorer/app/features/analysis.py" line="888" />
            <source>Gaussian Files (*.json *.csv);;All Files (*)</source>
            <translation>Gauß-Dateien (*.json *.csv);;Alle Dateien (*)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="57" />
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Gaussian Fit</source>
            <translation>Gauß-Fit</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Gaussian mixture</source>
            <translation>Gauß-Mischung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Gaussians</source>
            <translation>Gauß-Funktionen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>General Cache (MB):</source>
            <translation>Allgemeiner Cache (MB):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Generate</source>
            <translation>Erzeugen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Generate Reports</source>
            <translation>Berichte erzeugen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Generate the report and follow its progress.</source>
            <translation>Bericht erzeugen und seinen Fortschritt verfolgen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="646" />
            <source>Generating reports...</source>
            <translation>Berichte werden erzeugt...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="644" />
            <source>Generating reports... {index}/{total}: {folder}</source>
            <translation>Berichte werden erzeugt... {index}/{total}: {folder}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="733" />
            <source>Generation canceled.</source>
            <translation>Erzeugung abgebrochen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="454" />
            <source>Give how many populations, or their names (HF, LF).</source>
            <translation>Angeben, wie viele Populationen oder ihre Namen (HF, LF).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Green channels:</source>
            <translation>Grüne Kanäle:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="418" />
            <source>Guide {n}/{total}: {title}</source>
            <translation>Anleitung {n}/{total}: {title}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>HDBSCAN</source>
            <translation>HDBSCAN</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="295" />
            <source>HDBSCAN finished</source>
            <translation>HDBSCAN abgeschlossen</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="90" />
            <source>HDF5 files</source>
            <translation>HDF5-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Half-width, in bins, of the window a clicked Gaussian's width is measured in.</source>
            <translation>Halbbreite in Bins des Fensters, in dem die Breite einer angeklickten Gauß-Funktion gemessen wird.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Has a report already</source>
            <translation>Hat bereits einen Bericht</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="442" />
            <source>Held fixed (not calibrated):</source>
            <translation>Fixiert gehalten (nicht kalibriert):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="80" />
            <location filename="ndxplorer/app/menus.py" line="81" />
            <source>Help</source>
            <translation>Hilfe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Hi</source>
            <translation>Ob.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Hide all</source>
            <translation>Alle ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Hide columns that contain no values</source>
            <translation>Spalten ohne Werte ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Hide empty</source>
            <translation>Leere ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Hide every column in the burst table.</source>
            <translation>Jede Spalte der Burst-Tabelle ausblenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1264" />
            <source>Hide this column</source>
            <translation>Diese Spalte ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Histogram</source>
            <translation>Histogramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Histogram Computation</source>
            <translation>Histogrammberechnung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Histogram Threads:</source>
            <translation>Histogramm-Threads:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Histogram computation and caching settings, saved to the settings file.</source>
            <translation>Einstellungen zu Histogrammberechnung und Caching, gespeichert in der Einstellungsdatei.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="37" />
            <source>Histograms</source>
            <translation>Histogramme</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Hold the centre of a Gaussian added by a click on the map.</source>
            <translation>Das Zentrum einer per Klick auf die Karte hinzugefügten Gauß-Funktion festhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>How</source>
            <translation>Wie</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>How bursts count in the Separation score. Low-photon bursts are wide (shot noise) and fill the valleys between FRET populations: weight each burst by its photons, or keep only bursts with at least Min photons. Needs a 'Number of Photons' column.</source>
            <translation>Wie Bursts in den Trennungs-Score eingehen. Photonenarme Bursts sind breit (Schrotrauschen) und füllen die Täler zwischen FRET-Populationen: jeden Burst nach Photonen gewichten oder nur Bursts mit mindestens Min. Photonen behalten. Braucht eine Spalte 'Number of Photons'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>How conservative the density estimate is. Larger leaves more points unlabelled as noise.</source>
            <translation>Wie konservativ die Dichteschätzung ist. Größer lässt mehr Punkte als Rauschen unmarkiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="107" />
            <source>How do you want to merge the new data?</source>
            <translation>Wie sollen die neuen Daten zusammengeführt werden?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>How many (3: populations 0, 1, 2), or their names (HF, LF).</source>
            <translation>Wie viele (3: Populationen 0, 1, 2) oder ihre Namen (HF, LF).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="656" />
            <source>How many bursts fall into clearly separated islands: donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line. 0: one population; 0.5: two equal islands with empty space between; 0.67: three.</source>
            <translation>Wie viele Bursts in klar getrennten Inseln liegen: Donor-only-, Akzeptor-only- und FRET-Spezies in E vs S, eine dynamische Population abseits der statischen FRET-Linie. 0: eine Population; 0,5: zwei gleich große Inseln mit leerem Raum dazwischen; 0,67: drei.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>How many slices the range is cut into. The width of one slice is the range divided by this, so a longer measurement gets wider slices and the playback lasts the same time either way. An index column (frames) starts at one step per value.</source>
            <translation>In wie viele Abschnitte der Bereich geteilt wird. Die Breite eines Abschnitts ist der Bereich geteilt durch diesen Wert; eine längere Messung erhält also breitere Abschnitte, und die Wiedergabe dauert in beiden Fällen gleich lang. Eine Indexspalte (Frames) beginnt mit einem Schritt pro Wert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>How the UMAP embedding is initialised (e.g. spectral or random).</source>
            <translation>Wie die UMAP-Einbettung initialisiert wird (z. B. spektral oder zufällig).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>How the donor-only, acceptor-only and FRET populations are found in the gating dimensions. 'HDBSCAN' (default) finds dense clusters of any shape and leaves sparse bursts unassigned, so a smeared or non-Gaussian population is not split into several components or merged with a neighbour; outliers are removed per dimension before the dimensions are scaled. 'Gaussian mixture' fits Gaussian components and picks their number by the BIC. On cal1 with S+E the mixture took 45 s and lost the donor-only class; HDBSCAN took 3 s. Only used when gating dimensions beyond S are chosen. Needs a tttrlib whose calibration has the population_method option; otherwise this choice is disabled and the Gaussian mixture is used.</source>
            <translation>Wie die Donor-only-, Akzeptor-only- und FRET-Populationen in den Gating-Dimensionen gefunden werden. 'HDBSCAN' (Standard) findet dichte Cluster beliebiger Form und lässt dünne Bursts unzugeordnet, sodass eine verschmierte oder nicht-gaußsche Population weder in mehrere Komponenten geteilt noch mit einem Nachbarn verschmolzen wird; Ausreißer werden pro Dimension entfernt, bevor die Dimensionen skaliert werden. 'Gauß-Mischung' passt Gauß-Komponenten an und wählt ihre Zahl per BIC. Bei cal1 mit S+E brauchte die Mischung 45 s und verlor die Donor-only-Klasse; HDBSCAN brauchte 3 s. Wird nur verwendet, wenn Gating-Dimensionen über S hinaus gewählt sind. Benötigt eine tttrlib, deren Kalibrierung die Option population_method hat; andernfalls ist diese Auswahl deaktiviert und die Gauß-Mischung wird verwendet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>How the gamma correction factor is obtained for the accurate FRET calibration.</source>
            <translation>Wie der Gamma-Korrekturfaktor für die genaue FRET-Kalibrierung bestimmt wird.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="96" />
            <source>IRF / reference measurement</source>
            <translation>IRF / Referenzmessung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>IRF / reference:</source>
            <translation>IRF / Referenz:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="127" />
            <source>IRF{suffix}: {photons} photons, {percent} % flat background removed; the file's f_rep is {header} MHz (constant f_rep {f_rep})</source>
            <translation>IRF{suffix}: {photons} Photonen, {percent} % flacher Hintergrund entfernt; f_rep der Datei ist {header} MHz (konstantes f_rep {f_rep})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="398" />
            <source>Identifiable: no — per-population γ needs, for every FRET population, a donor lifetime that puts it on the static FRET line (0.05 &lt; E &lt; 0.95), and at least two populations</source>
            <translation>Identifizierbar: nein — populationsweises γ braucht für jede FRET-Population eine Donor-Lebensdauer, die sie auf die statische FRET-Linie legt (0.05 &lt; E &lt; 0.95), und mindestens zwei Populationen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="397" />
            <source>Identifiable: yes</source>
            <translation>Identifizierbar: ja</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>If checked histogram as are weighted by selected axis</source>
            <translation>Wenn markiert, werden Histogramme mit der gewählten Achse gewichtet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>If checked the axis is changed and no default scale is defined the axis scale is updated.</source>
            <translation>Wenn markiert und die Achse geändert wird, ohne dass eine Standardskala definiert ist, wird die Achsenskala aktualisiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="629" />
            <location filename="ndxplorer/app/menus.py" line="23" />
            <source>Import</source>
            <translation>Importieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="24" />
            <source>Import Text files (*.csv,*.dat)</source>
            <translation>Textdateien importieren (*.csv,*.dat)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1096" />
            <source>In the browser the page loads the newest published build: reload the page.</source>
            <translation>Im Browser lädt die Seite den neuesten veröffentlichten Build: Seite neu laden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Include X/Y marginal histograms</source>
            <translation>X-/Y-Randhistogramme einbeziehen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Initial value of the new overlay parameter.</source>
            <translation>Anfangswert des neuen Overlay-Parameters.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Initialisation:</source>
            <translation>Initialisierung:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="231" />
            <source>Initializing UMAP computation...</source>
            <translation>UMAP-Berechnung wird initialisiert...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1339" />
            <source>Install</source>
            <translation>Installieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1333" />
            <source>Installation was cancelled or failed, so this method cannot run.</source>
            <translation>Die Installation wurde abgebrochen oder ist fehlgeschlagen, daher kann diese Methode nicht laufen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1103" />
            <source>Installed: ndXplorer {version}</source>
            <translation>Installiert: ndXplorer {version}</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="332" />
            <source>Installing {packages} with {solver}…</source>
            <translation>{packages} wird mit {solver} installiert…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1349" />
            <source>Installing {package}</source>
            <translation>{package} wird installiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Integrate</source>
            <translation>Integrieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1073" />
            <source>Invalid Merge Mode</source>
            <translation>Ungültiger Zusammenführungsmodus</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="677" />
            <source>Invalid config</source>
            <translation>Ungültige Konfiguration</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1074" />
            <source>Invalid mode: {mode}. Must be 'columns' or 'rows'.</source>
            <translation>Ungültiger Modus: {mode}. Erlaubt sind 'columns' oder 'rows'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Invert</source>
            <translation>Invertieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="312" />
            <source>K-means finished</source>
            <translation>K-means abgeschlossen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Keep the bursts outside the range instead of inside.</source>
            <translation>Die Bursts außerhalb des Bereichs behalten statt innerhalb.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Keep this calibration: into the .pto measurement it was determined from, or a separate *.fretcal.json file.</source>
            <translation>Diese Kalibrierung behalten: in der .pto-Messung, aus der sie bestimmt wurde, oder in einer separaten Datei *.fretcal.json.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Kind:</source>
            <translation>Art:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Label</source>
            <translation>Label</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Label every burst of the table by the island of the view on the axes and write the labels as the clusters (Cluster Label and Cluster Probability, replacing K-means/HDBSCAN clusters) and as a column 'Island Label (x vs y)'. Islands are numbered by size, largest first. The probability is the island's share of the smoothed density at the burst: 1 deep inside, falling toward 1/2 at a ridge. Then the Cluster spin box, colour, gates and Save Burst IDs work on the islands.</source>
            <translation>Jeden Burst der Tabelle mit der Insel der Ansicht auf den Achsen labeln und die Labels als Cluster (Cluster Label und Cluster Probability, ersetzt K-means/HDBSCAN-Cluster) sowie als Spalte 'Island Label (x vs y)' schreiben. Inseln sind nach Größe nummeriert, die größte zuerst. Die Wahrscheinlichkeit ist der Anteil der Insel an der geglätteten Dichte beim Burst: 1 tief im Inneren, abfallend Richtung 1/2 an einem Grat. Danach wirken das Cluster-Feld, Farbe, Gates und Burst-IDs speichern auf die Inseln.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Labels:</source>
            <translation>Beschriftungen:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="857" />
            <location filename="ndxplorer/app/features/settings.py" line="923" />
            <source>Language</source>
            <translation>Sprache</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Learning rate:</source>
            <translation>Lernrate:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Leave out points with an infinite value on a plotted axis.</source>
            <translation>Punkte mit unendlichem Wert auf einer dargestellten Achse auslassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Leave out points with no value on a plotted axis.</source>
            <translation>Punkte ohne Wert auf einer dargestellten Achse auslassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Leave the figure background transparent.</source>
            <translation>Den Abbildungshintergrund transparent lassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Left Axis</source>
            <translation>Linke Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Left Axis Label</source>
            <translation>Linke Achsenbeschriftung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Limit histograms to overlay selection, dynamic</source>
            <translation>Histogramme auf die Overlay-Auswahl beschränken, dynamisch</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="161" />
            <source>Linear decomposition. Reports which parameters carry the variance.</source>
            <translation>Lineare Zerlegung. Zeigt, welche Parameter die Varianz tragen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="530" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Link</source>
            <translation>Verknüpfen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Link the new parameter to the selected existing parameter so they share one value.</source>
            <translation>Den neuen Parameter mit dem ausgewählten vorhandenen Parameter verknüpfen, sodass beide einen Wert teilen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="488" />
            <source>Link {name}</source>
            <translation>{name} verknüpfen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Linker σ (Å)</source>
            <translation>Linker-σ (Å)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="416" />
            <source>Link…</source>
            <translation>Verknüpfen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>List of analysis folders that the report is generated for.</source>
            <translation>Liste der Analyseordner, für die der Bericht erzeugt wird.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>List of the overlay curves drawn over the plots, with their parameters.</source>
            <translation>Liste der über die Diagramme gezeichneten Overlay-Kurven mit ihren Parametern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/umap_progress.view.json" line="0" />
            <source>Live log of the UMAP embedding run (read only).</source>
            <translation>Live-Protokoll des UMAP-Einbettungslaufs (schreibgeschützt).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Lo</source>
            <translation>Unt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Load</source>
            <translation>Laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="895" />
            <source>Load Error</source>
            <translation>Ladefehler</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="887" />
            <source>Load Gaussian Fits</source>
            <translation>Gauß-Fits laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="899" />
            <source>Load Gaussians</source>
            <translation>Gauß-Funktionen laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Load Gaussians from a .json or .csv file.</source>
            <translation>Gauß-Funktionen aus einer .json- oder .csv-Datei laden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="300" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Load Mask</source>
            <translation>Maske laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Load a mask from an integer TIFF (one label per bin, the map's binning).</source>
            <translation>Eine Maske aus einer ganzzahligen TIFF laden (ein Label pro Bin, mit der Einteilung der Karte).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Load a report.yaml (YAML or JSON)</source>
            <translation>Eine report.yaml laden (YAML oder JSON)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="829" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="843" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="882" />
            <source>Load calibration</source>
            <translation>Kalibrierung laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="626" />
            <source>Load calibration…</source>
            <translation>Kalibrierung laden…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Load gates from a file.</source>
            <translation>Gates aus einer Datei laden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="53" />
            <source>Load settings</source>
            <translation>Einstellungen laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="845" />
            <source>Load the most recent one? No opens a file instead.</source>
            <translation>Die neueste laden? Nein öffnet stattdessen eine Datei.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="493" />
            <source>Loaded {rows} rows from {name}</source>
            <translation>{rows} Zeilen aus {name} geladen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="474" />
            <source>Loading</source>
            <translation>Laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="481" />
            <source>Loading failed: {error}</source>
            <translation>Laden fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="473" />
            <location filename="ndxplorer/app/features/io.py" line="474" />
            <source>Loading {names}…</source>
            <translation>{names} wird geladen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Load…</source>
            <translation>Laden…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Local window (bins):</source>
            <translation>Lokales Fenster (Bins):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Log Gauss</source>
            <translation>Log-Gauß</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="151" />
            <source>Log tail</source>
            <translation>Protokollende</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Logarithmic axis</source>
            <translation>Logarithmische Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Lower bound of the gate on this parameter.</source>
            <translation>Untere Grenze des Gates für diesen Parameter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Lower bound. −∞: none. Type a number to set it, ∞ (or inf) to remove it.</source>
            <translation>Untere Grenze. −∞: keine. Eine Zahl eingeben zum Setzen, ∞ (oder inf) zum Entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Lower colour limit of the 2-D histogram.</source>
            <translation>Untere Farbgrenze des 2D-Histogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="89" />
            <source>MFD HDF5 files</source>
            <translation>MFD-HDF5-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="46" />
            <source>Make Report</source>
            <translation>Bericht erstellen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Make a report for every listed analysis folder that has none</source>
            <translation>Einen Bericht für jeden aufgelisteten Analyseordner erstellen, der keinen hat</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="408" />
            <source>Make scalar</source>
            <translation>In Skalar umwandeln</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="421" />
            <source>Make vector…</source>
            <translation>In Vektor umwandeln…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="435" />
            <source>Make {name} a vector</source>
            <translation>{name} zu einem Vektor machen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Marginals</source>
            <translation>Randverteilungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="332" />
            <source>Mask file failed: {error}</source>
            <translation>Maskendatei fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="292" />
            <source>Mask gate added: category {category}, {bins} bins</source>
            <translation>Maskengate hinzugefügt: Kategorie {category}, {bins} Bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="327" />
            <source>Mask loaded from {path}</source>
            <translation>Maske aus {path} geladen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="330" />
            <source>Mask saved to {path}</source>
            <translation>Maske in {path} gespeichert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Max</source>
            <translation>Max</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Max iterations:</source>
            <translation>Max. Iterationen:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Maximum number of EM iterations of the Gaussian mixture fit.</source>
            <translation>Maximale Anzahl der EM-Iterationen des Gauß-Mischmodell-Fits.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Mean fluorescence-weighted lifetime of the population in ns.</source>
            <translation>Mittlere fluoreszenzgewichtete Lebensdauer der Population in ns.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Mean inter-dye distance R in angstrom derived from the FRET efficiency.</source>
            <translation>Mittlerer Abstand R zwischen den Farbstoffen in Angström, abgeleitet aus der FRET-Effizienz.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Mean stoichiometry S of the population.</source>
            <translation>Mittlere Stöchiometrie S der Population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="100" />
            <location filename="ndxplorer/app/features/session.py" line="255" />
            <source>Measurement</source>
            <translation>Messung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Measurement:</source>
            <translation>Messung:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Memory &amp; Caching</source>
            <translation>Speicher &amp; Caching</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Memory limit for general-purpose caching (selections, computations, etc.). Recommended range: 10-500 MB</source>
            <translation>Speichergrenze für allgemeines Caching (Auswahlen, Berechnungen usw.). Empfohlener Bereich: 10-500 MB</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Merge</source>
            <translation>Zusammenführen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Method:</source>
            <translation>Methode:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Metric:</source>
            <translation>Metrik:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Min</source>
            <translation>Min</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Min photons</source>
            <translation>Min. Photonen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Min. cluster size:</source>
            <translation>Min. Cluster-Größe:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Min. distance:</source>
            <translation>Min. Abstand:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Min. reference bursts</source>
            <translation>Min. Referenz-Bursts</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Min. samples:</source>
            <translation>Min. Stichproben:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Minimum spacing of embedded points. Smaller = tighter clumps.</source>
            <translation>Minimaler Abstand eingebetteter Punkte. Kleiner = dichtere Klumpen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Mode</source>
            <translation>Modus</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="382" />
            <source>Mode: {mode}</source>
            <translation>Modus: {mode}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="387" />
            <source>Model selection: not run (no acceptor-excitation channel or no FRET population)</source>
            <translation>Modellauswahl: nicht ausgeführt (kein Akzeptor-Anregungskanal oder keine FRET-Population)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="385" />
            <source>Model selection: not run — scalar factors only</source>
            <translation>Modellauswahl: nicht ausgeführt — nur skalare Faktoren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="393" />
            <source>Model selection: {selected} — BIC shared {bic_shared}, per population {bic_species}</source>
            <translation>Modellauswahl: {selected} — BIC gemeinsam {bic_shared}, pro Population {bic_species}</translation>
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
            <translation>Name</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Name of the burst-table column.</source>
            <translation>Name der Spalte der Burst-Tabelle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Name of the column that the equation writes.</source>
            <translation>Name der Spalte, in die die Gleichung schreibt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Name of the new overlay parameter.</source>
            <translation>Name des neuen Overlay-Parameters.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Name of the parameter or constant.</source>
            <translation>Name des Parameters oder der Konstante.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Names</source>
            <translation>Namen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1160" />
            <source>Names &amp; functions</source>
            <translation>Namen &amp; Funktionen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Names &amp; functions you can use</source>
            <translation>Verwendbare Namen und Funktionen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Navigation: Up/Down, PageUp/PageDown and Home/End move the selection; a click on a box toggles it.</source>
            <translation>Navigation: Auf/Ab, Bild auf/ab und Pos1/Ende bewegen die Auswahl; ein Klick auf ein Kästchen schaltet es um.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Neighbours:</source>
            <translation>Nachbarn:</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1051" />
            <source>New Columns Found</source>
            <translation>Neue Spalten gefunden</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="476" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="438" />
            <source>New columns: {columns}</source>
            <translation>Neue Spalten: {columns}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1052" />
            <source>New data contains columns not in current data: {names}. Only rows of existing columns will be appended.</source>
            <translation>Die neuen Daten enthalten Spalten, die in den aktuellen Daten fehlen: {names}. Es werden nur Zeilen bestehender Spalten angehängt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1031" />
            <source>New data has {new} rows, current has {current} rows. Not merging.</source>
            <translation>Neue Daten haben {new} Zeilen, aktuelle {current} Zeilen. Kein Zusammenführen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="438" />
            <source>Next</source>
            <translation>Weiter</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis.py" line="141" />
            <location filename="ndxplorer/app/features/analysis.py" line="1184" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>No</source>
            <translation>Nein</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="621" />
            <source>No .bst files were found in the selected folder.</source>
            <translation>Im gewählten Ordner wurden keine .bst-Dateien gefunden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="287" />
            <source>No .bur files in 'bi4_bur' or 'bur'.</source>
            <translation>Keine .bur-Dateien in 'bi4_bur' oder 'bur'.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="757" />
            <source>No 2D histogram available. Fit is restricted to visible data; please update histogram first.</source>
            <translation>Kein 2D-Histogramm verfügbar. Der Fit ist auf sichtbare Daten beschränkt; bitte zuerst das Histogramm aktualisieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="506" />
            <location filename="ndxplorer/app/features/playback_export.py" line="877" />
            <source>No 2D histogram is available yet — load data and update the plot first.</source>
            <translation>Noch kein 2D-Histogramm verfügbar — zuerst Daten laden und das Diagramm aktualisieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="620" />
            <source>No BST Files Found</source>
            <translation>Keine BST-Dateien gefunden</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="895" />
            <source>No CSV-like files found in zip: {name}</source>
            <translation>Keine CSV-ähnlichen Dateien im ZIP gefunden: {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="631" />
            <source>No ChiSurf connection. Open ndX from ChiSurf, or start it with --chisurf-rpc host:port.</source>
            <translation>Keine ChiSurf-Verbindung. ndX aus ChiSurf öffnen oder mit --chisurf-rpc host:port starten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1366" />
            <source>No Clustering Data</source>
            <translation>Keine Clustering-Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1058" />
            <source>No Common Columns</source>
            <translation>Keine gemeinsamen Spalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1606" />
            <source>No Data</source>
            <translation>Keine Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="464" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="170" />
            <source>No Gaussians</source>
            <translation>Keine Gauß-Kurven</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="825" />
            <source>No HDF5 files in zip: {name}</source>
            <translation>Keine HDF5-Dateien im ZIP: {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="465" />
            <location filename="ndxplorer/app/features/settings.py" line="684" />
            <source>No analysis folders found</source>
            <translation>Keine Analyseordner gefunden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="758" />
            <source>No analysis folders to clear.</source>
            <translation>Keine Analyseordner zum Leeren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="466" />
            <source>No analysis folders were found in the dropped directory/directories.</source>
            <translation>Im abgelegten Verzeichnis bzw. in den abgelegten Verzeichnissen wurden keine Analyseordner gefunden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="475" />
            <location filename="ndxplorer/app/features/selection.py" line="485" />
            <source>No clipboard to copy to here.</source>
            <translation>Keine Zwischenablage zum Kopieren vorhanden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1367" />
            <source>No clustering data available. Please apply clustering before saving.</source>
            <translation>Keine Clustering-Daten vorhanden. Bitte vor dem Speichern ein Clustering anwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="424" />
            <source>No column to play back</source>
            <translation>Keine Spalte zum Abspielen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1215" />
            <source>No columns are selected, so only the current X, Y and Z axes will be used — which rarely groups the data well.

Choose columns now?</source>
            <translation>Es sind keine Spalten ausgewählt, daher werden nur die aktuellen X-, Y- und Z-Achsen verwendet – das gruppiert die Daten selten gut.

Jetzt Spalten wählen?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1295" />
            <source>No components could be computed from the selected columns.</source>
            <translation>Aus den gewählten Spalten konnten keine Komponenten berechnet werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="470" />
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="475" />
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="479" />
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="488" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="186" />
            <location filename="ndxplorer/app/features/analysis.py" line="1237" />
            <source>No data</source>
            <translation>Keine Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="268" />
            <source>No data available for clustering.</source>
            <translation>Keine Daten für das Clustering verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="470" />
            <source>No data available for fitting.</source>
            <translation>Keine Daten zum Anpassen verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="531" />
            <source>No data found in folder: {folder}</source>
            <translation>Keine Daten im Ordner gefunden: {folder}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="489" />
            <source>No data in {paths}</source>
            <translation>Keine Daten in {paths}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/model.py" line="209" />
            <source>No data in {path}</source>
            <translation>Keine Daten in {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="634" />
            <source>No data loaded.</source>
            <translation>Keine Daten geladen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1606" />
            <source>No data loaded—nothing to show.</source>
            <translation>Keine Daten geladen – nichts anzuzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="476" />
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="187" />
            <source>No data within the visible histogram range to fit.</source>
            <translation>Keine Daten im sichtbaren Histogrammbereich zum Anpassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1190" />
            <source>No file service is available in this window.</source>
            <translation>In diesem Fenster ist kein Dateidienst verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="899" />
            <source>No file service to save with.</source>
            <translation>Kein Dateidienst zum Speichern vorhanden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="803" />
            <source>No finite pairs, or a constant column.</source>
            <translation>Keine endlichen Paare oder eine konstante Spalte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>No folder selected</source>
            <translation>Kein Ordner ausgewählt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="680" />
            <location filename="ndxplorer/app/features/settings.py" line="758" />
            <source>No folders</source>
            <translation>Keine Ordner</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="520" />
            <source>No gate: no data on the plot.</source>
            <translation>Kein Gate: keine Daten im Diagramm.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="528" />
            <source>No gate: {reason}</source>
            <translation>Kein Gate: {reason}</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>No gating: the whole measurement at once.</source>
            <translation>Kein Gating: die gesamte Messung auf einmal.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="756" />
            <source>No histogram</source>
            <translation>Kein Histogramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="596" />
            <source>No images found</source>
            <translation>Keine Bilder gefunden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="506" />
            <source>No other parameters are open to link to (a curve, the Gaussians or a fit).</source>
            <translation>Keine anderen Parameter zum Verknüpfen verfügbar (eine Kurve, die Gauß-Funktionen oder ein Fit).</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1058" />
            <source>No overlapping columns. Cannot append rows.</source>
            <translation>Keine übereinstimmenden Spalten. Zeilen können nicht angehängt werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="807" />
            <source>No overlay data available yet. Create/update overlays first.</source>
            <translation>Noch keine Overlay-Daten vorhanden. Zuerst Overlays erstellen/aktualisieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="177" />
            <source>No populations</source>
            <translation>Keine Populationen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="489" />
            <source>No positive data available on log-scaled axis for fitting.</source>
            <translation>Keine positiven Daten auf der logarithmischen Achse zum Anpassen verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="770" />
            <source>No report folders were found to delete.</source>
            <translation>Es wurden keine Berichtsordner zum Löschen gefunden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="454" />
            <source>No row selected.</source>
            <translation>Keine Zeile ausgewählt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="641" />
            <source>No selection. Draw a gate first — the whole table would be sent.</source>
            <translation>Keine Auswahl. Zuerst ein Gate zeichnen — sonst würde die ganze Tabelle gesendet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="143" />
            <source>No stored table {name}; the project holds: {names}</source>
            <translation>Keine gespeicherte Tabelle {name}; das Projekt enthält: {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="56" />
            <source>No such project: {path}</source>
            <translation>Projekt nicht gefunden: {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="900" />
            <source>No valid Gaussian rows found in the selected file.</source>
            <translation>In der gewählten Datei wurden keine gültigen Gauß-Zeilen gefunden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="685" />
            <source>No valid analysis subfolders were found. Please check your selection.</source>
            <translation>Keine gültigen Analyseunterordner gefunden. Bitte die Auswahl prüfen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="811" />
            <source>No visible curves to save.</source>
            <translation>Keine sichtbaren Kurven zum Speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="375" />
            <source>Noise</source>
            <translation>Rauschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="172" />
            <source>Non-linear projection to 2-3 dimensions for visual inspection.</source>
            <translation>Nichtlineare Projektion auf 2-3 Dimensionen zur visuellen Inspektion.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1237" />
            <source>None of the chosen columns is in the table.</source>
            <translation>Keine der gewählten Spalten befindet sich in der Tabelle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Normalized density</source>
            <translation>Normierte Dichte</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Not a correction factor — it converts efficiency to distance. Off by default: it belongs to the dye pair and its environment, not to this measurement.</source>
            <translation>Kein Korrekturfaktor — er rechnet Effizienz in Abstand um. Standardmäßig aus: Er gehört zum Farbstoffpaar und seiner Umgebung, nicht zu dieser Messung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="287" />
            <source>Not enough data points for HDBSCAN: need at least {n} (min. samples).</source>
            <translation>Zu wenige Datenpunkte für HDBSCAN: mindestens {n} nötig (Min. Samples).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="284" />
            <source>Not enough data points for HDBSCAN: need at least {n}.</source>
            <translation>Zu wenige Datenpunkte für HDBSCAN: mindestens {n} nötig.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="303" />
            <source>Not enough data points for K-means: need at least {n} (one per cluster).</source>
            <translation>Zu wenige Datenpunkte für K-means: mindestens {n} nötig (einer pro Cluster).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="404" />
            <source>Not enough data points for UMAP: need at least {n}.</source>
            <translation>Zu wenige Datenpunkte für UMAP: mindestens {n} nötig.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="352" />
            <source>Not in the browser. ChiSurf's RPC needs a native socket; run ndX on the desktop to send a selection</source>
            <translation>Nicht im Browser. Der RPC von ChiSurf benötigt einen nativen Socket; ndX auf dem Desktop ausführen, um eine Auswahl zu senden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="356" />
            <source>Not stored automatically: {error}</source>
            <translation>Nicht automatisch gespeichert: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="863" />
            <source>Note: {note}</source>
            <translation>Hinweis: {note}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="138" />
            <source>Nothing is painted. Enable drawing and paint on the 2-D plot first.</source>
            <translation>Es ist nichts gemalt. Zuerst Zeichnen aktivieren und im 2D-Diagramm malen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="769" />
            <source>Nothing to clear</source>
            <translation>Nichts zu löschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="690" />
            <source>Nothing to do</source>
            <translation>Nichts zu tun</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="864" />
            <source>Nothing would change.</source>
            <translation>Es würde sich nichts ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Number of 1D bins</source>
            <translation>Anzahl 1D-Bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Number of 2D bins</source>
            <translation>Anzahl 2D-Bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Number of bursts in the population.</source>
            <translation>Anzahl der Bursts in der Population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Number of points:</source>
            <translation>Anzahl der Punkte:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Number of sigmas used for Gaussian burst selection (1.0 = 1σ).</source>
            <translation>Anzahl der Sigma für die Gauß-Burst-Auswahl (1.0 = 1σ).</translation>
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
            <translation>Aus</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>On</source>
            <translation>An</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="667" />
            <source>One population in {x} vs {y}: no islands to use as clusters.</source>
            <translation>Eine Population in {x} vs {y}: keine Inseln, die als Cluster dienen könnten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="795" />
            <source>One population: no significant density valley over {n} sampled bursts.</source>
            <translation>Eine Population: kein signifikantes Dichtetal über {n} gezogene Bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>One slice at a time: the data inside the current playback window.</source>
            <translation>Ein Abschnitt nach dem anderen: die Daten im aktuellen Wiedergabefenster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>One step back</source>
            <translation>Einen Schritt zurück</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>One step forward</source>
            <translation>Einen Schritt vor</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="441" />
            <source>One value of {name} per population; a burst takes its population's value, and a burst in no population the global one.</source>
            <translation>Ein Wert von {name} je Population; ein Burst übernimmt den Wert seiner Population, ein Burst ohne Population den globalen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>One value per population, picked by a column of the burst table.</source>
            <translation>Ein Wert je Population, gewählt über eine Spalte der Burst-Tabelle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>One value shared by all bursts.</source>
            <translation>Ein Wert für alle Bursts.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>One γ for all FRET populations, or one per population. A local environment can change a dye's quantum yield in one population, and with it that population's γ; β, α and δ stay shared.

'Off' writes one global factor set, as before — the per-population model is not tried.
'Auto' (default) fits both a shared and a per-population γ and keeps the per-population one only when it lowers the BIC.
'On' writes the per-population γ whenever it is identifiable, even when the BIC prefers the shared one.

Per-population γ is only identifiable with lifetimes: every FRET population needs a donor lifetime (the static FRET line pins its E), and there must be at least two populations. Without a donor lifetime column all three modes give the same scalar result. Written γ vectors appear in the Parameters tab; right-click &gt; Make scalar removes one again. The test itself is cheap; it is the gating dimensions below that cost time.</source>
            <translation>Ein γ für alle FRET-Populationen oder eines pro Population. Eine lokale Umgebung kann die Quantenausbeute eines Farbstoffs in einer Population ändern und damit das γ dieser Population; β, α und δ bleiben gemeinsam.

'Aus' schreibt einen globalen Faktorsatz wie bisher — das populationsweise Modell wird nicht versucht.
'Auto' (Standard) passt sowohl ein gemeinsames als auch ein populationsweises γ an und behält Letzteres nur, wenn es den BIC senkt.
'An' schreibt das populationsweise γ, wann immer es identifizierbar ist, auch wenn der BIC das gemeinsame bevorzugt.

Populationsweises γ ist nur mit Lebensdauern identifizierbar: Jede FRET-Population braucht eine Donor-Lebensdauer (die statische FRET-Linie legt ihr E fest), und es müssen mindestens zwei Populationen vorliegen. Ohne Donor-Lebensdauerspalte liefern alle drei Modi dasselbe skalare Ergebnis. Geschriebene γ-Vektoren erscheinen im Reiter Parameter; Rechtsklick &gt; In Skalar umwandeln entfernt einen wieder. Der Test selbst ist billig; die Gating-Dimensionen unten kosten Zeit.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="61" />
            <source>Only bursts with at least Min photons</source>
            <translation>Nur Bursts mit mindestens Min. Photonen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Open</source>
            <translation>Öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="86" />
            <source>Open CSV Files</source>
            <translation>CSV-Dateien öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="167" />
            <location filename="ndxplorer/io/loading.py" line="102" />
            <source>Open ChiSurf Project</source>
            <translation>ChiSurf-Projekt öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Open FCS Correlator Wizard to correlate BST files</source>
            <translation>FCS-Korrelator-Assistent öffnen, um BST-Dateien zu korrelieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="92" />
            <source>Open MFD HDF5 Files</source>
            <translation>MFD-HDF5-Dateien öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="167" />
            <location filename="ndxplorer/io/loading.py" line="100" />
            <source>Open PTO Container</source>
            <translation>PTO-Container öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="94" />
            <location filename="ndxplorer/io/loading.py" line="97" />
            <source>Open Sampling Files</source>
            <translation>Sampling-Dateien öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="88" />
            <source>Open SmFRET Files</source>
            <translation>SmFRET-Dateien öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="632" />
            <source>Open a burst selection registered in MMFDB (ChiSurf's database; {reason}).</source>
            <translation>Eine in MMFDB (der Datenbank von ChiSurf; {reason}) registrierte Burst-Auswahl öffnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="32" />
            <source>Open a sampling chain stored in a ChiSurf project; asks which one when the project holds several.</source>
            <translation>Eine in einem ChiSurf-Projekt gespeicherte Sampling-Kette öffnen; fragt nach, welche, wenn das Projekt mehrere enthält.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Open clustering dialog: find structure (PCA, UMAP, HDBSCAN, K-means) in chosen columns.</source>
            <translation>Clustering-Dialog öffnen: Struktur (PCA, UMAP, HDBSCAN, K-means) in gewählten Spalten finden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="523" />
            <source>Open config</source>
            <translation>Konfiguration öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1132" />
            <source>Open equations</source>
            <translation>Gleichungen öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="893" />
            <source>Open from MMFDB</source>
            <translation>Aus MMFDB öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Open nothing.</source>
            <translation>Nichts öffnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="93" />
            <source>Open sampling folder</source>
            <translation>Sampling-Ordner öffnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Open the FCS correlator wizard afterwards to correlate the burst photon files.</source>
            <translation>Danach den FCS-Korrelator-Assistenten öffnen, um die Burst-Photonendateien zu korrelieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Open the chosen table.</source>
            <translation>Die gewählte Tabelle öffnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="894" />
            <source>Opening a burst selection registered in MMFDB needs ChiSurf's MMFDB client: it works when ndX runs inside ChiSurf.</source>
            <translation>Das Öffnen einer in MMFDB registrierten Burst-Auswahl braucht den MMFDB-Client von ChiSurf: es funktioniert, wenn ndX in ChiSurf läuft.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1549" />
            <location filename="ndxplorer/app/features/phasor_reference.py" line="218" />
            <source>Opening files needs the io feature.</source>
            <translation>Zum Öffnen von Dateien wird das Feature io benötigt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="507" />
            <source>Opening {name} in napari...</source>
            <translation>{name} wird in napari geöffnet...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Optimisation epochs; Auto lets UMAP choose from the data size.</source>
            <translation>Optimierungs-Epochen; Auto lässt UMAP sie aus der Datengröße wählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Optimise every free parameter against the selected data</source>
            <translation>Jeden freien Parameter gegen die ausgewählten Daten optimieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Optional: the TTTR file the pixel table was made from; its flat background gives n_bg per pixel and frame.</source>
            <translation>Optional: die TTTR-Datei, aus der die Pixeltabelle erzeugt wurde; ihr flacher Hintergrund liefert n_bg pro Pixel und Frame.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Options that speed up histogram computation for large burst tables.</source>
            <translation>Optionen, die die Histogrammberechnung für große Burst-Tabellen beschleunigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Options that trade memory for speed by caching intermediate results.</source>
            <translation>Optionen, die Speicher gegen Geschwindigkeit tauschen, indem Zwischenergebnisse zwischengespeichert werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Output</source>
            <translation>Ausgabe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Overlay Plot</source>
            <translation>Overlay-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Overlay curve that owns the parameter.</source>
            <translation>Overlay-Kurve, der der Parameter gehört.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="44" />
            <location filename="ndxplorer/app/features/overlays.py" line="1641" />
            <location filename="ndxplorer/app/menus.py" line="67" />
            <source>Overlays</source>
            <translation>Overlays</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Owner</source>
            <translation>Besitzer</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1294" />
            <source>PCA failed</source>
            <translation>PCA fehlgeschlagen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>PCA, UMAP, HDBSCAN and K-means over the columns you choose: projections add PC_n / UMAP_n columns, labellings add Cluster Label.</source>
            <translation>PCA, UMAP, HDBSCAN und K-means über die gewählten Spalten: Projektionen fügen PC_n- / UMAP_n-Spalten hinzu, Zuordnungen fügen Cluster Label hinzu.</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/publication_figure.py" line="28" />
            <source>PDF (vector)</source>
            <translation>PDF (Vektor)</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/publication_figure.py" line="30" />
            <source>PNG (raster)</source>
            <translation>PNG (Raster)</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/screenshots.py" line="25" />
            <source>PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp)</source>
            <translation>PNG-Bild (*.png);;JPEG-Bild (*.jpg *.jpeg);;BMP-Bild (*.bmp)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="98" />
            <source>PTO Measurement Containers</source>
            <translation>PTO-Messcontainer</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="99" />
            <source>PTO files</source>
            <translation>PTO-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Paint a region on the 2-D plot and apply it as a gate.</source>
            <translation>Eine Region im 2D-Diagramm malen und als Gate anwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Paint the category, or erase back to unpainted.</source>
            <translation>Die Kategorie malen oder bis zum Unbemalten zurücklöschen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Parallel jobs:</source>
            <translation>Parallele Jobs:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="313" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter</source>
            <translation>Parameter</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Parameter name:</source>
            <translation>Parametername:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter on the x axis.</source>
            <translation>Parameter auf der x-Achse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter on the y axis.</source>
            <translation>Parameter auf der y-Achse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Parameter on the z axis.</source>
            <translation>Parameter auf der z-Achse.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="44" />
            <location filename="ndxplorer/app/features/overlays.py" line="1640" />
            <location filename="ndxplorer/app/menus.py" line="65" />
            <source>Parameters</source>
            <translation>Parameter</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="287" />
            <source>Parameters saved to {path}</source>
            <translation>Parameter gespeichert unter {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="516" />
            <source>Parse warning</source>
            <translation>Parse-Warnung</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="193" />
            <source>Partitions every point into exactly k groups of similar spread.</source>
            <translation>Teilt jeden Punkt in genau k Gruppen ähnlicher Streuung ein.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1257" />
            <location filename="ndxplorer/app/parameter_table.py" line="414" />
            <source>Paste</source>
            <translation>Einfügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="405" />
            <location filename="ndxplorer/app/parameter_table.py" line="471" />
            <source>Paste values</source>
            <translation>Werte einfügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Path</source>
            <translation>Pfad</translation>
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
            <translation>Anisotropie des Akzeptors pro Burst: trennt Populationen, deren Akzeptor festsitzt. Kosten: Das mehrdimensionale Gating ist etwa zehnmal langsamer als das Stöchiometrie-Gating (25 s statt 2.4 s bei der Messung cal1, 44 270 Bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst acceptor lifetime. Tracks the acceptor quantum yield of each population, the usual reason a population has its own γ. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Akzeptor-Lebensdauer pro Burst. Folgt der Akzeptor-Quantenausbeute jeder Population, dem üblichen Grund für ein eigenes γ einer Population. Kosten: Das mehrdimensionale Gating ist etwa zehnmal langsamer als das Stöchiometrie-Gating (25 s statt 2.4 s bei der Messung cal1, 44 270 Bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst donor anisotropy: separates populations whose donor is stuck. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Anisotropie des Donors pro Burst: trennt Populationen, deren Donor festsitzt. Kosten: Das mehrdimensionale Gating ist etwa zehnmal langsamer als das Stöchiometrie-Gating (25 s statt 2.4 s bei der Messung cal1, 44 270 Bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Per-burst donor lifetime. Separates species at equal E but different lifetime (dynamics, a changed quantum yield), and it is what makes population-wise γ identifiable. Cost: the multidimensional gating is about ten times slower than the stoichiometry gating (25 s instead of 2.4 s on the cal1 measurement, 44 270 bursts).</source>
            <translation>Donor-Lebensdauer pro Burst. Trennt Spezies bei gleichem E, aber unterschiedlicher Lebensdauer (Dynamik, geänderte Quantenausbeute) und macht populationsweises γ erst identifizierbar. Kosten: Das mehrdimensionale Gating ist etwa zehnmal langsamer als das Stöchiometrie-Gating (25 s statt 2.4 s bei der Messung cal1, 44 270 Bursts).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="358" />
            <source>Performance Configuration</source>
            <translation>Leistungskonfiguration</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="332" />
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="52" />
            <source>Performance Settings</source>
            <translation>Leistungseinstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="383" />
            <source>Performance settings have been saved.</source>
            <translation>Die Leistungseinstellungen wurden gespeichert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="53" />
            <source>Phasor reference from IRF</source>
            <translation>Phasor-Referenz aus IRF</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="238" />
            <source>Phasor reference from IRF…</source>
            <translation>Phasor-Referenz aus IRF…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="154" />
            <source>Phasor reference: set {names}</source>
            <translation>Phasor-Referenz: {names} setzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Pick a measurement of a reference dye of known lifetime as the phasor reference.</source>
            <translation>Eine Messung eines Referenzfarbstoffs bekannter Lebensdauer als Phasor-Referenz wählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Pick the IRF measurement that serves as the phasor reference.</source>
            <translation>Die IRF-Messung wählen, die als Phasor-Referenz dient.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>Picked by:</source>
            <translation>Gewählt durch:</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Play backward</source>
            <translation>Rückwärts abspielen</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Play forward</source>
            <translation>Vorwärts abspielen</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Play the data back along one of its own columns: macro time for bursts, frame index for image stacks.</source>
            <translation>Die Daten entlang einer ihrer eigenen Spalten abspielen: Makrozeit bei Bursts, Frame-Index bei Bildstapeln.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Playback</source>
            <translation>Wiedergabe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="680" />
            <source>Please add analysis folders.</source>
            <translation>Bitte Analyseordner hinzufügen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="823" />
            <source>Please select one or more Gaussian rows in the table.</source>
            <translation>Bitte eine oder mehrere Gauß-Zeilen in der Tabelle auswählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="42" />
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <location filename="ndxplorer/app/menus.py" line="64" />
            <source>Plot</source>
            <translation>Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/docks.py" line="41" />
            <location filename="ndxplorer/app/menus.py" line="62" />
            <source>Plot controls</source>
            <translation>Diagrammsteuerung</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="537" />
            <source>Plot {index}</source>
            <translation>Diagramm {index}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Plot:</source>
            <translation>Diagramm:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="361" />
            <source>Plots are drawn by emtk here; the Qt window's plot backend ({backend}) is kept in the settings for it.</source>
            <translation>Diagramme werden hier von emtk gezeichnet; das Diagramm-Backend des Qt-Fensters ({backend}) bleibt dafür in den Einstellungen erhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="614" />
            <location filename="ndxplorer/app/features/io.py" line="623" />
            <source>Plugin Not Available</source>
            <translation>Plugin nicht verfügbar</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="371" />
            <source>Points</source>
            <translation>Punkte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Points an equation curve is drawn with.</source>
            <translation>Punkte, mit denen eine Gleichungskurve gezeichnet wird.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Points loaded.</source>
            <translation>Geladene Punkte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Points shown (after the gates).</source>
            <translation>Angezeigte Punkte (nach den Gates).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Population finder</source>
            <translation>Populationsfinder</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/names.view.json" line="0" />
            <source>Population number.</source>
            <translation>Nummer der Population.</translation>
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
            <translation>Populationsweise Faktoren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="474" />
            <source>Population-wise factors:</source>
            <translation>Populationsweise Faktoren:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays.py" line="453" />
            <source>Populations</source>
            <translation>Populationen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="433" />
            <source>Populations of {name}</source>
            <translation>Populationen von {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>Populations:</source>
            <translation>Populationen:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="407" />
            <source>Populations…</source>
            <translation>Populationen…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="269" />
            <source>Preparing the data</source>
            <translation>Daten werden vorbereitet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Press &lt;b&gt;Start&lt;/b&gt;.</source>
            <translation>&lt;b&gt;Start&lt;/b&gt; drücken.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="206" />
            <source>Press Start to rank every view.</source>
            <translation>Start drücken, um jede Ansicht zu ranken.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Preview of the selected generated image.</source>
            <translation>Vorschau des ausgewählten erzeugten Bildes.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="47" />
            <source>Print window</source>
            <translation>Fenster drucken</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="206" />
            <location filename="ndxplorer/app/features/io/burst_ids.view.json" line="0" />
            <source>Process Burst IDs</source>
            <translation>Burst-IDs verarbeiten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <source>Progress</source>
            <translation>Fortschritt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Progress of the report generation.</source>
            <translation>Fortschritt der Berichterstellung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="555" />
            <location filename="ndxplorer/app/features/playback_export.py" line="876" />
            <location filename="ndxplorer/app/features/playback_export.py" line="893" />
            <location filename="ndxplorer/app/features/playback_export.py" line="899" />
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Publication export</source>
            <translation>Publikationsexport</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Python expression or function that defines the overlay curve.</source>
            <translation>Python-Ausdruck oder -Funktion, die die Overlay-Kurve definiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <source>Question</source>
            <translation>Frage</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>R (Å)</source>
            <translation>R (Å)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Rank by</source>
            <translation>Ranking nach</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Ranked parameter pairs; click a row to show that view in the main plot.</source>
            <translation>Gerankte Parameterpaare; auf eine Zeile klicken, um diese Ansicht im Hauptdiagramm zu zeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Ranked views - click one to show it</source>
            <translation>Gerankte Ansichten - zum Anzeigen anklicken</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Ranking</source>
            <translation>Ranking</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="452" />
            <source>Ranking failed: {error}</source>
            <translation>Ranking fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Raster resolution. Ignored for vector formats.</source>
            <translation>Rasterauflösung. Bei Vektorformaten ignoriert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Ratio of the two lasers' excitation flux and cross-sections. Comes from the same E-S fit as γ.</source>
            <translation>Verhältnis von Anregungsfluss und Wirkungsquerschnitten der beiden Laser. Stammt aus demselben E-S-Fit wie γ.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Read equations from a YAML file</source>
            <translation>Gleichungen aus einer YAML-Datei lesen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="202" />
            <source>Read from the column '{column}'.</source>
            <translation>Aus der Spalte '{column}' gelesen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1114" />
            <source>Recompute failed:
{error}</source>
            <translation>Neuberechnung fehlgeschlagen:
{error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="262" />
            <source>Recompute failed: {error}</source>
            <translation>Neuberechnung fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Red channels:</source>
            <translation>Rote Kanäle:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Redraw the plots with these axes</source>
            <translation>Die Diagramme mit diesen Achsen neu zeichnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Redraw the plots.</source>
            <translation>Diagramme neu zeichnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Reference lifetime (ns):</source>
            <translation>Referenz-Lebensdauer (ns):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Reg. covar:</source>
            <translation>Reg. Kovarianz:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Remove</source>
            <translation>Entfernen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="500" />
            <source>Remove all folders from the list?</source>
            <translation>Alle Ordner aus der Liste entfernen?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Remove every Gaussian.</source>
            <translation>Jede Gauß-Funktion entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Remove every folder from the list</source>
            <translation>Alle Ordner aus der Liste entfernen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Remove every gate.</source>
            <translation>Alle Gates entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Remove the curve.</source>
            <translation>Kurve entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Remove the painted area from the mask.</source>
            <translation>Die bemalte Fläche aus der Maske entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Remove the reference's flat background</source>
            <translation>Den flachen Hintergrund der Referenz entfernen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Remove the selected Gaussian (or the last).</source>
            <translation>Die ausgewählte (oder die letzte) Gauß-Funktion entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Remove the selected equation</source>
            <translation>Ausgewählte Gleichung entfernen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Remove the selected folder from the list</source>
            <translation>Den ausgewählten Ordner aus der Liste entfernen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="231" />
            <source>Removed {n} saved session(s) from {name}</source>
            <translation>{n} gespeicherte Sitzung(en) aus {name} entfernt</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="112" />
            <source>Replace existing data</source>
            <translation>Vorhandene Daten ersetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/merge.view.json" line="0" />
            <source>Replace: the new table replaces the one on screen. Columns: its columns are added beside these (the rows must match). Rows: its rows are appended under these, for the columns both have.</source>
            <translation>Ersetzen: die neue Tabelle ersetzt die angezeigte. Spalten: ihre Spalten werden neben diesen hinzugefügt (die Zeilen müssen übereinstimmen). Zeilen: ihre Zeilen werden unter diese angehängt, für die Spalten, die beide haben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/constants_group.py" line="236" />
            <source>Replaced population-wise {symbol} with shared {symbol} = {value}</source>
            <translation>Populationsweises {symbol} durch gemeinsames {symbol} = {value} ersetzt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Report</source>
            <translation>Bericht</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Report YAML (report.yaml):</source>
            <translation>Bericht-YAML (report.yaml):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="454" />
            <source>Report downloaded as {name}</source>
            <translation>Bericht als {name} heruntergeladen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="460" />
            <source>Report written to {path}</source>
            <translation>Bericht nach {path} geschrieben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="766" />
            <source>Reports cleared</source>
            <translation>Berichte gelöscht</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="733" />
            <source>Reports generated.</source>
            <translation>Berichte erzeugt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Resamples used for the factor uncertainties, with the population assignment held fixed. 0 skips them. It is cheap — the classification, not the resampling, is what costs.</source>
            <translation>Für die Faktorunsicherheiten verwendete Stichproben, bei festgehaltener Populationszuordnung. 0 überspringt sie. Das ist billig — die Klassifizierung kostet, nicht das Resampling.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="399" />
            <source>Reset</source>
            <translation>Zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="402" />
            <source>Reset Settings</source>
            <translation>Einstellungen zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Reset all performance settings to their default values</source>
            <translation>Alle Leistungseinstellungen auf ihre Standardwerte zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="403" />
            <source>Reset all performance settings to their default values?</source>
            <translation>Alle Leistungseinstellungen auf ihre Standardwerte zurücksetzen?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Reset to Defaults</source>
            <translation>Auf Standard zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="78" />
            <source>Reset window layout</source>
            <translation>Fensterlayout zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1266" />
            <source>Resize columns to contents</source>
            <translation>Spaltenbreite an Inhalt anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="242" />
            <source>Restart with new settings</source>
            <translation>Mit neuen Einstellungen neu starten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="203" />
            <source>Restored the session saved {when} UTC</source>
            <translation>Gespeicherte Sitzung vom {when} UTC wiederhergestellt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="205" />
            <source>Restored the session saved {when} UTC; not restored: {notes}</source>
            <translation>Gespeicherte Sitzung vom {when} UTC wiederhergestellt; nicht wiederhergestellt: {notes}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="595" />
            <source>Restored {n} constants stored in {name}</source>
            <translation>{n} in {name} gespeicherte Konstanten wiederhergestellt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="42" />
            <source>Revert to saved session</source>
            <translation>Auf gespeicherte Sitzung zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Right Axis</source>
            <translation>Rechte Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Right Axis Label</source>
            <translation>Rechte Achsenbeschriftung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Right-click a row to copy, paste, link, or make it a vector (one value per population).</source>
            <translation>Rechtsklick auf eine Zeile zum Kopieren, Einfügen, Verknüpfen oder um sie zum Vektor zu machen (ein Wert pro Population).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Routing channels of the green detectors (empty: skip green).</source>
            <translation>Routing-Kanäle der grünen Detektoren (leer: Grün überspringen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Routing channels of the red detectors (empty: skip red).</source>
            <translation>Routing-Kanäle der roten Detektoren (leer: Rot überspringen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Routing channels of the unlabelled g, s columns (empty: skip).</source>
            <translation>Routing-Kanäle der unmarkierten g-, s-Spalten (leer: überspringen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/data_source.py" line="1030" />
            <source>Row Count Mismatch</source>
            <translation>Zeilenanzahl stimmt nicht überein</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1332" />
            <source>Rows whose '{column}' contains:</source>
            <translation>Zeilen, deren '{column}' enthält:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Run it</source>
            <translation>Ausführen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Run the method on the chosen columns.</source>
            <translation>Die Methode auf den gewählten Spalten ausführen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="160" />
            <source>Run {label} in the current ndX session.</source>
            <translation>{label} in der aktuellen ndX-Sitzung ausführen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="292" />
            <source>Running HDBSCAN</source>
            <translation>HDBSCAN läuft</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="308" />
            <source>Running K-means</source>
            <translation>K-means läuft</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="511" />
            <source>Running {method}…</source>
            <translation>{method} läuft…</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>R₀ Förster radius</source>
            <translation>R₀ Förster-Radius</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>S</source>
            <translation>S</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="379" />
            <source>S (stoichiometry gating)</source>
            <translation>S (Stöchiometrie-Gating)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>S stoichiometry</source>
            <translation>S Stöchiometrie</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/publication_figure.py" line="29" />
            <source>SVG (vector)</source>
            <translation>SVG (Vektor)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Sample</source>
            <translation>Stichprobe</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="96" />
            <source>Sampling files</source>
            <translation>Sampling-Dateien</translation>
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
            <translation>Speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="255" />
            <source>Save .pto with session</source>
            <translation>.pto mit Sitzung speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="577" />
            <source>Save Burst IDs</source>
            <translation>Burst-IDs speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Save CSV</source>
            <translation>CSV speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="878" />
            <location filename="ndxplorer/app/features/analysis.py" line="1383" />
            <source>Save Error</source>
            <translation>Speicherfehler</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="748" />
            <source>Save Final Combined Report</source>
            <translation>Endgültigen kombinierten Bericht speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="864" />
            <source>Save Gaussian Fits</source>
            <translation>Gauß-Fits speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="859" />
            <source>Save Gaussians</source>
            <translation>Gauß-Funktionen speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="300" />
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Save Mask</source>
            <translation>Maske speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="827" />
            <source>Save Overlay Curves</source>
            <translation>Overlay-Kurven speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="806" />
            <location filename="ndxplorer/app/features/overlays.py" line="811" />
            <location filename="ndxplorer/app/features/overlays.py" line="822" />
            <source>Save Overlays</source>
            <translation>Overlays speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/screenshots.py" line="22" />
            <source>Save Screenshot</source>
            <translation>Bildschirmfoto speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Save a picture of the window.</source>
            <translation>Bild des Fensters speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Save and close.</source>
            <translation>Speichern und schließen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Save axis label settings to the settings folder</source>
            <translation>Achsenbeschriftungs-Einstellungen im Einstellungsordner speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="796" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="818" />
            <source>Save calibration</source>
            <translation>Kalibrierung speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="622" />
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Save calibration…</source>
            <translation>Kalibrierung speichern…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="547" />
            <source>Save config</source>
            <translation>Konfiguration speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1019" />
            <location filename="ndxplorer/app/features/settings.py" line="1022" />
            <source>Save constants</source>
            <translation>Konstanten speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1148" />
            <source>Save equations</source>
            <translation>Gleichungen speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="533" />
            <source>Save error</source>
            <translation>Speicherfehler</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/window.py" line="58" />
            <source>Save histograms</source>
            <translation>Histogramme speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="284" />
            <location filename="ndxplorer/app/features/overlays/parameters.view.json" line="0" />
            <source>Save parameters</source>
            <translation>Parameter speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="462" />
            <source>Save report</source>
            <translation>Bericht speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Save report…</source>
            <translation>Bericht speichern…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="160" />
            <location filename="ndxplorer/app/menus.py" line="41" />
            <source>Save session</source>
            <translation>Sitzung speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="54" />
            <source>Save settings</source>
            <translation>Einstellungen speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Save the Gaussians with the histogram and model (.json and .csv files).</source>
            <translation>Die Gauß-Funktionen mit Histogramm und Modell speichern (.json- und .csv-Dateien).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Save the burst IDs of the selected bursts.</source>
            <translation>Die Burst-IDs der ausgewählten Bursts speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Save the configuration as YAML or JSON</source>
            <translation>Die Konfiguration als YAML oder JSON speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Save the gates to a file.</source>
            <translation>Die Gates in einer Datei speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection/draw_mask.view.json" line="0" />
            <source>Save the mask as an integer TIFF.</source>
            <translation>Die Maske als ganzzahlige TIFF speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Save the settings</source>
            <translation>Einstellungen speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Save the settings and close</source>
            <translation>Einstellungen speichern und schließen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Save the settings to your ndX user folder without closing.</source>
            <translation>Die Einstellungen im ndX-Benutzerordner speichern, ohne zu schließen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>Save visible overlay curves as CSV (curve, x, y)</source>
            <translation>Sichtbare Overlay-Kurven als CSV speichern (Kurve, x, y)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="880" />
            <source>Saved</source>
            <translation>Gespeichert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="880" />
            <source>Saved files:
{files}</source>
            <translation>Gespeicherte Dateien:
{files}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="825" />
            <source>Saved overlay curves to {path}</source>
            <translation>Overlay-Kurven gespeichert unter {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="353" />
            <location filename="ndxplorer/app/features/accurate_fret.py" line="793" />
            <source>Saved to {target}</source>
            <translation>Gespeichert in {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="860" />
            <source>Saved {when} ({where}: {target})</source>
            <translation>Gespeichert {when} ({where}: {target})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Save…</source>
            <translation>Speichern…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="580" />
            <source>Saving Burst ID files...</source>
            <translation>Burst-ID-Dateien werden gespeichert...</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="580" />
            <source>Saving Files</source>
            <translation>Dateien speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/writer.py" line="169" />
            <source>Saving cluster labels...</source>
            <translation>Cluster-Labels werden gespeichert...</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/writer.py" line="157" />
            <source>Saving clustering parameters...</source>
            <translation>Cluster-Parameter werden gespeichert...</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/region_selection.py" line="210" />
            <source>Saving drawn regions, masks or Gaussian gates needs ChiSurf's region module (chisurf.core.roi), which is not installed here; interval gates alone can be saved.</source>
            <translation>Zum Speichern gezeichneter Regionen, Masken oder Gauß-Gates wird das Regionsmodul von ChiSurf (chisurf.core.roi) benötigt, das hier nicht installiert ist; nur Intervall-Gates können gespeichert werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1539" />
            <source>Saving files needs the io feature.</source>
            <translation>Zum Speichern von Dateien wird das Feature io benötigt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Scalar</source>
            <translation>Skalar</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Scalar: one value for all bursts. Vector: one value per population.</source>
            <translation>Skalar: ein Wert für alle Bursts. Vektor: ein Wert je Population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Scale colours across all columns instead of per column</source>
            <translation>Farben über alle Spalten statt pro Spalte skalieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Scale each column to unit variance first. Leave this on unless the columns genuinely share a scale.</source>
            <translation>Jede Spalte zuerst auf Einheitsvarianz skalieren. Eingeschaltet lassen, außer die Spalten haben tatsächlich dieselbe Skala.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Scan first</source>
            <translation>Zuerst scannen</translation>
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
            <translation>Ansichten bewerten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="351" />
            <source>Scoring views…</source>
            <translation>Ansichten werden bewertet…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Screenshot</source>
            <translation>Bildschirmfoto</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Select</source>
            <translation>Auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="52" />
            <source>Select All</source>
            <translation>Alle auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="174" />
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Select Columns for Clustering</source>
            <translation>Spalten für Clustering auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="822" />
            <source>Select Gaussian</source>
            <translation>Gauß-Funktion auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1259" />
            <source>Select all</source>
            <translation>Alles auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1076" />
            <source>Select an equation to see it here.</source>
            <translation>Eine Gleichung auswählen, um sie hier zu sehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="482" />
            <source>Select analysis folder</source>
            <translation>Analyseordner auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1207" />
            <source>Select at least {n} columns.</source>
            <translation>Mindestens {n} Spalten auswählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1210" />
            <source>Select columns for {method}</source>
            <translation>Spalten für {method} auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Select columns to use for clustering:</source>
            <translation>Spalten für das Clustering auswählen:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1214" />
            <source>Select columns?</source>
            <translation>Spalten auswählen?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="542" />
            <source>Select current path</source>
            <translation>Aktuellen Pfad auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Select point</source>
            <translation>Punkt auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_mixture.py" line="480" />
            <source>Selected data contains no finite values for fitting.</source>
            <translation>Die ausgewählten Daten enthalten keine endlichen Werte zum Anpassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>Selecting a row sets the axes of the main plot. &lt;b&gt;Islands&lt;/b&gt; says how many populations the view splits into, and the line under the table what the score means in numbers. Picking axes by hand in the plot selects the matching row here.</source>
            <translation>Eine Zeile auszuwählen setzt die Achsen des Hauptdiagramms. &lt;b&gt;Islands&lt;/b&gt; gibt an, in wie viele Populationen die Ansicht zerfällt, und die Zeile unter der Tabelle, was die Bewertung in Zahlen bedeutet. Wählt man die Achsen von Hand im Diagramm, wird hier die passende Zeile ausgewählt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Selection</source>
            <translation>Auswahl</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="644" />
            <location filename="ndxplorer/app/features/io.py" line="662" />
            <source>Selection JSON</source>
            <translation>Auswahl-JSON</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Selection σ:</source>
            <translation>Auswahl-σ:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="55" />
            <source>Send selection to</source>
            <translation>Auswahl senden an</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="54" />
            <source>Send to Napari</source>
            <translation>An Napari senden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="496" />
            <source>Send to Napari: {reason}.</source>
            <translation>An Napari senden: {reason}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="652" />
            <source>Sent {bursts} bursts from {files} file(s) to {target} (not recorded: no database product attached)</source>
            <translation>{bursts} Bursts aus {files} Datei(en) an {target} gesendet (nicht aufgezeichnet: kein Datenbankprodukt angehängt)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="658" />
            <source>Sent {bursts} bursts from {files} file(s) to {target} and recorded it</source>
            <translation>{bursts} Bursts aus {files} Datei(en) an {target} gesendet und aufgezeichnet</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="655" />
            <source>Sent {bursts} bursts from {files} file(s) to {target} — but the provenance record failed: {error}</source>
            <translation>{bursts} Bursts aus {files} Datei(en) an {target} gesendet — aber der Herkunftseintrag ist fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="649" />
            <source>Separation</source>
            <translation>Trennung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="156" />
            <source>Session not saved in {name}: {reason}</source>
            <translation>Sitzung nicht in {name} gespeichert: {reason}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="152" />
            <source>Session saved in {name}</source>
            <translation>Sitzung in {name} gespeichert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Set</source>
            <translation>Setzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1051" />
            <location filename="ndxplorer/app/features/settings.py" line="1055" />
            <location filename="ndxplorer/app/menus.py" line="59" />
            <source>Set default axis</source>
            <translation>Standardachse festlegen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="240" />
            <source>Set g_irf, s_irf (and n_bg) of the corrected phasor columns from an IRF and the measurement.</source>
            <translation>g_irf, s_irf (und n_bg) der korrigierten Phasor-Spalten aus einer IRF und der Messung setzen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Set the colour limits from the data.</source>
            <translation>Farbgrenzen aus den Daten setzen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings.py" line="857" />
            <location filename="ndxplorer/app/menus.py" line="51" />
            <source>Settings</source>
            <translation>Einstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="382" />
            <source>Settings Applied</source>
            <translation>Einstellungen angewendet</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="371" />
            <source>Settings are saved to: {path}</source>
            <translation>Einstellungen werden gespeichert in: {path}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="400" />
            <source>Settings reset to defaults. Apply or OK saves them.</source>
            <translation>Einstellungen auf Standard zurückgesetzt. Anwenden oder OK speichert sie.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Settings that steer convergence rather than the result's meaning.</source>
            <translation>Einstellungen, die die Konvergenz steuern, nicht die Bedeutung des Ergebnisses.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/project_reader.py" line="139" />
            <source>Several stored tables; choose one of: {names}</source>
            <translation>Mehrere gespeicherte Tabellen; eine auswählen aus: {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Shade numeric cells by their value</source>
            <translation>Numerische Zellen nach ihrem Wert schattieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="172" />
            <source>Show a 2-D map first: the mask is loaded onto its bins.</source>
            <translation>Zuerst eine 2D-Karte anzeigen: Die Maske wird auf deren Bins geladen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Show all</source>
            <translation>Alle anzeigen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show every axis title; untick to choose them one by one</source>
            <translation>Jeden Achsentitel anzeigen; abwählen, um sie einzeln zu wählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Show every column in the burst table.</source>
            <translation>Jede Spalte der Burst-Tabelle anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Show islands on the map</source>
            <translation>Inseln auf der Karte zeigen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="865" />
            <source>Show ndX in this language.</source>
            <translation>ndX in dieser Sprache anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Show only the columns whose name contains this text.</source>
            <translation>Nur Spalten anzeigen, deren Name diesen Text enthält.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Show only this cluster; -1 shows all.</source>
            <translation>Nur diesen Cluster zeigen; -1 zeigt alle.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Show the curve on the plot.</source>
            <translation>Kurve im Diagramm anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>Show the data table.</source>
            <translation>Datentabelle anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Show the projection in its own window.</source>
            <translation>Die Projektion in einem eigenen Fenster anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the 2D plot</source>
            <translation>Untere Achse des 2D-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the X plot</source>
            <translation>Untere Achse des X-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the Y plot</source>
            <translation>Untere Achse des Y-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the Z plot</source>
            <translation>Untere Achse des Z-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the bottom axis of the overlay plot</source>
            <translation>Untere Achse des Overlay-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the 2D plot</source>
            <translation>Linke Achse des 2D-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the X plot</source>
            <translation>Linke Achse des X-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the Y plot</source>
            <translation>Linke Achse des Y-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the Z plot</source>
            <translation>Linke Achse des Z-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the left axis of the overlay plot</source>
            <translation>Linke Achse des Overlay-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the 2D plot</source>
            <translation>Rechte Achse des 2D-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the X plot</source>
            <translation>Rechte Achse des X-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the Y plot</source>
            <translation>Rechte Achse des Y-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the right axis of the overlay plot</source>
            <translation>Rechte Achse des Overlay-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the 2D plot</source>
            <translation>Obere Achse des 2D-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the X plot</source>
            <translation>Obere Achse des X-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the Y plot</source>
            <translation>Obere Achse des Y-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Show/hide the top axis of the overlay plot</source>
            <translation>Obere Achse des Overlay-Diagramms ein-/ausblenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Shown</source>
            <translation>Angezeigt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Size of the local neighbourhood. Larger = more global structure, smaller = more local detail.</source>
            <translation>Größe der lokalen Nachbarschaft. Größer = mehr globale Struktur, kleiner = mehr lokale Details.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Smallest donor-only / acceptor-only population accepted when fitting a background. Below it that channel is left at whatever it had rather than guessed from a handful of bursts.</source>
            <translation>Kleinste Donor-only-/Akzeptor-only-Population, die beim Anpassen eines Hintergrunds akzeptiert wird. Darunter bleibt der Kanal bei seinem bisherigen Wert, statt aus wenigen Bursts geraten zu werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Smallest group that counts as a cluster rather than noise.</source>
            <translation>Kleinste Gruppe, die als Cluster und nicht als Rauschen zählt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Smallest weight a component keeps; 0 disables the floor.</source>
            <translation>Kleinstes Gewicht, das eine Komponente behält; 0 deaktiviert die Untergrenze.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="384" />
            <source>Some changes may require restarting ndX to take full effect.</source>
            <translation>Manche Änderungen erfordern einen Neustart von ndX, um vollständig zu wirken.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="806" />
            <source>Spearman ρ = {rho}, p = {p} over {n} sampled bursts: the two move together, which says nothing about populations.</source>
            <translation>Spearman ρ = {rho}, p = {p} über {n} gezogene Bursts: beide bewegen sich gemeinsam, was nichts über Populationen aussagt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Speed</source>
            <translation>Geschwindigkeit</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Spread:</source>
            <translation>Streuung:</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Stack</source>
            <translation>Stapel</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Standard error from the bootstrap (population assignment held fixed).</source>
            <translation>Standardfehler aus dem Bootstrap (Populationszuordnung bleibt fest).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Standardise columns</source>
            <translation>Spalten standardisieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.py" line="94" />
            <location filename="ndxplorer/analysis/vizrank.py" line="95" />
            <location filename="ndxplorer/analysis/vizrank.py" line="96" />
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <location filename="ndxplorer/analysis/vizrank_model.py" line="244" />
            <source>Start</source>
            <translation>Start</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Start the ranking, continue it, or restart it with new settings.</source>
            <translation>Das Ranking starten, fortsetzen oder mit neuen Einstellungen neu starten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="267" />
            <source>Starting…</source>
            <translation>Wird gestartet…</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Step</source>
            <translation>Schritt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Step through the data along one of its columns.</source>
            <translation>Die Daten schrittweise entlang einer ihrer Spalten durchlaufen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Steps</source>
            <translation>Schritte</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Steps per second while playing. A redraw takes a few tens of milliseconds, so above roughly 30 the plot cannot keep up and steps are dropped rather than shown faster.</source>
            <translation>Schritte pro Sekunde bei der Wiedergabe. Ein Neuzeichnen dauert einige zehn Millisekunden; oberhalb von etwa 30 kommt das Diagramm nicht mehr mit, und Schritte werden ausgelassen statt schneller gezeigt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Stop</source>
            <translation>Stopp</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>Stop after the folder being processed</source>
            <translation>Nach dem gerade verarbeiteten Ordner anhalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Stop scoring; Start continues from here.</source>
            <translation>Scoring anhalten; Start setzt hier fort.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/progress.view.json" line="0" />
            <source>Stop the calibration; the window keeps the constants it had.</source>
            <translation>Die Kalibrierung stoppen; das Fenster behält die bisherigen Konstanten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>Stop the fit after the step it is on.</source>
            <translation>Den Fit nach dem laufenden Schritt stoppen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Stop the running method.</source>
            <translation>Die laufende Methode anhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/progress.view.json" line="0" />
            <source>Stop; what is finished stays</source>
            <translation>Anhalten; Fertiges bleibt erhalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Store the calibration in the measurement</source>
            <translation>Kalibrierung in der Messung speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="819" />
            <source>Store the calibration in the measurement?</source>
            <translation>Die Kalibrierung in der Messung speichern?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="624" />
            <source>Store the current FRET factors in the measurement or a calibration file.</source>
            <translation>Die aktuellen FRET-Faktoren in der Messung oder einer Kalibrierungsdatei speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="351" />
            <source>Stored in the measurement: {target}</source>
            <translation>In der Messung gespeichert: {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="812" />
            <source>Stored in {target}</source>
            <translation>In {target} gespeichert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Stored table</source>
            <translation>Gespeicherte Tabelle</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>Subtract the flat background of the reference decay before computing the phasor reference.</source>
            <translation>Den flachen Hintergrund des Referenzzerfalls vor der Berechnung der Phasor-Referenz abziehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="858" />
            <source>System language</source>
            <translation>Systemsprache</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="302" />
            <source>TIFF files</source>
            <translation>TIFF-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference/reference.view.json" line="0" />
            <source>TTTR file (.ptu, .ht3, ...) of the instrument response: scatter, a mirror, or a dye of known lifetime.</source>
            <translation>TTTR-Datei (.ptu, .ht3, ...) der Instrumentenantwort: Streuung, ein Spiegel oder ein Farbstoff bekannter Lebensdauer.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="33" />
            <source>TTTR files</source>
            <translation>TTTR-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1188" />
            <source>Table Editor</source>
            <translation>Tabelleneditor</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Table of parameters (burst-table columns) with their per-parameter settings.</source>
            <translation>Tabelle der Parameter (Burst-Tabellenspalten) mit ihren Einstellungen pro Parameter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>Table:</source>
            <translation>Tabelle:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Take from</source>
            <translation>Übernehmen aus</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/text.view.json" line="0" />
            <source>Text</source>
            <translation>Text</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="462" />
            <source>Text (*.txt);;All files (*)</source>
            <translation>Text (*.txt);;Alle Dateien (*)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="84" />
            <source>Text files</source>
            <translation>Textdateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/window.py" line="59" />
            <source>Text files (*.txt *.tsv)</source>
            <translation>Textdateien (*.txt *.tsv)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Text report of the accurate FRET calibration (read only).</source>
            <translation>Textbericht der genauen FRET-Kalibrierung (schreibgeschützt).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <source>Text to enter.</source>
            <translation>Einzugebender Text.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="624" />
            <source>The FCS Correlator Wizard is a ChiSurf plugin and does not run in this window. Open the {n} .bst file(s) in {folder} with ChiSurf's FCS correlator.</source>
            <translation>Der FCS-Korrelator-Assistent ist ein ChiSurf-Plugin und läuft nicht in diesem Fenster. Die {n} .bst-Datei(en) in {folder} mit dem FCS-Korrelator von ChiSurf öffnen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="615" />
            <source>The Microtime Histogram plugin (chisurf) is not available in this standalone build.</source>
            <translation>Das Plugin Mikrozeit-Histogramm (ChiSurf) ist in diesem eigenständigen Build nicht verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/vector.view.json" line="0" />
            <source>The burst column whose value says which population a burst is in.</source>
            <translation>Die Burst-Spalte, deren Wert angibt, in welcher Population ein Burst liegt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>The calibration's whole text, as the Qt window's report shows it and as Save report writes it.</source>
            <translation>Der gesamte Text der Kalibrierung, wie ihn der Bericht des Qt-Fensters zeigt und wie Bericht speichern ihn schreibt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>The cloud fits the curve to the distribution itself: every populated bin pulls on it, weighted by what it counted, and a bin more than a couple of bins away stops pulling -- so the curve follows the populations and ignores the junk. Reducing each column to one point instead cannot describe a population: a blob reduces to a horizontal streak across its own columns.</source>
            <translation>Die Wolke passt die Kurve an die Verteilung selbst an: Jeder besetzte Bin zieht an ihr, gewichtet mit seinen Zählungen, und ein Bin, der mehr als ein paar Bins entfernt ist, zieht nicht mehr -- so folgt die Kurve den Populationen und ignoriert den Ausschuss. Jede Spalte auf einen Punkt zu reduzieren kann dagegen keine Population beschreiben: Ein Blob wird zu einem horizontalen Streifen über seine eigenen Spalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1383" />
            <source>The clustering data could not be written.</source>
            <translation>Die Clustering-Daten konnten nicht geschrieben werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="122" />
            <source>The configuration must define a top-level 'plots' list.</source>
            <translation>Die Konfiguration muss eine 'plots'-Liste auf oberster Ebene definieren.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="345" />
            <source>The correction factors were optimized against the loaded data.</source>
            <translation>Die Korrekturfaktoren wurden an den geladenen Daten optimiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/overlays.view.json" line="0" />
            <source>The curve to add: Custom Equation (type your own) or one of the curves in curve_equations.yaml.</source>
            <translation>Die hinzuzufügende Kurve: Benutzerdefinierte Gleichung (eigene eingeben) oder eine der Kurven in curve_equations.yaml.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>The curve with the parameter values written in (select to copy).</source>
            <translation>Die Kurve mit eingesetzten Parameterwerten (zum Kopieren auswählen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>The curve's colour.</source>
            <translation>Farbe der Kurve.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>The displayed data fits y(x) to the two-dimensional distribution (one point per populated x column); a marginal fits the curve to that axis's histogram of counts.</source>
            <translation>Die angezeigten Daten passen y(x) an die zweidimensionale Verteilung an (ein Punkt pro besetzter x-Spalte); bei einer Randverteilung wird die Kurve an das Zählhistogramm dieser Achse angepasst.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>The full path of the selected folder</source>
            <translation>Der vollständige Pfad des ausgewählten Ordners</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The gates in force. Edit a bound in place; the Delete key removes a row.</source>
            <translation>Die geltenden Gates. Eine Grenze direkt bearbeiten; die Entf-Taste entfernt eine Zeile.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>The generated images of the selected folder</source>
            <translation>Die erzeugten Bilder des ausgewählten Ordners</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="219" />
            <source>The help text is not installed.</source>
            <translation>Der Hilfetext ist nicht installiert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>The labels a view should keep apart: the gate in the Selection table, each gate as its own population, the clusters, or a z parameter that holds labels. Parameters a gate is defined on are left out.</source>
            <translation>Die Labels, die eine Ansicht auseinanderhalten soll: das Gate in der Auswahltabelle, jedes Gate als eigene Population, die Cluster oder ein z-Parameter mit Labels. Parameter, auf denen ein Gate definiert ist, werden ausgelassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="200" />
            <source>The map changed: the painted mask was cleared and drawing stopped.</source>
            <translation>Die Karte hat sich geändert: Die gemalte Maske wurde gelöscht und das Zeichnen beendet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="142" />
            <source>The mask has no bins of any category.</source>
            <translation>Die Maske enthält keine Bins irgendeiner Kategorie.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="143" />
            <source>The mask has no bins of category {category}.</source>
            <translation>Die Maske enthält keine Bins der Kategorie {category}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="176" />
            <source>The mask is {mask_x} x {mask_y} bins; the map is {map_x} x {map_y}.</source>
            <translation>Die Maske hat {mask_x} x {mask_y} Bins; die Karte {map_x} x {map_y}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="824" />
            <source>The mean {classes} of each burst's {k} nearest neighbours predicts its own with R² = {r2}; weighted by the {share} of sampled rows that have values.</source>
            <translation>Der Mittelwert von {classes} der {k} nächsten Nachbarn jedes Bursts sagt den eigenen mit R² = {r2} voraus; gewichtet mit dem Anteil {share} der gezogenen Zeilen, die Werte haben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>The parameter this one follows (right-click to link or unlink). Shown while one is linked.</source>
            <translation>Der Parameter, dem dieser folgt (Rechtsklick zum Verknüpfen oder Lösen). Sichtbar, solange einer verknüpft ist.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io/store_choice.view.json" line="0" />
            <source>The sampling chain to open: the fit it belongs to, with its number of draws and parameters.</source>
            <translation>Die zu öffnende Sampling-Kette: der zugehörige Fit mit Anzahl der Ziehungen und Parameter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="191" />
            <source>The score; the bar is its share of the range.</source>
            <translation>Der Score; der Balken ist sein Anteil am Bereich.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="161" />
            <source>The session could not be saved in {name}: {error}</source>
            <translation>Die Sitzung konnte nicht in {name} gespeichert werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="316" />
            <source>The settings could not be saved.</source>
            <translation>Die Einstellungen konnten nicht gespeichert werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>The table fills while it computes, best rows at the top. &lt;b&gt;Pause&lt;/b&gt; stops it and &lt;b&gt;Start&lt;/b&gt; continues; closing the panel pauses too.</source>
            <translation>Die Tabelle füllt sich während der Berechnung, die besten Zeilen oben. &lt;b&gt;Pause&lt;/b&gt; hält an und &lt;b&gt;Start&lt;/b&gt; setzt fort; das Schließen des Bereichs pausiert ebenfalls.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The third axis: its own marginal, and a range slider that gates the plot.</source>
            <translation>Die dritte Achse: eigene Randverteilung und ein Bereichsregler, der das Diagramm gatet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>The value. Double-click to type one; a linked parameter shows its master's.</source>
            <translation>Der Wert. Doppelklick zum Eingeben; ein verknüpfter Parameter zeigt den seines Masters.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>The working folder: where files are opened from.</source>
            <translation>Der Arbeitsordner: Von hier werden Dateien geöffnet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The x parameter's name above the X plot</source>
            <translation>Name des x-Parameters über dem X-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The y parameter's name above the Y plot</source>
            <translation>Name des y-Parameters über dem Y-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The y parameter's name right of the Y plot</source>
            <translation>Name des y-Parameters rechts vom Y-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The z axis has no 2D bins</source>
            <translation>Die z-Achse hat keine 2D-Bins</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>The z marginal; drag the region to set the z range, and its bottom edge to resize it.</source>
            <translation>Die z-Randverteilung; die Region ziehen, um den z-Bereich zu setzen, und ihre Unterkante, um die Größe zu ändern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The z parameter's name left of the Z plot</source>
            <translation>Name des z-Parameters links vom Z-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>The z parameter's name under the Z plot</source>
            <translation>Parametername unter dem Z-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="196" />
            <source>The {axis} parameter of the view; hover a shortened name for the whole of it.</source>
            <translation>Der {axis}-Parameter der Ansicht; über einem gekürzten Namen schweben, um ihn ganz zu sehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1101" />
            <source>Then restart ndXplorer.</source>
            <translation>Danach ndXplorer neu starten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="859" />
            <source>There are no Gaussian rows to save.</source>
            <translation>Es gibt keine Gauß-Zeilen zum Speichern.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="643" />
            <source>This ChiSurf advertises no burst analyses. It may be an older version, or the burst services are not loaded.</source>
            <translation>Dieses ChiSurf bietet keine Burst-Analysen an. Möglicherweise ist es eine ältere Version, oder die Burst-Dienste sind nicht geladen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="844" />
            <source>This measurement carries {n} stored calibration(s).</source>
            <translation>Diese Messung enthält {n} gespeicherte Kalibrierung(en).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="220" />
            <source>This measurement holds no saved session</source>
            <translation>Diese Messung enthält keine gespeicherte Sitzung</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="637" />
            <source>This table has no burst provenance: {missing} missing. Sending needs the photon intervals each burst came from.</source>
            <translation>Diese Tabelle hat keine Burst-Herkunft: {missing} fehlt. Zum Senden werden die Photonenintervalle jedes Bursts benötigt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="404" />
            <source>This will clear your custom configuration.</source>
            <translation>Dadurch wird Ihre benutzerdefinierte Konfiguration gelöscht.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="774" />
            <source>This will permanently delete report folders for {n} analysis folder(s). Continue?</source>
            <translation>Dadurch werden die Berichtsordner von {n} Analyseordner(n) dauerhaft gelöscht. Fortfahren?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="379" />
            <source>This window cannot show context menus yet.</source>
            <translation>Dieses Fenster kann noch keine Kontextmenüs anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="771" />
            <source>This window carries no constants to save.</source>
            <translation>Dieses Fenster enthält keine zu speichernden Konstanten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Threads UMAP may use; -1 uses all cores.</source>
            <translation>Threads, die UMAP nutzen darf; -1 nutzt alle Kerne.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Tick every column in the list.</source>
            <translation>Jede Spalte der Liste anhaken.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Tick the axes each plot shows. Apply or OK redraws the plots; Save also writes the axis titles and their colour to the settings folder.</source>
            <translation>Achsen markieren, die jedes Diagramm zeigt. Anwenden oder OK zeichnet die Diagramme neu; Speichern schreibt zusätzlich die Achsentitel und ihre Farbe in den Einstellungsordner.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Tick the burst-table columns to include in the analysis.</source>
            <translation>Die Spalten der Burst-Tabelle ankreuzen, die in die Analyse eingehen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Tick to apply this gate to the selection.</source>
            <translation>Markieren, um dieses Gate auf die Auswahl anzuwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Tick to include this column in the analysis.</source>
            <translation>Anhaken, um diese Spalte in die Analyse aufzunehmen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/columns.view.json" line="0" />
            <source>Tick to show this column in the burst table.</source>
            <translation>Ankreuzen, um diese Spalte in der Burst-Tabelle anzuzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Title color</source>
            <translation>Titelfarbe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Tolerance (tol):</source>
            <translation>Toleranz (tol):</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Top Axis</source>
            <translation>Obere Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Top Axis Label</source>
            <translation>Beschriftung obere Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Transparent background</source>
            <translation>Transparenter Hintergrund</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>Turn the selected Gaussian (or the only one) into an elliptical gate at Selection σ.</source>
            <translation>Die ausgewählte (oder einzige) Gauß-Funktion in ein elliptisches Gate bei Auswahl-σ umwandeln.</translation>
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
            <translation>Fortschritt der UMAP-Berechnung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="333" />
            <location filename="ndxplorer/app/features/analysis.py" line="353" />
            <source>UMAP Projection</source>
            <translation>UMAP-Projektion</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="352" />
            <source>UMAP Projection (3D)</source>
            <translation>UMAP-Projektion (3D)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="417" />
            <source>UMAP finished</source>
            <translation>UMAP abgeschlossen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>UMAP learning rate of the embedding optimisation; larger values move points faster.</source>
            <translation>UMAP-Lernrate der Einbettungsoptimierung; größere Werte bewegen Punkte schneller.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>UMAP spread; sets how widely the embedded points are scattered.</source>
            <translation>UMAP-Streuung; legt fest, wie weit die eingebetteten Punkte verteilt sind.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="197" />
            <source>Unavailable: this measurement has no {need}.</source>
            <translation>Nicht verfügbar: Diese Messung hat kein {need}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="206" />
            <source>Unavailable: {reason}.</source>
            <translation>Nicht verfügbar: {reason}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="418" />
            <source>Unlink</source>
            <translation>Verknüpfung lösen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Untick every column in the list.</source>
            <translation>Bei jeder Spalte der Liste das Häkchen entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1102" />
            <location filename="ndxplorer/app/menus.py" line="84" />
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Update</source>
            <translation>Aktualisieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Update default axis range. To save current default axis settings use the Settings-&gt;Save Menu.</source>
            <translation>Standard-Achsenbereich aktualisieren. Zum Speichern der aktuellen Standard-Achseneinstellungen das Menü Einstellungen-&gt;Speichern verwenden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1098" />
            <source>Update with the package manager that installed ndXplorer:</source>
            <translation>Mit dem Paketmanager aktualisieren, mit dem ndXplorer installiert wurde:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Upper bound of the gate on this parameter.</source>
            <translation>Obere Grenze des Gates für diesen Parameter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Upper bound. ∞: none. Type a number to set it, ∞ (or inf) to remove it.</source>
            <translation>Obere Grenze. ∞: keine. Eine Zahl eingeben zum Setzen, ∞ (oder inf) zum Entfernen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>Upper colour limit of the 2-D histogram.</source>
            <translation>Obere Farbgrenze des 2D-Histogramms.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>Use</source>
            <translation>Verwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Use Fast Histogram Optimizations</source>
            <translation>Schnelle Histogramm-Optimierungen verwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Use Parallel Computation</source>
            <translation>Parallele Berechnung verwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>Use islands as clusters</source>
            <translation>Inseln als Cluster verwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Use light-path priors</source>
            <translation>Lichtweg-Priors verwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Use multiple CPU cores for histogram computation when available.</source>
            <translation>Mehrere CPU-Kerne für die Histogrammberechnung nutzen, wenn verfügbar.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Validate all equations and recompute the derived columns</source>
            <translation>Alle Gleichungen validieren und die abgeleiteten Spalten neu berechnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <location filename="ndxplorer/app/views/parameter_table.view.json" line="0" />
            <source>Value</source>
            <translation>Wert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Value after the calibration.</source>
            <translation>Wert nach der Kalibrierung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Value before the calibration.</source>
            <translation>Wert vor der Kalibrierung.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="391" />
            <source>Value for '{name}':</source>
            <translation>Wert für '{name}':</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <location filename="ndxplorer/app/features/overlays/link.view.json" line="0" />
            <source>Value of the correction factor.</source>
            <translation>Wert des Korrekturfaktors.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/performance.view.json" line="0" />
            <source>Values in settings file override environment variables.</source>
            <translation>Werte in der Einstellungsdatei überschreiben Umgebungsvariablen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>Vector</source>
            <translation>Vektor</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/publication_export.view.json" line="0" />
            <source>Vector (PDF/SVG) is resolution-independent and best for print; PNG is a high-resolution raster.</source>
            <translation>Vektor (PDF/SVG) ist auflösungsunabhängig und am besten für den Druck; PNG ist ein hochauflösendes Raster.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="419" />
            <source>Vector constants written: none — scalar factors only</source>
            <translation>Vektorkonstanten geschrieben: keine — nur skalare Faktoren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="415" />
            <source>Vector constants written: {vectors}</source>
            <translation>Vektorkonstanten geschrieben: {vectors}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Verbose:</source>
            <translation>Ausführlich:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Verbosity of the Gaussian mixture fit log (0 is silent).</source>
            <translation>Ausführlichkeit des Logs des Gauß-Mischmodell-Fits (0 ist still).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/menus.py" line="61" />
            <source>View</source>
            <translation>Ansicht</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="60" />
            <source>Weight by photons</source>
            <translation>Nach Photonen gewichten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gmm_settings.view.json" line="0" />
            <source>Weight floor:</source>
            <translation>Gewichtsuntergrenze:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank.view.json" line="0" />
            <source>What makes a view informative. Separation (default): how many bursts fall into clearly separated islands -- donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line; one population scores 0 however correlated. Correlation: parameters that move together (related measurements, not populations). Classes (only with gates or clusters): views that keep the labelled bursts apart.</source>
            <translation>Was eine Ansicht informativ macht. Trennung (Standard): wie viele Bursts in klar getrennten Inseln liegen -- Donor-only-, Akzeptor-only- und FRET-Spezies in E vs S, eine dynamische Population abseits der statischen FRET-Linie; eine Population erhält 0, egal wie korreliert. Korrelation: Parameter, die sich gemeinsam bewegen (verwandte Messungen, keine Populationen). Klassen (nur mit Gates oder Clustern): Ansichten, die die gelabelten Bursts auseinanderhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>What the populations are told apart by. S alone is the stoichiometry gating (fast, the default); any other ticked dimension switches to the multidimensional mixture over all ticked ones, about ten times slower (25 s instead of 2.4 s on cal1). Dimensions this measurement has no column for are disabled; their tooltip says which column is missing.</source>
            <translation>Woran die Populationen unterschieden werden. S allein ist das Stöchiometrie-Gating (schnell, Standard); jede andere aktivierte Dimension wechselt zur mehrdimensionalen Mischung über alle aktivierten, etwa zehnmal langsamer (25 s statt 2.4 s bei cal1). Dimensionen, für die diese Messung keine Spalte hat, sind deaktiviert; ihr Tooltip nennt die fehlende Spalte.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export/vizrank_guide.json" line="0" />
            <source>What this panel does</source>
            <translation>Was dieser Bereich tut</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>When it finishes</source>
            <translation>Nach Abschluss</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Where the curve ends (t1); it is traced with the tab's number of points.</source>
            <translation>Wo die Kurve endet (t1); sie wird mit der Punktzahl des Tabs gezeichnet.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Where the curve starts (t0).</source>
            <translation>Wo die Kurve beginnt (t0).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Where the result is kept. The measurement container is the default: it already holds the photons, the burst table and the background estimate, and a calibration determined from them belongs in the same file.</source>
            <translation>Wo das Ergebnis abgelegt wird. Standard ist der Messcontainer: Er enthält bereits die Photonen, die Burst-Tabelle und die Hintergrundschätzung, und eine daraus bestimmte Kalibrierung gehört in dieselbe Datei.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>Where:</source>
            <translation>Wo:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Whether each FRET population got its own γ: the mode, the model the BIC selected (shared or per population) with both BICs, whether the per-population model was identifiable, and the vector constants written. A written vector is an expandable row of the Parameters tab; right-click &gt; Make scalar turns it back into one value.</source>
            <translation>Ob jede FRET-Population ihr eigenes γ erhielt: der Modus, das vom BIC gewählte Modell (gemeinsam oder pro Population) mit beiden BIC-Werten, ob das Modell pro Population identifizierbar war, und die geschriebenen Vektorkonstanten. Ein geschriebener Vektor ist eine aufklappbare Zeile des Tabs Parameter; Rechtsklick &gt; Make scalar macht daraus wieder einen einzelnen Wert.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Whether the correction factors may differ between the FRET populations, and what the populations are told apart by. A population-wise γ is written as a vector constant (γ[FRET 1], γ[FRET 2]…) that the Parameters tab lists as an expandable row; to go back to one value, right-click it there and choose Make scalar.</source>
            <translation>Ob die Korrekturfaktoren zwischen den FRET-Populationen abweichen dürfen und woran die Populationen unterschieden werden. Ein populationsweises γ wird als Vektorkonstante geschrieben (γ[FRET 1], γ[FRET 2]…), die der Reiter Parameter als aufklappbare Zeile listet; um zu einem Wert zurückzukehren, dort Rechtsklick und In Skalar umwandeln wählen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Whether the factor was written into the window, or held at the value it had (the options' Determine toggles).</source>
            <translation>Ob der Faktor ins Fenster geschrieben oder auf seinem bisherigen Wert gehalten wurde (die Determine-Schalter der Optionen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Which axes and axis titles the plots show, and the titles' colour.</source>
            <translation>Welche Achsen und Achsentitel die Diagramme zeigen, und die Farbe der Titel.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Which correction factors this calibration is allowed to change. The others keep the value the window already has.</source>
            <translation>Welche Korrekturfaktoren diese Kalibrierung ändern darf. Die anderen behalten den Wert, den das Fenster bereits hat.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Which question to ask of the chosen columns.</source>
            <translation>Welche Frage an die gewählten Spalten gestellt wird.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Which slice is on screen. Drag to scrub through the measurement; double-click to type a step. Hovering shows the slice and how many points survive it.</source>
            <translation>Welcher Abschnitt angezeigt wird. Ziehen, um durch die Messung zu scrubben; Doppelklick, um einen Schritt einzutippen. Beim Darüberfahren werden der Abschnitt und die Zahl der verbleibenden Punkte angezeigt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="381" />
            <source>Whole islands</source>
            <translation>Ganze Inseln</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Width (standard deviation) of the FRET efficiency distribution of the population.</source>
            <translation>Breite (Standardabweichung) der FRET-Effizienzverteilung der Population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Width of the dye-linker distance distribution, which sets the curvature of the static FRET line.</source>
            <translation>Breite der Farbstoff-Linker-Abstandsverteilung, die die Krümmung der statischen FRET-Linie festlegt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Window</source>
            <translation>Fenster</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>Window: one slice at a time — what the sample looked like then. Integrate: everything up to the current step, accumulating, so a population that only appears late is visible as it arrives. Stack: no gating, the whole measurement at once.</source>
            <translation>Fenster: ein Abschnitt nach dem anderen — wie die Probe damals aussah. Integrieren: alles bis zum aktuellen Schritt, akkumulierend, sodass eine erst spät auftretende Population beim Eintreffen sichtbar wird. Stapel: kein Gating, die gesamte Messung auf einmal.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>Write the changes back to the data and redraw</source>
            <translation>Die Änderungen in die Daten zurückschreiben und neu zeichnen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>Write the cluster assignment to a folder.</source>
            <translation>Die Cluster-Zuordnung in einen Ordner schreiben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Write the corrected per-burst columns under new names. Not redundant with applying the constants: ndX's own efficiency equation has no direct-excitation term, so constants alone cannot make its native column accurate. Its own columns are left untouched.</source>
            <translation>Die korrigierten Spalten pro Burst unter neuen Namen schreiben. Nicht redundant zum Anwenden der Konstanten: Die eigene Effizienzgleichung von ndX hat keinen Direktanregungsterm, daher können Konstanten allein ihre native Spalte nicht genau machen. Die eigenen Spalten bleiben unberührt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>Write the equations to a YAML file</source>
            <translation>Die Gleichungen in eine YAML-Datei schreiben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Write the report text to a file.</source>
            <translation>Den Berichtstext in eine Datei schreiben.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>Writes the factors, their uncertainties and the report into the .pto container the bursts came from. Each save is kept as its own object, so an earlier calibration is still there afterwards. With no container, the report window offers a file instead.</source>
            <translation>Schreibt die Faktoren, ihre Unsicherheiten und den Bericht in den .pto-Container, aus dem die Bursts stammen. Jedes Speichern bleibt als eigenes Objekt erhalten, sodass eine frühere Kalibrierung danach noch vorhanden ist. Ohne Container bietet das Berichtsfenster stattdessen eine Datei an.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>Written</source>
            <translation>Geschrieben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>X Plot</source>
            <translation>X-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>X Plot Labels</source>
            <translation>X-Diagramm-Beschriftungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>X axis maximum value</source>
            <translation>Maximalwert der X-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>X axis minimum value</source>
            <translation>Minimalwert der X-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="76" />
            <source>X marginal histogram</source>
            <translation>X-Randverteilung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Y Plot</source>
            <translation>Y-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Y Plot Labels</source>
            <translation>Y-Diagramm-Beschriftungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Y axis maximum value</source>
            <translation>Maximalwert der Y-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Y axis minimum value</source>
            <translation>Minimalwert der Y-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="77" />
            <source>Y marginal histogram</source>
            <translation>Y-Randverteilung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/analysis.py" line="140" />
            <location filename="ndxplorer/app/features/analysis.py" line="1183" />
            <location filename="ndxplorer/app/features/analysis/question.view.json" line="0" />
            <location filename="ndxplorer/app/features/settings/confirm.view.json" line="0" />
            <source>Yes</source>
            <translation>Ja</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="820" />
            <source>Yes keeps it beside the photons and the burst table. No writes a separate file instead.</source>
            <translation>Ja behält sie neben den Photonen und der Burst-Tabelle. Nein schreibt stattdessen eine separate Datei.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Z Plot</source>
            <translation>Z-Diagramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings/axis_control.view.json" line="0" />
            <source>Z Plot Labels</source>
            <translation>Z-Diagramm-Beschriftungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Z axis maximum value</source>
            <translation>Maximalwert der Z-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>Z axis minimum value</source>
            <translation>Minimalwert der Z-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/loading.py" line="90" />
            <source>ZIP files</source>
            <translation>ZIP-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="57" />
            <source>acceptor anisotropy column (e.g. 'r Scatter (yellow)' or 'r Scatter (red)')</source>
            <translation>Akzeptor-Anisotropiespalte (z. B. 'r Scatter (yellow)' oder 'r Scatter (red)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="55" />
            <source>acceptor lifetime column (e.g. 'Tau (yellow)' or 'Tau (red)')</source>
            <translation>Akzeptor-Lebensdauerspalte (z. B. 'Tau (yellow)' oder 'Tau (red)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>add</source>
            <translation>hinzufügen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="816" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1057" />
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="189" />
            <source>all parameters are fixed</source>
            <translation>alle Parameter sind fixiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>auto</source>
            <translation>auto</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="375" />
            <source>auto (the BIC decides)</source>
            <translation>auto (BIC entscheidet)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="144" />
            <source>background{suffix}: {percent} % of the photons, over {rows} pixels x frames</source>
            <translation>Hintergrund{suffix}: {percent} % der Photonen, über {rows} Pixel x Frames</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="182" />
            <source>burst table lacks provenance column(s) {missing}; the selection cannot be resolved to TTTR photon intervals</source>
            <translation>In der Burst-Tabelle fehlen Herkunftsspalten ({missing}); die Auswahl kann nicht auf TTTR-Photonenintervalle zurückgeführt werden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="739" />
            <source>calibration failed</source>
            <translation>Kalibrierung fehlgeschlagen</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="677" />
            <source>cannot compile the function: {error}</source>
            <translation>Funktion kann nicht kompiliert werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1215" />
            <source>cannot evaluate equation: {error}</source>
            <translation>Gleichung kann nicht ausgewertet werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="922" />
            <source>cannot fit: {error}</source>
            <translation>Anpassung nicht möglich: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/mask_helpers.py" line="74" />
            <source>cannot write an empty mask (shape {shape}) to {path}: a TIFF needs at least one pixel</source>
            <translation>Eine leere Maske (Form {shape}) kann nicht nach {path} geschrieben werden: Ein TIFF braucht mindestens ein Pixel</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>clear</source>
            <translation>leeren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="280" />
            <source>cluster</source>
            <translation>Cluster</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>colour</source>
            <translation>Farbe</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="238" />
            <source>column for it</source>
            <translation>Spalte dafür</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="301" />
            <source>column mask does not match the bin edges</source>
            <translation>Spaltenmaske passt nicht zu den Bin-Kanten</translation>
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
            <translation>Konstanten (eine nach der Sitzung gespeicherte Kalibrierung enthält neuere)</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/container.py" line="49" />
            <source>could not commit {path}: {error}</source>
            <translation>{path} konnte nicht committet werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="215" />
            <source>could not identify the {role} column among {columns}…; pass it explicitly</source>
            <translation>Spalte {role} konnte unter {columns}… nicht erkannt werden; explizit angeben</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/container.py" line="45" />
            <source>could not open {path}: {error}</source>
            <translation>{path} konnte nicht geöffnet werden: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_background.py" line="179" />
            <source>could not read a background from {container}</source>
            <translation>Hintergrund aus {container} konnte nicht gelesen werden</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="286" />
            <source>could not write into the container ({reason})</source>
            <translation>Schreiben in den Container nicht möglich ({reason})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="358" />
            <source>curve has no equation to fit</source>
            <translation>Kurve hat keine anpassbare Gleichung</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1125" />
            <source>curve has no function to fit</source>
            <translation>Kurve hat keine anpassbare Funktion</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1127" />
            <source>curve has no parameters to fit</source>
            <translation>Kurve hat keine anpassbaren Parameter</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/gaussian_fit.view.json" line="0" />
            <source>del</source>
            <translation>löschen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="56" />
            <source>donor anisotropy column (e.g. 'r Scatter (green)')</source>
            <translation>Donor-Anisotropiespalte (z. B. 'r Scatter (green)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="54" />
            <source>donor lifetime column (e.g. 'Tau (green)')</source>
            <translation>Donor-Lebensdauerspalte (z. B. 'Tau (green)')</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="196" />
            <source>donor-excitation channel counts</source>
            <translation>Zählraten des Donor-Anregungskanals</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>dynamic z-selection</source>
            <translation>dynamische z-Auswahl</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_graph.py" line="136" />
            <source>empty expression</source>
            <translation>leerer Ausdruck</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1208" />
            <source>equation has no free parameters</source>
            <translation>Gleichung hat keine freien Parameter</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>es</source>
            <translation>es</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="340" />
            <source>failed: {error}</source>
            <translation>fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="215" />
            <source>finished</source>
            <translation>abgeschlossen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>fit</source>
            <translation>fit</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="509" />
            <source>fit failed</source>
            <translation>Anpassung fehlgeschlagen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="836" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1090" />
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="198" />
            <location filename="ndxplorer/app/features/overlays.py" line="990" />
            <source>fit failed: {error}</source>
            <translation>Anpassung fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="934" />
            <source>fitting — the data is re-derived at every step… step {n}</source>
            <translation>Anpassung läuft — die Daten werden bei jedem Schritt neu abgeleitet… Schritt {n}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="936" />
            <source>fitting… step {n}</source>
            <translation>Anpassung läuft… Schritt {n}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="140" />
            <source>gate {name}</source>
            <translation>Gate {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="237" />
            <source>gating dimension {dim} left out: this table has no {need}</source>
            <translation>Gating-Dimension {dim} ausgelassen: Diese Tabelle hat kein(e) {need}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="381" />
            <source>held</source>
            <translation>festgehalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="380" />
            <source>held at {value}</source>
            <translation>auf {value} festgehalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="119" />
            <source>histogram does not match its bin edges</source>
            <translation>Histogramm passt nicht zu seinen Bin-Kanten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_corner.view.json" line="0" />
            <source>inf</source>
            <translation>inf</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="266" />
            <source>inside vs outside the gate</source>
            <translation>innerhalb vs. außerhalb des Gates</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/package_install.py" line="339" />
            <source>installed</source>
            <translation>installiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="50" />
            <source>invalid</source>
            <translation>ungültig</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="154" />
            <source>it is open for writing in another program</source>
            <translation>sie ist in einem anderen Programm zum Schreiben geöffnet</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>lifetime</source>
            <translation>lifetime</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>load</source>
            <translation>laden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_header.view.json" line="0" />
            <source>log #</source>
            <translation>log #</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/mask_helpers.py" line="90" />
            <source>mask holds a negative class label ({label}); class labels are unsigned and 0 is background</source>
            <translation>Maske enthält ein negatives Klassenlabel ({label}); Klassenlabels sind vorzeichenlos, und 0 ist Hintergrund</translation>
        </message>
        <message>
            <location filename="ndxplorer/utils/mask_helpers.py" line="95" />
            <source>mask holds class label {label}, above the 65535 a 16-bit TIFF can carry; relabel the classes consecutively</source>
            <translation>Maske enthält Klassenlabel {label}, über den 65535, die ein 16-Bit-TIFF tragen kann; die Klassen fortlaufend neu nummerieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>measurement</source>
            <translation>measurement</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="48" />
            <source>missing output name</source>
            <translation>Ausgabename fehlt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve_fit.view.json" line="0" />
            <source>nDXplorer parameters -- a freed one moves the data, which is re-derived from the equations at every step.</source>
            <translation>nDXplorer-Parameter -- ein freigegebener verschiebt die Daten, die bei jedem Schritt aus den Gleichungen neu berechnet werden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="135" />
            <source>n_bg: the table is not a pixel table (no x pixel, y pixel); set n_bg or edit the f_bg equation</source>
            <translation>n_bg: Die Tabelle ist keine Pixeltabelle (kein x-Pixel, y-Pixel); n_bg setzen oder die f_bg-Gleichung bearbeiten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="371" />
            <source>napari is not installed</source>
            <translation>napari ist nicht installiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="414" />
            <location filename="ndxplorer/app/features/settings/report.view.json" line="0" />
            <source>ndX Report Tool</source>
            <translation>ndX-Berichtswerkzeug</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>ndX constants</source>
            <translation>ndX-Konstanten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="431" />
            <source>ndX constants:</source>
            <translation>ndX-Konstanten:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="945" />
            <source>ndX settings</source>
            <translation>ndX-Einstellungen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="944" />
            <source>ndX settings file</source>
            <translation>ndX-Einstellungsdatei</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1087" />
            <source>ndXplorer -- interactive exploration of multidimensional data (single-molecule fluorescence, sampling, any table).</source>
            <translation>ndXplorer -- interaktive Exploration mehrdimensionaler Daten (Einzelmolekülfluoreszenz, Sampling, beliebige Tabellen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="1083" />
            <source>ndXplorer Help</source>
            <translation>ndXplorer-Hilfe</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="69" />
            <source>ndXplorer shows a table of measurements -- bursts, pixels, samples -- as histograms you can gate.</source>
            <translation>ndXplorer zeigt eine Tabelle von Messungen -- Bursts, Pixel, Samples -- als Histogramme, die sich gaten lassen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="1131" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1197" />
            <source>need at least 3 matching data points</source>
            <translation>mindestens 3 passende Datenpunkte nötig</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="392" />
            <source>no 2-D histogram displayed ({error})</source>
            <translation>kein 2D-Histogramm angezeigt ({error})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="111" />
            <source>no 2-D histogram to fit</source>
            <translation>kein 2D-Histogramm zum Anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="394" />
            <source>no ChiSurf RPC connection — launch ndX with --chisurf-rpc host:port, or open it from ChiSurf, to use analysis bridges</source>
            <translation>keine ChiSurf-RPC-Verbindung — ndX mit --chisurf-rpc host:port starten oder aus ChiSurf öffnen, um die Analysebrücken zu nutzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="415" />
            <source>no columnar HDF5 table in the file</source>
            <translation>keine spaltenorientierte HDF5-Tabelle in der Datei</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="291" />
            <source>no container for this window and no path given</source>
            <translation>kein Container für dieses Fenster und kein Pfad angegeben</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="373" />
            <source>no histogram</source>
            <translation>kein Histogramm</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/mask_paint.py" line="162" />
            <source>no mask to save</source>
            <translation>keine Maske zum Speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="505" />
            <source>no parameter {name}</source>
            <translation>kein Parameter {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="187" />
            <source>no points near the click; click where the population is</source>
            <translation>keine Punkte in der Nähe des Klicks; dort klicken, wo die Population liegt</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="160" />
            <source>no points on this plane</source>
            <translation>keine Punkte auf dieser Ebene</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="409" />
            <source>no sampled states in the file</source>
            <translation>keine gesampelten Zustände in der Datei</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="454" />
            <source>no table to rank</source>
            <translation>keine Tabelle zum Ranking</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="414" />
            <source>no {target} histogram displayed ({error})</source>
            <translation>kein {target}-Histogramm angezeigt ({error})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="377" />
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>none</source>
            <translation>keine</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/selection.py" line="367" />
            <source>not in the browser</source>
            <translation>nicht im Browser</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="115" />
            <source>not installed</source>
            <translation>nicht installiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/export/report.py" line="545" />
            <source>nothing to histogram</source>
            <translation>nichts zum Histogrammieren</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="375" />
            <source>off (one global factor set)</source>
            <translation>aus (ein globaler Faktorsatz)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="376" />
            <source>on (per population whenever identifiable)</source>
            <translation>an (pro Population, wann immer identifizierbar)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="55" />
            <source>only inside ChiSurf</source>
            <translation>nur innerhalb von ChiSurf</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="210" />
            <source>only {n} point(s) in the population at the click</source>
            <translation>nur {n} Punkt(e) in der Population am Klick</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="360" />
            <source>ordering parameters</source>
            <translation>Parameter werden geordnet</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="297" />
            <source>pass 1 of 2 (backgrounds): </source>
            <translation>Durchgang 1 von 2 (Hintergründe): </translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="307" />
            <source>pass 2 of 2: </source>
            <translation>Durchgang 2 von 2: </translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="213" />
            <source>paused</source>
            <translation>pausiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="390" />
            <source>per population</source>
            <translation>pro Population</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="392" />
            <source>per population (forced; the BIC preferred shared)</source>
            <translation>pro Population (erzwungen; BIC bevorzugte gemeinsam)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="722" />
            <source>playback column</source>
            <translation>Wiedergabespalte</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="729" />
            <source>playback {key} ({error})</source>
            <translation>Wiedergabe {key} ({error})</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="248" />
            <source>population finder {method} not available ({reason}); the Gaussian mixture was used</source>
            <translation>Populationsfinder {method} nicht verfügbar ({reason}); die Gauß-Mischung wurde verwendet</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="270" />
            <source>population {label} has no displayed data</source>
            <translation>Population {label} hat keine angezeigten Daten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="381" />
            <source>populations found by HDBSCAN</source>
            <translation>von HDBSCAN gefundene Populationen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="737" />
            <source>python-docx is not installed: PNGs and CSVs were written, no DOCX.</source>
            <translation>python-docx ist nicht installiert: PNGs und CSVs wurden geschrieben, kein DOCX.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>r_A acceptor anisotropy</source>
            <translation>r_A Akzeptor-Anisotropie</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>r_D donor anisotropy</source>
            <translation>r_D Donor-Anisotropie</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="507" />
            <source>reduced χ² = {chi2r}</source>
            <translation>reduziertes χ² = {chi2r}</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="575" />
            <source>refusing to load {name} out of a data file</source>
            <translation>{name} wird nicht aus einer Datendatei geladen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>save</source>
            <translation>speichern</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="194" />
            <source>saved on another table</source>
            <translation>auf einer anderen Tabelle gespeichert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="195" />
            <source>saved on {saved} rows, {now} now</source>
            <translation>auf {saved} Zeilen gespeichert, jetzt {now}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>select</source>
            <translation>auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="449" />
            <source>selection is empty — no bursts to send to {target}</source>
            <translation>Auswahl ist leer — keine Bursts zum Senden an {target}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="604" />
            <source>selection is empty — nothing to send</source>
            <translation>Auswahl ist leer — nichts zu senden</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="390" />
            <source>shared</source>
            <translation>gemeinsam</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="835" />
            <location filename="ndxplorer/analysis/curve_fit.py" line="1081" />
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="197" />
            <source>stopped</source>
            <translation>gestoppt</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_graph.py" line="140" />
            <source>syntax error: {error}</source>
            <translation>Syntaxfehler: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>t from</source>
            <translation>t von</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>t values:</source>
            <translation>t-Werte:</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_background.py" line="174" />
            <source>the bursts carry no container, so no measured background</source>
            <translation>die Bursts tragen keinen Container, daher kein gemessener Hintergrund</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="460" />
            <source>the chosen classes are no longer available</source>
            <translation>die gewählten Klassen sind nicht mehr verfügbar</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="157" />
            <source>the click is not on a log axis's positive range</source>
            <translation>der Klick liegt nicht im positiven Bereich einer Log-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="83" />
            <source>the cloud (every populated bin)</source>
            <translation>die Wolke (jeder besetzte Bin)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="383" />
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="441" />
            <source>the curve has no parameters to fit</source>
            <translation>die Kurve hat keine anpassbaren Parameter</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="136" />
            <source>the data has no population column '{column}'</source>
            <translation>die Daten haben keine Populationsspalte '{column}'</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="197" />
            <source>the data has no population column '{column}' to fit the populations by</source>
            <translation>die Daten haben keine Populationsspalte '{column}', nach der die Populationen angepasst werden könnten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="273" />
            <source>the gate a burst falls in</source>
            <translation>das Gate, in das ein Burst fällt</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="85" />
            <source>the mean of each column</source>
            <translation>der Mittelwert jeder Spalte</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_background.py" line="182" />
            <source>the measurement stores no background</source>
            <translation>die Messung speichert keinen Hintergrund</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="151" />
            <source>the plotted range is empty (or not positive on a log axis)</source>
            <translation>der dargestellte Bereich ist leer (oder auf einer Log-Achse nicht positiv)</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/population_pick.py" line="217" />
            <source>the points are collinear: no ellipse describes them</source>
            <translation>die Punkte sind kollinear: keine Ellipse beschreibt sie</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="84" />
            <source>the population of each column</source>
            <translation>die Population jeder Spalte</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="415" />
            <source>this file is not a ChiSurf FRET calibration</source>
            <translation>diese Datei ist keine ChiSurf-FRET-Kalibrierung</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="452" />
            <source>this measurement carries no stored calibration</source>
            <translation>diese Messung enthält keine gespeicherte Kalibrierung</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="445" />
            <source>this measurement would have given {value}</source>
            <translation>diese Messung hätte {value} ergeben</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_backend.py" line="72" />
            <source>this tttrlib's calibration has no population_method option (only the Gaussian mixture)</source>
            <translation>Die Kalibrierung dieser tttrlib hat keine Option population_method (nur die Gauß-Mischung)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="238" />
            <source>this window cannot split its data by population</source>
            <translation>dieses Fenster kann seine Daten nicht nach Population aufteilen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>to</source>
            <translation>bis</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="295" />
            <source>too few points to fit in population {label} (need 3)</source>
            <translation>zu wenige Punkte zum Anpassen in Population {label} (3 nötig)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit.py" line="297" />
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="400" />
            <source>too few populated columns to fit (need 3)</source>
            <translation>zu wenige besetzte Spalten zum Anpassen (3 nötig)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_populations.py" line="279" />
            <source>too little displayed data in population {label}</source>
            <translation>zu wenige angezeigte Daten in Population {label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/curve_fit_setup.py" line="445" />
            <source>too little displayed data to fit</source>
            <translation>zu wenige angezeigte Daten zum Anpassen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="117" />
            <location filename="ndxplorer/app/features/settings.py" line="1094" />
            <source>unknown</source>
            <translation>unbekannt</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/session.py" line="155" />
            <source>unknown error</source>
            <translation>unbekannter Fehler</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_graph.py" line="170" />
            <source>unknown name(s): {names}</source>
            <translation>unbekannte(r) Name(n): {names}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>weight</source>
            <translation>Gewicht</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret.py" line="379" />
            <source>written</source>
            <translation>geschrieben</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="509" />
            <source>x and y differ in length</source>
            <translation>x und y haben unterschiedliche Länge</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>x as a function of t; every name that is not t, a definition or a maths function is a parameter.</source>
            <translation>x als Funktion von t; jeder Name, der nicht t, eine Definition oder eine mathematische Funktion ist, ist ein Parameter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>x(t) =</source>
            <translation>x(t) =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>x:</source>
            <translation>x:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>y as a function of t.</source>
            <translation>y als Funktion von t.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>y as a function of x; every other name is a parameter.</source>
            <translation>y als Funktion von x; jeder andere Name ist ein Parameter.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>y(t) =</source>
            <translation>y(t) =</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>y:</source>
            <translation>y:</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>z axis</source>
            <translation>z-Achse</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="54" />
            <source>z parameter: {name}</source>
            <translation>z-Parameter: {name}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/views/plot_controls.view.json" line="0" />
            <source>z range</source>
            <translation>z-Bereich</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/phasor_reference.py" line="114" />
            <source>{channel}: channels are numbers, e.g. 0 1</source>
            <translation>{channel}: Kanäle sind Zahlen, z. B. 0 1</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="788" />
            <source>{count} islands holding {shares} of the {n} sampled bursts; {inside} % sit clearly inside one (not on a bridge or in a tail). Score {score}: the chance that two bursts are in two different, clearly separated populations.</source>
            <translation>{count} Inseln mit {shares} der {n} gezogenen Bursts; {inside} % liegen klar innerhalb einer (nicht auf einer Brücke oder in einem Ausläufer). Score {score}: die Wahrscheinlichkeit, dass zwei Bursts in zwei verschiedenen, klar getrennten Populationen liegen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="803" />
            <source>{current} of {total} points</source>
            <translation>{current} von {total} Punkten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="566" />
            <source>{done} / {total} files</source>
            <translation>{done} / {total} Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="211" />
            <source>{done} scored</source>
            <translation>{done} bewertet</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="208" />
            <source>{done}/{total} scored ({percent} %)</source>
            <translation>{done}/{total} bewertet ({percent} %)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io_service.py" line="190" />
            <source>{ext} files</source>
            <translation>{ext}-Dateien</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>{filled_label}</source>
            <translation>{filled_label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="171" />
            <source>{gate} (drawn regions need ChiSurf's region module)</source>
            <translation>{gate} (gezeichnete Bereiche benötigen das Regionenmodul von ChiSurf)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="176" />
            <source>{gate} (unknown kind {kind!r})</source>
            <translation>{gate} (unbekannte Art {kind!r})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/prompt.view.json" line="0" />
            <source>{label}</source>
            <translation>{label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1268" />
            <source>{method} failed</source>
            <translation>{method} fehlgeschlagen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/burst_bridge.py" line="406" />
            <source>{method} failed: {error}</source>
            <translation>{method} fehlgeschlagen: {error}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1357" />
            <source>{method} installed</source>
            <translation>{method} installiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="138" />
            <source>{method} is not available in the browser: {package} needs numba's compiled code, which the browser cannot run. Use PCA for a projection here, or the desktop app for {method}.</source>
            <translation>{method} ist im Browser nicht verfügbar: {package} braucht den kompilierten Code von numba, den der Browser nicht ausführen kann. Hier PCA für eine Projektion verwenden oder die Desktop-App für {method}.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1206" />
            <source>{method} needs more columns</source>
            <translation>{method} benötigt mehr Spalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="149" />
            <source>{method} needs {package}, which is not installed.</source>
            <translation>{method} braucht {package}, das nicht installiert ist.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="143" />
            <source>{method} needs {package}, which this page did not load.</source>
            <translation>{method} braucht {package}, das diese Seite nicht geladen hat.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1332" />
            <location filename="ndxplorer/app/features/analysis.py" line="1335" />
            <source>{method} not installed</source>
            <translation>{method} nicht installiert</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1328" />
            <source>{method} unavailable</source>
            <translation>{method} nicht verfügbar</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="186" />
            <source>{name} ({rows} draws, {params} parameters)</source>
            <translation>{name} ({rows} Ziehungen, {params} Parameter)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="183" />
            <source>{name} ({rows} rows, {columns} columns)</source>
            <translation>{name} ({rows} Zeilen, {columns} Spalten)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="472" />
            <source>{name} has {n} populations; the clipboard holds {count} number(s).</source>
            <translation>{name} hat {n} Populationen; die Zwischenablage enthält {count} Zahl(en).</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/pto_reader.py" line="142" />
            <source>{name} holds no burst or image table: convert the photons with a burst search first, or point ndX at the analysis folder if one was written.</source>
            <translation>{name} enthält keine Burst- oder Bildtabelle: zuerst die Photonen mit einer Burst-Suche umwandeln oder ndX auf den Analyseordner verweisen, falls einer geschrieben wurde.</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/reader.py" line="816" />
            <source>{name} holds no columnar HDF5 table (one 1-D dataset per column, at the root or under /results)</source>
            <translation>{name} enthält keine spaltenorientierte HDF5-Tabelle (ein 1D-Datensatz pro Spalte, an der Wurzel oder unter /results)</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="445" />
            <location filename="ndxplorer/io/project_reader.py" line="135" />
            <source>{name} holds no stored sampling chain</source>
            <translation>{name} enthält keine gespeicherte Sampling-Kette</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="178" />
            <source>{name} holds {n} stored tables. Which one?</source>
            <translation>{name} enthält {n} gespeicherte Tabellen. Welche?</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/io.py" line="176" />
            <source>{name} holds {n} tables. Which one?</source>
            <translation>{name} enthält {n} Tabellen. Welche?</translation>
        </message>
        <message>
            <location filename="ndxplorer/io/fret_calibration_io.py" line="414" />
            <source>{name} is not a ChiSurf FRET calibration</source>
            <translation>{name} ist keine ChiSurf-FRET-Kalibrierung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="508" />
            <source>{name} will follow the parameter you pick (double-click, or select and Link).</source>
            <translation>{name} folgt dem gewählten Parameter (Doppelklick oder auswählen und Verknüpfen).</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="444" />
            <source>{name}: kept {value}</source>
            <translation>{name}: {value} beibehalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="206" />
            <source>{name}: one value per population, picked per burst by the column '{column}' or mixed by the assignment probabilities. Right-click for the vector's menu.</source>
            <translation>{name}: ein Wert pro Population, pro Burst gewählt über die Spalte '{column}' oder gemischt nach den Zuordnungswahrscheinlichkeiten. Rechtsklick für das Vektormenü.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="209" />
            <source>{name}: one value per population, picked per burst by the column '{column}'. Right-click for the vector's menu.</source>
            <translation>{name}: ein Wert pro Population, pro Burst gewählt über die Spalte '{column}'. Rechtsklick für das Vektormenü.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="217" />
            <source>{name}: population {label}</source>
            <translation>{name}: Population {label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/parameter_table.py" line="213" />
            <source>{name}: the value of a burst in no population.</source>
            <translation>{name}: der Wert eines Bursts in keiner Population.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1378" />
            <source>{n} column(s) written</source>
            <translation>{n} Spalte(n) geschrieben</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/vizrank_model.py" line="217" />
            <source>{n} failed</source>
            <translation>{n} fehlgeschlagen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="274" />
            <source>{n} finite rows</source>
            <translation>{n} endliche Zeilen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/settings.py" line="734" />
            <source>{n} folder(s).</source>
            <translation>{n} Ordner.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="128" />
            <source>{n} islands of {x} vs {y} written as clusters 0–{last}; {labelled} % of bursts labelled, {rest} % on ridges/outliers (−1)</source>
            <translation>{n} Inseln von {x} vs. {y} als Cluster 0–{last} geschrieben; {labelled} % der Bursts zugeordnet, {rest} % auf Graten/Ausreißern (−1)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="131" />
            <source>{n} islands of {x} vs {y} written as clusters 0–{last}; {labelled} % of bursts labelled, {rest} % outside the cores (−1)</source>
            <translation>{n} Inseln von {x} vs. {y} als Cluster 0–{last} geschrieben; {labelled} % der Bursts zugeordnet, {rest} % außerhalb der Kerne (−1)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="485" />
            <source>{n} parameters left out or merged</source>
            <translation>{n} Parameter weggelassen oder zusammengeführt</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="694" />
            <source>{n} tabulated points</source>
            <translation>{n} tabellierte Punkte</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="693" />
            <source>{n} tabulated points from {source}</source>
            <translation>{n} tabellierte Punkte aus {source}</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="146" />
            <source>{package} could not be imported, although it ships with the application. The installation is likely broken.</source>
            <translation>{package} konnte nicht importiert werden, obwohl es mit der Anwendung geliefert wird. Die Installation ist wahrscheinlich defekt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1358" />
            <source>{package} was installed but could not be imported yet.
Please restart the application and try again.</source>
            <translation>{package} wurde installiert, konnte aber noch nicht importiert werden.
Bitte die Anwendung neu starten und es erneut versuchen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/phasor_reference.py" line="132" />
            <source>{path}: channels {channels} hold no instrument response ({percent} % of the photons are flat background)</source>
            <translation>{path}: Kanäle {channels} enthalten keine Instrumentenantwort ({percent} % der Photonen sind flacher Hintergrund)</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/phasor_reference.py" line="122" />
            <source>{path}: fewer than 10 photons in channels {channels}</source>
            <translation>{path}: weniger als 10 Photonen in den Kanälen {channels}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="1336" />
            <source>{reason}

{blurb}

Install {package} now (conda, conda-forge)?</source>
            <translation>{reason}

{blurb}

{package} jetzt installieren (conda, conda-forge)?</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/gaussian_populations.py" line="177" />
            <source>{reason}: the population-wise Gaussians cannot tell the bursts apart.</source>
            <translation>{reason}: Die populationsweisen Gauß-Kurven können die Bursts nicht unterscheiden.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_rank_model.py" line="480" />
            <source>{rows} of {total} bursts sampled</source>
            <translation>{rows} von {total} Bursts gezogen</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="439" />
            <source>{rows} rows fitted, {dropped} dropped as non-finite; {share}% of the variance retained.</source>
            <translation>{rows} Zeilen angepasst, {dropped} als nicht endlich verworfen; {share}% der Varianz erhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="442" />
            <source>{rows} rows fitted; {share}% of the variance retained.</source>
            <translation>{rows} Zeilen angepasst; {share}% der Varianz erhalten.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="816" />
            <source>{share} of each burst's {k} nearest neighbours share its class ({classes}); κ = {kappa} above chance, over {valid} of {n} sampled rows.</source>
            <translation>{share} der {k} nächsten Nachbarn jedes Bursts teilen seine Klasse ({classes}); κ = {kappa} über dem Zufall, über {valid} von {n} gezogenen Zeilen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/structure.py" line="435" />
            <source>{share}% of variance: {drivers}</source>
            <translation>{share}% der Varianz: {drivers}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1230" />
            <source>{shown} / {total} rows × {columns} columns</source>
            <translation>{shown} / {total} Zeilen × {columns} Spalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/playback.py" line="444" />
            <source>{step} · index {index}</source>
            <translation>{step} · Index {index}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/curve.view.json" line="0" />
            <source>{title}</source>
            <translation>{title}</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="62" />
            <source>{total} equation(s), all valid</source>
            <translation>{total} Gleichung(en), alle gültig</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/equation_table.py" line="61" />
            <source>{total} equation(s), {bad} with problems</source>
            <translation>{total} Gleichung(en), {bad} mit Problemen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays.py" line="1232" />
            <source>{total} rows × {columns} columns</source>
            <translation>{total} Zeilen × {columns} Spalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/add_parameter.view.json" line="0" />
            <source>{value_label}</source>
            <translation>{value_label}</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/session_state.py" line="96" />
            <source>{what} (no column {columns})</source>
            <translation>{what} (keine Spalte {columns})</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/playback_export.py" line="663" />
            <source>{x} vs {y} was not ranked by Separation: show a ranked view first.</source>
            <translation>{x} vs {y} wurde nicht nach Separation bewertet: zuerst eine bewertete Ansicht anzeigen.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/projection_scores.py" line="660" />
            <source>|Spearman rho| of the pair: parameters that measure related things (E and a lifetime, a rate and its count), not populations. Parameters that are the same quantity are ranked once.</source>
            <translation>|Spearman-rho| des Paars: Parameter, die verwandte Größen messen (E und eine Lebensdauer, eine Rate und ihre Zählung), keine Populationen. Parameter derselben Größe werden einmal gerankt.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>±</source>
            <translation>±</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>α leakage</source>
            <translation>α Übersprechen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>α leakage, δ direct excitation, γ detection/QY ratio, β excitation flux ratio (Hellenkamp et al. 2018); R₀ the Förster radius.</source>
            <translation>α Übersprechen, δ direkte Anregung, γ Detektions-/QY-Verhältnis, β Anregungsflussverhältnis (Hellenkamp et al. 2018); R₀ der Förster-Radius.</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>β excitation flux</source>
            <translation>β Anregungsfluss</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>γ detection / QY</source>
            <translation>γ Detektion / QA</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>γ from</source>
            <translation>γ aus</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration.py" line="402" />
            <source>γ is held fixed: no per-population γ was written</source>
            <translation>γ bleibt fixiert: Es wurde kein populationsweises γ geschrieben</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>δ direct excitation</source>
            <translation>δ Direktanregung</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/accurate_fret/report.view.json" line="0" />
            <source>σE</source>
            <translation>σE</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>τ_A acceptor lifetime</source>
            <translation>τ_A Akzeptor-Lebensdauer</translation>
        </message>
        <message>
            <location filename="ndxplorer/analysis/fret_calibration_options.view.json" line="0" />
            <source>τ_D donor lifetime</source>
            <translation>τ_D Donor-Lebensdauer</translation>
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
            <translation>↺ Zurücksetzen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>−</source>
            <translation>−</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>∥ One scale</source>
            <translation>∥ Eine Skala</translation>
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
            <translation>■ Abbrechen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="466" />
            <source>▦ Columns</source>
            <translation>▦ Spalten</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis.py" line="465" />
            <source>▦ Columns ({count})</source>
            <translation>▦ Spalten ({count})</translation>
        </message>
        <message>
            <location filename="ndxplorer/plotting/playback.view.json" line="0" />
            <source>▶</source>
            <translation>▶</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/structure.view.json" line="0" />
            <source>▶ Run</source>
            <translation>▶ Ausführen</translation>
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
            <translation>☐ Alle abwählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>☑ Columns…</source>
            <translation>☑ Spalten…</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/analysis/columns.view.json" line="0" />
            <source>☑ Select All</source>
            <translation>☑ Alle auswählen</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>✓</source>
            <translation>✓</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>✓ Apply</source>
            <translation>✓ Anwenden</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/equations.view.json" line="0" />
            <source>✓ valid; ✗ the problem is shown under the table when the row is selected.</source>
            <translation>✓ gültig; ✗ das Problem wird unter der Tabelle angezeigt, wenn die Zeile ausgewählt ist.</translation>
        </message>
        <message>
            <location filename="ndxplorer/app/features/overlays/store_editor.view.json" line="0" />
            <source>✕ Cancel</source>
            <translation>✕ Abbrechen</translation>
        </message>
        <message>
            <location filename="ndxplorer/core/overlay_curves.py" line="72" />
            <source>Custom Equation</source>
            <translation>Eigene Gleichung</translation>
        </message>
    </context>
</TS>
