# 10 — Leftovers

**Status: verified** for everything with an address or a byte count.
Reproduced by [`tools/leftovers.py`](../tools/leftovers.py) and
[`tools/script_scan.py`](../tools/script_scan.py); output in
[`reports/leftovers.txt`](../reports/leftovers.txt) and
[`reports/script-debug.txt`](../reports/script-debug.txt).

A retail disc from 1997, packed to 0.07% slack, with almost the entire
development scaffolding still bolted to the inside.

## `\DEBUG.TXT` — a switch the disc does not carry

The first thing `main()` does, before the GPU is initialised, is ask the CD
for a file that is not there:

```
801502F4  addiu a0, sp, 16
801502FC  lui   a1, 0x800A
80150300  addiu a1, a1, 20388        ; "\DEBUG.TXT;1"
8015030C  jal   0x8015DF8C           ; search the file system
80150314  beq   v0, zero, 0x80150320
80150318  addiu v1, zero, 4          ; not found -> 4
8015031C  addiu v1, zero, 8          ; found     -> 8
80150328  sh    v1, 19152(v0)        ; -> 0x80174AD0
```

`\DEBUG.TXT;1` is not on the disc, so the word at `0x80174AD0` is always 4.
The string appears nowhere else in the executable and no other code writes
that address before this runs. Whatever the 8 unlocks, the mechanism to reach
it survived onto every pressed copy: put a file called `DEBUG.TXT` in the root
of a rebuilt image and the flag changes.

## `DBG.D` — a debug save, shipped next to the real one

`DAT/INI.D` and `DAT/DBG.D` are 797 and 705 bytes on disc, both method-3
blocks, and both decompress to **2,804 bytes of identical structure**: ten
character records of 0xAC bytes from `+0x0C`, then five Swordian records of
0x5C from `+0x934`.

They differ in 270 places totalling 526 bytes.

| | `INI.D` | `DBG.D` |
|---|---|---|
| byte at `+0x08` | 20 | 10 |
| Stahn's three 16-bit stat fields | 142 | **3000** |
| Rutee | 434 | 3000 |
| Leon | 712 | 3000 |
| Woodrow | 904 | 3000 |
| Philia | 647 | 3000 |
| Mary | 493 | 3000 |
| Johnny | 1304 | 3000 |
| Chelsea | 213 | 3000 |
| Mighty | 2935 | 3000 |
| Lilith | 649 | 3000 |
| 16 bytes at `+0x94` | all zero | `01 02 05 04 06 07 03 08 09 0A 0B 0D 0E 0C 0F 10` |

`INI.D` is the shipping new-game template — every character at their real
starting values, and an empty roster. `DBG.D` is the same file with every
character flattened to 3000 and the roster fully populated: the state a
developer starts from to test anything that is not the first hour.

The file registry gives them ids 1250 and 1251, side by side, both loaded
through the same `\DAT\%s;1` path. Both names are in the executable at
`0x801B943C` and `0x801B9434`.

The records also spell out the cast in Shift-JIS, given name and family name
in separate fields:

```
スタン・エルロン      ルーティ・カトレット   リオン・マグナス
ウッドロウ・ケルヴィン フィリア・フィリス     マリー・エージェント
ジョニー・シデン      チェルシー・トーン     マイティ・コングマン
リリス・エルロン
```

and, after them, the five Swordians: ディムロス, アトワイト, シャルティエ,
イクティノス, クレメンテ.

## `KAISEN.BIN` — a mini-game with its profiler still attached

73,160 bytes, a MIPS overlay linked at `0x80010000` — the same 576 KiB arena
the map data uses ([03](03-executable.md)). Its first 0x118 bytes are a header
of strings and pointers; code starts at `+0x118`.

The strings:

```
+0000  'CPU:%03d/%03d\n'
+0010  'ALL:%03d/%03d\n'
+0020  'PRM:%05X\n'
+002C  'SCORE'
+0034  'MODE:%d STEP:%d\n'
+0048  'BATTLE'   'START'   'NEXT'   'ENEMY'   'WIN'
+006C  'YOUR RANK :'
+0078  'SEAMAN' 'SERGENT' 'OFFICER' 'LIEUTENANT' 'CAPTAIN'
       'MAJOR' 'COLONEL' 'GENERAL' 'MONKEY' 'BROKEN'
+00E0  'PAUSE'
+00E8  'dmg: %d\n'
+0108  'sim:PICTURE.BIN'
```

*Kaisen* (海戦) is "naval battle", and the rank ladder confirms it — except
that the ladder does not stop at `GENERAL`. `MONKEY` and `BROKEN` are below
and beyond it, which is what a programmer writes at four in the morning and
never removes.

`CPU:%03d/%03d`, `ALL:%03d/%03d` and `PRM:%05X` are a frame profiler: CPU time
used against budget, total time against budget, and the primitive count. With
`MODE:%d STEP:%d`, `PAUSE` and `dmg: %d`, that is a complete development HUD,
compiled into a retail overlay.

`SERGENT` is misspelled — the English word is *sergeant*.

And `sim:PICTURE.BIN` names a file that does not exist on the disc, prefixed
with a tag that reads like a build target. Whatever `PICTURE.BIN` was, the
mini-game was at some point run somewhere that could load it.

## Debug menus in the retail script

The map archive holds 538,900 Shift-JIS strings ([09](09-text.md)). Thirty-
seven of them name a variable called `tod2`, and reading the strings around
them shows what they belong to.

Map extent 974, `id 0C20`:

```
シャワー室                  shower room
作戦会議室                  strategy meeting room
モンスター襲来              monster attack
助手、目覚める              the assistant awakens
レンズ回収業務              lens collection duty
前の日の晩                  the night before
レンズ砲発射                the lens cannon fires
ウソエンディング            FAKE ENDING
ｔｏｄ２＝１７０にするっぺ  "I'll set tod2 to 170, y'know"
チェックルーチン作動        activate check routine
ｔｏｄ２を１５０にしたさ    "set tod2 to 150"
「日記みたいだ」            "looks like a diary"   <- ordinary dialogue resumes
```

A scene-select list — eleven entries, one of them **ウソエンディング, "fake
ending"**, one of them a check routine — sitting in the same string pool as
the room's normal dialogue, in the same shipped extent.

Map extent 859, `id 0707`, has a second one, this time for the ship:

```
ｔｏｄ２：０
水門を閉じます              close the floodgate
船は自由移動になりました    the ship is now in free movement
ｔｏｄ２：９５０
水門を開きます              open the floodgate
船は自動移動になりました    the ship is now in automatic movement
自動移動では船は貫通します。 in automatic movement the ship clips through
現状では船頭さんに話かけてね in the current build, talk to the boatman
旧自由移動です              this is the old free movement
```

「現状では船頭さんに話かけてね」 — *in the current build, talk to the boatman* —
is a note from one developer to another, addressed with the casual 〜てね, and
it went to press.

Thirteen further strings are bare flag references where a line should be:
`『Ｆ４８`, `『Ｆ−２７`, `『Ｆ５２`, `『Ｆ３３`, and nine more.

## The eighth `PIC` file

The file registry ([05](05-containers-and-index.md)) numbers the `PIC`
directory 1000–1007 and skips **1004**:

```
1000 MC   1001 I   1002 FACE   1003 FACE2   [1004]   1005 RC   1006 WM   1007 BF
```

Seven `.D` files ship; the eighth slot was removed after the numbering was
fixed. Nothing else references it.

## Names the sound team marked

The 174-entry sound test list ([07](07-audio.md)) carries its own annotations:

| Index | Name |
|---|---|
| 0 | `*` |
| 1 | `Preview edition` |
| 75–85 | ` namco 1` … ` namco 11` — eleven tracks with no name, only a number |
| 92 | `Fin` |
| 140 | `*(DoorKnock:DonDon)` |
| 161 | `*(SnowWalk:KyuKyu)` |
| 173 | `?` |

The `*( … )` convention is used exactly twice, on a door knock and on the
sound of walking in snow. Whatever it meant to the person who wrote it —
unused, provisional, duplicate — it is a note in a shipping data table.
Entry 1, `Preview edition`, is named for a build that is not this one.

## A code path that cannot work

The codec dispatcher's method-0 branch passes the *header* pointer where the
payload pointer belongs, and the packed length where the unpacked length
belongs ([04](04-block-codec.md)). It would emit nine bytes of header in front
of the data.

It has never been exercised: of the 6,638 packed blocks on the disc, 157 are
method 1 and 6,481 are method 3. Not one is method 0. The stored path exists
because the format the codec was ported from had one — see
[11](11-tales-lineage.md) — and nothing ever tested the port.

## Seventeen undefined bytes in the dictionary

The method-3 decoder clears ring indices 0–4078 and starts writing at 4079.
Indices 4079–4095 are whatever the previous call left on the stack. Method 1
clears 0–4077, starts at 4078, and leaves eighteen.

A block that referenced them would decode differently every time it was
loaded. Across 6,638 blocks, none does.

## The screen-adjust and photograph modes

Two strings suggest features that are, at minimum, unusual for a retail JRPG:

```
0x800A2770  [Photgraphic mode]
0x800A2758  X=%3d Y=%3d ATR=%02X
0x800A380C  ADJUST SCREEN
0x800A381C  EXIT:START BUTTON
0x801B9054  MapNo:
0x801B9060  Evt No:
0x801B906C  movie:
```

`[Photgraphic mode]` — misspelled — sits next to a coordinate-and-attribute
readout, and `MapNo:` / `Evt No:` / `movie:` are the three fields of a
one-line debug overlay. `ADJUST SCREEN` is a legitimate option-screen feature.

## The memory card

```
0x801869E8  bu00:BISLPS-01100<TOD-01>     NUL-terminated, in a table of pointers
0x80186C04  bu00:TOD_TEMP                 not NUL-preceded; the byte before it is 'U'
```

The first is the ordinary save-file name: `BI` plus the product code plus a
title tag. The second names a **second memory-card file called `TOD_TEMP`**,
a working name that no player-facing feature would need.

## Reading it yourself

```sh
python tools/leftovers.py   "$TOD" iso/ --filler
python tools/script_scan.py iso/SLPS_011.00 iso/DAT --labels
python tools/script_scan.py iso/SLPS_011.00 iso/DAT --map 974
python tools/dismips.py     iso/SLPS_011.00 0x801502F4 20
python tools/tod_codec.py iso/DAT/DBG.D -o dbg.bin && python tools/sjis_strings.py dbg.bin
```
