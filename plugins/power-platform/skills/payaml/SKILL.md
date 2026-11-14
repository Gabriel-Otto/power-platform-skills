---
name: "payaml"
description: "Crie, corrija e blinde apps Power Apps em YAML (pa.yaml / Source Code) e pacotes de importação (.zip/.msapp). Use ao colar YAML com erro do compilador (PA1001, PA2108, PA2109, PA1011, YamlInvalidSyntax, Unknown property/variant), pedir para corrigir código, criar tela nova, remontar/reempacotar o app para importar ou testar pelo .msapp, quando a importação do pacote falha, ou quando o app SharePoint dá erro de Patch, não salva (ex.: Responsável/coluna Pessoa), demora para salvar/carregar ou tem avisos de delegação."
---

# Correção e criação de YAML do Power Apps (PaYaml / "Source Code" schema)

## Por que isso importa

O formato YAML de telas do Power Apps (".pa.yaml", schema "Source Code") parece YAML comum,
mas tem armadilhas específicas que quebram o parser mesmo quando o código "parece certo"
visualmente. Código gerado por IA quase sempre cai nessas mesmas armadilhas — porque elas não
são visíveis a olho nu, só aparecem quando o parser tenta ler a indentação ou os caracteres
literalmente. O objetivo desta skill é tratar cada correção com o mesmo rigor: localizar a
causa raiz exata, corrigir cirurgicamente, e **validar com um parser de verdade antes de
entregar** — nunca confiar só na leitura visual.

## Fluxo de trabalho

1. **Recrie o arquivo localmente.** Cole o YAML do usuário em um arquivo de trabalho. Se houver
   entidades HTML (`&amp;`, `&lt;`, `&gt;`) dentro das fórmulas, decodifique para os caracteres
   reais (`&`, `<`, `>`) — geralmente são artefato de como o código foi colado, e o Power Fx
   real precisa dos caracteres literais.
2. **Localize a linha/coluna exata do erro** reportado (formato `(linha,coluna) : erro CÓDIGO`).
   Use o catálogo abaixo para identificar o padrão.
3. **Corrija a causa raiz**, não só o sintoma. Vários erros desse formato são cascata: o
   compilador para no primeiro problema e nem chega a validar o resto do arquivo. Depois de
   corrigir o erro relatado, **sempre rode uma busca pelo arquivo inteiro pelo mesmo padrão**
   (ver `scripts/validate_payaml.py`) — é extremamente comum o mesmo erro se repetir mais
   adiante e só não ter sido reportado ainda.
4. **Valide com o script antes de responder:**
   ```bash
   python3 scripts/validate_payaml.py caminho/arquivo.yaml
   ```
   Só entregue o arquivo corrigido depois que o script não reportar nenhum problema. Se o
   parser falhar, o script aponta a linha/coluna exata para você investigar — não tente
   adivinhar visualmente se a indentação está certa.
5. **Liste rapidamente o que foi corrigido**, sem precisar reexplicar o arquivo inteiro: erro
   reportado → causa → correção, e qualquer problema extra encontrado proativamente.

Ao **criar um YAML novo do zero**, siga a mesma lógica ao contrário: use o checklist da seção
"Criando YAML novo" para não introduzir esses erros, e ainda assim rode o validador no final.

---

## Catálogo de erros conhecidos

### 1. `PA1001 YamlInvalidSyntax` — "While parsing a block mapping, did not find expected key"

**Causa quase sempre:** uma fórmula Power Fx multilinha foi escrita como **escalar simples**
(sem `|` ou `|-`), e a linha de fechamento (`)`, `}`) voltou para a **mesma indentação da
chave**. Em YAML, a continuação de um escalar simples precisa ficar **mais indentada** que a
chave — se uma linha volta para o mesmo nível, o YAML entende que ali começa uma nova chave do
mapeamento, e como `)` não é uma chave válida, dá esse erro.

Errado (a indentação do `)` é igual à de `Color:`):
```yaml
Color: =If(
    condição,
    RGBA(192, 57, 43, 1),
    RGBA(17, 24, 39, 1)
)
Height: =22
```

Corrigido (vira bloco literal `|-`, com TODO o conteúdo — inclusive o fecha-parênteses —
indentado a mais que a chave):
```yaml
Color: |-
  =If(
      condição,
      RGBA(192, 57, 43, 1),
      RGBA(17, 24, 39, 1)
  )
Height: =22
```

Use `|-` (não `|`) quando a fórmula é só Power Fx sem quebra de linha final desejada — é o
padrão usado nos arquivos originais do Power Apps Studio para fórmulas de uma propriedade só.

### 2. `PA1001 YamlInvalidSyntax` — "Named object value cannot be null"

**Causa:** um controle foi acidentalmente embrulhado numa camada extra de `Children:` com o
**mesmo nome** duplicado dentro, por exemplo:

```yaml
- lblCategoria:
    Children:
      - lblCategoria:
          Control: Label@2.5.1
          ...
```

Isso faz `lblCategoria` (o de fora) não ter `Control`/`Properties` — só um `Children` —
então o "objeto nomeado" fica sem valor (null). A correção é remover o embrulho e devolver
`Control`/`Properties` direto no item:

```yaml
- lblCategoria:
    Control: Label@2.5.1
    Properties:
      ...
```

**Atenção:** esse tipo de erro de cópia/cola quase sempre desloca a indentação de TODOS os
itens irmãos que vêm depois (eles ficam aninhados um nível mais profundo do que deveriam,
dentro do controle errado). Corrigir só a linha do erro não basta — é preciso realinhar o
bloco inteiro até o próximo ponto em que a estrutura volta a fazer sentido. Veja
`references/estrutura-payaml.md` para o modelo de indentação usado para recalcular os recuos
corretos com segurança.

### 3. Texto de uma linha com `": "` dentro de uma string da fórmula

Mesmo dentro de aspas do Power Fx, o YAML não sabe que aquilo é uma string — ele lê o
caractere `:` seguido de espaço e tenta interpretar como separador de chave/valor.

Errado:
```yaml
Text: ="Selecionado: " & If(varImpacto = 0, "—", Text(varImpacto))
```

Corrigido (qualquer linha assim deve virar bloco `|-`):
```yaml
Text: |-
  ="Selecionado: " & If(varImpacto = 0, "—", Text(varImpacto))
```

O mesmo vale para registros/objetos do Power Fx escritos inline, tipo
`{searchTerm: Self.SearchText, top: 15}` — o `:` dentro do `{}` quebra o escalar simples.
Nesse caso o padrão usado no projeto original é bloco `|` (não `|-`):
```yaml
Items: |
  =UsuáriosdoOffice365.SearchUser({searchTerm: Self.SearchText, top: 15})
```

### 4. `PA2108` — "Unknown property 'RadiusTopLeft/RadiusTopRight/RadiusBottomLeft/RadiusBottomRight' for control type 'X'"

Nem todo controle aceita cantos arredondados por propriedade. Pelos erros observados:

| Controle | Aceita `Radius*`? |
|---|---|
| `GroupContainer@1.x` | Sim |
| `Classic/Button@2.x` | Sim |
| `Classic/TextInput@2.x` | Sim |
| `Rectangle@2.3.0` | **Não** |
| `Label@2.5.1` | **Não** |

Se o controle for `Rectangle` ou `Label`, a correção é **remover as 4 linhas** de
`RadiusBottomLeft/RadiusBottomRight/RadiusTopLeft/RadiusTopRight` (não existe substituto —
esses controles não desenham canto arredondado nessa versão). Esse erro é extremamente comum
em "badges"/pílulas de status feitas com `Label` e em fundos feitos com `Rectangle` —
sempre vale procurar por **todas** as ocorrências no arquivo, não só a primeira reportada.

### 5. `PA2109` — "Unknown variant 'BrowseLayout.Vertical' for control type 'Gallery@2.15.0'"

A variante de `Gallery` não usa o prefixo `BrowseLayout.`. O valor correto observado é só:
```yaml
Variant: Vertical
```
Sempre que vir `Variant: BrowseLayout.Vertical` (ou qualquer `Variant` com um ponto, tipo
`Algo.Vertical`) em uma Gallery, troque para a palavra simples.

### 6. `PA1011` — "The keyword 'Variant' is required but is missing or empty"

Alguns controles (Gallery é o caso mais comum) exigem `Variant` mesmo quando não é óbvio.
Se faltar, adicione `Variant: Vertical` (para galerias de lista vertical, que é o caso mais
comum neste projeto) logo abaixo de `Control:`.

---

## Checklist ao criar YAML novo (para não cair nesses erros)

- **Toda fórmula que tenha quebra de linha** (qualquer `If(`, `Switch(`, `Patch(` formatado em
  várias linhas) **sempre** vira bloco `Propriedade: |-` (ou `|` se quiser manter a quebra de
  linha final), nunca escalar simples de várias linhas.
- **Toda fórmula de uma linha só que tenha `": "` dentro de uma string entre aspas**, ou que
  use sintaxe de registro `{chave: valor}` inline, também vira bloco `|-` (ou `|`). É mais
  seguro usar bloco sempre que a fórmula tiver qualquer `:` que não seja o `Propriedade:` do
  YAML.
- **Nunca** coloque `Radius*` em `Rectangle` ou `Label`. Para cantos arredondados, use
  `GroupContainer`, `Classic/Button` ou `Classic/TextInput`.
- **Gallery sempre precisa de `Variant: Vertical`** (ou `Horizontal`, se for o caso) — nunca
  use prefixos como `BrowseLayout.`.
- **Indentação:** dentro de um item de lista (`- nomeDoControle:`), as chaves `Control:`,
  `Variant:`, `Properties:`, `Children:` ficam todas no mesmo nível de recuo; o conteúdo de
  `Properties:` e os itens de `Children:` ficam um nível mais recuados. Itens irmãos na mesma
  lista (`- item1:`, `- item2:`) têm que ter exatamente a mesma indentação. Veja
  `references/estrutura-payaml.md` para o detalhamento.
- Depois de escrever, **rode `scripts/validate_payaml.py`** no resultado antes de entregar.

---

## Validação automática

Use sempre o script bundled em vez de reescrever esses checks na mão a cada vez:

```bash
python3 scripts/validate_payaml.py caminho/do/arquivo.yaml
```

Ele faz, nessa ordem:
1. Tenta parsear com PyYAML; se falhar, mostra linha/coluna do erro e dá um diagnóstico
   sugerido (qual dos padrões do catálogo provavelmente é a causa, baseado no texto do erro
   e no que tem perto da linha indicada).
2. Se parseou, varre a árvore inteira procurando:
   - valores `None` (sinal de chave duplicada/aninhamento quebrado — erro #2 do catálogo)
   - `Radius*` em `Label`/`Rectangle` (erro #4)
   - `Gallery` sem `Variant` ou com `Variant` contendo `.` (erros #5/#6)
   - entidades HTML não decodificadas (`&amp;`, `&lt;`, `&gt;`) dentro de fórmulas
3. Imprime um relatório claro em português com cada problema encontrado e a linha.

Se o usuário pedir para criar/corrigir vários arquivos na mesma conversa, rode o script em
cada um — não pule a validação mesmo que o arquivo "pareça" simples.

Para mais detalhes sobre a estrutura de indentação do formato (necessário quando um erro de
chave duplicada desalinha vários blocos em cascata), veja `references/estrutura-payaml.md`.

---

## Validador: falsos positivos conhecidos

- **`PaddingTop: =` (fórmula vazia)** faz o PyYAML falhar com
  `could not determine a constructor for the tag 'tag:yaml.org,2002:value'`. Isso NÃO é erro:
  o próprio Studio exporta propriedades vazias assim. Antes de validar, registre o construtor:
  ```python
  import yaml
  yaml.SafeLoader.add_constructor('tag:yaml.org,2002:value', lambda l, n: l.construct_scalar(n))
  ```
  (copie o `validate_payaml.py` para a pasta de trabalho e adicione essas 2 linhas logo depois do
  bloco `try: import yaml ... except ImportError: ... sys.exit(2)` — **não** dentro do `try`).
- **`Variant: BrowseLayout_Flexible_SocialFeed_ver5.0`** (e similares com `_ver5.0`) em Gallery são
  variantes legítimas exportadas pelo Studio — o alerta "Variant contém '.'" só vale para o padrão
  `BrowseLayout.Vertical`. Não altere variantes que vieram do export original.
- **`&amp;`/`&lt;`/`&gt;` dentro de `Substitute(...)`** que escapa texto para um `HtmlText` é intencional
  (é o próprio escape de HTML), não artefato de colagem — não decodifique.
- Além do parser, rode uma checagem de **balanceamento de `()[]{}` e aspas** em toda fórmula
  alterada (removendo strings e comentários `//` antes) — pega erros de Power Fx que o YAML aceita.

---

## Entrega: colar YAML vs. pacote de importação (.zip)

- Um zip só com `.pa.yaml` **não importa** ("O arquivo de manifesto não pôde ser encontrado no
  pacote de importação"). Se o usuário vai usar **Aplicativos > Importar aplicativo de tela**, é
  preciso devolver o pacote no mesmo formato do export: `manifest.json` + `Microsoft.PowerApps/apps/<id>/`
  (`<id>.json`, `*-identity.json`, `*-document.msapp`, logo), mesma ordem e nomes de entrada.
- O `.msapp` é um zip com caminhos usando **barra invertida** (`Src\Tela.pa.yaml`, `Controls\4.json`).
  Extraia em Python trocando `\` por `/`, e ao reempacotar grave de volta com os nomes originais.
- **O Studio carrega do `Controls/*.json`, não do `Src/*.pa.yaml`** (os yaml são só para revisão).
  Para o pacote refletir as correções:
  1. Para cada controle/propriedade alterada no YAML, atualize em `Controls/<n>.json` a entrada de
     `Rules` (`Property`, `InvariantScript` = fórmula SEM o `=` inicial, `RuleProviderType: "User"`,
     `Category`: `Behavior` para `On*`, senão `Data`/`Design`) e garanta o nome em `ControlPropertyState`.
  2. **Desligue `AutoRuleBindingEnabled`** (`false`) na entrada de `ControlPropertyState` de toda
     propriedade alterada. Em cards travados (`IsLocked: true`, ex.: DataCards de formulário), o
     Studio regrava `Update`/`Items`/`Default` com o valor automático ao abrir — a correção "some"
     sem erro. Também defina `IsLocked: false` nesses cards.
  3. Controles novos: clone o JSON de um controle do mesmo tipo já existente no app, troque `Name`,
     `Parent`, `ControlUniqueId` (maior existente + 1), `Index`/`PublishOrderIndex`, e remova
     regras que referenciam filhos não clonados. Trocar o tipo de um controle (ex.: ComboBox clássico
     → ModernCombobox) = substituir o nó pelo clone mantendo o `Name`.
  4. Atualize também `Src/*.pa.yaml` dentro do msapp e `ControlCount` em `Properties.json`. O
     `*-identity.json` do pacote pode ficar como o original (o Studio completa os nomes novos); se mexer,
     grave compacto (`separators=(',', ':')`).
  5. Para testar, entregue **também o `.msapp` solto** (ver "Testar sem importar" abaixo). Se for importar,
     oriente **"Criar como novo"** primeiro (teste) antes de "Atualizar" o app de produção.
- Ao passar fórmulas para o usuário **colar no Studio em pt-BR**, converta: `,` → `;` entre
  argumentos e `;` → `;;` no encadeamento. Dentro do `.pa.yaml`/JSON a sintaxe é sempre a
  invariante (en-US: `,` e `;`).

---

## Armadilhas de Power Fx em runtime (apps SharePoint) — checklist de "blindagem"

Quando o pedido for "o app dá erro / não salva / demora", revise estes pontos:

1. **`SubmitForm` não espera terminar.** Nada de `Refresh`/`Set(var, LookUp(...))`/`Navigate`
   logo depois dele. Guarde (`Set(varSalvando, true)`), faça `SubmitForm` e trate tudo em
   `OnSuccess` (atualiza coleção, notifica, navega) e `OnFailure` (libera flag, mostra
   `Form.Error`, **mantém o usuário na tela** com os dados).
2. **Vários `Patch` seguidos no mesmo item no `OnSuccess`** (histórico, status...) geram
   "Erro de rede ao usar a função Patch: Ocorreu um erro no servidor". Leve os campos extras para
   **cards ocultos no próprio formulário** (um único envio) ou para um único `Patch`.
3. **`{Value: Blank()}` em coluna Choice** → erro de servidor. Sempre
   `{Value: Coalesce(dd.Selected.Value, "Sem Status")}` ou bloqueie o salvar se vazio.
4. **Trocar o `Item` do formulário (Set da variável) depois de um Patch de outra parte da tela**
   reseta os campos e apaga o que o usuário digitou. Use uma variável separada
   (ex.: `varRegistroAtual`) para o que é exibido/atualizado fora do form.
5. **Histórico/observação sobrescritos:** ao anexar histórico, parta do registro fresco
   (`LookUp(DS, ID = x)`), não do registro da coleção; pré-preencha campos de observação com o
   valor atual (senão salvar só o status apaga a observação).
6. **Recarregar a base inteira a cada ação** (OnVisible, botão X, após salvar) deixa o app lento.
   Carregue uma vez (flag + validade em minutos), e após cada operação atualize só o registro:
   ```
   If(IsBlank(LookUp(col, ID = r.ID)), Collect(col, r), Patch(col, LookUp(col, ID = r.ID), r))
   ```
   Exclusão: `IfError(Remove(DS, LookUp(DS, ID = x)), Notify(erro), RemoveIf(col, ID = x); Notify(ok))`.
   Popups devem abrir instantaneamente — nenhuma chamada à fonte antes de mostrar.
7. **Carga > 2000 itens sem aviso de delegação:** a coluna `ID` do SharePoint só delega `=`; use
   uma coluna número (ex.: `ID_Index`) e **faixas constantes** (a variável de escopo do `ForAll`
   dentro do `Filter` e `IsBlank()` geram aviso de delegação):
   ```
   If(_max > 0,    Collect(tmp, Filter(DS, ID_Index > 0    && ID_Index <= 2000)));
   If(_max > 2000, Collect(tmp, Filter(DS, ID_Index > 2000 && ID_Index <= 4000)));  // ...
   ```
   `_max` = `First(Sort(DS, ID, SortOrder.Descending)).ID` (delegável). Carregue em coleção
   temporária e só no fim `ClearCollect(colPrincipal, tmp)`.
8. **Itens criados sem o índice (Patch pós-criação falhou) ficam invisíveis.** Na criação use
   `Patch(DS, LookUp(DS, ID = id), {ID_Index: id})` com 1 retentativa via `IfError`, e na carga
   faça autocorreção delegável: percorra os ~100 IDs mais recentes com `LookUp(DS, ID = n)`
   (só os que não vieram na carga) e grave o índice. Nunca use `Form.LastSubmit` como base de Patch.
9. **Clique duplo** em Criar/Salvar/Excluir duplica registros: flag (`varSalvandoNovo` etc.) no
   `OnSelect` + `DisplayMode` desabilitado + texto "Salvando...".
10. **`Reset()` só funciona em controle fora de formulário/galeria** (ou dentro do mesmo). Na tela,
    use `ResetForm(Form)`; nunca `Reset(DataCardValueX)` no `OnVisible`.

### Coluna Pessoa (SharePoint) — Responsável que "salva com sucesso" mas não muda

- **`Choices([@Lista].Pessoa)` + `SearchFields: ["Claims"]`** não encontra ninguém pelo nome.
  Use `UtilizadoresdoOffice365.SearchUser({searchTerm: Self.SearchText, top: 25})` (bloco `|-`
  por causa do `{chave: valor}`).
- **ComboBox clássico com Items do Office 365 perde o `.Selected`** quando a busca é refeita
  com texto vazio → o `Update` cai no fallback "manter atual" e nada muda, sem erro.
  **Use `ModernCombobox@1.1.2`** (`ItemDisplayText: =ThisItem.DisplayName`) e capture a escolha no
  `OnChange` numa variável; o `Update` do card lê a variável (com o `.Selected` como reforço):
  ```
  OnChange: =With({_u: Self.Selected}, If(IsBlank(Coalesce(_u.UserPrincipalName, _u.Mail)),
      Set(varRespNovo, Blank()),
      Set(varRespNovo, {Nome: _u.DisplayName, Login: Lower(Coalesce(_u.UserPrincipalName, _u.Mail)),
                        Email: Coalesce(_u.Mail, _u.UserPrincipalName)})))
  Update (card):
  {'@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedUser",
   Claims: "i:0#.f|membership|" & varRespNovo.Login, Department: "",
   DisplayName: varRespNovo.Nome, Email: varRespNovo.Email, JobTitle: "", Picture: ""}
  ```
  Limpe `varRespNovo` no `OnVisible` da tela e após salvar.
- **Claims pelo UPN, não pelo Mail** (`UserPrincipalName` primeiro). O erro
  "O usuário i:0#.f|membership|... especificado não foi encontrado" significa login inexistente
  ou vazio — se aparecer `membership|` sem nada depois, a variável/seleção está vazia (bug do app,
  não do SharePoint).
- Dentro de um card, prefira `ThisItem.Pessoa.Email` a `Parent.Default.Email` (após trocar os
  Items do combo, `Parent.Default` pode perder o tipo: "O nome não é válido. 'Email' não é reconhecido").
- **Blindagem pós-salvar:** no `OnSuccess`, relê o item e compara `Lower(_srv.Pessoa.Claims)` com o
  Claims desejado; se diferente, `Patch` direto só da pessoa; se ainda falhar, mostra aviso em vez
  de "salvo com sucesso".
- **Roteiro de diagnóstico** quando "não salva": (1) ver a variável no painel Variáveis após
  escolher; (2) botão de teste com `Patch` direto usando a variável + `Notify("Login: [" & ... & "]")`;
  (3) Histórico de versões do item no SharePoint + fluxos do Power Automate na lista (algo
  revertendo o campo).

### Deep link (`Param`) e OnStart não bloqueante — "o link do e-mail abre a tela mas sem a solicitação"

- Confira `AppPreviewFlagsMap.usenonblockingonstartrule` em `Properties.json`. Se `true`, o `StartScreen`
  (ex.: `If(!IsBlank(Param("solicitacao")), scr_detalhe, scr_login)`) abre a tela e roda o `OnVisible`
  **antes do OnStart terminar**: variáveis como `vSolicitacaoSel`, `vEmailLogado`, `vTipoPerfil` ainda estão vazias.
  Pela galeria funciona porque o `OnSelect` faz `Set(vSolicitacaoSel, ThisItem)` antes de navegar.
- Correção: a tela de destino precisa ser **autossuficiente** no `OnVisible`:
  1. se `IsBlank(vEmailLogado)`, carrega usuário/perfil ali mesmo (`User().Email`, `LookUp(lista_usuarios, ...)`);
  2. consome o parâmetro uma única vez com flag (`!vDeepLinkLido And !IsBlank(Param("x"))` → `Set(vDeepLinkLido, true)`),
     senão toda navegação posterior para a tela volta a abrir o registro do link;
  3. busca o registro **na fonte** (a coleção pode não ter carregado ou estar cortada em 500/2000 linhas) e o
     coloca na coleção usada pelas galerias para manter o **mesmo tipo** da variável:
     `With({_sol: LookUp(Lista, Title = _id)}, If(!IsBlank(_sol), Collect(col_visiveis, _sol))); Set(vSel, LookUp(col_visiveis, Title = _id))`;
  4. no OnStart, só sobrescreva a variável do deep link se ela ainda estiver vazia ou for o mesmo registro
     (o OnStart termina depois e pode apagar o que a tela já carregou / o que o usuário abriu).
- Confirme no fluxo qual valor vai no link (`&solicitacao=@{triggerBody()?['text']}`) e se é o mesmo campo usado no `LookUp` (ex.: `Title` "SOL-123").

### Departamento/área do usuário vindo errado (ex.: todo mundo cai em "Suprimentos")

- `Pessoa.Department` de coluna Pessoa do SharePoint (ex.: `vPerfilLogado.usuario.Department`) vem do perfil do
  site e costuma estar **vazio** para muitos usuários → cai no fallback fixo. Funciona "só com o meu" porque o perfil
  do criador está sincronizado. O `OnChange` do combo funciona porque usa o Office 365 (`Self.Selected.Department`).
- Use a mesma fonte no carregamento: `Coalesce(IfError(UsuáriosdoOffice365.MyProfileV2().department, ""), gMe.department,
  vPerfilLogado.depto, vPerfilLogado.usuario.Department, "Padrão")` (o `Coalesce` pula `""`).

### Tela restrita por perfil

- **`Navigate` NÃO pode ser usado no `OnVisible`** (erro do Studio: "A navegação não pode ser usada em OnVisible").
  Nunca proponha redirecionar a partir do `OnVisible`.
- O controle de acesso mais simples é **esconder a aba no menu** (`gNav` por perfil). Se quiser
  reforço, no `OnVisible` apenas não carregue os dados (`If(<perfil permitido>, <carga>)`) e/ou cubra o conteúdo com um
  container "Acesso restrito" (`Visible` pela mesma regra), sem navegar.
- Use a **mesma regra** no menu e na tela (ex.: um `OnVisible` que checa só um perfil acaba barrando o Administrador).
- JSON de `Controls/*.json` do export vem com `indent=2` e CRLF: regrave no mesmo formato
  (`json.dumps(d, ensure_ascii=False, indent=2).replace("\n", "\r\n")`, `newline=""`) para o diff ficar só nas regras alteradas.
  Os scripts podem ter `\xa0` (espaço não separável) — a regex tolerante com `\s*` cobre.

---

## Edição direta do pacote (.msapp) — mudanças grandes sem o Studio

Ao alterar o app pelo pacote (sem o Studio), trate o `Controls/*.json` como fonte da verdade e replique
cada mudança no `Src/*.pa.yaml`. Fluxo recomendado:

1. **Biblioteca única de edição:** funções `set_prop(controle, prop, formula)`, `clone(modelo, nome, regras)`,
   `insert(pai, nó, after/before/last)` que alteram o JSON **e registram a mesma operação** para replicar no YAML.
   Rode o script sempre a partir do export original (reprodutível), nunca em cima de uma cópia já editada.
   Em apps grandes, divida em etapas (arquivos encadeados) e valide ao fim de cada uma.
2. **Antes de definir qualquer propriedade, confira se ela existe no tipo do controle** em
   `References/Templates.json` (`re.findall(r'name="([A-Za-z]+)"', template)`). Erros reais encontrados:
   - `ModernDropdown@1.0.3` usa **`Default`** (um registro), **não** `DefaultSelectedItems` (isso é do `ModernCombobox`).
     Ex.: `Default: =If(IsBlank(varEdit), Blank(), LookUp(colSimNao, Value = If(varEdit.GxP, "Sim", "Não")))`.
   - `Classic/Button@2.2.0` **não tem** `AccessibleLabel` (o `Classic/TextInput` tem).
3. **Fórmulas no JSON têm espaçamento/quebra diferentes do YAML** (às vezes `\r\n`, recuo menor).
   Nunca faça `str.replace` com o texto copiado do YAML: use regex tolerante a espaços
   (`r"\s*".join(re.escape(t) for t in antigo.split())`) e confira a contagem de ocorrências.
   No YAML, o objeto `App` (OnStart) não tem `Children:` — trate o fim do bloco como fim do arquivo.
4. **`PublishOrderIndex`** é global e crescente entre telas, em pré-ordem (DFS); a tela (TopParent) fica com 0.
   Depois de inserir controles, renumere todas as telas em ordem DFS, mantendo a ordem relativa original.
5. **Tela nova:** clone a árvore de uma tela parecida (`deepcopy`), renomeie todos os controles (sufixo) e
   **reescreva as referências** nas fórmulas com regex de palavra inteira (sem renomear o nome de outras telas
   usadas em `Navigate`). Novo `ControlUniqueId` para cada controle, `Index` da tela = próxima posição,
   arquivo `Controls/<UID da tela>.json`, `Src/<tela>.pa.yaml`, entrada em `_EditorState.pa.yaml` (ScreensOrder),
   `ControlCount.screen + 1`.
6. **Lista SharePoint nova embutida no pacote** (evita "adicione a fonte de dados no Studio"):
   - em `References/DataSources.json`, clone a entrada de uma lista existente do mesmo site, troque `Name`,
     `TableName` (GUID da lista), `DataEntityMetadataJson` (`{GUID: json}` com `name`, `title`, `webUrl` e as
     colunas no formato do conector: número = shape de uma coluna número existente, várias linhas = shape de uma
     coluna nota, texto = shape de texto) e `ConnectedDataSourceInfoNameMapping`;
   - em `Properties.json` → `LocalConnectionReferences` (string JSON), acrescente o nome em `dataSources` e
     `datasets[site].dataSources[nome] = {"tableName": GUID}` da conexão SharePoint.
   - Para obter o GUID, crie a lista via REST (`/_api/web/lists`, `/fields`) num navegador já logado; indexe a
     coluna usada em filtros (`Indexed: true`) e deixe `Title` opcional se o app não preencher sempre.
7. **Variáveis globais** que recebem registros de várias telas precisam ter **o mesmo tipo** (ex.: todas vindas
   de `colRegistros`); se uma vier da fonte (`LookUp(lista, ...)`) e outra da coleção, use variáveis diferentes.
8. **Delegação:** `LookUp(Lista, ID = _reg.ID)` com `_reg` vindo de `With`/`LookUp` em tabela local gera
   `app-SuggestRemoteExecutionHint`. Isole o valor num escalar antes: `With({_id: varReg.ID}, LookUp(Lista, ID = _id))`.
   Leia sempre o `AppCheckerResult.sarif` do pacote (regras `app-SuggestRemoteExecutionHint*`) para achar avisos existentes.
9. **Valide com um verificador automático** em toda regra `RuleProviderType: "User"`: propriedade existe no
   template, parênteses/aspas balanceados, controles citados existem, variáveis usadas são definidas por
   `Set/Collect/ClearCollect` em algum lugar, fontes `Lista` existem em `DataSources.json`.
   Ao juntar fórmulas para procurar `Set(`, **separe por quebra de linha** (concatenar sem separador quebra o `\b`).
10. **Status novos** num app com lógica de status copiada em várias telas: mapeie com `grep` todos os
    filtros, contadores, cores de etiqueta (`If(... Status = ...)` aninhados) e textos de etapa. Prefira **embrulhar**
    a fórmula existente (`If(S = "Novo1", a, S = "Novo2", b, <original>)`) a reescrever, e confira o ramo `else`
    (ex.: um `else` "Reprovada: ..." exibiria texto errado para status novo). Revise também os fluxos do
    Power Automate que reagem ao status (e-mail, Planner) para o status novo não cair no caso genérico.
11. **Formulário reaproveitado para edição** (rascunho, devolução, corrigir e reenviar): variável de entrada
    consumida no `OnVisible` (`Set(varEdit, LookUp(...varAbrir.ID)); Set(varAbrir, Blank())`) para que a navegação
    pelo menu continue abrindo em branco; `Item` do form = `varEdit`; `NewForm/EditForm` conforme o caso; no
    `OnSuccess`, um único `Patch` preservando campos de outras etapas com `Coalesce(varRegNovo.Campo, padrão)`;
    no erro, só remove a linha órfã se for criação. Antes, confira se a variável que "leva" o registro para a
    tela é realmente lida lá (já houve `Set(varReenvioDe, ...)` que nenhuma tela usava).
12. **HtmlText com `AutoHeight: true`** é a forma estável de feed/listas de texto de altura variável dentro de
    containers AutoLayout (container com `Height = 34 + titulo.Height + ... + html.Height`). Escape o texto do
    usuário (`&`, `<`, `>`) e troque `Char(10)` por `<br>`.
13. **Popup/modal:** container `ManualLayout` na raiz da tela, **último filho** e com `ZIndex` alto,
    `X: 0, Y: 0, Width: Parent.Width, Height: Parent.Height`, `Fill` semitransparente e `Visible` por variável;
    dentro, um card centralizado (`X: (Parent.Width - Self.Width) / 2`). Zere a variável no `OnVisible` da tela.

---

## Gerar telas inteiras ou um template a partir de protótipos (sem o Studio)

- Gere `Controls/*.json` **clonando um nó real do mesmo tipo** (de apps exportados) e trocando `Name`, `Parent`,
  `ControlUniqueId`, `Index`, `PublishOrderIndex`; escreva o `Src/*.pa.yaml` a partir da mesma especificação
  (uma estrutura Python `C(nome, tipo, props, filhos)` → JSON + YAML).
- Regras padrão: use o valor mais comum das regras não-`User` daquele tipo, mas **nunca herde**: regras `On*`
  (vazou `Navigate(scrLogin)` de outro app), padrões que citem nomes do app de origem (`col*`, `var*`, `scr*`, `txt*`, `g*`/`v*`…),
  `text.MaxLength` (veio `13` e cortaria o texto), `Text`/`Default`/`HintText`. Label veio com `FontWeight.Bold` como padrão →
  sempre defina `FontWeight`. GroupContainer vem com `Height = 168` / `Width = 420` → container dentro de AutoLayout vertical
  precisa de `Height` explícito ou fórmula (`42 + galX.Height`); não existe altura automática de container.
- Filho de container AutoLayout: `HasDynamicProperties: true` + `DynamicProperties` (FillPortions, AlignInContainer, LayoutMinWidth,
  LayoutMinHeight, LayoutMaxWidth, LayoutMaxHeight) no formato `{PropertyName, Rule: {...}, ControlPropertyState}`; fora de AutoLayout,
  `HasDynamicProperties: false` sem a chave. `VariantName`: `horizontalAutoLayoutContainer` (também para vertical, com `LayoutDirection`),
  `manualLayoutContainer`, galeria `galleryVertical`.
- Galeria: o primeiro filho é um nó `galleryTemplate` (Name = GUID, `Children: []`) que guarda o `OnSelect` da galeria.
- `ZIndex` sequencial pela ordem dos filhos (a ordem no AutoLayout segue o ZIndex).
- UIDs a partir do maior usado em `Controls/1.json` + `AppTests/2.json`; tela com `Index` = posição e arquivo `Controls/<UID>.json`;
  atualize `_EditorState.pa.yaml` (ScreensOrder), `ControlCount` e `Templates.json` (só os usados; copie de outro app o que faltar,
  ex.: `modernDropdown`). JSON no formato do export (`indent=2`, CRLF).
- Usando o msapp de outro app como base: tire fontes SharePoint/fluxos de `DataSources.json` e `LocalConnectionReferences`,
  renomeie o recurso de imagem em `Resources.json` (mantendo o arquivo), gere novo `Id`/`FileID` em `Properties.json`.
- Ao concatenar blocos de fórmula, cuidado com `;;` e `;` antes de `)` — deixe os blocos sem `;` final e junte explicitamente.
- **Verificador obrigatório** em todas as regras `User`: parênteses/aspas, `;;`, `;` antes de fechar, variáveis globais (`Set`),
  de contexto (`UpdateContext` na mesma tela) e coleções (`ClearCollect/Collect`) definidas, controles e telas citados existentes,
  propriedade existente no tipo, e **nenhum `Navigate` dentro de `OnVisible`**.
- Estrutura de telas sugerida para apps de solicitação: `scrLogin` (ponto único de carga), `scrInicio`, `scrLista`, `scrDetalhe`,
  `scrFormulario`, `scrAdmin`, `scrComponentes`, `scrAjuda`; `colStatus` = fonte única de status, frases de etapa e cores das pílulas.
  **Atenção:** é comum tentar resolver deep link e bloqueio de perfil com `Navigate` no `OnVisible` (scrLogin, scrDetalhe,
  scrAdmin) — isso não compila. Deep link correto: `StartScreen = If(!IsBlank(Param("id")), scrDetalhe, scrLogin)` com a
  scrDetalhe autossuficiente (carrega usuário/registro no próprio `OnVisible`), ou o usuário clica em "Entrar" e o botão navega
  para o detalhe quando houver `Param("id")`.

---

## Testar sem importar: abrir o `.msapp` direto no Studio

Método preferido para o usuário **testar uma versão sem aplicar a importação** (e a saída quando a
importação do pacote falha). Sempre entregue, junto com o `.zip`, o `.msapp` solto com nome claro
(ex.: `APP_v10.msapp` = cópia do `*-document.msapp` já remontado).

Passo a passo para o usuário:
1. make.powerapps.com › **+ Criar › Aplicativo de tela em branco** (abre o Studio).
2. No Studio: **Arquivo › Abrir › Procurar** › escolher o `.msapp`.
3. Testar. Ao **Salvar**, o Studio normalmente cria uma **cópia nova** (outro ID/link) — o app de produção
   fica intacto. Avise que links fixos no app/fluxos (`vAppLink`, deep link dos e-mails) apontam para o app
   oficial; para virar produção, importe o pacote com "Atualizar" (ou salve por cima do app oficial).
4. Os fluxos **não** são importados por esse caminho: o app usa os fluxos já existentes no ambiente
   (mudanças nos fluxos precisam ir por import próprio ou edição no Power Automate).

## Importação do pacote falhou — diagnóstico

- **"Ocorreu um erro. Tente novamente mais tarde."** é genérico. Peça a aba **Rede (Network) › Fetch/XHR**
  do F12, linha vermelha › **Response** (a aba Console só tem ruído de CSP/`ERR_BLOCKED_BY_CLIENT`).
- **Variáveis de ambiente quebram a importação legada** (fora de solução). Quando o usuário re-adiciona uma
  lista SharePoint no Studio com `autocreateenvironmentvariables: true` (em `Properties.json` ›
  `AppPreviewFlagsMap`), o export passa a ter em `LocalConnectionReferences` (e no `<id>.json` do pacote,
  `connectionReferences`) um dataset extra `"<site>_new_shared_sharepointonline_..."` com `datasetOverride` /
  `tableNameOverride` + `environmentVariableName`. Correção: mover essas listas para o dataset normal do site
  (`{"tableName": GUID}`), apagar o dataset com override nos dois arquivos e pôr
  `autocreateenvironmentvariables: false`. Procure sempre `new_shared_` / `environmentVariableName` no export
  recebido antes de reempacotar.
- **`MissingAuthorizationHeaderAndClientCertificate`** = token não enviado (sessão/acesso condicional/extensão),
  não é o pacote. Políticas de acesso condicional podem barrar janela anônima e o navegador do Claude no
  Power Apps (mesmo com SharePoint funcionando) — nesse caso use o caminho do `.msapp`.
- **Mapeamento dos fluxos na tela de importação:** confira cada 🔧 — o portal pode sugerir "Atualizar" um
  fluxo **de outro app** com nome parecido (ex.: `FLOW_NotificarSolicitante` → `APPX_Notificacao_Solicitante`),
  o que sobrescreveria o outro. "Criar como novo" gera cópias que o app não usa.
- **Depois de tentativas falhas**, fluxos podem ficar desligados: erro no app
  `WorkflowTriggerIsNotEnabled ... trigger 'manual' with state 'Disabled'` → ativar o fluxo (o GUID do erro é o
  `workflowName` em `LocalConnectionReferences`) e apagar cópias criadas.
- Não altere o `*-identity.json` sem necessidade (pacotes que importaram bem mantinham o original); se
  precisar, preserve o formato compacto.
