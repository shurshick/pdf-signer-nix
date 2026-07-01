# PDF Signer Nix v0.2.7

Исправлен приоритет поиска утилит CryptoPro.

## Что исправлено

- Приложение теперь предпочитает canonical пути CryptoPro из `/opt/cprocsp/...`, а не первый попавшийся `certmgr` из `PATH`.
- Это важно для систем, где в `/usr/bin/certmgr` лежит обёртка, ссылка или другой бинарник, который ведёт себя не так, как штатный CryptoPro `certmgr`.
- За счёт этого поиск сертификатов теперь должен идти через тот же бинарник, который у тебя вручную показывает сертификат в `uMy`.

## English

Fixed CryptoPro tool lookup priority.

- The app now prefers canonical CryptoPro binaries from `/opt/cprocsp/...` instead of the first `certmgr` found in `PATH`.
- This fixes systems where `/usr/bin/certmgr` is a wrapper, symlink, or a different binary that does not behave like the real CryptoPro `certmgr`.
