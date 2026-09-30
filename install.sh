#!/usr/bin/env bash
# Kontur — native do ~/.local albo paczka pacman przez makepkg.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

VERSION=$(python3 -c "from pathlib import Path; import re; t=Path('src/kontur/__init__.py').read_text(); print(re.search(r'__version__\\s*=\\s*\"([^\"]+)\"', t).group(1))")
MODE="native"

usage() {
  cat <<EOF
Użycie: $0 [opcje]

  (domyślnie)   instalacja native do ~/.local
  --uninstall   usuń skrót i launcher (paleta ~/.config/kontur zostaje)
  -h, --help

Zależności CachyOS / Arch:
  sudo pacman -S python python-gobject gtk4 libadwaita gobject-introspection

Paczka:
  makepkg -si
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --uninstall)
      rm -f "$HOME/.local/bin/kontur"
      rm -f "$HOME/.local/share/applications/pl.gorian.Kontur.desktop"
      rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/pl.gorian.Kontur.svg"
      if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
      fi
      echo "Kontur odinstalowany. Konfiguracja ~/.config/kontur i blok w gtk.css zostają."
      echo "Blok CSS zdejmiesz wcześniej w programie albo: kontur reset"
      exit 0
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Nieznana opcja: $1" >&2; usage >&2; exit 1 ;;
  esac
done

echo "=========================================="
echo "  Kontur ${VERSION} — native"
echo "=========================================="

missing=()
for cmd in python3; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
python3 -c "import gi" >/dev/null 2>&1 || missing+=("python-gobject")
if (( ${#missing[@]} )); then
  echo "Brakuje: ${missing[*]}"
  echo "sudo pacman -S python python-gobject gtk4 libadwaita gobject-introspection"
  exit 1
fi

mkdir -p "$HOME/.local/bin" \
  "$HOME/.local/share/applications" \
  "$HOME/.local/share/icons/hicolor/scalable/apps"

cat > "$HOME/.local/bin/kontur" << EOF
#!/usr/bin/env bash
export PYTHONPATH="${ROOT}/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m kontur "\$@"
EOF
chmod 755 "$HOME/.local/bin/kontur"

install -m644 "$ROOT/data/pl.gorian.Kontur.desktop" "$HOME/.local/share/applications/pl.gorian.Kontur.desktop"
sed -i "s|^Exec=.*|Exec=${HOME}/.local/bin/kontur|" "$HOME/.local/share/applications/pl.gorian.Kontur.desktop"
install -m644 "$ROOT/icons/kontur.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/pl.gorian.Kontur.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

echo "Gotowe. Uruchom: kontur"
echo "Zapis CSS bez okna: kontur apply"
echo "Zdjęcie bloku: kontur reset"
