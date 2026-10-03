# tests/unit/test_avisos_de_terceiros.py
"""
The THIRD-PARTY-NOTICES.md generator (scripts/avisos_de_terceiros.py).

What is protected:

- **The right license for each PyPI package.** The declared SPDX expression
  beats everything; without it, the one read in the package (READ_FROM_PACKAGE),
  the short name and the classifier, in that order. A vague field (a whole text,
  "BSD" without saying which) must not become a license the package didn't
  declare.
- **Nothing incompatible slips through silently.** A license outside COMPATIVEIS,
  or an expression that can't be parsed, goes to "Para revisar" (to review); with
  OR one compatible alternative is enough, with AND all of them are needed.
- **Only what the production install ships.** npm `dev` packages are left out,
  except the ones the build bundles anyway (the CSS imports tailwindcss); the
  `optional` ones (sharp's per-platform binary) get in.
- **The icons and the copied code.** Each react-icons set the sources import
  goes out with its project's license, and a work copied into the repository
  goes with the license text next to it.

No network: the PyPI query is swapped for a dictionary.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def avisos():
    spec = importlib.util.spec_from_file_location("avisos_de_terceiros", RAIZ / "scripts" / "avisos_de_terceiros.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# ── The license of a PyPI package ────────────────────────────────────────────

def test_the_declared_expression_beats_everything(avisos):
    info = {"license_expression": "Apache-2.0 OR BSD-3-Clause", "license": "MIT", "classifiers": ["License :: OSI Approved :: MIT License"]}
    assert avisos.pypi_license("jinja2", info) == "Apache-2.0 OR BSD-3-Clause"


def test_without_expression_the_one_read_from_package_applies(avisos):
    info = {"license": "BSD", "classifiers": ["License :: OSI Approved :: BSD License"]}
    assert avisos.pypi_license("pandas", info) == "BSD-3-Clause"


def test_compound_license_read_from_package_goes_to_review(avisos, monkeypatch):
    # A LICENSE that also covers what came from outside (that was passlib's case:
    # md5-crypt under Beerware, UnixCrypt with its own notice) goes in whole
    # in READ_FROM_PACKAGE, and with AND the license only passes if all pass.
    monkeypatch.setitem(avisos.READ_FROM_PACKAGE, "pacote-composto",
                        "BSD-3-Clause AND Beerware AND LicenseRef-UnixCrypt")
    info = {"license": "BSD", "classifiers": ["License :: OSI Approved :: BSD License"]}
    licenca = avisos.pypi_license("pacote-composto", info)
    assert licenca.startswith("BSD-3-Clause AND ")
    assert not avisos.compativel(licenca)


def test_the_short_field_does_not_erase_the_other_license_of_a_dual_package(avisos):
    # uvloop: "MIT" in the field, and the MIT and Apache classifiers.
    info = {"license": "MIT", "classifiers": [
        "License :: OSI Approved :: Apache Software License",
        "License :: OSI Approved :: MIT License",
    ]}
    assert avisos.pypi_license("uvloop", info) == "Apache-2.0 OR MIT"
    # The field that says something else still wins.
    info["license"] = "BSD 3-Clause"
    assert avisos.pypi_license("pacote", info) == "BSD-3-Clause"


@pytest.mark.parametrize(("campo", "esperada"), [
    ("MIT", "MIT"),
    ("MIT License", "MIT"),
    ("Apache License, Version 2.0", "Apache-2.0"),
    ("BSD 3-Clause", "BSD-3-Clause"),
    ("MPL-2.0", "MPL-2.0"),
])
def test_the_short_name_becomes_spdx(avisos, campo, esperada):
    assert avisos.pypi_license("pacote", {"license": campo}) == esperada


def test_a_full_text_is_not_a_license_and_falls_to_the_classifier(avisos):
    info = {
        "license": "MIT License\n\nCopyright (c) 2020 Alguém\n\nPermission is hereby granted…",
        "classifiers": ["License :: OSI Approved", "License :: OSI Approved :: MIT License"],
    }
    assert avisos.pypi_license("pacote", info) == "MIT"


def test_two_classifiers_are_a_choice_between_them(avisos):
    info = {"classifiers": ["License :: OSI Approved :: MIT License", "License :: OSI Approved :: Apache Software License"]}
    assert avisos.pypi_license("pacote", info) == "Apache-2.0 OR MIT"


@pytest.mark.parametrize("info", [
    {},
    {"license": "Dual License", "classifiers": ["License :: OSI Approved :: BSD License"]},
    {"license": "", "classifiers": ["License :: OSI Approved :: BSD License", "License :: OSI Approved :: MIT License"]},
])
def test_the_vague_stays_unknown(avisos, info):
    assert avisos.pypi_license("pacote", info) == avisos.UNKNOWN


# ── Compatible or not ────────────────────────────────────────────────────────

@pytest.mark.parametrize(("licenca", "esperado"), [
    ("MIT", True),
    ("(MIT OR Apache-2.0)", True),
    ("GPL-2.0-only OR MIT", True),
    ("Apache-2.0 AND LGPL-3.0-or-later AND MIT", True),
    ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", True),
    ("GPL-2.0-or-later WITH Classpath-exception-2.0", True),
    ("(MIT AND (BSD-3-Clause OR SSPL-1.0))", True),
    # GPL-2.0-only doesn't coexist with AGPL-3.0, and AND requires all.
    ("MIT AND GPL-2.0-only", False),
    ("GPL-2.0-only", False),
    ("SSPL-1.0", False),
    ("BUSL-1.1", False),
    ("BSD", False),
    ("SEE LICENSE IN LICENSE.md", False),
    ("desconhecida", False),
    ("(MIT", False),
    ("MIT AND", False),
    ("MIT WITH", False),
    ("", False),
])
def test_compatible(avisos, licenca, esperado):
    assert avisos.compativel(licenca) is esperado


# ── The lockfiles ────────────────────────────────────────────────────────────

def test_from_npm_only_what_goes_to_production_stays(avisos, tmp_path):
    lock = tmp_path / "package-lock.json"
    lock.write_text(json.dumps({"packages": {
        "": {"name": "raiz", "version": "1.0.0", "license": "AGPL-3.0-only"},
        "node_modules/react": {"version": "19.0.0", "license": "MIT"},
        "node_modules/vitest": {"version": "5.0.0", "license": "MIT", "dev": True},
        "node_modules/tailwindcss": {"version": "4.3.3", "license": "MIT", "dev": True},
        "node_modules/@img/sharp-linux-x64": {"version": "0.35.0", "license": "Apache-2.0", "optional": True},
        "node_modules/a/node_modules/b": {"version": "2.0.0", "license": {"type": "BSD-2-Clause", "url": "…"}},
        "node_modules/c": {"version": "3.0.0", "license": [{"type": "MIT"}, {"type": "Apache-2.0"}]},
        "node_modules/sem-licenca": {"version": "0.1.0"},
        "node_modules/ligado": {"resolved": "../outro", "link": True},
    }}), encoding="utf-8")

    assert avisos.npm_packages(lock) == {
        ("react", "19.0.0"): "MIT",
        ("tailwindcss", "4.3.3"): "MIT",
        ("@img/sharp-linux-x64", "0.35.0"): "Apache-2.0",
        ("b", "2.0.0"): "BSD-2-Clause",
        ("c", "3.0.0"): "MIT OR Apache-2.0",
        ("sem-licenca", "0.1.0"): avisos.UNKNOWN,
    }


def test_from_pypi_each_pin_comes_with_the_normalized_name(avisos, tmp_path):
    lock = tmp_path / "requirements.txt"
    lock.write_text(
        "# cabeçalho do pip-compile\n"
        "Jinja2==3.1.6 \\\n    --hash=sha256:" + "0" * 64 + "\n    # via fastapi\n"
        "typing_extensions==4.16.0 \\\n    --hash=sha256:" + "1" * 64 + "\n"
        "uvicorn[standard]==0.53.0 \\\n    --hash=sha256:" + "2" * 64 + "\n",
        encoding="utf-8",
    )
    assert avisos.pypi_pins(lock) == {("jinja2", "3.1.6"), ("typing-extensions", "4.16.0"), ("uvicorn", "0.53.0")}


# ── O arquivo ────────────────────────────────────────────────────────────────

def test_the_file_groups_who_uses_counts_and_separates_what_to_review(avisos, tmp_path, monkeypatch):
    (tmp_path / "web").mkdir()
    (tmp_path / "desktop").mkdir()
    (tmp_path / "web" / "package-lock.json").write_text(json.dumps({"packages": {
        "node_modules/react": {"version": "19.0.0", "license": "MIT"},
        "node_modules/proprietario": {"version": "1.0.0", "license": "SEE LICENSE IN LICENSE.txt"},
    }}), encoding="utf-8")
    (tmp_path / "desktop" / "package-lock.json").write_text(json.dumps({"packages": {
        "node_modules/react": {"version": "19.0.0", "license": "MIT"},
    }}), encoding="utf-8")
    (tmp_path / "api.txt").write_text("fastapi==1.0 \\\n    --hash=sha256:" + "0" * 64 + "\n", encoding="utf-8")
    (tmp_path / "exec.txt").write_text("fastapi==1.0 \\\n    --hash=sha256:" + "0" * 64 + "\n", encoding="utf-8")
    monkeypatch.setattr(avisos, "RAIZ", tmp_path)
    monkeypatch.setattr(avisos, "LOCKS_NPM", [("web", "web/package-lock.json"), ("desktop", "desktop/package-lock.json")])
    monkeypatch.setattr(avisos, "LOCKS_PYPI", [("API", "api.txt"), ("executor", "exec.txt")])
    monkeypatch.setattr(avisos, "consultar_pypi", lambda pins: {pin: "MIT" for pin in pins})

    texto, fora = avisos.gerar()

    assert "| `react` | 19.0.0 | MIT | web, desktop |" in texto
    assert "| `fastapi` | 1.0 | MIT | API, executor |" in texto
    assert "| MIT | 1 | 1 |" in texto
    assert "| **Total** | **2** | **1** |" in texto
    assert fora == [("npm", "proprietario", "1.0.0", "SEE LICENSE IN LICENSE.txt")]
    assert "| npm | `proprietario` | 1.0.0 | SEE LICENSE IN LICENSE.txt |" in texto


def test_what_lives_in_the_repo_has_the_license_alongside(avisos):
    # A third-party work copied here (the Inter font, for example) goes
    # with the license text, and the license coexists with AGPL-3.0.
    for work, onde, licenca, textos in avisos.IN_REPOSITORY:
        for caminho in onde:
            assert (RAIZ / caminho).exists(), (work, caminho)
        for texto in textos:
            assert (RAIZ / texto).is_file(), (work, texto)
        # A font served separately may be OFL (AGGREGABLE); what is compiled
        # together with the program has to be truly compatible.
        aggregated = "separate file" in work
        assert avisos.compativel(licenca) or (aggregated and licenca in avisos.AGGREGABLE), work


def test_the_dev_dep_in_the_build_is_what_the_css_imports(avisos):
    # An `@import "<pacote>"` in the CSS takes the package into the stylesheet the
    # installation serves: either it is a production one, or it is in DEV_SHIPPED_IN_BUILD.
    importados = set()
    for base, lock in (("web", "web/package-lock.json"), ("desktop/src", "desktop/package-lock.json")):
        pacotes = json.loads((RAIZ / lock).read_text(encoding="utf-8"))["packages"]
        for css in sorted((RAIZ / base).rglob("*.css")):
            if "node_modules" in css.parts or ".next" in css.parts or "public" in css.parts:
                continue
            for nome in re.findall(r"""@import\s+["']([^"'./][^"']*)["']""", css.read_text(encoding="utf-8")):
                pacote = "/".join(nome.split("/")[:2]) if nome.startswith("@") else nome.split("/")[0]
                dados = pacotes.get(f"node_modules/{pacote}")
                assert dados is not None, (css, pacote)
                if dados.get("dev"):
                    assert pacote in avisos.DEV_SHIPPED_IN_BUILD, (css, pacote)
                    importados.add(pacote)
    # And the list doesn't keep what no CSS imports anymore.
    assert importados == avisos.DEV_SHIPPED_IN_BUILD


def test_icon_sets_come_from_the_sources_and_not_the_tests(avisos, tmp_path, monkeypatch):
    (tmp_path / "web" / "app").mkdir(parents=True)
    (tmp_path / "web" / "app" / "a.tsx").write_text('import { TbX } from "react-icons/tb"\nimport { FaEye } from \'react-icons/fa\'\n', encoding="utf-8")
    (tmp_path / "web" / "app" / "b.test.tsx").write_text('import { SiX } from "react-icons/si"\n', encoding="utf-8")
    (tmp_path / "web" / "__tests__").mkdir()
    (tmp_path / "web" / "__tests__" / "c.tsx").write_text('import { GiX } from "react-icons/gi"\n', encoding="utf-8")
    (tmp_path / "web" / "node_modules" / "x").mkdir(parents=True)
    (tmp_path / "web" / "node_modules" / "x" / "d.js").write_text('require("react-icons/ti")\n', encoding="utf-8")
    (tmp_path / "desktop" / "src").mkdir(parents=True)
    (tmp_path / "desktop" / "src" / "e.ts").write_text('import { XyZ } from "react-icons/novo"\n', encoding="utf-8")
    monkeypatch.setattr(avisos, "RAIZ", tmp_path)

    icons = avisos.icon_sets()

    assert list(icons) == ["fa", "novo", "tb"]
    assert icons["fa"][1] == "CC-BY-4.0"
    assert icons["tb"][1] == "MIT"
    assert icons["novo"][1] == avisos.UNKNOWN


def test_wheels_with_native_libraries_are_in_the_locks(avisos):
    pins = set()
    for _who, lock in avisos.LOCKS_PYPI:
        pins |= {nome for nome, _version in avisos.pypi_pins(RAIZ / lock)}
    for pacote, *_rest in avisos.NATIVE_IN_WHEELS:
        assert avisos.normalizar(pacote) in pins, pacote
