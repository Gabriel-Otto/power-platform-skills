# Power Platform Skills para o Claude

Duas skills para o Claude trabalhar com **Power Automate** e **Power Apps** sem quebrar na importação. São regras, armadilhas e validações aprendidas em projetos reais, já testadas em importação de verdade.

| Skill | Para que serve |
|---|---|
| [`power-automate`](plugins/power-platform/skills/power-automate/SKILL.md) | Criar, importar, exportar ou corrigir fluxos em **ZIP**: pacotes legados (`definition.json`) e **soluções Dataverse** (`solution.xml`), inclusive com agentes do Copilot Studio. Traz operationIds confirmados (SharePoint, Outlook, OneDrive, Copilot Studio), armadilhas de expressões e tabela de erros comuns. |
| [`payaml`](plugins/power-platform/skills/payaml/SKILL.md) | Criar e corrigir apps **Power Apps em YAML** (`.pa.yaml` / Source Code) e pacotes de importação (`.zip` / `.msapp`). Catálogo de erros do compilador (PA1001, PA2108, PA2109, PA1011…), **validador em Python**, edição do `.msapp` sem o Studio e checklist de "blindagem" de apps SharePoint (Patch, coluna Pessoa, delegação, deep link). |

## Instalação

### Claude Code (direto do GitHub)

```bash
claude plugin marketplace add Gabriel-Otto/power-platform-skills
claude plugin install power-platform@power-platform-skills
```

Ou, dentro de uma sessão: `/plugin marketplace add Gabriel-Otto/power-platform-skills` e depois `/plugin install power-platform@power-platform-skills`.

As skills ficam disponíveis como `/power-platform:power-automate` e `/power-platform:payaml`, e o Claude também as usa sozinho quando o assunto aparece.

**Sem plugin:** copie as pastas de `plugins/power-platform/skills/` para `~/.claude/skills/` (todas as sessões) ou `.claude/skills/` (só no projeto).

### Claude (app web / desktop)

1. Baixe a pasta da skill como `.zip`. Por exemplo, cole o link da pasta ([power-automate](https://github.com/Gabriel-Otto/power-platform-skills/tree/main/plugins/power-platform/skills/power-automate) ou [payaml](https://github.com/Gabriel-Otto/power-platform-skills/tree/main/plugins/power-platform/skills/payaml)) em [download-directory.github.io](https://download-directory.github.io/). Outra opção é baixar o repositório inteiro e compactar só a pasta da skill.
2. Nas configurações do Claude, na área de **Skills**, envie o `.zip` (o recurso de skills precisa estar ativado na sua conta).

## Exemplos de uso

- *"Gere um fluxo do Power Automate que, ao receber um item novo na lista X do SharePoint, envia e-mail ao responsável. Quero o ZIP para importar."*
- *"Importei a solução e deu este erro: `already installed ... as an unmanaged solution`. Corrija o pacote."*
- *"Meu YAML do Power Apps dá `PA1001 YamlInvalidSyntax` na linha 120. Segue o código."*
- *"O app salva com sucesso, mas o campo Responsável (Pessoa) não muda no SharePoint."*

## Validador do `payaml`

```bash
pip install pyyaml
python plugins/power-platform/skills/payaml/scripts/validate_payaml.py MinhaTela.pa.yaml
```

Aponta linha e coluna do erro, sugere qual padrão do catálogo é a causa e procura problemas que o compilador só mostraria depois (Radius em Label/Rectangle, Gallery sem Variant, entidades HTML, chaves nulas).

## Contribuindo

Achou um operationId, parâmetro ou erro novo? Abra uma *issue* ou um *pull request* com o JSON copiado do designer (`...` → "Copiar para área de transferência") ou com a mensagem de erro exata.

---

Feito por **Gabriel Otto** · [LinkedIn](https://www.linkedin.com/in/gabrielottoaurich/) · Licença [MIT](LICENSE)

<details>
<summary><b>English</b></summary>

Two Claude skills for **Power Automate** (build/fix importable flow ZIPs and Dataverse solutions) and **Power Apps YAML** (`.pa.yaml`/`.msapp`, compiler error catalog and a Python validator). Content is in Portuguese.

Install in Claude Code: `claude plugin marketplace add Gabriel-Otto/power-platform-skills` then `claude plugin install power-platform@power-platform-skills`.

</details>
