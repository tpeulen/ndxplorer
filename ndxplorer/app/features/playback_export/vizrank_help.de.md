# Informative Projektionen finden

Eine Burst-Tabelle mit vierzig Parametern enthält 780 Darstellungen aus je zwei
Parametern. Dieses Fenster (**Ansicht ▸ Informative Projektionen finden…**,
direkt unter *UMAP*; der Eintrag *(z-Achse)* darunter bewertet die dritte Achse)
bewertet jede davon im Hintergrund und listet sie, die beste zuerst. **Klicken
Sie auf eine Zeile, und ndX zeigt diese Darstellung.** Wählen Sie die Achsen im
Plot von Hand, wird die passende Zeile ausgewählt; so sehen Sie, wo Ihre eigene
Wahl steht.

Die Tabelle füllt sich während der Berechnung. **Pause** hält sie an, und
**Start** setzt dort fort, wo sie angehalten hat; das Schließen des Fensters
pausiert ebenfalls, das erneute Öffnen setzt fort. Am Ende wird die beste Zeile
ausgewählt und gezeigt. Die Zeile unter der Tabelle sagt in Zahlen, was die
Bewertung der ausgewählten Zeile bedeutet.

## Bewerten nach

**Trennung** (Standard) — in welcher Ansicht zerfallen die Bursts in klar
getrennte Populationen? Das ist die smFRET-Frage: Donor-only-, Akzeptor-only-
und FRET-Spezies, die in E gegen S auseinanderliegen, eine dynamische
Population abseits der statischen FRET-Linie in E gegen τ oder im
Varianzplot. Es werden keine Labels benötigt.

Die Bursts der Ansicht werden gebinnt und geglättet; jedes Dichtemaximum mit
einem Tal ringsum ist eine **Insel**. Ein Tal zählt, wenn es tiefer ist als das
Schrotrauschen des Histogramms und die kleinere Seite mindestens 3 % der Bursts
enthält — ein Ausläufer oder ein Häufchen Ausreißer ist also keine Population.
Die Bewertung ist die **Wahrscheinlichkeit, dass zwei zufällig gezogene Bursts
in zwei verschiedenen, klar getrennten Inseln liegen**: Nur die Bursts im Kern
einer Insel zählen (nicht die auf einer Brücke zwischen zwei Populationen, in
einem Ausläufer oder im Rauschen), und ein flaches Tal zählt weniger als leerer
Raum. 0 ist eine Population — wie langgestreckt, schief oder korreliert sie auch
ist —, 0,5 zwei gleiche Inseln mit leerem Raum dazwischen, 0,18 eine 10-%-Insel
neben einem 90-%-Klumpen, 0,67 drei gleiche Inseln. Die Spalte **Inseln** sagt,
wie viele es gibt.

Bevor ein Paar bewertet wird, werden die Parameter beiseitegelegt, die Moleküle
nicht unterscheiden können: Flags (weniger als 20 Werte), die Erfassungsuhr
(erstes Photon, Makrozeit) und Faltungen eines anderen Parameters (`(1-E)*E`
von E). Parameter, die dieselbe Größe sind — *Proximity ratio* und *FRET
efficiency*, eine Rate und ihre Zählung —, werden einmal bewertet; die Zeile
nennt die anderen. Jede Achse wird so gelesen, wie der Plot sie zeichnet (eine
logarithmische Achse in Dekaden), mit entfernten Fit-Platzhaltern (`-1`, wo ein
Kanal nicht gefittet wurde, eine Grenze, an der viele Bursts liegen) und
Ausreißern, und die Achse wird mit ihrem robusten Bereich skaliert, damit ein
Parameter nicht durch seine Einheiten gewinnt.

**Bursts** — photonenarme Bursts sind breit (Schrotrauschen) und füllen die
Täler zwischen Populationen. *Nach Photonen gewichten* zählt jeden Burst mit
seinen Photonen; *Nur Bursts mit mindestens Min. Photonen* lässt die schwachen
weg. Beides braucht eine Spalte *Number of Photons*.

**Inseln auf der Karte zeigen** färbt die Karte nach den Inseln, die in der
Ansicht auf den Achsen gefunden wurden (emtk-App).

**Inseln als Cluster verwenden** versieht jeden Burst der Tabelle mit der Insel
der Ansicht auf den Achsen und schreibt die Labels als Cluster (`Cluster Label`,
ersetzt K-means/HDBSCAN-Cluster) und als Spalte `Island Label (x vs y)`. Die
Inseln werden nach der Zahl ihrer Bursts nummeriert, die größte zuerst. Das
Cluster-Drehfeld, *Farbe*, Gates, Burst-IDs speichern und die Populationsachse
von Vektorparametern arbeiten dann mit den Inseln. **Label** neben der
Schaltfläche sagt, welche Bursts eines erhalten:

- *Ganze Inseln* (Standard): jeder Burst im Einzugsgebiet der Insel -- der
  Wasserscheide der geglätteten Dichte, die die Trennungsbewertung segmentiert
  -- einschließlich des photonenarmen Schleiers zwischen den Spezies. -1 nur
  für Bursts auf dem Grat zwischen zwei Inseln (die Insel hält dort weniger als
  2/3 der geglätteten Dichte, ein Band von etwa einer halben Kernbreite), in
  einem Häufchen, das zu klein für eine Insel ist (unter 3 % der Bursts; es wird
  nicht einem Nachbarn zugeschlagen), sowie für Ausreißer und fehlende Werte.
  In der cal1-ALEX-Datei (S gegen PR) erhalten so 94 % der Bursts ein Label.
- *Nur Kerne*: nur die Bursts klar innerhalb einer Insel, 2 Sigma des
  Schrotrauschens über ihrem Tal zu den anderen; Brücken, Ausläufer und der
  Schleier bleiben -1 (37 % der cal1-Bursts mit Label).

`Cluster Probability` ist der Anteil der Insel an der geglätteten Dichte beim
Burst: 1 tief in einer Insel, fallend gegen 1/2 an einem Grat, 0 für -1. Die
Statuszeile sagt, wie viele Bursts ein Label erhielten.

**Korrelation** — welche Parameter bewegen sich gemeinsam (Spearman |ρ|,
Vorzeichen angezeigt)? Sie findet verwandte Messgrößen — E und eine
Lebensdauer, eine Rate und ihre Zählung —, keine Populationen; dieselben Regeln
zum Beiseitelegen gelten, damit doppelte Parameter die Spitze nicht überfluten.

**Klassen** — angeboten, wenn es Labels gibt: das Gate in der Auswahltabelle
(innen gegen außen), eine Population je Gate, die Cluster aus *Cluster* oder
ein z-Parameter, der Labels enthält. Liegen Bursts einer Klasse in dieser
Ansicht beieinander? Für jeden Burst werden die 10 auf dem Bildschirm
nächstgelegenen Bursts gesucht und der Anteil derselben Klasse gezählt, über
dem Zufall (κ). Parameter, auf denen ein Gate definiert ist, und daraus
berechnete werden nicht gegen dieses Gate bewertet.

## Einstellungen

**Stichprobe** — zufällig gezogene Bursts für die Bewertung. Dieselbe
Stichprobe dient jeder Zeile, damit die Zeilen Gleiches mit Gleichem
vergleichen. Die Spitze der Rangfolge ändert sich oberhalb einiger Tausend
selten.

Das Ändern einer Einstellung pausiert die Bewertung, und der nächste **Start**
bewertet mit den neuen Einstellungen neu. Das Ändern der Tabelle, der Gates
oder eines Achsenbereichs macht die Zeilen ungültig; erneutes Wählen von
**Ansicht ▸ Informative Projektionen finden…** startet eine neue Bewertung.

## Weiterführende Literatur

- [Interactive multidimensional exploration](docs/concepts/multidimensional_exploration.md)
- [Exploring & fitting multidimensional data (ndX)](docs/guides/46_ndxplorer.md)
- Edelsbrunner, Letscher & Zomorodian, *Topological persistence and
  simplification* (die Ältestenregel, die jedes Dichtemaximum mit seinem Tal
  paart) —
  [10.1007/s00454-002-2885-2](https://doi.org/10.1007/s00454-002-2885-2)
