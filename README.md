# Dark Souls: Reforged

A Dark Souls Remastered mod (working name FirelinkHub), played with Seamless Co-op + ModEngine2.
The plan is in [docs/Dark_Souls_Reforged_GDD.docx](docs/Dark_Souls_Reforged_GDD.docx); the test route in
[FirelinkHub_mod/ПРОВЕРКА.md](FirelinkHub_mod/ПРОВЕРКА.md), playthrough notes in
[FirelinkHub_mod/ЗАМЕЧАНИЯ.md](FirelinkHub_mod/ЗАМЕЧАНИЯ.md).

## Layout

- `work/` — the build: `build.py` reads the vanilla game files and writes the mod into `work/out/h`,
  `install.py` copies it into `ModEngine2/FirelinkHub`. One `hub_*.py` per feature, the docstring at the
  top says what it changes. `souls.py`, `msb.py`, `emevd.py`, `tae.py`, `luabnd.py`, `tpf.py` — file formats.
- `work/dll/firelinkhub.c` — the DLL (estus cap, respec, ...), built with zig by `build.py`.
- `work/icons/{herbs,spells,escape_death}`, `work/icons/estus_shard.png` — generated item icons.

## Not in the repo (needed to build)

- `work/orig/` — vanilla files from the game: `GameParam_vanilla.parambnd.dcx`, `paramdef.paramdefbnd.dcx`,
  `msg/<lang>/item.msgbnd.dcx` and `menu.msgbnd.dcx`.
- `tools_dl/` — `esdtool/esdtool-v0.5.1`, `zig/zig-x86_64-windows-0.16.0`, `ds2icons/*.png`,
  `spell_icons/*.png`, `escape_death/Escapedeath.png`.

## Build

```
cd work
python build.py
python install.py
```

`python build.py --release` builds without the bonfire debug menu (hub_debug.py); the default build has it.

Don't rebuild while the game runs (the DLL is locked), and in co-op both players need the same build.
