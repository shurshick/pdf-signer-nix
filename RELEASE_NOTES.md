# PDF Signer Nix v0.2.13

Доведены отчет верификации, метаданные автора и CI-релизный workflow.

## Что исправлено

- В отчетах embedded и detached-проверки теперь заполняются данные сертификата, извлеченные из CMS.
- Исправлены русские строки в модуле верификации.
- Обновлены авторские данные: Александр Коваленко, `shurshick@bk.ru`.
- GitHub Actions больше не используют устаревающий release-action для публикации релиза.

## English

Verification reporting, author metadata and the release workflow were cleaned up.

- Embedded and detached verification reports now include certificate details extracted from CMS.
- Author metadata now uses Alexander Kovalenko / `shurshick@bk.ru`.
- The GitHub release workflow now publishes via `gh release` instead of the deprecated release action.
