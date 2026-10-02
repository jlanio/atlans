# tests/unit/test_avisos_de_terceiros.py
"""
O gerador do THIRD-PARTY-NOTICES.md (scripts/avisos_de_terceiros.py).

O que se protege:

- **A licença certa de cada pacote do PyPI.** A expressão SPDX declarada ganha
  de tudo; sem ela, a lida no pacote (LIDAS_NO_PACOTE), o nome curto e o
  classificador, nesta ordem. Um campo vago (um texto inteiro, «BSD» sem dizer
  qual) não pode virar uma licença que o pacote não declarou.
- **Nada incompatível passa calado.** Uma licença fora de COMPATIVEIS, ou uma
  expressão que não se lê, vai para «Para revisar»; com OR basta uma
  alternativa compatível, com AND precisa de todas.
- **Só o que a instalação de produção leva.** Os pacotes `dev` do npm ficam de
  fora, menos os que o build junta assim mesmo (o CSS importa o tailwindcss);
  os `optional` (o binário do sharp de cada plataforma) entram.
- **Os ícones e o código copiado.** Cada conjunto do react-icons que os fontes
  importam sai com a licença do projeto dele, e uma obra copiada para o
  repositório vai com o texto da licença ao lado.

Sem rede: a consulta ao PyPI é trocada por um dicionário.
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


# ── A licença de um pacote do PyPI ───────────────────────────────────────────

def test_a_expressao_declarada_ganha_de_tudo(avisos):
    info = {"license_expression": "Apache-2.0 OR BSD-3-Clause", "license": "MIT", "classifiers": ["License :: OSI Approved :: MIT License"]}
    assert avisos.licenca_do_pypi("jinja2", info) == "Apache-2.0 OR BSD-3-Clause"


def test_sem_expressao_vale_a_lida_no_pacote(avisos):
    info = {"license": "BSD", "classifiers": ["License :: OSI Approved :: BSD License"]}
    assert avisos.licenca_do_pypi("pandas", info) == "BSD-3-Clause"


def test_a_licenca_composta_lida_no_pacote_vai_para_a_revisao(avisos, monkeypatch):
    # Um LICENSE que cobre também o que veio de fora (era o caso do passlib:
    # o md5-crypt em Beerware, o UnixCrypt com aviso próprio) entra inteiro
    # em LIDAS_NO_PACOTE, e com AND a licença só passa se todas passarem.
    monkeypatch.setitem(avisos.LIDAS_NO_PACOTE, "pacote-composto",
                        "BSD-3-Clause AND Beerware AND LicenseRef-UnixCrypt")
    info = {"license": "BSD", "classifiers": ["License :: OSI Approved :: BSD License"]}
    licenca = avisos.licenca_do_pypi("pacote-composto", info)
    assert licenca.startswith("BSD-3-Clause AND ")
    assert not avisos.compativel(licenca)


def test_o_campo_curto_nao_apaga_a_outra_licenca_de_um_pacote_duplo(avisos):
    # O uvloop: «MIT» no campo, e os classificadores do MIT e do Apache.
    info = {"license": "MIT", "classifiers": [
        "License :: OSI Approved :: Apache Software License",
        "License :: OSI Approved :: MIT License",
    ]}
    assert avisos.licenca_do_pypi("uvloop", info) == "Apache-2.0 OR MIT"
    # O campo que diz outra coisa continua ganhando.
    info["license"] = "BSD 3-Clause"
    assert avisos.licenca_do_pypi("pacote", info) == "BSD-3-Clause"


@pytest.mark.parametrize(("campo", "esperada"), [
    ("MIT", "MIT"),
    ("MIT License", "MIT"),
    ("Apache License, Version 2.0", "Apache-2.0"),
    ("BSD 3-Clause", "BSD-3-Clause"),
    ("MPL-2.0", "MPL-2.0"),
])
def test_o_nome_curto_vira_spdx(avisos, campo, esperada):
    assert avisos.licenca_do_pypi("pacote", {"license": campo}) == esperada


def test_um_texto_inteiro_nao_e_licenca_e_cai_no_classificador(avisos):
    info = {
        "license": "MIT License\n\nCopyright (c) 2020 Alguém\n\nPermission is hereby granted…",
        "classifiers": ["License :: OSI Approved", "License :: OSI Approved :: MIT License"],
    }
    assert avisos.licenca_do_pypi("pacote", info) == "MIT"


def test_dois_classificadores_sao_a_escolha_entre_eles(avisos):
    info = {"classifiers": ["License :: OSI Approved :: MIT License", "License :: OSI Approved :: Apache Software License"]}
    assert avisos.licenca_do_pypi("pacote", info) == "Apache-2.0 OR MIT"


@pytest.mark.parametrize("info", [
    {},
    {"license": "Dual License", "classifiers": ["License :: OSI Approved :: BSD License"]},
    {"license": "", "classifiers": ["License :: OSI Approved :: BSD License", "License :: OSI Approved :: MIT License"]},
])
def test_o_vago_fica_desconhecido(avisos, info):
    assert avisos.licenca_do_pypi("pacote", info) == avisos.DESCONHECIDA


# ── Compatível ou não ────────────────────────────────────────────────────────

@pytest.mark.parametrize(("licenca", "esperado"), [
    ("MIT", True),
    ("(MIT OR Apache-2.0)", True),
    ("GPL-2.0-only OR MIT", True),
    ("Apache-2.0 AND LGPL-3.0-or-later AND MIT", True),
    ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", True),
    ("GPL-2.0-or-later WITH Classpath-exception-2.0", True),
    ("(MIT AND (BSD-3-Clause OR SSPL-1.0))", True),
    # A GPL-2.0 só ela não convive com a AGPL-3.0, e AND exige todas.
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
def test_compativel(avisos, licenca, esperado):
    assert avisos.compativel(licenca) is esperado


# ── Os locks ─────────────────────────────────────────────────────────────────

def test_do_npm_fica_so_o_que_vai_para_producao(avisos, tmp_path):
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

    assert avisos.pacotes_npm(lock) == {
        ("react", "19.0.0"): "MIT",
        ("tailwindcss", "4.3.3"): "MIT",
        ("@img/sharp-linux-x64", "0.35.0"): "Apache-2.0",
        ("b", "2.0.0"): "BSD-2-Clause",
        ("c", "3.0.0"): "MIT OR Apache-2.0",
        ("sem-licenca", "0.1.0"): avisos.DESCONHECIDA,
    }


def test_do_pypi_vem_cada_pino_com_o_nome_normalizado(avisos, tmp_path):
    lock = tmp_path / "requirements.txt"
    lock.write_text(
        "# cabeçalho do pip-compile\n"
        "Jinja2==3.1.6 \\\n    --hash=sha256:" + "0" * 64 + "\n    # via fastapi\n"
        "typing_extensions==4.16.0 \\\n    --hash=sha256:" + "1" * 64 + "\n"
        "uvicorn[standard]==0.53.0 \\\n    --hash=sha256:" + "2" * 64 + "\n",
        encoding="utf-8",
    )
    assert avisos.pinos_pypi(lock) == {("jinja2", "3.1.6"), ("typing-extensions", "4.16.0"), ("uvicorn", "0.53.0")}


# ── O arquivo ────────────────────────────────────────────────────────────────

def test_o_arquivo_junta_quem_usa_conta_e_separa_o_que_revisar(avisos, tmp_path, monkeypatch):
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
    monkeypatch.setattr(avisos, "consultar_pypi", lambda pinos: {pino: "MIT" for pino in pinos})

    texto, fora = avisos.gerar()

    assert "| `react` | 19.0.0 | MIT | web, desktop |" in texto
    assert "| `fastapi` | 1.0 | MIT | API, executor |" in texto
    assert "| MIT | 1 | 1 |" in texto
    assert "| **Total** | **2** | **1** |" in texto
    assert fora == [("npm", "proprietario", "1.0.0", "SEE LICENSE IN LICENSE.txt")]
    assert "| npm | `proprietario` | 1.0.0 | SEE LICENSE IN LICENSE.txt |" in texto


def test_o_que_mora_no_repositorio_tem_a_licenca_ao_lado(avisos):
    # Uma obra de terceiros copiada para cá (a fonte Inter, por exemplo) vai
    # com o texto da licença, e a licença convive com a AGPL-3.0.
    for obra, onde, licenca, textos in avisos.NO_REPOSITORIO:
        for caminho in onde:
            assert (RAIZ / caminho).exists(), (obra, caminho)
        for texto in textos:
            assert (RAIZ / texto).is_file(), (obra, texto)
        # Uma fonte servida à parte pode ser OFL (AGREGAVEIS); o que é compilado
        # junto do programa precisa ser compatível de verdade.
        agregada = "separate file" in obra
        assert avisos.compativel(licenca) or (agregada and licenca in avisos.AGREGAVEIS), obra


def test_o_dev_que_vai_no_build_e_o_que_o_css_importa(avisos):
    # Um `@import "<pacote>"` no CSS leva o pacote para a folha de estilo que a
    # instalação serve: ou ele é de produção, ou está em DEV_QUE_VAI_NO_BUILD.
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
                    assert pacote in avisos.DEV_QUE_VAI_NO_BUILD, (css, pacote)
                    importados.add(pacote)
    # E a lista não guarda o que nenhum CSS importa mais.
    assert importados == avisos.DEV_QUE_VAI_NO_BUILD


def test_os_conjuntos_de_icones_saem_dos_fontes_e_nao_dos_testes(avisos, tmp_path, monkeypatch):
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

    icones = avisos.conjuntos_de_icones()

    assert list(icones) == ["fa", "novo", "tb"]
    assert icones["fa"][1] == "CC-BY-4.0"
    assert icones["tb"][1] == "MIT"
    assert icones["novo"][1] == avisos.DESCONHECIDA


def test_as_wheels_com_bibliotecas_nativas_estao_nos_locks(avisos):
    pinos = set()
    for _quem, lock in avisos.LOCKS_PYPI:
        pinos |= {nome for nome, _versao in avisos.pinos_pypi(RAIZ / lock)}
    for pacote, *_resto in avisos.NATIVAS_NAS_WHEELS:
        assert avisos.normalizar(pacote) in pinos, pacote
