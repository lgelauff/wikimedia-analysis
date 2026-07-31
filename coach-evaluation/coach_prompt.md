# Coach prompt — evaluatie 10Guillot (Gio)

*Werkinstructie voor de coach-evaluatie die volgt uit
[Deblokkade 10Guillot (3)](https://nl.wikipedia.org/wiki/Wikipedia:Arbitragecommissie/Zaken/Deblokkade_10Guillot_(3)).
De mentee is 10Guillot.*

## Doel

Vaststellen of Guillot als constructieve Wikipediaan kan functioneren, en of
hij alle door hem geschreven artikelen met deugdelijke bronnen heeft hersteld.
De norm uit de uitspraak:

> Hij mag geen nieuwe artikelen aanmaken totdat de problemen met al zijn oude,
> door hem gestarte artikelen zijn opgelost en in ieder geval niet eerder dan de
> coach en moderators daar toestemming voor hebben gegeven.

De oorspronkelijke klacht betrof **neutraliteit (NPOV), origineel onderzoek
(OO) en verifieerbaarheid (VER)**; "opgelost" wordt dus primair gemeten aan de
aanwezigheid en kwaliteit van bronnen en aan beleidsconformiteit.

## Werkwijze

**Spoor 1 — artikelpas.** Eén pas over álle artikelen die Gio startte of
significant uitbreidde (`articles_under_review.md`). Per artikel:

1. **Wat heeft hij toegevoegd sinds de arbcom-uitspraak?** (diffs van zijn
   bewerkingen sinds de uitspraakdatum)
2. **Bevatten die verbeteringen bronnen?** (toegevoegde `<ref>`-verwijzingen,
   literatuur, externe links — en zijn ze deugdelijk: onafhankelijk,
   gepubliceerd, dekkend voor de claim)
3. **In hoeverre zijn ze in lijn met beleid?** (NPOV / geen OO / VER)
4. **Waar klaagden mensen over?** (artikeloverleg en projectpagina's sinds de
   uitspraak; ook eerdere klachten die onopgelost bleven)

Oordeel per artikel: `opgelost` / `verbeterd, nog niet opgelost` /
`onveranderd` / `verslechterd`, met één regel motivering en de belangrijkste
diff(s) als bewijs.

**Spoor 2 — gedragspas.** Interactie sinds de deblokkade
(`interactions_since_unblock.md`): reageert hij constructief op feedback van
mentor, moderatoren en gemeenschap; volgt hij aanwijzingen op; escaleert of
de-escaleert hij bij onenigheid.

**Eindoordeel.** Pas als spoor 1 over de volle breedte "opgelost" laat zien én
spoor 2 constructief gedrag laat zien, is er grond voor de toestemming
(coach + moderators) waar de uitspraak om vraagt. Twijfelgevallen expliciet
benoemen — het voordeel van de twijfel is aan de gemeenschap, niet aan de
evaluatie.

## Hulpmiddelen

| Stap | Gereedschap |
|---|---|
| Populatie bepalen | `collect_articles.py` → `articles_under_review.md` |
| Diffs + brontellingen sinds uitspraak | `evaluate_articles.py` → `evaluation/` per artikel |
| Klachten verzamelen | `evaluate_articles.py` (artikeloverleg) + handmatige controle projectpagina's |
| Gedrag sinds deblokkade | `collect_interactions.py` → `interactions_since_unblock.md` |

De scripts verzamelen en ordenen; het oordeel in de beoordelingskolommen is en
blijft mensenwerk.
