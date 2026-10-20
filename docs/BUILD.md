# Сборка Dark Souls: Reforged

## Структура

- `work/` — сборка: `build.py` читает ванильные файлы игры и пишет мод в `work/out/h`, `install.py` копирует его
  в `ModEngine2/FirelinkHub`. По одному `hub_*.py` на систему, в шапке каждого — что он меняет.
  `souls.py`, `msb.py`, `emevd.py`, `tae.py`, `luabnd.py`, `tpf.py` — форматы файлов.
- `work/dll/firelinkhub.c` — DLL (эстус, травы, респек, перенос между кострами), собирается zig из `build.py`.
- `work/hub_bossai.py` — ИИ боссов: декомпиляция Lua, правка, сборка своим luac 5.0.3.
- `work/audit.py` — проверка после сборки: флаги мода против всех флагов игры, сущности карт, меню.
- `work/icons/{herbs,spells,escape_death}`, `work/icons/estus_shard.png` — сгенерированные иконки предметов.
- `work/make_readme_art.py` — баннер и подвал README (`docs/art/`).

## Чего нет в репозитории (нужно для сборки)

- `work/orig/` — ванильные файлы игры: `GameParam_vanilla.parambnd.dcx`, `paramdef.paramdefbnd.dcx`,
  `msg/<lang>/item.msgbnd.dcx` и `menu.msgbnd.dcx`.
- `tools_dl/` — `esdtool/esdtool-v0.5.1`, `zig/zig-x86_64-windows-0.16.0`, `ds2icons/*.png`,
  `spell_icons/*.png`, `escape_death/Escapedeath.png`;
  `lua50/luac50.exe` — luac 5.0.3 с lua.org, собранный 64-битным через zig (ИИ боссов):
  `zig cc -target x86_64-windows-gnu -O2 -w -DLUA_OPNAMES -Iinclude -Isrc -o ../luac50.exe src/*.c (без lua.c)
  src/luac/luac.c src/luac/print.c src/lib/lauxlib.c`;
  `SoulsAI/` (очищенные скрипты ИИ DS1 от Grimrukh, справка), `paramreloader/` (DS1R Param Reloader),
  `blender/io_soulstruct-3.2.1.zip` (аддон для Blender 5.2).
- `~/.reforged/venv` — Python с `soulstruct` 2.6.0 и `soulstruct-havok` от Grimrukh (короткий путь: в путь
  проекта их длинные имена файлов не помещаются). `hub_bossai.py` берёт оттуда DSLuaDecompiler.

## Сборка

```
cd work
python build.py
python audit.py      # должно быть "problems: 0"
python install.py
```

- `python build.py --release` — без меню отладки у костров (по умолчанию оно есть).
- `--no-bossai` — ИИ боссов как в оригинале (если игра не примет пересобранный скрипт).
- Не пересобирать при запущенной игре (DLL занята). В кооперативе у обоих игроков должна быть одна сборка.
