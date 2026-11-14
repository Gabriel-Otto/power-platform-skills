# Estrutura de indentação do PaYaml

Este arquivo explica o "esqueleto" de indentação usado nos arquivos de tela do Power Apps,
para você conseguir recalcular recuos corretos quando um erro de chave duplicada ou aninhamento
quebrado desalinha um bloco inteiro de controles (catálogo de erros #2 do SKILL.md).

## Regra básica do YAML (não é específica do Power Apps, mas é a raiz de quase todo problema)

- Um item de lista (`- algo:`) e suas chaves filhas só são "filhas de fato" se estiverem
  indentadas **mais** do que a coluna onde o texto da chave do item começa.
- Itens irmãos numa mesma sequência (`- item1:`, `- item2:`) precisam ter **exatamente a
  mesma indentação** entre si — senão o YAML não os reconhece como irmãos.
- YAML não exige um número fixo de espaços por nível (pode ser 2, pode ser 4) — só exige
  **consistência**: cada nível precisa ser mais indentado que o pai, e os irmãos entre si
  precisam ser iguais. Isso quer dizer que, ao reparar uma cascata de indentação errada, o
  mais seguro é **deslocar o bloco inteiro em bloco** (mesma quantidade de espaços a menos/mais
  em cada linha), preservando a indentação relativa interna — em vez de tentar reescrever cada
  linha com um número "ideal" de espaços.

## Padrão observado nos arquivos de tela do Power Apps

Cada controle, dentro de uma lista `Children:`, segue este formato:

```yaml
Children:
  - nomeDoControle:
      Control: TipoDoControle@versao
      Variant: NomeDaVariante      # quando aplicável
      Properties:
        Propriedade1: =valor
        Propriedade2: =valor
      Children:                    # só se o controle tiver filhos
        - filho1:
            ...
        - filho2:
            ...
```

Ou seja, dentro de um item `- nomeDoControle:`:
- `Control:`, `Variant:`, `Properties:`, `Children:` ficam **todas no mesmo nível de recuo**
  entre si (um nível mais recuado que o `-` do item).
- O conteúdo de `Properties:` (as propriedades em si) e os itens da lista de `Children:` ficam
  **mais um nível** recuados a partir daí — ou seja, no mesmo nível de recuo um do outro.
- Cada item dentro de `Children:` repete essa mesma estrutura recursivamente.

Isso significa que **o nível de recuo de `Control:`/`Properties:`/`Children:` é sempre igual
ao nível de recuo dos próprios itens dentro do `Children:` do controle pai** (ambos um passo
além de onde o `-` do controle está escrito). Ou seja, se você sabe o recuo de `Children:` de
um controle, já sabe o recuo correto de cada `- filhoX:` dentro dele.

## Como reparar uma cascata

Quando encontrar um trecho desalinhado (por exemplo, vários controles irmãos que deveriam
estar no mesmo nível de `cntExemplo1`, mas apareceram mais recuados por causa de um erro de
aninhamento anterior):

1. **Identifique o nível correto** olhando um controle irmão que já está certo (ex.: o
   primeiro item da mesma lista `Children:`, ou o controle imediatamente anterior ao trecho
   corrompido).
2. **Calcule o deslocamento**: `recuo_atual_do_bloco_errado - recuo_correto = deslocamento`.
3. **Aplique esse mesmo deslocamento em TODAS as linhas do bloco**, do início ao fim do trecho
   afetado (inclusive sub-controles e fórmulas multilinha dentro dele) — não recalcule linha a
   linha, só subtraia/some o mesmo número de espaços de cada uma. Isso preserva a estrutura
   relativa interna do bloco, que normalmente já está certa, só presa no nível errado.
4. **Repita para cada bloco subsequente** que também tenha sido empurrado pela mesma cascata
   (normalmente todo o restante do arquivo, até o fim da seção, foi afetado em conjunto — não
   pare no primeiro bloco corrigido, confira até onde a indentação errada se estende).
5. Depois do deslocamento, **valide com `scripts/validate_payaml.py`** e também reconstruindo
   a árvore com `yaml.safe_load` para confirmar que cada controle agora tem `Control:` e
   `Properties:` no lugar certo (nenhum valor `None`).

## Fórmulas multilinha (`|` / `|-`) dentro desse esqueleto

Quando uma propriedade usa bloco literal (`Propriedade: |-`), o conteúdo do bloco:
- Começa pelo menos 2 espaços mais recuado que a própria chave `Propriedade:`.
- Todas as linhas internas do bloco (inclusive parênteses/chaves de fechamento) devem manter
  recuo igual ou maior que a primeira linha do bloco — uma linha menos recuada **encerra** o
  bloco e volta a ser lida como uma nova chave do mapeamento pai.

Isso é o motivo do erro #1 do catálogo: o fecha-parênteses "solto" sem o bloco `|-` volta para
o recuo da chave, e como não há marcador de bloco, o YAML tenta (e falha) interpretá-lo como
uma nova chave.
