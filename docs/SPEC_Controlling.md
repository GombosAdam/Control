# Controlling modul — Üzleti specifikáció

---

## 1. Célkitűzés

A Controlling modul a cég pénzügyi tervezését és végrehajtásának nyomon követését biztosítja. Lehetővé teszi éves és havi szintű budget tervezést, a terv és a tényadatok összehasonlítását, valamint a pénzügyi lekötések (megrendelések) figyelését.

---

## 2. Alapfogalmak

### 2.1 Tervezési időszak

Egy jól körülhatárolt időszak, amelyre a pénzügyi terv vonatkozik. Jellemzően egy teljes naptári év (január–december), de lehet rövidebb is.

Minden tervsor kötelezően tartozik egy tervezési időszakhoz — nem létezhet "gazdátlan" tervadat.

Egy tervezési időszak lehet:
- **Budget** (éves terv) — az elfogadott költségvetés
- **Forecast** (előrejelzés) — módosított várható értékek az év során

### 2.2 Szcenárió

Egy tervezési változat (pl. "Alap", "Optimista", "Pesszimista"). Ugyanarra az időszakra több szcenárió is készülhet, hogy a vezetőség összehasonlíthassa a különböző forgatókönyveket. Egy szcenárió az alapértelmezett.

### 2.3 Tervsor (Budget Line)

Egyetlen havi tervezett összeg, amely egy osztályhoz, egy főkönyvi kategóriához és egy hónaphoz tartozik.

**Példa:** "IT osztály – Közvetlen költség – 2024. március – 14 700 000 Ft"

Egy tervsor három állapotban lehet:

| Állapot | Jelentés |
|---------|----------|
| **Tervezet (draft)** | Szabadon szerkeszthető, a tervezett összeg módosítható |
| **Jóváhagyott (approved)** | Elfogadva, már nem szerkeszthető, de zárolható |
| **Zárolt (locked)** | Végleges, módosíthatatlan — lezárt időszakhoz tartozik |

Átmenet: Tervezet → Jóváhagyott → Zárolt (csak előre, visszafelé nem).

### 2.4 P&L kategóriák

A rendszer a következő eredménykimutatás (P&L) struktúrát használja:

| Kategória | Magyar név |
|-----------|------------|
| Árbevétel (Revenue) | Értékesítésből származó bevétel |
| Közvetlen költség (COGS) | Az értékesített termék/szolgáltatás közvetlen költsége |
| Működési költség (OpEx) | Általános működési költségek |
| Értékcsökkenés (D&A) | Tárgyi eszközök és immateriális javak amortizációja |
| Pénzügyi ráfordítás (Interest) | Bankhitelek kamata és egyéb pénzügyi költségek |
| Adó (Tax) | Társasági adó és egyéb adók |

---

## 3. P&L waterfall (Eredménykimutatás)

A rendszer fő nézete a P&L waterfall, amely a következő struktúrát követi:

```
  Árbevétel (Revenue)
- Közvetlen költségek (COGS)
= Bruttó profit (Gross Profit)                  margin%
- Működési költségek (OpEx)
= EBITDA                                         margin%
- Értékcsökkenés (D&A)
= Működési eredmény (EBIT)                      margin%
- Kamatköltség (Interest)
= Adózás előtti eredmény (PBT)                  margin%
- Adó (Tax)
= Nettó eredmény (Net Income)                   margin%
```

**Megjelenítés soronként:**

| Oszlop | Tartalom |
|--------|----------|
| TERV | Az adott kategória tervezett összege |
| TÉNY | A könyvelésben rögzített tényleges összeg |
| ELTÉRÉS | Terv − Tény (pozitív = alulteljesítés, negatív = túlköltekezés) |
| VAR % | Eltérés százalékban |

A margin % mindig az árbevételhez viszonyított arány.

A kategória sorok kinyithatók — alattuk megjelennek az egyes osztályok tervsorai részletezve.

---

## 4. Felhasználói nézetek

### 4.1 Controlling áttekintő

Összefoglaló dashboard, amely mutatja:
- **Teljes budget** — az összes jóváhagyott/zárolt tervsor összege
- **Lekötött** — megrendelésekkel lefoglalt összeg
- **Elköltött** — ténylegesen könyvelt összeg
- **Szabad keret** — budget − lekötött − elköltött

Osztályonkénti bontásban, kihasználtsági jelzéssel:
- Zöld: 70% alatt
- Narancs: 70–90%
- Piros: 90% felett

### 4.2 P&L Tervezés

A rendszer legösszetettebb felülete, amely az alábbi funkciókat kínálja:

**Szűrők és navigáció:**
- Időszak váltás: hónap, negyedév vagy éves nézet
- Tervezési időszak kiválasztása (kötelező — időszak nélkül nincs adat)
- Budget / Forecast váltás
- Szcenárió kiválasztása
- Osztály szűrő
- Státusz szűrő (tervezet / jóváhagyott / zárolt)

**KPI sáv:** Árbevétel, Bruttó profit, EBITDA, Nettó eredmény — terv, tény és eltérés értékekkel.

**Tervsorok szerkesztése:**
- Tervezet (draft) státuszú sorok összege közvetlenül szerkeszthető a táblázatban
- Jóváhagyott és zárolt sorok csak olvashatók

**Tömeges műveletek (kijelölt tervezet sorokon):**
- **Jóváhagyás** — validáció: negatív összeg → hiba, nulla összeg → figyelmeztetés
- **Zárolás** — véglegesítés
- **Százalékos módosítás** — pl. az összes kijelölt sor +10%-kal emelése

**Másolási lehetőségek:**
- Periódus másolás: egy hónap tervadatainak átvétele másik hónapba, opcionális %-os módosítással
- Éves terv létrehozása: előző év adatai alapján növekedési szorzóval
- Forecast készítés: budget adatokból előrejelzés, módosítási %-kal
- Szcenárió másolás: meglévő szcenárió lemásolása %-os eltéréssel

**Megjegyzések:** Minden tervsorhoz megjegyzés fűzhető, amely a kollaboratív tervezést támogatja.

**Audit trail:** Minden tervsor változásának nyomon követése — ki, mikor, mit módosított (létrehozás, jóváhagyás, zárolás, összeg módosítás, másolás).

**Waterfall diagram:** Vizuális oszlopdiagram a P&L struktúráról.

### 4.3 Terv vs. Tény

Részletes összehasonlító nézet:
- Összesítő kártyák: tervezett, tényleges, eltérés
- Osztály és hónap szerinti szűrés
- Vizuális összehasonlítás (bar chart)
- Tábla soronkénti eltéréssel — színkódolás: zöld ha a tény a terv alatt, piros ha felette

### 4.4 Lekötések

A nyitott megrendelések (Purchase Order) áttekintése:
- Összes lekötés összege és darabszáma
- Szűrés osztály szerint
- Megrendelés szám, osztály, szállító, összeg, státusz, dátum

---

## 5. Üzleti szabályok

### 5.1 Tervezési időszak kötelezősége

Minden tervsor kötelezően egy tervezési időszakhoz tartozik. Időszak nélkül a P&L nézet üres — nem jeleníthetők meg "gazdátlan" adatok.

### 5.2 Tény adatok forrása

A "tény" oszlop adatai kizárólag a számlafeldolgozási folyamatból (számla modul) származnak. A könyvelt számlatételek automatikusan aggregálódnak osztály, főkönyvi kategória és hónap szerint.

A tényadatok közvetlenül nem módosíthatók a controlling felületen — kizárólag a számla könyvelésen keresztül keletkeznek.

### 5.3 Szezonalitás

A havi tervek szezonális szorzókkal készülnek az éves alapösszegből:

| Hónap | Szorzó | Hónap | Szorzó |
|-------|--------|-------|--------|
| Január | 0,85 | Július | 1,10 |
| Február | 0,90 | Augusztus | 1,05 |
| Március | 1,00 | Szeptember | 1,00 |
| Április | 1,05 | Október | 0,95 |
| Május | 1,10 | November | 0,90 |
| Június | 1,15 | December | 0,80 |

### 5.4 Éves növekedés

Éves tervek között növekedési szorzó alkalmazható. Például a 2024-es terv a 2023-as +8%-a, a 2025-ös a 2024-es +6%-a.

### 5.5 Budget fedezet

Egy tervsorhoz tartozó megrendelések összértéke nem haladhatja meg a tervezett összeget. A rendszer nyomon követi:
- **Tervezett** — a jóváhagyott budget összeg
- **Lekötött** — aktív megrendelések összege
- **Elköltött** — könyvelt tételek összege
- **Szabad keret** — tervezett − lekötött − elköltött

---

## 6. Jogosultságok

| Szerepkör | P&L megtekintés | Tervsor szerkesztés | Jóváhagyás | Zárolás |
|-----------|----------------|---------------------|------------|---------|
| Rendszergazda | ✓ | ✓ | ✓ | ✓ |
| CFO | ✓ | ✓ | ✓ | ✓ |
| Osztályvezető | ✓ | ✓ | ✓ | — |
| Könyvelő | ✓ | — | — | — |
| Ellenőr | ✓ | — | — | — |

---

## 7. Osztályok

A rendszerben 5 osztály működik:

| Kód | Név |
|-----|-----|
| IT | Informatika |
| MKT | Marketing |
| OPS | Operáció |
| HR | HR |
| SALES | Értékesítés |

Minden osztálynak van egy felelős vezetője (osztályvezető).
