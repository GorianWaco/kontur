# Maintainer: GorianWaco
# https://github.com/GorianWaco/kontur
#
# Lokalnie z katalogu projektu:
#   makepkg -si

pkgname=kontur
pkgver=0.4.0
pkgrel=1
pkgdesc="Kolory, obrys, czcionki i geometria okien GTK bez przezroczystości"
arch=('any')
url="https://github.com/GorianWaco/kontur"
license=('MIT')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'gobject-introspection'
)

source=()
sha256sums=()

package() {
    local root
    if [[ -f "$srcdir/${pkgname}-${pkgver}/src/kontur/__init__.py" ]]; then
        root="$srcdir/${pkgname}-${pkgver}"
    else
        root="$startdir"
    fi

    local share="$pkgdir/usr/share/kontur"
    install -dm755 "$share" \
        "$pkgdir/usr/bin" \
        "$pkgdir/usr/share/applications" \
        "$pkgdir/usr/share/licenses/$pkgname" \
        "$pkgdir/usr/share/doc/$pkgname" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps" \
        "$pkgdir/usr/share/metainfo"

    cp -a "$root/src/kontur" "$share/kontur"
    find "$share" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find "$share" -type f -name '*.pyc' -delete 2>/dev/null || true

    install -Dm755 /dev/stdin "$pkgdir/usr/bin/kontur" <<'EOF'
#!/bin/sh
export PYTHONPATH="/usr/share/kontur${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m kontur "$@"
EOF

    install -Dm644 "$root/data/pl.gorian.Kontur.desktop" \
        "$pkgdir/usr/share/applications/pl.gorian.Kontur.desktop"
    sed -i 's|^Exec=.*|Exec=/usr/bin/kontur|' \
        "$pkgdir/usr/share/applications/pl.gorian.Kontur.desktop"
    install -Dm644 "$root/icons/kontur.svg" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/pl.gorian.Kontur.svg"
    install -Dm644 "$root/data/pl.gorian.Kontur.metainfo.xml" \
        "$pkgdir/usr/share/metainfo/pl.gorian.Kontur.metainfo.xml"
    install -Dm644 "$root/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 "$root/README.md" "$pkgdir/usr/share/doc/$pkgname/README.md"
}
