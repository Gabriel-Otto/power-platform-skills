#!/usr/bin/env python3
"""
validate_payaml.py — Validador de arquivos YAML de tela do Power Apps (PaYaml).

Uso:
    python3 validate_payaml.py caminho/arquivo.yaml [mais_arquivos...]

Faz, em ordem:
  1. Tenta parsear com PyYAML. Se falhar, mostra a linha/coluna do erro e um
     diagnóstico sugerido com base nos padrões de erro conhecidos.
  2. Se parseou com sucesso, varre a árvore inteira procurando:
       - valores None (sinal de chave duplicada / aninhamento quebrado)
       - 'Radius*' em controles Label/Rectangle (não suportado)
       - Gallery sem 'Variant' ou com 'Variant' contendo '.' (variante inválida)
       - entidades HTML não decodificadas (&amp; &lt; &gt;) dentro de fórmulas
  3. Imprime um relatório em português. Saída sem problemas == exit code 0.

Este script não modifica o arquivo — só diagnostica. As correções devem ser
aplicadas manualmente seguindo o catálogo em SKILL.md / references/.
"""

import sys
import re

try:
    import yaml
except ImportError:
    print("Erro: PyYAML não está instalado. Rode: pip install pyyaml --break-system-packages")
    sys.exit(2)


def diagnosticar_erro_parse(texto, erro):
    """Dá um diagnóstico sugerido baseado na mensagem de erro e no contexto."""
    linhas = texto.splitlines()
    mark = getattr(erro, "problem_mark", None)
    sugestoes = []

    if mark is not None:
        linha_idx = mark.line  # 0-indexed
        coluna = mark.column + 1
        linha_num = linha_idx + 1

        contexto_ini = max(0, linha_idx - 6)
        contexto_fim = min(len(linhas), linha_idx + 2)
        print(f"  Linha reportada pelo parser: {linha_num}, coluna {coluna}")
        print("  Contexto:")
        for i in range(contexto_ini, contexto_fim):
            marcador = ">>" if i == linha_idx else "  "
            print(f"  {marcador} {i+1:>5}: {linhas[i]}")
        print()

        # Heurística 1: escalar multilinha sem '|' (o ')' ou '}' voltou pro nivel da chave)
        for i in range(linha_idx, contexto_ini - 1, -1):
            m = re.match(r"^(\s*)(\w+):\s*=.*[\(\{]\s*$", linhas[i])
            if m:
                indent_chave = len(m.group(1))
                # ve se alguma linha entre i e linha_idx volta pra indentacao <= indent_chave
                for j in range(i + 1, linha_idx + 1):
                    if linhas[j].strip() == "":
                        continue
                    indent_j = len(linhas[j]) - len(linhas[j].lstrip(" "))
                    if indent_j <= indent_chave:
                        sugestoes.append(
                            f"Padrão #1 do catálogo: a propriedade '{m.group(2)}' (linha {i+1}) "
                            f"parece ser uma fórmula multilinha sem bloco '|-'. A linha {j+1} "
                            f"volta para a indentação da chave (ou menos), o que quebra o "
                            f"escalar simples. Converta '{m.group(2)}:' para '{m.group(2)}: |-' "
                            f"e recue todo o conteúdo (inclusive o fecha-parênteses/chaves) mais "
                            f"do que a chave."
                        )
                        break
                if sugestoes:
                    break

        # Heurística 2: ': ' dentro de string de uma fórmula de linha única
        linha_erro_texto = linhas[linha_idx] if linha_idx < len(linhas) else ""
        for i in range(max(0, linha_idx - 1), linha_idx + 1):
            if i >= len(linhas):
                continue
            if re.search(r':\s*=.*"[^"]*:\s[^"]*"', linhas[i]) or re.search(
                r":\s*=\w[\w.]*\(\{[^}]*:\s", linhas[i]
            ):
                sugestoes.append(
                    f"Padrão #3 do catálogo: a linha {i+1} tem ': ' dentro de uma string ou "
                    f"de um registro '{{chave: valor}}' dentro de uma fórmula de uma linha só. "
                    f"O YAML interpreta isso como separador de chave, mesmo estando dentro de "
                    f"aspas do Power Fx. Converta essa propriedade para bloco '|-' (ou '|')."
                )

    if "could not find expected ':'" in str(erro) or "did not find expected key" in str(erro):
        sugestoes.append(
            "Mensagem genérica de mapeamento quebrado: também pode ser uma chave duplicada "
            "com aninhamento extra (padrão #2 do catálogo — ex. um 'Children:' embrulhando o "
            "mesmo nome do controle de novo). Confira se algum controle ficou sem 'Control:' "
            "logo abaixo do nome."
        )

    if mark is not None and not sugestoes:
        linha_erro_texto = linhas[mark.line] if mark.line < len(linhas) else ""
        if re.match(r"^\s*-\s+\w+:", linha_erro_texto):
            sugestoes.append(
                "A linha apontada é um item de lista ('- nome:') que provavelmente está com "
                "indentação diferente dos seus irmãos (ou aninhado um nível errado por causa de "
                "uma cascata vinda de um erro anterior no arquivo — padrão #2 do catálogo). "
                "Veja references/estrutura-payaml.md para recalcular o recuo correto deslocando "
                "o bloco inteiro, em vez de ajustar linha por linha."
            )

    if not sugestoes:
        sugestoes.append(
            "Não foi possível identificar automaticamente o padrão. Revise manualmente a "
            "indentação e os caracteres especiais (':', '{', '}') perto da linha indicada."
        )

    print("  Diagnóstico sugerido:")
    for s in sugestoes:
        print(f"   - {s}")


def encontrar_entidades_html(texto):
    problemas = []
    for i, linha in enumerate(texto.splitlines(), start=1):
        if re.search(r"&(amp|lt|gt|quot|#39);", linha):
            problemas.append((i, linha.strip()))
    return problemas


def walk(node, path, achados):
    if isinstance(node, dict):
        ctrl = node.get("Control")
        if isinstance(ctrl, str):
            base_ctrl = ctrl.split("@")[0]
            props = node.get("Properties") or {}
            if isinstance(props, dict):
                radii = [k for k in props if k.startswith("Radius")]
                if radii and base_ctrl in ("Label", "Rectangle"):
                    achados["radius_invalido"].append((path, ctrl, radii))
            if base_ctrl == "Gallery":
                variant = node.get("Variant")
                if not variant:
                    achados["gallery_sem_variant"].append(path)
                elif isinstance(variant, str) and "." in variant:
                    achados["gallery_variant_suspeita"].append((path, variant))
        for k, v in node.items():
            if v is None:
                achados["valores_none"].append(path + "/" + str(k))
            else:
                walk(v, path + "/" + str(k), achados)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            chave_filho = None
            if isinstance(item, dict) and len(item) == 1:
                chave_filho = next(iter(item))
            label = f"[{i}:{chave_filho}]" if chave_filho else f"[{i}]"
            walk(item, path + label, achados)


def validar_arquivo(caminho):
    print(f"\n=== {caminho} ===")
    with open(caminho, encoding="utf-8") as f:
        texto = f.read()

    try:
        data = yaml.safe_load(texto)
    except yaml.YAMLError as erro:
        print("FALHA AO PARSEAR O YAML.")
        diagnosticar_erro_parse(texto, erro)
        return False

    achados = {
        "valores_none": [],
        "radius_invalido": [],
        "gallery_sem_variant": [],
        "gallery_variant_suspeita": [],
    }
    walk(data, "", achados)
    entidades = encontrar_entidades_html(texto)

    tudo_ok = True

    if achados["valores_none"]:
        tudo_ok = False
        print("✗ Valores nulos encontrados (provável chave duplicada / aninhamento quebrado):")
        for p in achados["valores_none"]:
            print(f"    {p}")

    if achados["radius_invalido"]:
        tudo_ok = False
        print("✗ Propriedades 'Radius*' em controle que não suporta (Label/Rectangle):")
        for path, ctrl, radii in achados["radius_invalido"]:
            print(f"    {path}  [{ctrl}]  ->  {', '.join(radii)}")

    if achados["gallery_sem_variant"]:
        tudo_ok = False
        print("✗ Gallery sem 'Variant' definido:")
        for p in achados["gallery_sem_variant"]:
            print(f"    {p}")

    if achados["gallery_variant_suspeita"]:
        tudo_ok = False
        print("✗ Gallery com 'Variant' suspeito (contém '.', ex. 'BrowseLayout.Vertical'):")
        for p, v in achados["gallery_variant_suspeita"]:
            print(f"    {p}  ->  Variant: {v}  (provavelmente deveria ser só 'Vertical')")

    if entidades:
        tudo_ok = False
        print("✗ Entidades HTML não decodificadas dentro do arquivo (&amp; &lt; &gt;):")
        for i, linha in entidades[:10]:
            print(f"    linha {i}: {linha}")
        if len(entidades) > 10:
            print(f"    ... e mais {len(entidades) - 10} ocorrência(s).")

    if tudo_ok:
        print("✓ Nenhum problema conhecido encontrado. YAML válido e dentro dos padrões.")

    return tudo_ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    resultado_geral = True
    for caminho in sys.argv[1:]:
        ok = validar_arquivo(caminho)
        resultado_geral = resultado_geral and ok

    sys.exit(0 if resultado_geral else 1)


if __name__ == "__main__":
    main()
