#!/usr/bin/env python3
"""Generate SVG visual diagrams for all MODU-C keyboard layers.

Coordinates and layout geometry are read from config/modu.json.
Key bindings are parsed directly from config/modu.keymap.
Generated SVGs follow the exact styling of docs/layout-preview.svg.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

LAYER_METADATA = {
    "default_layer": {
        "file_name": "layer-0-default.svg",
        "title": "MODU-C Layer 0: Windows Default",
        "note": "Windows 기본 레이어 · 왼쪽 엄지 MO 1(Lower), 오른쪽 엄지 MO 4(Raise), 양손 엄지(Adjust)",
        "is_mac": False,
    },
    "lower_layer": {
        "file_name": "layer-1-lower.svg",
        "title": "MODU-C Layer 1: Windows Lower (F1~F12, Symbols, Mouse, Nav)",
        "note": "왼쪽 엄지 MO 1 홀드 시 활성화 · F1~F12, 방향키, 넘패드/기호, 마우스, Win 클립보드",
        "is_mac": False,
    },
    "mac_layer": {
        "file_name": "layer-2-mac.svg",
        "title": "MODU-C Layer 2: Mac Default",
        "note": "Mac 기본 레이어 (Command ⌘, Option ⌥) · 왼쪽 엄지 MO 3(Lower), 오른쪽 엄지 MO 4(Raise)",
        "is_mac": True,
    },
    "mac_lower_layer": {
        "file_name": "layer-3-mac-lower.svg",
        "title": "MODU-C Layer 3: Mac Lower (F1~F12, Symbols, Mouse, Nav)",
        "note": "왼쪽 엄지 MO 3 홀드 시 활성화 · F1~F12, 방향키, 기호, 마우스, Mac 클립보드(Cmd+C/V)",
        "is_mac": True,
    },
    "raise_media": {
        "file_name": "layer-4-raise-media.svg",
        "title": "MODU-C Layer 4: Media Controls (Raise)",
        "note": "오른쪽 엄지 MO 4 홀드 시 활성화 (Win/Mac 공용) · 밝기, Spotlight, 음성입력, 미디어/볼륨",
        "is_mac": False,
    },
    "adjust_system": {
        "file_name": "layer-5-adjust-system.svg",
        "title": "MODU-C Layer 5: System Adjust (Bootloader, BT, OS Toggle)",
        "note": "양손 엄지 동시 홀드 시 활성화 · BT 1~3, BT CLR, 부트로더, Studio Unlock, USB 출력, Win/Mac 모드 전환",
        "is_mac": False,
    },
}

LABEL_MAP: dict[str, str] = {
    "&bootloader": "BOOT",
    "&studio_unlock": "Studio",
    "&out OUT_USB": "USB Out",
    "&bt BT_CLR": "BT CLR",
    "&bt BT_SEL 0": "BT 1",
    "&bt BT_SEL 1": "BT 2",
    "&bt BT_SEL 2": "BT 3",
    "&kp BACKSPACE": "BSPC",
    "&kp DEL": "DEL",
    "&kp DELETE": "DEL",
    "&kp BSLH": "\\",
    "&kp CAPS": "CAPS",
    "&kp COMMA": ",",
    "&kp DOT": ".",
    "&kp FSLH": "/",
    "&kp SEMI": ";",
    "&kp SQT": "'",
    "&kp GRAVE": "~",
    "&kp MINUS": "-",
    "&kp EQUAL": "=",
    "&kp LBKT": "[",
    "&kp RBKT": "]",
    "&kp DOWN": "DOWN",
    "&kp UP": "UP",
    "&kp LEFT": "LEFT",
    "&kp RIGHT": "RIGHT",
    "&kp ESC": "ESC",
    "&kp TAB": "TAB",
    "&kp ENTER": "RET",
    "&kp HOME": "HOME",
    "&kp END": "END",
    "&kp INS": "INS",
    "&kp INSERT": "INS",
    "&kp PSCRN": "PSCRN",
    "&kp LALT": "LALT",
    "&kp RALT": "RALT",
    "&kp LCTRL": "LCTL",
    "&kp RCTRL": "RCTL",
    "&kp LGUI": "LGUI",
    "&kp RGUI": "RGUI",
    "&kp LSHFT": "LSFT",
    "&kp RIGHT_SHIFT": "RSFT",
    "&kp LANG1": "한/영",
    "&kp SPACE": "SPACE",
    "&mkp LCLK": "L-CLK",
    "&mkp MCLK": "M-CLK",
    "&mkp RCLK": "R-CLK",
    "&kp LG(LS(S))": "SNIP\nWin+Shift+S",
    "&kp LG(LS(N4))": "SNIP\nCmd+Shift+4",
    "&kp LC(INS)": "COPY\nCtrl+Ins",
    "&kp LS(INS)": "PASTE\nShift+Ins",
    "&kp LC(INSERT)": "COPY\nCtrl+Ins",
    "&kp LS(INSERT)": "PASTE\nShift+Ins",
    "&kp LG(C)": "COPY\nCmd+C",
    "&kp LG(V)": "PASTE\nCmd+V",
    "&kp PG_UP": "PG-UP",
    "&kp PG_DN": "PG-DN",
    "&kp PAGE_UP": "PG-UP",
    "&kp PAGE_DOWN": "PG-DN",
    "&mo 1": "MO 1",
    "&mo 2": "MO 2",
    "&mo 4": "MO 4",
    "&mo 6": "MO 6",
    "&mo 8": "MO 8",
    "&kp C_BRI_DN": "BRI -",
    "&kp C_BRI_UP": "BRI +",
    "&kp C_AC_SEARCH": "SEARCH",
    "&kp C_VOICE_COMMAND": "VOICE",
    "&kp C_PREV": "PREV",
    "&kp C_PP": "PLAY",
    "&kp C_NEXT": "NEXT",
    "&kp C_MUTE": "MUTE",
    "&kp C_VOL_DN": "VOL -",
    "&kp C_VOL_UP": "VOL +",
}


def clean_label(binding: str, is_mac: bool = False, layer_name: str = "", index: int = -1) -> str:
    """Format a ZMK binding into a clean, short SVG label."""
    if binding == "&to 0":
        return "TO WIN"
    if binding in ("&to 2", "&to 3"):
        return "TO MAC"

    if binding in LABEL_MAP:
        label = LABEL_MAP[binding]
        if is_mac:
            if label == "LGUI":
                return "CMD"
            if label == "RGUI":
                return "CMD"
            if label == "LALT":
                return "OPT"
            if label == "RALT":
                return "OPT"
        return label

    # &kp N0 -> 0, &kp A -> A, &kp F1 -> F1
    match = re.match(r"&kp\s+(?:N([0-9])|([A-Za-z0-9_]+))", binding)
    if match:
        num, key = match.groups()
        if num is not None:
            return num
        return key

    if binding.startswith("&mo "):
        return f"MO {binding.split()[1]}"

    return binding.lstrip("&")


def load_layout_geometry() -> list[dict[str, Any]]:
    path = ROOT / "config/modu.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["layouts"]["default_transform"]["layout"]


def parse_keymap_layers() -> list[tuple[str, list[str]]]:
    path = ROOT / "config/modu.keymap"
    text = path.read_text(encoding="utf-8")
    # Strip comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)

    keymap_start = text.find("keymap {")
    if keymap_start == -1:
        raise ValueError("keymap block not found in modu.keymap")
    body = text[keymap_start + len("keymap {") :]

    layer_pattern = re.compile(
        r"([A-Za-z0-9_]+)\s*\{[^b]*?bindings\s*=\s*<(.*?)>;", re.DOTALL
    )
    layers: list[tuple[str, list[str]]] = []
    for match in layer_pattern.finditer(body):
        name = match.group(1)
        raw = match.group(2)
        tokens = [
            b.strip()
            for b in re.findall(r"&[A-Za-z0-9_]+(?:\s+[A-Za-z0-9_()]+)*", raw)
        ]
        layers.append((name, tokens))
    return layers


def generate_svg(
    layer_name: str,
    bindings: list[str],
    layout: list[dict[str, Any]],
    title: str,
    note: str,
    is_mac: bool = False,
) -> str:
    esc_title = (
        title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    esc_note = (
        note.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="918" height="419" viewBox="0 0 918 419">',
        '<rect width="100%" height="100%" fill="white"/>',
        "<style>",
        "text{font-family:Arial,sans-serif;fill:#111}",
        ".key{fill:#f7f7f7;stroke:#222;stroke-width:1.2}",
        ".trans{fill:#fcfcfc;stroke:#ccc;stroke-width:1;stroke-dasharray:3 3}",
        ".mo{fill:#eef3ff;stroke:#3366cc;stroke-width:1.3}",
        ".boot{fill:#ffeeee;stroke:#cc3333;stroke-width:1.3}",
        ".none{fill:#ddd;stroke:#777;stroke-width:0.8}",
        ".title{font-weight:700;font-size:18px}",
        ".note{font-size:12px;fill:#555}",
        ".label{font-size:11px;text-anchor:middle;dominant-baseline:middle}",
        ".label-sm{font-size:9.5px;text-anchor:middle;dominant-baseline:middle}",
        ".label-multi-1{font-size:10px;font-weight:700;text-anchor:middle;dominant-baseline:middle}",
        ".label-multi-2{font-size:7.5px;text-anchor:middle;dominant-baseline:middle;fill:#444}",
        ".label-trans{font-size:10px;text-anchor:middle;dominant-baseline:middle;fill:#aaa}",
        "</style>",
        f'<text x="24" y="18" class="title">{esc_title}</text>',
    ]

    for index, item in enumerate(layout):
        binding = bindings[index] if index < len(bindings) else "&none"
        x = item["x"]
        y = item["y"]
        w = item.get("w", 1.0)
        h = item.get("h", 1.0)

        if w < 0.5:
            # Placeholder tiny key
            rx = round(24.0 + x * 58.0, 1)
            ry = round(40.0 + y * 58.0, 1)
            rw = 9.8
            rh = 9.8
            lines.append(
                f'<rect class="none" x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="5"/>'
            )
            continue

        rx = round(24.0 + x * 58.0, 1)
        ry = round(40.0 + y * 58.0, 1)
        rw = 55.0
        rh = 55.0
        lx = round(rx + rw / 2.0, 1)
        ly = round(ry + rh / 2.0, 1)

        if binding == "&trans":
            lines.append(
                f'<rect class="trans" x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="5"/>'
            )
            lines.append(f'<text class="label-trans" x="{lx}" y="{ly}">▽</text>')
        elif binding == "&none":
            lines.append(
                f'<rect class="none" x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="5"/>'
            )
        else:
            label = clean_label(binding, is_mac=is_mac, layer_name=layer_name, index=index)

            if binding.startswith("&mo") or binding.startswith("&to") or binding == "&studio_unlock" or binding.startswith("&out"):
                rect_class = "mo"
            elif binding == "&bootloader":
                rect_class = "boot"
            else:
                rect_class = "key"

            lines.append(
                f'<rect class="{rect_class}" x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="5"/>'
            )

            if "\n" in label:
                line1, line2 = label.split("\n", 1)
                e1 = (
                    line1.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                e2 = (
                    line2.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                lines.append(
                    f'<text class="label-multi-1" x="{lx}" y="{round(ly - 7.5, 1)}">{e1}</text>'
                )
                lines.append(
                    f'<text class="label-multi-2" x="{lx}" y="{round(ly + 8.5, 1)}">{e2}</text>'
                )
            else:
                escaped_label = (
                    label.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                label_class = "label-sm" if len(label) > 5 else "label"
                lines.append(
                    f'<text class="{label_class}" x="{lx}" y="{ly}">{escaped_label}</text>'
                )

    lines.append(f'<text x="24" y="411" class="note">{esc_note}</text>')
    lines.append("</svg>\n")
    return "\n".join(lines)


def main() -> None:
    layout = load_layout_geometry()
    layers = parse_keymap_layers()
    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loaded layout geometry ({len(layout)} keys)")
    print(f"Found {len(layers)} layers in modu.keymap:")

    for layer_name, bindings in layers:
        meta = LAYER_METADATA.get(
            layer_name,
            {
                "file_name": f"{layer_name}.svg",
                "title": f"MODU-C {layer_name}",
                "note": "",
                "is_mac": "mac" in layer_name,
            },
        )
        file_path = docs_dir / meta["file_name"]
        svg_content = generate_svg(
            layer_name=layer_name,
            bindings=bindings,
            layout=layout,
            title=meta["title"],
            note=meta["note"],
            is_mac=meta["is_mac"],
        )
        file_path.write_text(svg_content, encoding="utf-8")
        print(f"  Generated {file_path.name} ({len(bindings)} bindings)")



if __name__ == "__main__":
    main()
