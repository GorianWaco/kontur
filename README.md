# Kontur

Kolory, obrys, cień, czcionki i geometria okien **GTK 3, GTK 4 i Libadwaita** na GNOME (CachyOS / Arch). Każdy kolor jest `#RRGGBB`. Nie ma `rgba()`, rozmycia tła ani przezroczystości okna.

Kontur nie maluje paska GNOME Shell, Firefoksa, Electrona ani Qt. Te programy nie czytają `gtk.css`.

## Zależności

W oficjalnych repozytoriach, bez AUR:

```bash
sudo pacman -S python python-gobject gtk4 libadwaita gobject-introspection
```

Paczka lokalna (opcjonalnie, potrzebny `base-devel`):

```bash
makepkg -si
```

## Uruchomienie

Z katalogu projektu, bez instalacji:

```bash
./run
```

Launcher w `~/.local/bin`:

```bash
git clone https://github.com/GorianWaco/kontur.git ~/Projekty/kontur
~/Projekty/kontur/install.sh
kontur
```

`kontur apply` zapisuje ostatnią paletę (albo Adwaitę jasną, jeśli nic jeszcze nie zapisano) do CSS. `kontur reset` wyjmuje tylko blok Kontur.

## Co jest w plikach

| Plik | Rola |
| --- | --- |
| `src/kontur/cssgen.py` | Szablon CSS GTK 4 / Libadwaita i GTK 3 |
| `src/kontur/colors.py` | Paleta, zakresy, zestawy |
| `src/kontur/apply.py` | Wpisanie bloku między `kontur:begin` a `kontur:end` |
| `src/kontur/window.py` | Okno z próbnikiem i suwakami |
| `~/.config/gtk-4.0/gtk.css` | Aplikacje GTK 4 i Libadwaita |
| `~/.config/gtk-3.0/gtk.css` | Starsze aplikacje GTK 3 |
| `~/.config/kontur/config.json` | Ostatni wybór |

Tekst spoza bloku Kontur w `gtk.css` zostaje. Pierwsza podmiana niepustego pliku bez tego bloku zostawia kopię `gtk.css.kontur-bak` obok.

Podgląd w samym Konturze jest natychmiastowy. Zapis na dysk idzie chwilę po ruchu suwaka albo po **Zastosuj**. Już otwarty program czasem trzeba uruchomić ponownie, jeśli nie podłapie pliku sam.

## Sekcje

Ustawienia są ułożone według miejsca w oknie, a nie według rodzaju suwaka. Po lewej: zestaw, okno, pasek tytułu, pasek boczny, karty, widok i pola, menu, okna dialogowe, akcent, suwaki, stany, czcionki, ikony i kursory, opcje i podgląd. Kolor i wymiary jednego miejsca są na tej samej stronie. Język interfejsu jest w opcjach.

Pasek tytułu i pasek boczny mogą dostać własny obrazek tła. Kolor tego miejsca zostaje pod obrazkiem. Cień okna i cień paska tytułu mają osobny kolor.

Ikony i kursor zmieniają się tylko w programach GTK, przez `gtk-icon-theme-name` i `gtk-cursor-theme-name` w `settings.ini`. Pasek GNOME zostaje przy swoim motywie. Pusty wybór przywraca poprzednią wartość.

## Czcionki

Pusta nazwa i rozmiar 0 zostawiają czcionkę systemu. Da się wybrać czcionkę interfejsu, czcionkę o stałej szerokości i czcionkę tytułu. Rozmiar i pogrubienie tytułu zostają przy pasku tytułu.

## Kolory

Zmienne Libadwaita ustawiane na `window` (zawsze kryjące):

`--window-bg-color`, `--window-fg-color`, `--view-bg-color`, `--view-fg-color`, `--sidebar-bg-color`, `--sidebar-fg-color`, `--card-bg-color`, `--card-fg-color`, `--dialog-bg-color`, `--dialog-fg-color`, `--popover-bg-color`, `--popover-fg-color`, `--headerbar-bg-color`, `--headerbar-fg-color`, `--headerbar-backdrop-color`, `--accent-bg-color`, `--accent-fg-color`, `--accent-color`, `--destructive-bg-color`, `--success-color`, `--warning-color`, `--error-color`, `--border-color`, `--window-radius`.

`--border-opacity` jest ustawione na `1`. Odcienie, których Libadwaita normalnie miesza z przezroczystością (`--headerbar-shade-color` i podobne), dostają ten sam kryjący kolor co linia, a cień paska tytułu jest wyłączony i zastąpiony pełnym obrysem.

GTK 3 dostaje `@define-color` (`theme_bg_color`, `theme_fg_color`, `borders`, `theme_selected_bg_color` i reszta zestawu Adwaita) plus reguły `decoration`, `headerbar`, `entry`, `scrollbar`, `scale`.

## Geometria

- Narożniki: 0–48 px (`--window-radius` i `border-radius`). Okno zmaksymalizowane i przypięte do krawędzi zostaje kanciaste.
- Pasek tytułu: wysokość, odstęp w poziomie i w pionie, górne narożniki, grubość i kolor linii, rozmiar i pogrubienie tytułu, rozmiar i odstęp przycisków oraz miękki cień pod paskiem.
- Obrys: 1–4 px, osobny kolor aktywnego i nieaktywnego okna. To pełna linia `0 0 0 Npx #kolor`.
- Cień okna: przesunięcie, rozlanie, rozmycie oraz dwa kanały alfa (aktywne okno i okno w tle).
- Tło okna może dostać obrazek (wypełnienie, zmieszczenie, kafelek albo środek). Kopia ląduje w `~/.config/kontur/backgrounds`.
- Palety zapisujesz pod własną nazwą w `~/.config/kontur/palettes.json`.

Nieaktywny pasek tytułu w Libadwaita jest normalnie przygaszany filtrem. Kontur ten filtr zdejmuje (`filter: none`), żeby treść paska została kryjąca.

## Testy

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
