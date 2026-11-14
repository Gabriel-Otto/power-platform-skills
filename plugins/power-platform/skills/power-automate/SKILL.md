---
name: "power-automate"
description: "Criar, importar, exportar ou corrigir fluxos do Power Automate em ZIP: pacotes legados (definition.json) e soluções Dataverse (solution.xml), inclusive com agentes do Copilot Studio."
---

# Power Automate — Geração de Pacotes ZIP para Importação

## Visão Geral

Power Automate flows podem ser exportados/importados como pacotes `.zip` contendo um `definition.json`. Esta skill cobre como gerar esses pacotes via Python, com os operationIds e parâmetros corretos para cada conector.

---

## REGRA CRÍTICA — Consultar GitHub Antes de Cada Ação

> **OBRIGATÓRIO:** Antes de usar qualquer `operationId` ou parâmetro de conector, consulte a documentação oficial:
>
> - **Referência geral de conectores:** https://learn.microsoft.com/en-us/connectors/sharepointonline/
> - **Exemplos reais de definition.json:** https://github.com/OfficeDev/Microsoft-Teams-Shifts-Power-Automate-Templates
> - **Documentação de fluxos via código:** https://learn.microsoft.com/en-us/power-automate/manage-flows-with-code
>
> **Nunca assuma operationIds ou parâmetros de memória.** Sempre valide contra um exemplo real ou a documentação oficial antes de gerar o ZIP.
>
> Se não encontrar um exemplo real para uma operação, peça ao usuário que copie a ação do designer do Power Automate (via `...` → "Copiar para área de transferência") e use o JSON resultante como fonte de verdade.

---

## ANTES DE TUDO — Identificar o formato do ZIP recebido

Rode `unzip -l arquivo.zip` e decida:

| Conteúdo do ZIP | Formato | Como editar |
|---|---|---|
| `manifest.json` + `Microsoft.Flow/flows/{GUID}/definition.json` | Pacote legado | Seções "Estrutura do Pacote ZIP" em diante |
| `solution.xml` + `customizations.xml` + `Workflows/*.json` (+ `bots/`, `botcomponents/`) | **Solução Dataverse** | Seção "Soluções Dataverse" abaixo |

Nunca converta uma solução em pacote legado (nem o contrário): devolva no mesmo formato recebido.

## Soluções Dataverse (solution.xml)

- Cada fluxo fica em `Workflows/<Nome>-<GUID>.json` com a raiz `{"properties": {"connectionReferences": ..., "definition": ...}, "schemaVersion": "1.0.0.0"}`.
- `connectionReferences` usa `{"api": {"name": "shared_office365"}, "connection": {"connectionReferenceLogicalName": "prefixo_..."}, "runtimeSource": "embedded"}`. **Não mude esses nomes**; ações novas reutilizam o mesmo `connectionName` (ex.: `shared_office365`, `shared_office365-1`).
- Nas ações `OpenApiConnection` de solução NÃO há `authentication` (diferente do pacote legado).
- **Modo gerenciado x não gerenciado:** `<Managed>1</Managed>` ou `<Managed>0</Managed>` em `solution.xml`. O ambiente só aceita atualização no MESMO modo já instalado (erro: *"already installed on this system as an unmanaged solution and the package supplied is attempting to install it in managed mode"*). O sufixo `_managed` no nome do arquivo não garante o modo do ambiente: pergunte ou, na dúvida, entregue **não gerenciada** (`<Managed>0</Managed>`, sem `_managed` no nome). Nunca mande desinstalar a solução para contornar.
- **Sempre suba `<Version>`** em `solution.xml` a cada entrega.
- Em `customizations.xml`, entregue fluxos alterados **desligados** (`<StateCode>0</StateCode><StatusCode>1</StatusCode>`); o usuário liga depois.
- Arquivos da solução usam CRLF. Em Python, leia/grave com `newline=""`, senão `str.replace` com `\r\n` falha silenciosamente.
- Reempacote mantendo exatamente os mesmos caminhos do ZIP original (inclusive `[Content_Types].xml`).
- Para entregar só parte da solução: remova o `<Workflow>` do customizations.xml, o `<RootComponent type="29" id="{GUID}">` do solution.xml e o JSON em `Workflows/`. Em solução não gerenciada isso NÃO apaga o fluxo do ambiente.
- **Importar uma nova versão sobrescreve ajustes que o usuário fez no designer** (filtros de teste, destinatário etc.). Quando o usuário já está ajustando no designer, prefira passar a correção como passos manuais (ação + campo + expressão exata) e deixe o ZIP só como referência.
- Agente do Copilot Studio (`botcomponents/<agente>.gpt.default/data`) é YAML com `instructions: |-`; ajuste o texto mantendo a indentação de 2 espaços. Após importar, o usuário precisa **publicar o agente**.
- Operações confirmadas em solução real: SharePoint `GetItems`, `GetItem`, `PatchItem` (`id` + `item/Campo`, escolha = `item/Campo/Value`), `PostItem`, `CreateAttachment` (`itemId`, `displayName`, `body`); Outlook `GetEmailsV3`, `GetAttachment_V2` (`messageId`, `attachmentId`), `DraftEmail` (`draftMessage/To|Subject|Body|Importance`), `SendDraftEmail` (`messageId`); Copilot Studio `ExecuteCopilotAsyncV2` (`Copilot`, `body/message`, `body/attachments`; tipo `OpenApiConnectionWebhook`; saída `body/lastResponse`).

### Log de importação com erro

O log baixado é uma planilha Excel XML (pode vir no idioma do tenant, ex.: italiano). Extraia as abas com regex em `<Row>`/`<Data>` e leia Stato/CodiceErrore/TestoErrore da aba de componentes.

### Validação obrigatória antes de entregar

Rodar um script sobre o `definition` que confira:
1. todo `runAfter` aponta para ação do MESMO escopo;
2. toda referência `outputs()/body()/actions()/items()` aponta para ação existente, e `items('Loop')` só aparece dentro do loop;
3. toda variável usada foi inicializada no nível raiz (InitializeVariable não pode ficar dentro de loop/condição);
4. parênteses e aspas simples balanceados em cada `@...` e `@{...}`;
5. nenhuma string literal começando com `@` que não seja expressão (ex.: domínio `@empresa.com`);
6. nenhum `if()` usado para proteger função que quebra com valor vazio no outro ramo (ver "Expressões — Regras Críticas").
Depois, simular em Python as expressões críticas com dados reais do usuário, **inclusive com valores vazios**.

---

## Leitura de e-mails (Office 365 Outlook) — Armadilhas

- **`Get emails (V3)`: `subjectFilter`, `from`, `to`, `importance` e `fetchOnlyWithAttachment` só filtram os 250 e-mails mais recentes da pasta.** Use `searchQuery` (KQL do Graph `$search`), que pesquisa a pasta inteira: `subject:12345678000199 OR (subject:Vencidos AND subject:FORNECEDOR)`, `from:a@x.com OR from:b@x.com`. Prefira termos de uma palavra e nunca passe `searchQuery` vazio (retorna tudo) — use um valor dummy (`from:sem.remetente@invalido.local`).
- O Outlook leva alguns minutos para indexar e-mail novo na busca: em teste, espere ~5 min antes de executar.
- `includeAttachments: false` ainda devolve os metadados dos anexos (`id`, `name`, `contentType`, `isInline`); baixe o conteúdo com `GetAttachment_V2` só do que interessa.
- Campos de saída do V3: `id`, `from` (string), `subject`, `receivedDateTime`, `body` (HTML ou texto), `bodyPreview`, `conversationId`, `attachments`.
- **Rastrear respostas:** não dependa só do assunto do último envio. Combine token estável no assunto (ex.: CNPJ com 14 dígitos), busca pelos remetentes cadastrados, marca d'água de data (`receivedDateTime` do último e-mail processado, gravada na lista) e processe TODOS os e-mails novos, não só `first()`.
- **Exclua remetentes do domínio interno**: em teste a cobrança vai para o próprio usuário e seria lida como "resposta".
- Não avance a marca d'água quando a análise falhar, para reprocessar depois.
- Em teste, restrinja TODAS as consultas de itens (leitura e envio) ao registro de teste, senão o fluxo processa fornecedores reais.

## IA / JSON — Armadilhas

- **Não gere o schema do `Parse JSON` a partir de um exemplo em que o agente devolveu um JSON Schema** (`type`, `properties`, `additionalProperties`): o Parse passa e todos os campos chegam vazios. Prefira `Compose` com `@json(...)` + validação explícita dos campos (ex.: `acao_recomendada` numa lista permitida) e trate o `Failed` com `runAfter`.
- Na mensagem ao agente, diga explicitamente para devolver VALORES e não um schema.

## E-mail HTML de relatório

- Outlook ignora boa parte de `<style>`/`<title>`. Use **estilos inline** em `<table>/<th>/<td>` e monte as linhas com `Select` + `join()` em vez de `Create HTML table`.
- Mostre "—" em células vazias e inclua contexto (quantos e-mails, data do último).

## Dados de listas — Armadilhas

- CNPJ salvo como número perde zero à esquerda. Normalize: `substring(concat('00000000000000', x), length(x), 14)`.
- Contadores: use a mesma expressão na leitura e na gravação (ex.: `coalesce(field_11, Enviar_x0020_Email, 0)`).
- Nomes internos `field_N` seguem a ordem das colunas de uma lista importada de planilha; confirme pela saída de um `GetItems`.

---

## Estrutura do Pacote ZIP

```
FlowName_Timestamp.zip
├── manifest.json                          ← metadados e recursos
└── Microsoft.Flow/
    └── flows/
        └── {FLOW_GUID}/
            ├── definition.json            ← definição completa do fluxo
            ├── apisMap.json               ← mapa de APIs usadas
            └── connectionsMap.json        ← mapa de conexões
```

---

## Template Python Base

```python
import json, zipfile, uuid

def new_guid():
    return str(uuid.uuid4())

FLOW_GUID = new_guid()

# Montar definition, apis_map, connections_map, flows_manifest, root_manifest
# (ver seções abaixo)

zip_path    = "/home/claude/MEU_FLOW.zip"
flow_folder = f"Microsoft.Flow/flows/{FLOW_GUID}"

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("manifest.json",                      json.dumps(root_manifest,   ensure_ascii=False, indent=2))
    zf.writestr("Microsoft.Flow/flows/manifest.json", json.dumps(flows_manifest,  ensure_ascii=False, indent=2))
    zf.writestr(f"{flow_folder}/definition.json",     json.dumps(definition,      ensure_ascii=False, indent=2))
    zf.writestr(f"{flow_folder}/apisMap.json",        json.dumps(apis_map,        ensure_ascii=False, indent=2))
    zf.writestr(f"{flow_folder}/connectionsMap.json", json.dumps(connections_map, ensure_ascii=False, indent=2))
```

---

## manifest.json (raiz)

```python
root_manifest = {
    "schema": "1.0",
    "details": {
        "displayName": "NOME_DO_FLOW",
        "description": "Descrição",
        "createdTime": "2026-06-26T14:00:00.000Z",
        "packageTelemetryId": new_guid(),
        "creator": "usuario@empresa.com",
        "sourceEnvironment": "EMPRESA (default)"
    },
    "resources": {
        FLOW_GUID: {
            "type": "Microsoft.Flow/flows",
            "suggestedCreationType": "New",
            "creationType": "New, Update",
            "details": {"displayName": "NOME_DO_FLOW"},
            "configurableBy": "User",
            "hierarchy": "Root",
            "dependsOn": [API_SP_GUID, CONN_SP_GUID]  # listar todas as APIs e conexões
        },
        API_SP_GUID: {
            "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "name": "shared_sharepointonline",
            "type": "Microsoft.PowerApps/apis",
            "suggestedCreationType": "Existing",
            "details": {"displayName": "SharePoint"},
            "configurableBy": "System", "hierarchy": "Child", "dependsOn": []
        },
        CONN_SP_GUID: {
            "type": "Microsoft.PowerApps/apis/connections",
            "suggestedCreationType": "Existing",
            "creationType": "Existing",
            "details": {"displayName": "usuario@empresa.com"},
            "configurableBy": "User",
            "hierarchy": "Child",
            "dependsOn": [API_SP_GUID]
        }
    }
}
```

## flows/manifest.json

```python
flows_manifest = {
    "packageSchemaVersion": "1.0",
    "flowAssets": {"assetPaths": [FLOW_GUID]}
}
```

---

## definition.json — Estrutura Base

```python
definition = {
    "name": FLOW_GUID,
    "id": f"/providers/Microsoft.Flow/flows/{FLOW_GUID}",
    "type": "Microsoft.Flow/flows",
    "properties": {
        "apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows",
        "displayName": "NOME_DO_FLOW",
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "$authentication": {"defaultValue": {}, "type": "SecureObject"},
                "$connections":    {"defaultValue": {}, "type": "Object"}
            },
            "triggers": { ... },
            "actions":  { ... },
            "outputs":  {}
        },
        "connectionReferences": { ... },
        "flowFailureAlertSubscribed": False,
        "isManaged": False
    }
}
```

---

## Gatilhos (Triggers)

### PowerApp V2 (chamado pelo Power Apps)

```python
"triggers": {
    "manual": {
        "type": "Request",
        "kind": "PowerAppV2",
        "inputs": {
            "schema": {
                "type": "object",
                "properties": {
                    "text": {
                        "description": "Descrição do parâmetro",
                        "title": "NomeParam",
                        "type": "string",
                        "x-ms-content-hint": "TEXT",
                        "x-ms-dynamically-added": True
                    }
                    # Parâmetros adicionais: text_1, text_2, text_3...
                },
                "required": ["text"]
            }
        }
    }
}
```

> Parâmetros no trigger PowerApp V2 seguem o padrão `text`, `text_1`, `text_2`, `text_3`...
> Acessados via `triggerBody()?['text']`, `triggerBody()?['text_1']` etc.

---

## Ações Confirmadas — Operações Testadas e Aprovadas

> As operações abaixo foram **testadas e confirmadas funcionando** em importação real.
> Qualquer operação fora desta lista deve ser validada com o usuário antes de usar.

### SharePoint — GetItems

```python
"Obter_Itens": {
    "runAfter": {},
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "dataset": "https://empresa.sharepoint.com/sites/meusite",
            "table": "nome_da_lista",   # nome interno ou GUID da lista
            "$top": 1000                # limitar resultados
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "connectionName": "shared_sharepointonline",
            "operationId": "GetItems"
        },
        "authentication": "@parameters('$authentication')"
    }
}
```

### SharePoint — PostItem (Criar item)

```python
"Criar_Item": {
    "runAfter": { ... },
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "dataset": "https://empresa.sharepoint.com/sites/meusite",
            "table": "nome_da_lista",
            "item/Title": "valor",
            "item/OutroCampo": "@{expressao}"
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "connectionName": "shared_sharepointonline",
            "operationId": "PostItem"
        },
        "authentication": "@parameters('$authentication')"
    }
}
```

### SharePoint — DeleteItem (Excluir item)

```python
"Excluir_Item": {
    "runAfter": { ... },
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "dataset": "https://empresa.sharepoint.com/sites/meusite",
            "table": "nome_da_lista",
            "id": "@outputs('Criar_Item')?['body/ID']"
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
            "connectionName": "shared_sharepointonline",
            "operationId": "DeleteItem"
        },
        "authentication": "@parameters('$authentication')"
    }
}
```

### Filter Array (Query) — Filtrar array em memória

> **Use sempre Filter Array em vez de `$filter` OData dinâmico.**
> OData com valores dinâmicos do trigger causa erro de parse na importação.

```python
"Filtrar_Itens": {
    "runAfter": {"Obter_Itens": ["Succeeded"]},
    "type": "Query",
    "inputs": {
        "from": "@outputs('Obter_Itens')?['body/value']",
        "where": "@equals(item()?['Title'], triggerBody()?['text'])"
        # Múltiplas condições:
        # "where": "@and(equals(item()?['campo1'], triggerBody()?['text']), equals(item()?['campo2'], 'Pendente'))"
    }
}
```

### Initialize Variable

```python
"Variavel_vItem": {
    "runAfter": {"Filtrar_Itens": ["Succeeded"]},
    "type": "InitializeVariable",
    "inputs": {
        "variables": [{
            "name": "vItem",
            "type": "object",   # string | integer | float | boolean | object | array
            "value": "@first(body('Filtrar_Itens'))"
        }]
    }
}
```

### Compose (montar string/HTML)

```python
"Montar_Conteudo": {
    "runAfter": { ... },
    "type": "Compose",
    "inputs": "texto ou @{expressao} ou HTML completo aqui"
}
# Acessar output: @outputs('Montar_Conteudo')
```

### Switch (ramificação por valor)

```python
"Switch_Tipo": {
    "runAfter": { ... },
    "type": "Switch",
    "expression": "@triggerBody()?['text_1']",
    "cases": {
        "VALOR_A": {
            "case": "VALOR_A",
            "actions": {
                "Acao_A": { ... }
            }
        },
        "VALOR_B": {
            "case": "VALOR_B",
            "actions": {
                "Acao_B": { ... }
            }
        }
    },
    "default": {
        "actions": {}
    }
}
```

### Office 365 Outlook — SendEmailV2

> **Parâmetros confirmados:** apenas `emailMessage/To`, `emailMessage/Subject`, `emailMessage/Body`.
> `IsHtml`, `Importance`, `CC` e outros NÃO existem no formato de importação — causam erro.

```python
"Enviar_Email": {
    "runAfter": { ... },
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "emailMessage/To": "@variables('vItem')?['email']",
            "emailMessage/Subject": "@concat('[FLOW] Assunto ', triggerBody()?['text'])",
            "emailMessage/Body": "<p>Corpo do e-mail em HTML</p>"
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_office365",
            "connectionName": "shared_office365",
            "operationId": "SendEmailV2"
        },
        "authentication": "@parameters('$authentication')"
    }
}
```

### OneDrive for Business — CreateFile

> **Parâmetros confirmados (sem `dataset`!):** `folderPath`, `name`, `body`.

```python
"Criar_Arquivo_OneDrive": {
    "runAfter": { ... },
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "folderPath": "/NomeDaPasta",
            "name": "@{concat(triggerBody()?['text'], '.html')}",
            "body": "@outputs('Montar_Conteudo')"
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_onedriveforbusiness",
            "connectionName": "shared_onedriveforbusiness",
            "operationId": "CreateFile"
        },
        "authentication": "@parameters('$authentication')"
    }
}
# Output do Id: @outputs('Criar_Arquivo_OneDrive')?['body/Id']
# Output da URL: @outputs('Criar_Arquivo_OneDrive')?['body/WebUrl']
```

### OneDrive for Business — ConvertFile

> **Parâmetros confirmados (sem `source`!, sem `dataset`!):** apenas `id` e `type`.

```python
"Converter_para_PDF": {
    "runAfter": {"Criar_Arquivo_OneDrive": ["Succeeded"]},
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "id": "@outputs('Criar_Arquivo_OneDrive')?['body/Id']",
            "type": "pdf"
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_onedriveforbusiness",
            "connectionName": "shared_onedriveforbusiness",
            "operationId": "ConvertFile"
        },
        "authentication": "@parameters('$authentication')"
    }
}
```

### OneDrive for Business — DeleteFile

> **Parâmetros confirmados (sem `dataset`!):** apenas `id`.

```python
"Excluir_Arquivo": {
    "runAfter": { ... },
    "type": "OpenApiConnection",
    "inputs": {
        "parameters": {
            "id": "@outputs('Criar_Arquivo_OneDrive')?['body/Id']"
        },
        "host": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_onedriveforbusiness",
            "connectionName": "shared_onedriveforbusiness",
            "operationId": "DeleteFile"
        },
        "authentication": "@parameters('$authentication')"
    }
}
```

### Respond to PowerApp

```python
"Responder_ao_PowerApp": {
    "runAfter": { ... },
    "type": "Response",
    "kind": "PowerApp",
    "inputs": {
        "statusCode": 200,
        "schema": {
            "type": "object",
            "properties": {
                "resultado": {
                    "title": "resultado",
                    "type": "string",
                    "x-ms-content-hint": "TEXT",
                    "x-ms-dynamically-added": True
                }
            }
        },
        "body": {
            "resultado": "@concat('Concluído para ', triggerBody()?['text'])"
        }
    }
}
```

---

## connectionReferences

```python
"connectionReferences": {
    "shared_sharepointonline": {
        "connectionName": "shared-sharepointonl-XXXX",  # nome real da conexão do usuário
        "source": "Embedded",
        "id": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline",
        "tier": "NotSpecified"
    },
    "shared_office365": {
        "connectionName": "shared_office365",
        "source": "Embedded",
        "id": "/providers/Microsoft.PowerApps/apis/shared_office365",
        "tier": "NotSpecified"
    },
    "shared_onedriveforbusiness": {
        "connectionName": "shared_onedriveforbusiness",
        "source": "Embedded",
        "id": "/providers/Microsoft.PowerApps/apis/shared_onedriveforbusiness",
        "tier": "NotSpecified"
    }
}
```

---

## Expressões — Regras Críticas

### Filtros OData com valores dinâmicos — NUNCA usar no $filter direto

```python
# ❌ ERRADO — causa erro de parse na importação
"$filter": "Title eq '@{triggerBody()?[''text'']}'",
"$filter": "@{concat(\"Title eq '\", triggerBody()?['text'], \"'\")}",

# ✅ CORRETO — usar Filter Array (Query) depois do GetItems
```

### `if()` NÃO protege: os dois lados são avaliados

`if(empty(x), 'padrao', ticks(x))` quebra quando `x` é vazio, porque o Power Automate avalia os DOIS ramos (erro real: *InvalidTemplate ... In function 'ticks', the value provided for date time string '' was not valid*). Nunca use `if()` para evitar erro de `ticks`, `formatDateTime`, `convertFromUtc`, `int`, `substring`, `first` etc. Em vez disso: inicialize variáveis de data com valor válido (`1900-01-01T00:00:00Z`); em `substring`, use `max(0, indexOf(...))` e `min(...)` para que qualquer valor gere índices válidos. `coalesce()` só pula `null`, não string vazia.

### Literais que começam com `@`

Qualquer string que COMEÇA com `@` é tratada como expressão. `"@empresa.com"` gera *Unable to parse template language expression 'empresa.com': expected token 'LeftParenthesis' and actual 'Dot'* e o fluxo não liga. Use o valor sem `@` (com `endsWith`) ou escape com `@@`.

### Expressões dentro de strings

```python
# ✅ Correto — só aspas simples dentro de @{}
"@{triggerBody()?['text']}"
"@{variables('vSolic')?['campo']}"
"@{concat('[FLOW] ', triggerBody()?['text'])}"
"@{formatDateTime(utcNow(),'dd/MM/yyyy')}"
"@first(body('Filtrar_Itens'))"
"@outputs('Acao_Anterior')?['body/Id']"

# ❌ Errado — aspas duplas dentro de @{} causam erro de parse
"@{concat(\"texto\", triggerBody()?['text'])}"
```

### runAfter

```python
# Ação sem dependência (primeira do fluxo)
"runAfter": {}

# Ação que depende de outra
"runAfter": {"Nome_Da_Acao_Anterior": ["Succeeded"]}

# Ação que roda mesmo se a anterior falhar
"runAfter": {"Nome_Da_Acao_Anterior": ["Succeeded", "Failed"]}
```

---

## Erros Comuns e Correções

| Erro | Causa | Correção |
|---|---|---|
| `WorkflowOperationParametersExtraParameter 'dataset'` | Ação do OneDrive não aceita `dataset` | Remover `dataset` — OneDrive usa só `folderPath`, `name`, `body`, `id` |
| `WorkflowOperationParametersExtraParameter 'emailMessage/IsHtml'` | SendEmailV2 não aceita esse parâmetro no pacote | Usar só `To`, `Subject`, `Body` |
| `Unable to parse template language expression` | Aspas duplas dentro de `@{}` | Usar só aspas simples; concatenar com `concat()` |
| `ApiOperationNotFound 'UpdateItem'` (SharePoint) | O operationId é `PatchItem` | Usar `PatchItem` com `id` + `item/Campo` |
| `ApiOperationNotFound 'CreateFileV2'` | operationId incorreto para criar arquivo SP | Usar `CreateFile` para SharePoint listas/bibliotecas |
| Relatório com colunas vazias | Parse JSON com schema errado / agente devolveu schema | Ver "IA / JSON — Armadilhas" |
| Resposta não encontrada | `subjectFilter`/`from` só olham 250 e-mails; assunto muda por data | `searchQuery` + token estável + marca d'água |
| Fluxo "acha" resposta que não existe | Busca pegou a própria cobrança | Excluir remetentes do domínio interno |
| `expected token 'LeftParenthesis' and actual 'Dot'` ao ligar | String literal começando com `@` | Tirar o `@` ou usar `@@` |
| `InvalidTemplate ... In function 'ticks' ... '' was not valid` | `if()` avalia os dois ramos | Inicializar com data válida; não proteger com `if()` |
| `already installed ... as an unmanaged solution ... managed mode` | Pacote gerenciado indo para ambiente não gerenciado | `<Managed>0</Managed>` e reempacotar |
| `0x80040203` *published update ... when there exists an unpublished active row* | Registro do fluxo travado em rascunho no ambiente (não é o ZIP; importar desligado não resolveu) | Entregar pacote sem esse fluxo e passar as alterações dele como passos manuais; último recurso: excluir o fluxo no ambiente e reimportar |

---

## Como Obter operationIds Corretos do Usuário

Quando uma operação não está nesta skill, pedir ao usuário:

1. Abrir o Power Automate designer
2. Adicionar a ação desejada (não precisa preencher)
3. Clicar em `...` → **"Copiar para área de transferência"**
4. Colar o JSON aqui

O JSON retornado contém `operationId` e `parameters` exatos para aquela ação no ambiente do usuário.

---

## Como Importar o ZIP no Power Automate

1. Acessar **make.powerautomate.com**
2. **Meus fluxos** → **Importar** → **Importar pacote (herdado)**
3. Subir o arquivo `.zip`
4. Na tela de revisão:
   - Fluxo → **Criar como novo**
   - Cada conexão → clicar na chave e selecionar a conexão existente
5. Clicar **Importar**
