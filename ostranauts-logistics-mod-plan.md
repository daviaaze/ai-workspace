# Ostranauts — Logistics / Idle-Organization Mod (Plano)

> **Tipo:** Mod C# (BepInEx + Harmony) — um **idle-pledge de organização**.
> **Estilo:** igual ao `PledgeRecharge` (bateria) e ao `ProcessAutoTasks` (reparo em idle):
> roda **quando não há mais nada a fazer**, em baixa prioridade.
> **Alvo:** jogo 1.0.0.9 (compatível BepInEx 5.x, netstandard2.1, Mono).
> Docs relacionadas: `ostranauts-battery-workflow.md`, `ostranauts-ai-architecture.md` (§5 pledges).

---

## 1. O que o mod faz (comportamento-alvo)

Uma crew **ociosa e dona do navio** executa uma rotina de **organização/logística** em
prioridade baixa — depois de reparar, haular, socializar e recarregar baterias:

1. **Multi-haul** — ao pegar um item para haular, recolhe outros itens pequenos
   empilháveis/carregáveis ao longo do caminho (respeitando capacidade e mochila).
2. **Classifica por destino**:
   - itens **`IsPocketable`** → bolsos / mochila / slots de roupa;
   - itens **oversized/cumbersome** (`IsOversized`/`IsCumbersome`) → **Dolly** (único container que os aceita);
   - demais → containers/baús com espaço (`gridLayout.gridMaxSpace`).
3. **Empacota o chão/container (2D bin-packing tipo Tetris)** — ao largar, usa um algoritmo de
   **empacotamento 2D** que gira e compacta itens no grid para caber mais (o jogo só usa *First-Fit*).
4. **Move da L1 (chão) para a L2 (bins/containers)** — agrupa itens soltos da zona em baús/containers
   corretos (por `ctAllowed`/categoria); guarda **bolsas/mochilas/roupas** também em baús quando couber.
5. **Respeita bins oversized** (containers cujo `ctAllowed` aceita `IsOversized`).

---

## 2. Por que um pledge (arquitetura certa)

Registro do padrão base: o loop de pledges do `CondOwner` (linha 3454-3485) roda **somente para
crews com `HasCond("IsPledgeChecker")`**, iterando `dictPledges` da prioridade **11 (mais alta)
→ 1 (mais baixa)**, chamando `pledge.Do()` e parando no primeiro que retorna `true`.

```csharp
for (int num2 = 11; num2 > 0; num2--)          // prioridade 11 → 1
    if (dictPledges.ContainsKey(num2)) {
        Pledge2[] array = dictPledges[num2].ToArray();
        foreach (Pledge2 pledge in array) {
            flag7 = pledge.Do();
            if (flag7) { RecordPledge(pledge); break; }
        }
    }
```

- Reutilizamos esse loop **sem tocar em nada** do comportamento nativo.
- A organização deve ter **prioridade muito baixa** (ex: 1–2), abaixo de `PledgeRecharge` (4),
  reparos, comida, social — ou seja, só quando realmente ocioso.
- `IsPledgeChecker` já é dado por padrão a `Crew01`/`Robot01`/`Robot02` (`aStartingConds`).

---

## 3. Registro de um novo tipo de pledge

O `PledgeFactory.Factory` (`PledgeFactory.cs`) mapeia `strType` → `Type` num `dictTypes` **privado**.
Não há `LaunchControl` nesta build (grep: ausente). Para registrar um novo pledge:

```csharp
[HarmonyPatch(typeof(PledgeFactory), "Factory",
   new[] { typeof(CondOwner), typeof(JsonPledge), typeof(CondOwner) })]
[HarmonyPostfix]
static void RegisterOrganize(CondOwner coUs, JsonPledge jp, CondOwner coThem, ref Pledge2 __result)
{
    // só injeta se ainda não existe; Factory já retorna null p/ tipo desconhecido
    var pd = AccessTools.Field(typeof(PledgeFactory), "dictTypes");
    var dict = (Dictionary<string, Type>)pd.GetValue(null);
    if (jp != null && jp.strType == "organize" && !dict.ContainsKey("organize"))
    {
        dict["organize"] = typeof(PledgeOrganize);
        __result = PledgeOrganize.TryCreate(coUs, jp, coThem); // NULL se inaplicável
    }
}
```

Alternativa mais direta (evita touches em `dictTypes`):
- **Prefix em `PledgeFactory.Factory`** que, para `strType == "organize"`, retorna uma instância
  de `PledgeOrganize` sem tocar no dicionário (mais seguro, sem reflexão cross-namespace).

> Um `JsonPledge` com `strType:"organize"` e `nPriority` baixo precisa existir em `pledges.json`
> (data mods) **OU** ser injetado via `DataHandler`/peste no `AddPledge`. Recomendo:
> **data mod** minimal com o pledge + `mod_info.json` (mesmo do `SmartPick`), pois é o mesmo
> pipeline do `PledgeRecharge` (`strIATrigger`, `aIAEnd`).

---

## 4. Hooks e APIs reais (decompilado)

### 4.1 Containers / grid / rotação — `Container`, `GridLayout`
- `Container.CanFit(CondOwner coFit, bool bAuto, bool bSub, bool bAllowLocked)` → `bool`
  (checa `ctAllowed`, `gridMaxSpace`, stacks, subs-containers/slots).
- `Container.GetSpace(CondOwner co)` → `width × height` (tiles).
- `Container.AddCO(CondOwner objCO, bool bEquip, bool bOverflow, bool bIgnoreLocks)`.
- `container.gridLayout.gridMaxSpace` → capacidade total (grid).
- **Rotação:** `SilhouetteUtility.GetFloorVectorGrid(x, y, rotZ, co, ref vecList)` e
  `jsonItem.fRotation` — itens podem ser girados no grid antes de `AddCO`.

### 4.2 Slots / mochila / roupa — `CompSlots`, `Slots`
- `co.compSlots` → `CompSlots`.
- `GetSlotsHeldFirst(bool bDeep)` / `GetSlotsDepthFirst` / `GetSlotsChildFirst`.
- `Slot.CanFit(co, bAuto, bSub, checkStacks, bAllowLocked)` — para decidir se item vai p/ slot.
- `Slots.UnSlotItem` — remove de slot (limpa `IsCarried`, dá reset de flags — conserta local de holding).

### 4.3 Oversized / dolly — data
- Condições reais: **`IsOversized`**, **`IsCumbersome`**, **`IsDolly`**, **`IsPartsSmall`**, **`IsPocketable`**.
- `TIsFitContainerSolid` proíbe `IsCumbersome`+`IsOversized` → **não cabe em container comum**.
- `TIsFitDolly` proíbe apenas `IsDolly`+`IsPartsSmall` → **dolly aceita cumbersome** (não oversized).
- `TIsFitContainerSolidCumbersome` proíbe só `IsOversized` → buckets "cumbersome-friendly".

### 4.4 Interações de carregar/dolly
- `ACTLiftItem` / `ACTDropItem` / `ACTFeedItem` (deliver) — movimentam item.
- `ACTEquipItem` / `ACTPickupItem` — pegar de slot/container.
- Padrão de cadeia: `Interaction.AddDependent(next)` — enfileira multi-passos.

---

## 5. As DUAS camadas de inventário da nave (a chave do mod)

A nave tem **dois inventários distintos**, e o problema central do mod é entender e
orquestrar a passagem entre eles:

| Camada | Onde vive | Como itens chegam | Densidade |
|---|---|---|---|
| **L1 — chão (zona)** | itens soltos em tiles de chão de `IsZoneStockpile` | **via `Task2.AssignHaulZone`** (`TileUtils.TryFitItem` encaixa no tile, `CanStackOnItem` empilha) | alta/misturada |
| **L2 — bins/containers** | itens dentro do `GridLayout` de um container | via `Container.AddCO` explícita interação `ACTFeedItem` | baixa/organizada |

**Causa raiz do lixo no chão:**
- `AssignHaulZone` (Task2.cs:185) destina **sempre à zona de stockpile do chão**, nunca para
  bins/containers — não há roteamento por `ctAllowed` para container no haul.
- `GetCOsInZone(...TIsValidHaulDest)` só mira itens **top-level** (chão). Containers são
  **obstáculo** na zona — a crew enche L2 apenas via `AddCO` explícita, não pelo haul.

**Consequência arquitetural para o mod:**
O `PledgeOrganize` é a **ponte L1 → L2**: pega itens soltos na zona e os move para o
container/slot/dolly certo (respeitando `ctAllowed`, `gridMaxSpace`, oversized, empilhável).
Essa é exatamente a lacuna que o haul base não cobre. E o **multi-haul** do escopo não
re-executa o haul; ele reduz o número de viagens coletando vários itens da L1 de uma vez
antes de entregar à L2.

---

## 6. Desenho do `PledgeOrganize.Do()`

```
Do(us):
  1. se !IsPledgeChecker → false
  2. se não dono do navio (ship e ownsShip) → false
  3. SELEÇÃO do alvo (uma "bolsa de trabalho" por chamada):
     a. itens soltos no chão da nave (top-level, `ship.GetCOs(...)`)
     b. containers(vazios/parcial) e una carga ideal p/ cada item
  4. Para o item-alvo escolhido (via `FindSortableItem`):
     - se pocketable e não em slot → ENCONTRAR slot/bolsa  (CompSlots/Slot.CanFit)
     - caso contrário se oversized → target = Dolly  (só dolly aceita)
     - senão → target = container com gridMaxSpace disponível + ctAllowed
     - se target em outro container (bolsa em baú) → remover e aninhar
  5. Se encontrou target → QueueInteraction(delivery/feed) e RETORNA TRUE
  6. senão aprova compactação do chão (rotação+empacota) => retorna false para esperar
}
```

Priorizações na chamada (score):
- quanto mais "mocível trivial" (pocketable já com anel de slot disponível) → hoje.
- Ítens oversized sem dolly destino → **não move** (deixa até haver dolly; evita loop).
- Containers com "bem preenchido" → primeiro para reduzir viagens.

---


## 7. Empacotamento 2D (o algoritmo "Tetris" do chão/container)

O grid de item é **posicional e 2D**: `GridLayout.gridID[x,y]`, `gridMaxX/gridMaxY`,
`GridLayout.IsOccupied(x,y)`, `gridID[j,i]=co.strID`. O tamanho de cada item é
`GUIInventoryItem.itemWidthOnGrid × itemHeightOnGrid` (derivado de
`widthHeightForCO(CO)`), e a rotação é `Item.fLastRotation`/`fRotation` com
`MathUtils.IsRotationVertical(fRotation)` (troca largura↔altura).

### 6.1 O problema
O jogo coloca itens com **`GridLayout.FindFirstUnoccupiedTile(w,h)`**:
```csharp
for i in y..:  for j in x..:  if (gridRect j,i..j+w,i+h está vazio) return (j,i)
```
Isso é **First-Fit por scanline**: acha o *primeiro canto vagante*, sem noção de
otimizar uso do espaço. Resultado: furos/`j` vazios espalhados, itens grandes na
frente bloquemt, conteúdo não compacto.

### 6.2 Algoritmo-alvo (para o nosso "não-fit"→ recompacção)

Quando queremos colocar um item e o *First-Fit* falha (ou o grid está fragmentado),
rodamos um **empacotador 2D** sobre os itens soltos do alvo:

1. **Entrada:** a lista de itens atuais no grid (com `w×h` e rotação disponível), mais o
   item a inserir. Grid `W×H`.
2. **Pré-rotação:** para cada item, testamos as duas orientações (`w,h` e `h,w`) quando
   a física do item permite (`fRotation` livre / silhueta).
3. **Hill-shelf BMH (best-fit decreasing) / Guillotine:** ordena os itens por área
   (decrescente), e para cada um escolhe o **shelf (seção de altura)** que melhor reduz
   a folga; se não couber, abre um novo shelf.
   - *falta confirmar:* o grid é `gridID` (ocupado por `strCOID`), então recompilar =
     `gridLayout.Remove(co.strID)` + `Reinsert` nas posições calculadas.
4. **Não mover itens que são solo/estação fixa** — só itens soltos marcados como "movível"
   (não `IsInstalled`, não `IsSystem`, não parte da estrutura) — igual ao filtro de haul
   (`TIsValidHaulDest`).

Nota: para o **chão**, o modelo é o mesmo tipo de grid (o chão é uma grade de tiles);
para **containers**, é `GridLayout` do container. O mesmo `PackGrid()` serve ambos.

### 6.3 Complexidade passada
- `FindFirstUnoccupiedTile` = O(W×H) por item.
- BMH/guillotine naïve = O(K²) com K itens soltos no alvo (geralmente < 20) — aceitável
  para uma operação *rare* de idle.
- Todos os sacrifícios são por *evento* (chamado raro), **nunca por frame**.

---

## 8. Diagrama Mermaid

```mermaid
flowchart TD
    A[crew ociosa: EndTurn → GetWork idle] --> B{IsPledgeChecker?}
    B -- não --> Z[fim]
    B -- sim --> C[loop prioridade 11→1]
    C --> D{Pledge.Organize.Do}
    D --> E{crew é dona do navio?}
    E -- não --> Z
    E -- sim --> F[Seleciona alvo por score]
    F --> G{tem item no chão móvel?}
    G -- sim --> H{tipo do item}
    H -- pocketable --> I[encontra slot/bolsa p/ ele]
    H -- oversized --> J[precisa Dolly]
    H -- normal --> K[encontra container com espaço]
    I/J/K --> L[Queue interaction delivery]
    L --> M[RETURN true]
    G -- não --> N{strotous itens pois?}
    N -- sim → rotate+compact para caber → tentar de novo
    N -- não → Z[fim runaway: return false]
```

---

## 9. Viabilidade técnica (o que é factível / afirmação)

| Item | Factível? | Nota |
|---|---|---|
| Registrar pledge novo | Sim | postfix `PledgeFactory.Factory` (evita editar `dictTypes`). |
| Rodar como idle (baixa prioridade) | Sim | usa o loop de pledges; `nPriority:1` no JSON. |
| Multi-item no caminho | Sim | aTICKER interlacing / `AddDependent` cadeia + `TargetCO` de :s. |
| Slots de mochila/roupa | Sim | `CompSlots`, `Slot.CanFit`. |
| Dolly só p/ oversized | Sim | `TIsFitDolly` é gravado no próprio item; chegar `ctAllowed`/`ctTrigger` |
| Rotacionar/compactar chão | Parcial+ | `fRotation` + `GridUtils`/`SilhouetteUtility`; precisa benchmark p/ não mover built-in instalações |
| Aninhar (bolsa em baú) | ✅ | recursividade do `CanFit` (bSub) + `RemoveCO`/`AddCO`. |
| Respeitar bins oversized | ✅ | checa `ctAllowed.Triggered(co)` antes de mover para alvo. |

---

## 10. Riscos / anti-padrões a evitar (do `ostranauts-optimization-learnings.md`)

1. **Não rodar todo frame.** A organização é **charge vez por crew**, via `Do()` do pledge, já
   gated pelo idle — não usar `Update()` polling.
2. **Não alocar listas por frame.** Pré-aloca buffers/`List<AutoTask>`-like; varre `GetCOs` só
   quando o  pledge está prestes a agir (cooldown de segundos).
3. **Não intnerager o dono.** `DropCO`/`AddCO` assinatura verificar com decompilado (o `objCO`
   é o item; `__instance` é o dono). (supra: a lição do `OstBattFix`.)
4. **Não mexer em `strID` runtime** (efeitos colaterais no `mapCOs`/`ChangeCOID`).
5. **Limpar flags ao largar** (`IsCarried`/`IsSlotted`) — senão cria o bug "Forbidden: Carried".
6. **Registrar pledge com `AddDependency`** para ações multi-passo (esp. multi-item e aninhamento).

---

## 11. Passos de implementação (rascunho)

1. **Data mod**: `pledges.json` com `{strName:"SeaOrganize", strType:"organize", nPriority:1}`
   + `mod_info.json`. *(ou injeta via `DataHandler`)*
2. **Hook PledgeFactory** (prefix p/ `strType=="organize"` → instancia `PledgeOrganize`).
3. **`PledgeOrganize : Pledge2`** com `Do()` implementado como §5.
4. **Utilidades de logística** (reusa padrões do `Ostranauts.Common`):
   - `FindPocketableTarget`, `FindOversizedTarget`, `FindContainerTarget`,
     `RotateToFit`, `CompactFloorTile`.
5. **Compilar** (csproj netstandard2.1, LangVersion 9.0, HintPaths `/home/daviaaze/.local/share/
   Steam/...`, um `.cs` por plugin). Instalar em `BepInEx/plugins/`.
6. **Testar idle**: livre tempo, ver `DataOwner` que agente organiza; `UnityEngine.Debug.Log` → Player.log.

---

## 12. Estado

- [ ] Research de market de hooks (esta doc) — modelo L1/L2, packing 2D, registro de pledge
- [ ] Data mod (pledge)
- [ ] PledgeOrganize Do() MVP (multi-item + slots + dolly)
- [ ] Ponte L1→L2 (chão → bins/containers)
- [ ] Empacotamento 2D do chão/container
- [ ] Aninhamento bolsa-em-baú
- [ ] Respeito a bins oversized
- [ ] Build + instalar + testar em jogo