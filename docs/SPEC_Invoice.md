# Számla modul — Üzleti specifikáció

---

## 1. Célkitűzés

A Számla modul a bejövő szállítói számlák teljes életciklusát kezeli: a PDF beérkezésétől a könyvelésig. A folyamat nagyrészt automatizált — mesterséges intelligencia végzi a számlák beolvasását és adatkinyerését, de a jóváhagyás és egyeztetés emberi döntést igényel.

---

## 2. A számla életciklusa

```
Feltöltés → Beolvasás → Adatkinyerés → Felülvizsgálat → Jóváhagyás → Megrendelés-egyeztetés → Könyvelés
```

### 2.1 Feltöltés

A felhasználó PDF formátumú számlákat tölt fel a rendszerbe. Lehetőségek:
- Egyedi feltöltés (drag-and-drop)
- Tömeges feltöltés (több fájl egyszerre)
- Inbox mappa importálás (egy kijelölt mappából automatikus behúzás)

### 2.2 Beolvasás (OCR)

A rendszer automatikusan felismeri a PDF szöveges tartalmát gépi látás (VLM) segítségével. A beolvasás háttérben fut, nem blokkolja a felhasználót. A felület automatikusan frissül, amint a feldolgozás kész.

Az OCR megbízhatósági mutatót ad (0–100%), amely jelzi, mennyire volt olvasható a dokumentum.

### 2.3 Adatkinyerés

A beolvasott szövegből mesterséges intelligencia nyeri ki a strukturált számlaadatokat:

| Adat | Leírás |
|------|--------|
| Szállító neve | A kibocsátó cég neve |
| Szállító adószáma | Adószám (pl. 12345678-2-42) |
| Számlaszám | A számla egyedi azonosítója |
| Számla kelte | Kibocsátás dátuma |
| Teljesítés dátuma | Szolgáltatás/szállítás dátuma |
| Fizetési határidő | Mikor kell fizetni |
| Fizetési mód | Átutalás, készpénz, stb. |
| Nettó összeg | ÁFA nélküli összeg |
| ÁFA kulcs | Alkalmazott ÁFA százalék |
| ÁFA összeg | ÁFA értéke |
| Bruttó összeg | Végösszeg ÁFA-val |
| Pénznem | HUF, EUR, stb. |
| Tételek | Soronkénti bontás (leírás, mennyiség, egységár, összeg) |

A kinyerés végén a rendszer automatikusan felismeri vagy létrehozza a szállító partnert az adószám alapján.

### 2.4 Duplikátum-szűrés

A rendszer vektor-alapú hasonlóságkereséssel ellenőrzi, hogy az adott számla korábban már be lett-e töltve. Ha duplikátumot talál, jelzi a felhasználónak a hasonlósági pontszámmal együtt.

### 2.5 Felülvizsgálat

A kinyerés után a számla felülvizsgálatra vár. A felhasználó megtekintheti:
- Az eredeti PDF-et
- A kinyert adatokat
- A megbízhatósági mutatókat mezőnként

Szükség esetén a kinyert adatok manuálisan javíthatók.

### 2.6 Jóváhagyás

A felülvizsgált számla háromszintű jóváhagyási folyamaton megy keresztül:

| Lépés | Felelős | Feladat |
|-------|---------|---------|
| 1. Ellenőrzés | Ellenőr (reviewer) | Formai és tartalmi ellenőrzés |
| 2. Osztályvezetői jóváhagyás | Osztályvezető | Üzleti relevanciájának megerősítése |
| 3. CFO jóváhagyás | Pénzügyi vezető | Végső jóváhagyás |

**Szabályok:**
- Minden lépés sorrendben következik — a következő lépés csak az előző jóváhagyása után aktiválódik
- Bármelyik lépésnél elutasítható a számla — ilyenkor a további lépések automatikusan megszűnnek
- Elutasításkor kötelező indoklást írni

### 2.7 Megrendelés-egyeztetés (Reconciliation)

A jóváhagyott számlát a rendszerben nyilvántartott megrendelésekhez (PO) kell párosítani.

**Automatikus egyeztetés:**
1. A rendszer a szállító adószáma alapján keresi a megfelelő megrendelést
2. Összehasonlítja a számla nettó összegét a megrendelés összegével
3. Ha az eltérés **±3%-on belül** van → sikeres párosítás
4. Ha az eltérés nagyobb → "eltérés" jelzés, manuális beavatkozás szükséges

**Manuális egyeztetés:**
A felhasználó kézzel kiválaszthatja a megrendelést egy listából. A rendszer ellenőrzi, hogy a pénznem megegyezik-e.

### 2.8 Könyvelés

Az egyeztetett számla könyvelésbe feladásakor három könyvelési tétel keletkezik:

| Tétel | Típus | Összeg | Leírás |
|-------|-------|--------|--------|
| 1 | Tartozik (T) | Nettó | Költség elszámolás a megrendelés főkönyvi számára |
| 2 | Tartozik (T) | ÁFA | ÁFA elszámolás (466-os számla) |
| 3 | Követel (K) | Bruttó | Szállítói kötelezettség (454-es számla) |

A könyvelési időszak a számla keltéből származik (év-hónap).

A könyvelés után:
- A számla végleges "könyvelt" státuszba kerül
- A kapcsolódó megrendelés lezárul
- A könyvelési tételek megjelennek a Controlling modul tényadatai között

---

## 3. Könyvelési sablonok

A rendszerben definiálhatók könyvelési sablonok, amelyek meghatározzák, hogy egy adott főkönyvi kódú számla milyen tartozik/követel számlákra könyvelődjön.

A sablonok mintázat-alapúak (pl. "51*" illeszkedik az 5100, 5110, stb. kódokra). Ha több sablon is illeszkedik, a legpontosabb (leghosszabb) mintázat érvényesül.

---

## 4. Felhasználói nézetek

### 4.1 Számla lista

Két paneles elrendezés:
- **Bal oldal:** Számlák táblázata — fájlnév, számlaszám, státusz, megbízhatóság, dátum
- **Jobb oldal:** A kiválasztott számla PDF-je és jóváhagyási idővonalja

A jóváhagyási idővonal vizuálisan mutatja a három lépés állapotát:
- Zöld pipa: jóváhagyva
- Piros X: elutasítva (indoklással)
- Szürke óra: várakozik

A felhasználó innen indíthatja el a feldolgozást (egyenként vagy tömegesen) és a jóváhagyásra küldést.

### 4.2 Számla feltöltés

Egyszerű drag-and-drop felület PDF fájlok feltöltésére. A feltöltés után a fájlok sorban feldolgozásra kerülnek.

### 4.3 Jóváhagyási sor

A bejelentkezett felhasználó szerepkörének megfelelő, rá váró jóváhagyások listája. Minden sorban jóváhagyás/elutasítás gomb.

### 4.4 Egyeztetés (Reconciliation)

Két paneles nézet a megrendelés-egyeztetéshez:
- **Bal oldal:** Egyeztetésre váró számlák kártyái — szállító, számlaszám, adószám, összeg
- **Jobb oldal:** PDF megjelenítő

Műveletek számánként:
1. **Automatikus egyeztetés** — a rendszer megkeresi a megfelelő megrendelést
2. **Manuális egyeztetés** — felhasználó választ a megrendelések közül
3. **Könyvelésbe feladás** — sikeres egyeztetés után

### 4.5 Könyvelés áttekintő

Két paneles nézet:
- **Bal oldal:** Könyvelt számlák táblázata összesítő kártyákkal (darabszám, nettó/ÁFA/bruttó összegek)
- **Jobb oldal:** PDF és a hozzá tartozó könyvelési tételek

### 4.6 Könyvelési tételek

A létrejött könyvelési tételek listája szűrőkkel:
- Osztály szerinti szűrés
- Időszak (hónap) szerinti szűrés
- Megjelenítés: időszak, osztály, főkönyvi szám, megrendelés szám, összeg, T/K típus, könyvelő, dátum

### 4.7 Könyvelési sablonok

Sablonok kezelése: létrehozás, módosítás, törlés. Minden sablonnál megjelenik a mintázat, a tartozik és követel számla.

---

## 5. Számla státuszok összefoglalása

| Státusz | Magyar név | Leírás | Ki látja / mit tehet |
|---------|-----------|--------|---------------------|
| Feltöltve | Feltöltve | PDF beérkezett | Feldolgozás indítható |
| Beolvasás alatt | Feldolgozás | OCR fut a háttérben | Várakozás, automatikus frissítés |
| Beolvasva | Beolvasva | OCR kész | Automatikusan továbblép |
| Kinyerés alatt | Adatkinyerés | MI dolgozza fel | Várakozás |
| Felülvizsgálatra vár | Felülvizsgálat | Kinyert adatok ellenőrizhetők | Javítás, jóváhagyásra küldés |
| Jóváhagyás alatt | Jóváhagyás | 3 lépéses workflow fut | Ellenőr → Osztályvezető → CFO |
| Jóváhagyva | Jóváhagyva | Minden lépés OK | Egyeztetésre továbblép |
| Egyeztetésre vár | Egyeztetés | PO párosítás szükséges | Auto/manuális egyeztetés |
| Egyeztetve | Egyeztetve | PO-val párosítva | Könyvelésbe feladható |
| Könyvelve | Könyvelve | Végállapot | Controlling tényadata |
| Elutasítva | Elutasítva | Jóváhagyás során elutasítva | Indoklás olvasható |
| Hiba | Hiba | Feldolgozási hiba történt | Újrafeldolgozás kérhető |

---

## 6. Üzleti szabályok

### 6.1 PO egyeztetési tolerancia

Az automatikus egyeztetés **±3%** eltérést tolerál a megrendelés összege és a számla nettó összege között. Ennél nagyobb eltérés esetén manuális beavatkozás szükséges.

### 6.2 Jóváhagyási sorrend

A három jóváhagyási lépés szigorúan egymás után következik. A következő lépés csak az előző sikeres befejezése után aktiválódik. Elutasítás esetén a teljes folyamat leáll.

### 6.3 Könyvelési egyensúly

Minden könyvelt számlánál a tartozik tételek összege (nettó + ÁFA) megegyezik a követel tétellel (bruttó): **T összeg = K összeg**.

### 6.4 ÁFA kezelés

Az alapértelmezett ÁFA kulcs 27%. A rendszer támogatja az eltérő kulcsokat is — az ÁFA kulcs a számlából kinyert adat.

### 6.5 Megrendelés lezárás

A számla könyvelésekor a kapcsolódó megrendelés automatikusan lezárul. Egy lezárt megrendeléshez nem párosítható újabb számla.

### 6.6 Duplikátum-kezelés

A rendszer figyelmeztet a potenciális duplikátumokra, de nem akadályozza meg a feldolgozást — a végső döntés a felhasználóé.

---

## 7. Jogosultságok

| Művelet | Rendszergazda | CFO | Osztályvezető | Könyvelő | Ellenőr |
|---------|:---:|:---:|:---:|:---:|:---:|
| Számla feltöltés | ✓ | ✓ | ✓ | ✓ | ✓ |
| Számla megtekintés | ✓ | ✓ | ✓ | ✓ | ✓ |
| Számla adatok módosítása | ✓ | — | — | ✓ | — |
| Számla törlése | ✓ | — | — | — | — |
| Tömeges import | ✓ | — | — | — | — |
| Tömeges feldolgozás | ✓ | — | — | — | — |
| Újrafeldolgozás | ✓ | — | — | ✓ | — |
| Jóváhagyás – 1. lépés (ellenőrzés) | ✓ | — | — | — | ✓ |
| Jóváhagyás – 2. lépés (osztályvezető) | ✓ | — | ✓ | — | — |
| Jóváhagyás – 3. lépés (CFO) | ✓ | ✓ | — | — | — |
| Könyvelési sablon kezelés | ✓ | — | — | ✓ | — |
| Könyvelési sablon törlés | ✓ | — | — | — | — |

---

## 8. Integráció a Controlling modullal

A számla modul a controlling modul tényadatainak forrása. Amikor egy számla könyvelésbe kerül:

1. A könyvelési tételek (tartozik) automatikusan megjelennek a Controlling modul "Tény" oszlopában
2. Az összesítés osztály, főkönyvi kategória és hónap szerint történik
3. Az ÁFA (466) és szállítói kötelezettség (454) tételek nem jelennek meg a P&L-ben — kizárólag a költségszámlák (árbevétel, közvetlen költség, működési költség, stb.)

Ezáltal a tervezett és a tényleges költségek automatikusan összehasonlíthatók a controlling felületen.

---

## 9. Partnerek

A szállítói partnerek automatikusan keletkeznek a számlafeldolgozás során (adószám alapján). Egy partner lehet:
- **Szállító** — bejövő számlák kibocsátója
- **Vevő** — kimenő számlák címzettje
- **Mindkettő**

A partner nyilvántartja a nevét, adószámát, bankszámlaszámát, címét és elérhetőségét, valamint a hozzá tartozó számlák számát és összértékét.
