# PDF Signer Nix v0.2.5

Это уже не косметика, а реальный фикс поиска сертификатов.

## Что исправлено

- Исправлен разбор вывода `certmgr` на Linux для реальных русских хранилищ CryptoPro.
- Приложение теперь корректно понимает поля `Субъект`, `Издатель`, `Серийный номер`, `Контейнер`, `Имя провайдера`, `Выдан`, `Истекает`, `Ссылка на ключ`.
- Добавлен более устойчивый декод вывода CryptoPro: `utf-8`, `cp1251`, `cp866`.
- Если `certmgr` печатает сертификаты в `stderr` и даже возвращает неидеальный код выхода, приложение всё равно забирает сертификаты, если они реально есть в выводе.

## Почему прошлый релиз был плохим

Он исправлял только часть случаев и не покрывал реальный вывод `certmgr` из Linux-систем с русской локалью. По факту сертификаты могли быть в системе, но список в приложении оставался пустым.

## English

This release fixes real-world CryptoPro certificate discovery on Linux.

- Fixed parsing of actual Russian `certmgr` output.
- Added more robust CryptoPro output decoding: `utf-8`, `cp1251`, `cp866`.
- The app now accepts certificate listings from `stderr` and still parses them even when `certmgr` returns a non-ideal exit code.
