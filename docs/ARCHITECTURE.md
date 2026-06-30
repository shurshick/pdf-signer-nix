# Architecture

`pdf-signer-nix` состоит из независимых слоев:

- `crypto.py` - обнаружение и вызов инструментов CryptoPro;
- `pdf_tools.py` - штамп PDF, overlay, smart placement;
- `workflow.py` - сценарий подписи;
- `gui.py` - обычный desktop UI на PySide6/Qt;
- `scripts/` - сборка PyInstaller, DEB, RPM.

Такой подход оставляет runtime-пакеты простыми: пользователь получает один бинарник и desktop-файл, а Python/Qt-зависимости уже встроены.
