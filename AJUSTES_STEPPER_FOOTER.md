# 🔄 Ajustes de Layout - Stepper e Footer

## 📋 Mudanças Implementadas

### 1️⃣ Stepper - Distribuição Horizontal Completa

**ANTES:**
```
[1] [②] [3] [4] [5] [6] [7] [8] [9] ───────→
↑ Scroll horizontal, stepper compacto
```

**DEPOIS:**
```
[1]   [②]   [3]   [4]   [5]   [6]   [7]   [8]   [9]
↑ Distribuído uniformemente, ocupando toda largura
```

**Comportamento:**
- ✅ Cada botão de etapa ocupa espaço igual (`flex: 1`)
- ✅ Distribuição automática em toda largura disponível
- ✅ Sem scroll horizontal
- ✅ Touch targets maiores e mais espaçados

**CSS modificado:**
```css
@media (max-width: 768px) {
  .sr-stepper {
    gap: 4px;
    flex-wrap: nowrap;
    justify-content: space-between;
    width: 100%;
  }

  .sr-stepper__item {
    flex: 1;
    justify-content: center;
  }
}
```

---

### 2️⃣ Margem Abaixo do Stepper

**Adicionado espaçamento vertical:**

| Viewport | Padding Bottom | Margin Bottom |
|----------|---------------|---------------|
| Desktop  | 20px          | 8px           |
| Tablet   | 16px          | 6px           |
| Mobile   | 14px          | 4px           |

**Benefício:**
- ✅ Mais respiração visual entre stepper e conteúdo
- ✅ Separação clara dos blocos
- ✅ Melhor legibilidade

---

### 3️⃣ Footer - Reorganizado

**ANTES:**
```
Desktop:
[Voltar] ........................... [Visualizar] [Salvar] [Próximo]

Mobile:
Linha 1: [    Voltar    ] [    Próximo    ]
Linha 2: [  Visualizar  ] [Salvar rascunho]
```

**DEPOIS (Desktop e Mobile):**
```
[Voltar] ........................... [Salvar] [Visualizar] [Próximo]
   ↑                                    ↑         ↑           ↑
Esquerda                          Agrupados à direita
```

**Nova Estrutura TSX:**
```tsx
<div className="sr-resume-builder-wizard__actions">
  {/* Voltar à esquerda */}
  <Button variant="secondary">Voltar</Button>

  {/* Ações agrupadas à direita */}
  <div className="sr-resume-builder-wizard__actions-right">
    <Button variant="ghost">Salvar rascunho</Button>
    <Button variant="ghost">Visualizar</Button>
    <Button variant="primary">Próximo →</Button>
  </div>
</div>
```

**Ordem dos Botões (Direita para Esquerda):**
1. **Próximo** (primary) - extrema direita
2. **Visualizar** (ghost) - ao lado do Próximo
3. **Salvar rascunho** (ghost) - à esquerda do Visualizar

**Comportamento Mobile:**
- ✅ Layout horizontal mantido (não mais 2 linhas)
- ✅ Botões ajustam tamanho automaticamente
- ✅ Gap reduzido (6px) para caber melhor
- ✅ Font-size menor (13px) nos botões secundários

---

## 📐 Layout Visual Completo

### Desktop (> 768px)
```
┌─────────────────────────────────────────────────────────┐
│ [1 Modelo] [2 Básico] [3 Contato] ... [9 Revisão]      │
│                                                         │
│ ────────────────────────────────────────────────────    │
│                                                         │
│ [Formulário]                                            │
│                                                         │
│ ────────────────────────────────────────────────────    │
│ [Voltar]            [Salvar] [Visualizar] [Próximo →]  │
└─────────────────────────────────────────────────────────┘
```

### Tablet (≤ 768px)
```
┌──────────────────────────────────────────────────────┐
│ [1]  [②]  [3]  [4]  [5]  [6]  [7]  [8]  [9]          │
│ ↑ Distribuído em toda largura, sem scroll            │
│                                                      │
│ ────────────────────────────────────────────────     │
│                                                      │
│ [Formulário]                                         │
│                                                      │
│ ────────────────────────────────────────────────     │
│ [Voltar]           [Salvar] [Visualizar] [Próximo]  │
└──────────────────────────────────────────────────────┘
```

### Mobile (≤ 480px)
```
┌─────────────────────────────────────────────────┐
│ [1] [②] [3] [4] [5] [6] [7] [8] [9]             │
│ ↑ Cada botão ocupa espaço igual                │
│                                                 │
│ ───────────────────────────────────────────     │
│ ↑ Margem de 14px                               │
│                                                 │
│ [Formulário]                                    │
│                                                 │
│ ───────────────────────────────────────────     │
│ [Voltar]         [👁️ Vis.] [Próximo →]          │
└─────────────────────────────────────────────────┘
```

---

## 🎨 Hierarquia Visual do Footer

### Desktop
```
[Voltar]                    [Salvar rascunho] [👁️ Visualizar] [Próximo →]
────────                    ─────────────────────────────────────────────
secondary                            ghost        ghost         primary
(outline)                       (transparente)               (filled accent)
```

### Mobile
```
[Voltar]                                    [👁️ Vis.] [Próximo →]
────────                                    ──────────────────────
secondary                                      ghost     primary
Gap de 8px entre Voltar e ações            Gap de 6px entre ações
```

**Lógica de Exibição:**
- **"Salvar rascunho"**: Só aparece se `hasUnsavedChanges === true` e não estiver na etapa "review"
- **"Visualizar"**: Só aparece da etapa 2 em diante (não na template)
- **"Próximo"**: Sempre visível, muda para "Concluir" na última etapa

---

## 📊 Comparação de Espaçamento

### Stepper

| Elemento | Antes | Depois | Diferença |
|----------|-------|--------|-----------|
| Gap entre botões | 8px | 4-6px | Mais denso |
| Largura dos botões | 32-34px fixo | flex: 1 | Dinâmico |
| Padding bottom | 8px | 14px | +6px |
| Margin bottom | 0px | 4px | +4px |
| **Espaço total abaixo** | **8px** | **18px** | **+125%** |

### Footer

| Viewport | Gap principal | Gap actions-right | Antes | Depois |
|----------|---------------|-------------------|-------|--------|
| Desktop  | 12px          | 10px              | 2 linhas (mobile) | 1 linha |
| Mobile   | 8px           | 6px               | 2 linhas | 1 linha |

---

## ✅ Benefícios das Mudanças

### Stepper
- ✅ **Melhor uso do espaço horizontal**: Todos os 9 botões sempre visíveis
- ✅ **Touch targets maiores**: Mais fácil tocar corretamente
- ✅ **Sem scroll**: Navegação mais direta
- ✅ **Simetria visual**: Distribuição uniforme

### Footer
- ✅ **Hierarquia clara**: "Próximo" sempre na extrema direita
- ✅ **Ações relacionadas agrupadas**: Visualizar e Salvar juntos
- ✅ **Menos linhas no mobile**: 2 → 1 linha
- ✅ **Mais espaço para conteúdo**: ~44px economizados

### Geral
- ✅ **+18px de respiração**: Abaixo do stepper
- ✅ **Layout mais clean**: Menos elementos empilhados
- ✅ **Consistência**: Mesmo layout em desktop e mobile

---

## 🧪 Como Testar

1. **Abrir modal "Criar Currículo"**
2. **Verificar Stepper**:
   - [ ] 9 botões distribuídos uniformemente
   - [ ] Cada botão ocupa espaço igual
   - [ ] Não há scroll horizontal
   - [ ] Espaçamento visível abaixo do stepper

3. **Verificar Footer**:
   - [ ] "Voltar" à esquerda
   - [ ] "Próximo" na extrema direita
   - [ ] "Visualizar" ao lado esquerdo do "Próximo"
   - [ ] "Salvar rascunho" (se visível) antes de "Visualizar"
   - [ ] 1 linha apenas no mobile

4. **Testar em diferentes viewports**:
   - [ ] 375px (iPhone SE)
   - [ ] 412px (Android)
   - [ ] 768px (Tablet)
   - [ ] 1024px+ (Desktop)

---

## 📁 Arquivos Modificados

```
✅ client/src/shared/ui/stepper/Stepper.css
   → Flex: 1 nos itens, distribuição uniforme

✅ client/src/widgets/resume-builder/ui/ResumeBuilderWizard.tsx
   → Reorganizou estrutura do footer (botões agrupados)

✅ client/src/widgets/resume-builder/ui/ResumeBuilderWizard.css
   → Adicionou margin-bottom no stepper
   → Ajustou layout do footer (1 linha mobile)
```

---

## 🔄 Impacto nas Telas

### iPhone SE (375px)
**Antes:**
- Stepper: scroll horizontal
- Footer: 2 linhas (88px altura)

**Depois:**
- Stepper: 9 botões distribuídos (41px cada)
- Footer: 1 linha (52px altura)
- **Ganho: 36px de altura**

### Tablet (768px)
**Antes:**
- Stepper: scroll horizontal
- Footer: 1 linha

**Depois:**
- Stepper: distribuído (85px cada)
- Footer: 1 linha (mantém)
- **Ganho: melhor UX visual**

---

## 💡 Dicas de Implementação

### Para Ajustar Tamanhos dos Botões do Stepper

```css
@media (max-width: 480px) {
  .sr-stepper__circle {
    width: 32px;  /* Ajustar aqui */
    height: 32px; /* Ajustar aqui */
  }
}
```

### Para Ajustar Gap entre Etapas

```css
@media (max-width: 768px) {
  .sr-stepper {
    gap: 4px; /* Ajustar aqui */
  }
}
```

### Para Ajustar Espaçamento Abaixo do Stepper

```css
.sr-resume-builder-wizard__stepper {
  padding-bottom: 14px; /* Ajustar aqui */
  margin-bottom: 4px;   /* Ajustar aqui */
}
```

---

**Data:** Janeiro 2026  
**Versão:** 2.0 (Ajustes pós-implementação inicial)
