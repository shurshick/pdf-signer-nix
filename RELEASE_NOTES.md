# PDF Signer Nix v0.2.9

Исправлена проверка подписанного PDF после выпуска `v0.2.8`.

## Что исправлено

- Исправлена проверка detached и встроенных PDF-подписей.
- Вместо несуществующего для Linux-версии `csptest` ключа `-content` теперь используется корректный вызов `csptest -sfsign -verify -detached -in <данные> -signature <подпись>`.
- Из-за этого больше не должно быть ошибки `invalid option -- 'content'` при проверке встроенно подписанного PDF.

## English

Fixed PDF signature verification after `v0.2.8`.

- Replaced the invalid Linux `csptest -content` call with the correct detached verification syntax: `-detached -in <content> -signature <signature>`.
