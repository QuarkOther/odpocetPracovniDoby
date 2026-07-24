# Odpočet pracovní doby

Jednoduchá webová aplikace (Python / Flask): zadáš čas příchodu a dynamicky se
odpočítává pracovní doba **8 h 30 min**. Ukazuje také čas očekávaného odchodu.

## Náhled

![Náhled aplikace](Screenshot.png)

## Funkce

- **Čas příchodu** – jde napsat **ručně** (formát `H:MM`, např. `6:00`),
  nebo klikni na ikonu 🕐 a vyber hodinu a minutu na **ciferníku**.
- **Živý odpočet** s přesností na sekundy do konce pracovní doby.
  - Dokud pracovní doba ubývá, je odpočet **červený**.
  - Jakmile je odpracováno 8 h 30 min a více, změní se na **zelený** a začne
    počítat nahoru s předponou `+` (kolik už máš odpracováno navíc).
- **Přesčas (nadpracováno)** – volitelně zadej již naspořený přesčas. O jeho
  délku se zkrátí potřebná pracovní doba a zobrazí se druhý odpočet
  „S přesčasem stačí do …“.
- **Ciferník** – hodinu i minutu vybereš klikem nebo tažením. Vnější prstenec
  jsou hodiny `1–12`, vnitřní `13–23` a `00`; minuty jdou po libovolné hodnotě.
- **Uložení v prohlížeči** – zadané hodnoty se ukládají do `localStorage`,
  takže přežijí obnovení stránky. Tlačítkem **Vymazat údaje** je vyčistíš.

Příklad: příchod `6:00` → očekávaný odchod `14:30`.
S přesčasem `0:30` → stačí odejít v `14:00`.

## Spuštění

### Docker Compose
```bash
docker compose up --build
```

### Podman Compose
```bash
podman-compose up --build
```

Poté otevři <http://localhost:13400>.

> **Pozor – healthcheck podu:** healthcheck v `docker-compose.yml` míří na
> `http://localhost:13400/`. Pokud kontejner běží jako pod na jiném stroji (ne
> lokálně), je potřeba adresu `localhost` upravit na adresu daného stroje,
> například `http://192.0.2.10:13400/`.

## Lokální spuštění (bez kontejneru)
```bash
pip install -r requirements.txt
python app.py
```

## Struktura projektu

| Soubor / složka        | Účel                                                        |
| ---------------------- | ----------------------------------------------------------- |
| `app.py`               | Flask server, definice pracovní doby, běží na portu `13400` |
| `templates/index.html` | HTML šablona stránky                                         |
| `static/script.js`     | Logika odpočtu, přesčasu, ciferníku a ukládání              |
| `static/style.css`     | Vzhled                                                       |
| `Dockerfile`           | Obraz s Pythonem 3.12                                        |
| `docker-compose.yml`   | Spuštění kontejneru vč. healthchecku                        |

## Nastavení pracovní doby

Délka pracovní doby je jediná konstanta v `app.py`:

```python
WORK_MINUTES = 8 * 60 + 30  # 8 h 30 min
```
