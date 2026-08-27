# 09 — Text and the font

**Status: verified** for where the text is and how it is encoded;
**consistent** for how the glyph sheets are indexed. Output in
[`reports/exe-text.txt`](../reports/exe-text.txt),
[`reports/script-labels.txt`](../reports/script-labels.txt) and
[`reports/tkm-strings.txt`](../reports/tkm-strings.txt).

## The text is Shift-JIS, and there is a lot of it

No custom encoding, no dictionary of glyph indices, no per-string
compression beyond the block codec. The game's Japanese is stored as plain
Shift-JIS, in three places:

| Where | What | Roughly |
|---|---|---|
| `SLPS_011.00`, `0x800A0000`–`0x800A2FFF` | system, menu, battle and memory-card messages | 621 strings of ten glyphs or more |
| the map archive, in every extent's last member | **the entire scenario script** | **538,900 strings** |
| `DAT/TKM.BIN` | the janken mini-game's own text | ~40 strings |

Running [`tools/script_scan.py`](../tools/script_scan.py) over all 1,315 map
extents: **1,311 of them carry text**, 538,900 strings in total. Field
dialogue, NPC lines, shop inventories, item descriptions, floor names, chest
messages — all of it lives in the same member of the same container as the
map's logic, uncompressed within the block, and reachable with nothing more
than the codec.

That is the single largest thing on the disc that is *not* a texture or a
waveform, and it is stored in the most direct way available.

Examples, from map extent 900 (`id 0818`, a town):

```
モリュウ生活道具店          Moryu general store
道具屋『月見桜』            item shop "Tsukimizakura"
武器防具屋『海神』          weapon and armour shop "Kaijin"
```

## The Shift-JIS fold table

At `0x801807FC` there are 39 four-byte records:

```
u16  Shift-JIS code
u16  the code the engine uses instead
```

Every one of them maps a full-width punctuation mark onto a **single-byte**
JIS X 0201 code:

| | | | |
|---|---|---|---|
| `8140` 　 → `20` | `8141` 、 → `A4` | `8142` 。 → `A1` | `8143` ， → `2C` |
| `8145` ・ → `A5` | `8148` ？ → `3F` | `8149` ！ → `21` | `815B` ー → `B0` |
| `8175` 「 → `A2` | `8176` 」 → `A3` | `8181` ＝ → `3D` | `8197` ＠ → `40` |

`A1`–`B0` are the half-width katakana punctuation of JIS X 0201, and
`20`–`40` are plain ASCII. So the renderer's internal character code is
single-byte where a single byte will do and Shift-JIS where it will not — the
usual 1997 compromise, expressed as a 156-byte table.

## The technique-name font

At `0x8018089C`, immediately after that table, is a run of exactly 74
Shift-JIS codes and nothing else:

```
魔神剣飛燕連脚爪竜牙斬虎破烈空真獅子戦吼閃裂鳳凰天駆爆炎陣王撃波紅蓮昇殺劇舞荒未
定皇翔翼人闇風陽豪疾雹雨刃改剛雷猛襲迅死滅弓友情譜面演奏超断熱旋拳十
```

This is a **character inventory**: the complete set of kanji the game needs to
draw special-attack names, and nothing else. 魔神剣 (Majinken), 虎牙破斬
(Kogahazan), 獅子戦吼 (Shishisenkou), 鳳凰天駆 (Houou Tenku) — the *Tales*
series' signature move vocabulary, reduced to its 74 distinct characters so a
small dedicated font sheet can hold one tile per entry.

Two entries in that list are not part of any attack name:

* **未定** — *mitei*, "undecided", "to be determined". Both characters of the
  placeholder a designer types when a technique has no name yet were budgeted
  a glyph each, and shipped.
* **譜面演奏** — "sheet-music performance", four characters that belong to a
  support skill rather than to a technique.

## The same idea, in a file

`DAT/TKM.BIN` is the janken (rock-paper-scissors) mini-game: 63,420 bytes,
linked to load at `0x80010000` like `KAISEN.BIN` ([10](10-leftovers.md)) —
its pointer table holds absolute `0x8001xxxx` addresses into itself — and
structured as

```
0x0000 - 0x02E9   its text, NUL-terminated Shift-JIS
0x02EC - 0x0570   161 pointers to glyph bitmaps, absolute at 0x8001xxxx
0x0574 - 0x065F   a 119-glyph character inventory
0x0660 - 0xF7BC   the glyph bitmaps
```

The inventory reads:

```
０１２３４５６７８９勝負所持対戦金設定決方攻撃防御操作説明取分一度先取制払戻額元敗
あいうかきくけこさしすせたちつてとなねのはへまもやらりるをんがぎじだでどぽっゃょ
イキタトセチナハムルリレンガグゲドブベパポョー、。？：＋／＊＜＞□△×○
```

which is the exact set of characters used by the text above it — every kana
the file's own strings contain, and not one more. The mini-game carries its
own font because it is an overlay: it takes over the working arena and cannot
count on the main font sheets being resident.

The text itself is worth reading:

```
＜ゲーム説明＞
対戦レベルとかけるガルドを設定し、じゃんけんをします。
勝った方は、ハリセン攻撃。
負けた方は、ナベブタ防御。
５ポイント先取制。
○ハリセン：×ナベブタ
```

Best of five, bet in Gald, winner swings a *harisen* (paper fan) and the loser
defends with a *nabebuta* (pot lid).

## The font sheets

`PIC/MC.D` decompresses to a container of fifteen TIMs
([06](06-graphics.md)); members 0–9 are 344,064 pixels of 4bpp glyph sheet
spread across ten VRAM pages from `(320,0)` to `(960,400)`. `PIC/BF.D` is a
single 256×256 4bpp image that lands at `(896,256)` — the same rectangle, with
the same 16×16 CLUT geometry, that `MC.D` member 10 uses. The battle font
does not sit beside the menu font; it takes its place.

Neither sheet carries an inventory of its own. Which glyph is at which
position in those ten pages, and how a Shift-JIS code becomes a tile index, is
[open](99-open-questions.md) — the fold table above handles the single-byte
half, but the kanji half must be resolved by something not yet found.

## Development text in the shipping script

538,900 strings is a lot to proofread, and some of it was not meant for
players. 203 of them contain full-width Latin letters, which Japanese prose
does not use. Most are legitimate — floor labels `１Ｆ`, `Ａ　２Ｆ`, the shop
`Ｆマート百貨店` — but **37 of them name a variable called `tod2`**:

```
map   10  id 0600   ｔｏｄ２を８０に変更          "change tod2 to 80"
map  549  id 0447   ｔｏｄ２を７６０に変更        "change tod2 to 760"
map  596  id 0476   ｔｏｄ２＝１２００
map  859  id 0707   ｔｏｄ２：０ / ｔｏｄ２：９５０
map  974  id 0C20   ｔｏｄ２＝１７０にするっぺ    "I'll set tod2 to 170, y'know"
```

`tod2` is a scenario-progress variable, and these are the menu entries of
debug warps that were left in. Two of them are dialect — `〜っぺ`, `〜したさ` —
which means the scripter wrote them in character, in the same tool, in the
same file as the real dialogue. See [10](10-leftovers.md) for what the menus
around them say.

Thirteen more strings are bare flag references — `『Ｆ４８`, `『Ｆ−２７`,
`『Ｆ５２` — sitting where a line of dialogue should be.

## Reading it yourself

```sh
python tools/exe_tables.py  iso/SLPS_011.00 --fonts
python tools/sjis_strings.py iso/DAT/TKM.BIN --min 3 --offsets
python tools/script_scan.py iso/SLPS_011.00 iso/DAT --map 900
python tools/script_scan.py iso/SLPS_011.00 iso/DAT --labels
```
