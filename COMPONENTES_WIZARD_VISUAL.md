# 🎨 Referência Visual - Componentes do Wizard

## 📐 Estrutura Geral

```
┌─────────────────────────────────────────────────────────────┐
│ Modal (sr-modal)                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Header (fixo)                                           │ │
│ │ [Criar Currículo]                          [X]          │ │
│ │ Preencha as informações...                              │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ Body (sr-modal__body)                                   │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ ResumeBuilderWizard                                 │ │ │
│ │ │                                                     │ │ │
│ │ │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │ │ │
│ │ │ ┃ BLOCO 1: PROGRESSO (fixo, não rola)            ┃ │ │ │
│ │ │ ┠─────────────────────────────────────────────────┨ │ │ │
│ │ │ ┃ [2 de 9]                    [● Alt. não salvas] ┃ │ │ │
│ │ │ ┃ [████████░░░░░░░░░░░░░░░░░░]                   ┃ │ │ │
│ │ │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │ │ │
│ │ │                                                     │ │ │
│ │ │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │ │ │
│ │ │ ┃ BLOCO 2: STEPPER (fixo, não rola)              ┃ │ │ │
│ │ │ ┠─────────────────────────────────────────────────┨ │ │ │
│ │ │ ┃ [1] [②] [3] [4] [5] [6] [7] [8] [9] →          ┃ │ │ │
│ │ │ ┃      ↑ ativo (borda grossa)                    ┃ │ │ │
│ │ │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │ │ │
│ │ │                                                     │ │ │
│ │ │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │ │ │
│ │ │ ┃ BLOCO 3: CONTEÚDO (ÚNICA ÁREA SCROLLÁVEL) ▼▼▼ ┃ │ │ │
│ │ │ ┠─────────────────────────────────────────────────┨ │ │ │
│ │ │ ┃                                                 ┃ │ │ │
│ │ │ ┃ [Formulário da Etapa Atual]                    ┃ │ │ │
│ │ │ ┃                                                 ┃ │ │ │
│ │ │ ┃ - Campos de input                              ┃ │ │ │
│ │ │ ┃ - Textarea                                     ┃ │ │ │
│ │ │ ┃ - Cards de template                            ┃ │ │ │
│ │ │ ┃ - Listas editáveis                             ┃ │ │ │
│ │ │ ┃                                                 ┃ │ │ │
│ │ │ ┃ (Rola verticalmente)                           ┃ │ │ │
│ │ │ ┃                                                 ┃ │ │ │
│ │ │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │ │ │
│ │ │                                                     │ │ │
│ │ │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │ │ │
│ │ │ ┃ BLOCO 4: FOOTER (fixo, não rola)               ┃ │ │ │
│ │ │ ┠─────────────────────────────────────────────────┨ │ │ │
│ │ │ ┃ Linha 1 (Navegação Primária):                  ┃ │ │ │
│ │ │ ┃ [   Voltar   ] [   Próximo →   ]               ┃ │ │ │
│ │ │ ┃                                                 ┃ │ │ │
│ │ │ ┃ Linha 2 (Ações Secundárias):                   ┃ │ │ │
│ │ │ ┃ [ Visualizar ] [ Salvar rascunho ]             ┃ │ │ │
│ │ │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

LEGENDA:
━━━ = Bloco fixo (não rola com conteúdo)
─── = Separador visual
[②] = Item ativo (destaque)
→   = Indica scroll horizontal possível
▼▼▼ = Área scrollável
```

---

## 🎨 Bloco 1: Progresso

### Desktop (> 768px)
```
┌────────────────────────────────────────────────────────┐
│ ┌──────────────────────────────────────────┐           │
│ │ [████████████░░░░░░░░░░░░░░░░░░]         │  2 de 9  │
│ └──────────────────────────────────────────┘           │
│ ┌──────────────────────────────────────────────────┐   │
│ │ [✓ Salvo há 3min]                                │   │
│ └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

### Mobile (≤ 480px)
```
┌────────────────────────────────────────────────┐
│ [2 de 9]                [● Alterações...]      │ ← 1 linha
│ [████████████░░░░░░░░░░░░░░░░░░]              │ ← barra
└────────────────────────────────────────────────┘

Componentes:
├─ ProgressBar (__header)
│  ├─ __label: "2 de 9"
│  └─ rightContent: AutoSaveIndicator
└─ ProgressBar (__track + __fill)
```

---

## 🔢 Bloco 2: Stepper

### Desktop (> 768px)
```
┌──────────────────────────────────────────────────────────────┐
│ [1 Modelo] [2 Básico] [3 Contato] [4 Experiência] [5 Formação] │
│ [6 Habilidades] [7 Idiomas] [8 Resumo] [9 Revisão]            │
└──────────────────────────────────────────────────────────────┘
```

### Mobile (≤ 768px)
```
┌────────────────────────────────────────────────────┐
│ [1] [②] [3] [4] [5] [6] [7] [8] [9] ──────────→   │ ← scroll
└────────────────────────────────────────────────────┘
     ↑
  Ativo (borda 2px, cor accent)

Características:
├─ overflow-x: auto (scroll horizontal)
├─ scrollbar-width: none (esconde scrollbar)
├─ Labels ocultos (display: none)
└─ Chips: 34px × 34px (touch target ≥ 44px)
```

### Estados dos Números

```
[1]   ← Concluído (is-done)
      - background: rgba(accent, 0.08)
      - border: rgba(accent, 0.25)
      - Tem ícone ✓

[②]   ← Ativo (is-active)
      - background: rgba(accent, 0.18)
      - border: 2px solid accent (mobile)
      - font-weight: 900

[3]   ← Pendente (is-pending)
      - background: surface-2
      - border: 1px solid border
      - color: ink-muted
```

---

## 📝 Bloco 3: Conteúdo

```
┌────────────────────────────────────────────────────┐
│                                                    │
│  ▲ Scroll aqui (overflow-y: auto)                 │
│  │                                                 │
│  │ [Formulário da Etapa]                          │
│  │                                                 │
│  │ ┌──────────────────────────────────────┐       │
│  │ │ Nome completo                        │       │
│  │ │ [_____________________________]      │       │
│  │ └──────────────────────────────────────┘       │
│  │                                                 │
│  │ ┌──────────────────────────────────────┐       │
│  │ │ Cargo desejado                       │       │
│  │ │ [_____________________________]      │       │
│  │ └──────────────────────────────────────┘       │
│  │                                                 │
│  │ ... mais campos ...                            │
│  │                                                 │
│  ▼                                                 │
│                                                    │
└────────────────────────────────────────────────────┘

Grid template:
grid-template-rows: auto auto 1fr auto
                    ↑    ↑    ↑   ↑
                    │    │    │   └─ Footer (auto)
                    │    │    └───── Content (1fr = flex)
                    │    └────────── Stepper (auto)
                    └─────────────── Progress (auto)
```

---

## 🎯 Bloco 4: Footer

### Desktop (> 768px)
```
┌────────────────────────────────────────────────────────────┐
│ [Voltar]               [Visualizar] [Salvar] [Próximo →]   │
└────────────────────────────────────────────────────────────┘

Layout: flex, justify-content: space-between
├─ actions-left: [Voltar]
└─ actions-right: [Visualizar] [Salvar] [Próximo]
```

### Mobile (≤ 480px)
```
┌────────────────────────────────────────────────────┐
│                                                    │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│ ┃ Linha 1: Navegação (min-height: 44px)       ┃  │
│ ┠──────────────────────────────────────────────┨  │
│ ┃ [        Voltar        ] [     Próximo →   ] ┃  │
│ ┃        secondary                primary      ┃  │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                    │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│ ┃ Linha 2: Ações (min-height: 40px)           ┃  │
│ ┠──────────────────────────────────────────────┨  │
│ ┃ [    Visualizar    ] [  Salvar rascunho   ] ┃  │
│ ┃         ghost               ghost            ┃  │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                    │
└────────────────────────────────────────────────────┘

Layout: flex-direction: column
├─ actions-left (order: 1)
│  ├─ [Voltar] (flex: 1)
│  └─ [Próximo] (flex: 1)
└─ actions-right (order: 2)
   ├─ [Visualizar] (flex: 1)
   └─ [Salvar] (flex: 1)
```

### Variantes por Etapa

**Etapa 1 (Template):**
```
Linha 1: [  Cancelar  ] [  Próximo  ]
Linha 2: (vazia - visualizar só aparece da etapa 2)
```

**Etapa 2-8:**
```
Linha 1: [  Voltar  ] [  Próximo  ]
Linha 2: [Visualizar] [Salvar rasc.]  (se houver mudanças)
```

**Etapa 9 (Review):**
```
Linha 1: [  Voltar  ] [  Concluir  ]
Linha 2: [Visualizar] (sem Salvar - última etapa)
```

---

## 📊 Hierarquia de Cores e Pesos

### Navegação (Linha 1) - DESTAQUE MÁXIMO
```
[Voltar]              [Próximo →]
variant: secondary    variant: primary
────────────────────────────────────
▓▓▓▓▓░░░░░░           ▓▓▓▓▓▓▓▓▓▓
Outline, discreto     Filled, accent
Font: 14px            Font: 14px
Weight: 600           Weight: 700
```

### Ações (Linha 2) - SECUNDÁRIO
```
[Visualizar]          [Salvar rascunho]
variant: ghost        variant: ghost
────────────────────────────────────
░░░░░░░░              ░░░░░░░░░░░░
Transparente          Transparente
Font: 13px            Font: 13px
Weight: 600           Weight: 600
Ícone: 12px           Sem ícone
```

---

## 🎨 Tokens de Design

### Cores
```css
--sr-accent:        #6366f1 (indigo)
--sr-accent-rgb:    99, 102, 241
--sr-ink:           texto primário
--sr-ink-subtle:    texto secundário
--sr-ink-muted:     texto terciário
--sr-border:        bordas
--sr-surface:       fundo
--sr-surface-2:     fundo elevado
```

### Espaçamento (Mobile)
```css
gap:
  - wizard:    10px
  - progress:  6px (entre label e barra)
  - stepper:   8px (entre chips)
  - footer:    8px (entre linhas)

padding:
  - wizard:    12px
  - stepper:   8px 0
  - footer:    12px 0
```

### Tamanhos (Mobile)
```css
Stepper chip:  34px × 34px
Touch target:  ≥ 44px × 44px
Button:        linha 1: ≥ 44px altura
               linha 2: ≥ 40px altura
Progress bar:  6px altura
Border radius: 10-12px (chips)
               12px (botões)
```

---

## 🔄 Fluxo de Interação

```
1. Usuário abre modal
   ↓
2. Etapa 1 (Template) aparece
   - Stepper: [①][2][3]...[9]
   - Footer: [Cancelar][Próximo]
   ↓
3. Seleciona template
   ↓
4. Clica "Próximo"
   ↓
5. Etapa 2 (Básico)
   - Stepper: [✓][②][3]...[9] (1 vira ✓)
   - Footer linha 1: [Voltar][Próximo]
   - Footer linha 2: [Visualizar][Salvar]
   ↓
6. Preenche formulário
   - Status: "● Alterações não salvas"
   - "Salvar rascunho" disponível
   ↓
7. Clica "Salvar rascunho"
   - Status: "✓ Salvo há 0s"
   - "Salvar rascunho" some
   ↓
8. Continua até etapa 9
   ↓
9. Etapa 9 (Review)
   - Stepper: [✓][✓]...[✓][⑨]
   - Footer: [Voltar][Concluir]
   ↓
10. Clica "Concluir"
    ↓
11. Modal fecha, currículo criado
```

---

## 📐 Dimensões Críticas

### Breakpoints
```
> 768px   = Desktop
≤ 768px   = Tablet
≤ 480px   = Mobile
≤ 375px   = Mobile pequeno (iPhone SE)
```

### Alturas (Mobile)
```
Header modal:     ~60px
Progress:         ~50px
Stepper:          ~50px
Footer:           ~100px (2 linhas)
─────────────────────────
Total fixo:       ~260px

Content disponível: 100vh - 260px ≈ 550px (em tela 800px)
```

### Larguras (Mobile 375px)
```
Modal:            100vw (375px)
Padding wizard:   12px × 2 = 24px
Content width:    351px

Botão footer:     (351px - 8px gap) / 2 ≈ 171px cada
```

---

**Referência completa dos componentes visuais**
**Data:** Janeiro 2026
