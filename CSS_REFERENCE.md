# 📖 Referência Rápida - CSS Mobile

## Snippets principais aplicados na otimização

---

## 🎯 Layout Flex Container (Mobile)

### **Problema**: Modal rolava inteira, sem separação de áreas

```css
/* ANTES - Tudo junto */
.sr-new-resume {
  display: grid;
  gap: 14px;
}
```

### **Solução**: Flex container com áreas fixas e scrollável

```css
/* DEPOIS - Mobile (≤ 480px) */
@media (max-width: 480px) {
  .sr-new-resume {
    gap: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden; /* Previne scroll duplo */
  }
}
```

**Por quê funciona:**
- `display: flex` permite controle preciso de crescimento
- `height: 100%` faz container ocupar toda modal
- `overflow: hidden` previne scroll no container (só no conteúdo)

---

## 📊 Indicador de Progresso Mobile

### **Problema**: Stepper desktop ocupava muito espaço

```css
/* Desktop - Mantido */
.sr-new-resume__steps {
  display: flex;
  align-items: center;
  gap: 10px;
}
```

### **Solução**: Indicador compacto com barra visual

```css
/* Mobile - Novo componente */
.sr-new-resume__progress--mobile {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-bottom: 1px solid var(--sr-border);
  flex-shrink: 0; /* CRÍTICO: nunca encolhe */
}

.sr-new-resume__progress-text {
  font-size: 11px;
  font-weight: 700;
  color: var(--sr-ink-subtle);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sr-new-resume__progress-bar {
  height: 4px;
  border-radius: 2px;
  background: rgba(var(--sr-accent-rgb), 0.1);
  overflow: hidden;
}

.sr-new-resume__progress-fill {
  height: 100%;
  background: var(--sr-accent);
  transition: width 0.3s ease; /* Anima entre passos */
}
```

**Por quê funciona:**
- `flex-shrink: 0` garante altura fixa mesmo com pouco espaço
- `overflow: hidden` na barra cria efeito de preenchimento suave
- `transition` anima crescimento da barra (33% → 66% → 100%)

---

## 📜 Área Scrollável

### **Problema**: Scroll confuso, tudo rolava junto

```css
/* ANTES - Sem controle de scroll */
.sr-new-resume__panel {
  display: grid;
  gap: 10px;
}
```

### **Solução**: Wrapper com scroll isolado

```css
/* Wrapper scrollável */
.sr-new-resume__content {
  flex: 1; /* Ocupa espaço restante */
  overflow-y: auto; /* Scroll vertical */
  overflow-x: hidden; /* Sem scroll horizontal */
  padding: 12px;
  min-height: 0; /* CRÍTICO: fix para flexbox */
}
```

**Por quê funciona:**
- `flex: 1` faz área crescer e ocupar espaço entre header e footer
- `min-height: 0` resolve bug onde flex items ignoram overflow
- `overflow-x: hidden` previne scroll horizontal indesejado

**Explicação do `min-height: 0`:**
```
Flexbox tem comportamento padrão:
min-height: auto → "nunca seja menor que meu conteúdo"

Problema:
Conteúdo muito grande → flex item cresce → overflow não funciona

Solução:
min-height: 0 → "pode ser menor que conteúdo" → overflow funciona!
```

---

## 🎴 Cards Otimizados

### **Problema**: Cards muito grandes (2 colunas, preview 120px, botão abaixo)

```css
/* ANTES - Tablet */
@media (max-width: 768px) {
  .sr-new-resume__carousel {
    grid-template-columns: 1fr; /* Já era 1 coluna */
  }
  
  .sr-new-resume__preview {
    height: 120px;
  }
  
  .sr-new-resume__template-body {
    flex-direction: column; /* Botão abaixo */
  }
}
```

### **Solução**: Cards compactos (1 coluna, preview 80px, layout horizontal)

```css
/* Mobile ≤ 480px */
@media (max-width: 480px) {
  .sr-new-resume__carousel {
    gap: 10px; /* Reduzido de 12px */
  }

  .sr-new-resume__template {
    padding: 10px; /* Reduzido de 12px */
    gap: 8px;
  }

  /* Preview reduzido */
  .sr-new-resume__preview {
    height: 80px; /* Redução de 33% */
  }

  /* Layout horizontal (título + botão lado a lado) */
  .sr-new-resume__template-body {
    flex-direction: row;
    align-items: center;
    gap: 10px;
  }

  /* Textos menores */
  .sr-new-resume__template-title {
    font-size: 13px;
  }

  .sr-new-resume__template-desc {
    font-size: 11px;
    margin-top: 1px;
    -webkit-line-clamp: 1; /* Trunca em 1 linha */
  }
}
```

**Truncamento de texto:**
```css
/* Já estava no desktop */
.sr-new-resume__template-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2; /* 2 linhas no desktop */
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Mobile: apenas ajusta quantidade de linhas */
@media (max-width: 480px) {
  .sr-new-resume__template-desc {
    -webkit-line-clamp: 1; /* 1 linha no mobile */
  }
}
```

**Por quê funciona:**
- `flex-direction: row` coloca botão ao lado (aproveita largura)
- `height: 80px` reduz preview mantendo proporção
- `-webkit-line-clamp: 1` trunca automaticamente com "..."

---

## 🦶 Footer Fixo

### **Problema**: Botões rolavam junto com conteúdo

```css
/* ANTES - Inline com conteúdo */
.sr-new-resume__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}
```

### **Solução**: Footer sticky com botões flex

```css
/* Footer fixo (renomeado de __actions para __footer) */
.sr-new-resume__footer {
  flex-shrink: 0; /* CRÍTICO: nunca encolhe */
  padding: 12px;
  border-top: 1px solid var(--sr-border);
  background: var(--sr-surface);
  margin-top: 0;
  gap: 8px;
}

/* Dark mode */
[data-sr-theme-scope][data-theme='dark'] .sr-new-resume__footer {
  background: var(--sr-surface-soft);
}

/* Botões ocupam largura igual */
.sr-new-resume__footer > button {
  flex: 1;
  min-width: 0; /* Permite flex encolher se necessário */
}
```

**Por quê funciona:**
- `flex-shrink: 0` mantém footer sempre na altura definida
- `background` cria separação visual clara do conteúdo
- `flex: 1` nos botões divide espaço igualmente (UX mobile)
- `border-top` reforça que é área separada

---

## 📱 Modal Base (Ajustes)

### **Problema**: Header/body não otimizados para mobile extremo

```css
/* ANTES - Mobile genérico (≤ 768px) */
@media (max-width: 480px) {
  .sr-modal__header {
    padding: 12px;
  }
  
  .sr-modal__title {
    font-size: 15px;
  }
  
  .sr-modal__body {
    padding: 12px;
  }
}
```

### **Solução**: Header compacto, body sem padding

```css
/* DEPOIS - Mobile específico (≤ 480px) */
@media (max-width: 480px) {
  .sr-modal__header {
    padding: 10px 12px; /* -2px vertical */
  }

  .sr-modal__title {
    font-size: 14px; /* -1px */
    line-height: 1.3;
  }

  .sr-modal__subtitle {
    font-size: 11px; /* -2px do 768px */
    margin-top: 4px;
    line-height: 1.4;
  }

  .sr-modal__body {
    padding: 0; /* Remove padding */
    display: flex;
    flex-direction: column;
  }

  .sr-modal__close {
    width: 32px; /* -2px */
    height: 32px;
    font-size: 16px; /* -2px */
  }
}
```

**Por quê funciona:**
- `padding: 0` no body delega controle para conteúdo interno
- `display: flex` permite NewResumeModal usar flex: 1
- Reduções sutis (1-2px) economizam ~8px de altura total

---

## 🎨 Padrão de Visibilidade

### **Toggle Desktop ↔ Mobile**

```css
/* Desktop: mostrar stepper */
.sr-new-resume__steps--desktop {
  display: flex;
}

/* Mobile: ocultar stepper */
@media (max-width: 480px) {
  .sr-new-resume__steps--desktop {
    display: none;
  }
}
```

```css
/* Desktop: ocultar progress */
.sr-new-resume__progress--mobile {
  display: none;
}

/* Mobile: mostrar progress */
@media (max-width: 480px) {
  .sr-new-resume__progress--mobile {
    display: flex;
  }
}
```

**Alternativa (sem classes extras):**
```css
/* Opção 1: Classes específicas (implementado) */
.sr-new-resume__steps--desktop { }
.sr-new-resume__progress--mobile { }

/* Opção 2: :not() selector (mais complexo) */
.sr-new-resume__steps:not(.sr-new-resume__progress) { }
```

---

## 🔧 Truques Úteis

### **1. Prevenir Scroll Horizontal**
```css
.sr-new-resume__content {
  overflow-x: hidden;
  max-width: 100%;
}

/* Nos children */
* {
  max-width: 100%;
  box-sizing: border-box;
}
```

### **2. Área de Toque Mínima (44px)**
```css
.sr-new-resume__footer > button {
  min-height: 44px; /* Recomendação Apple/Google */
  min-width: 44px;
}
```

### **3. Animação Suave de Transição**
```css
.sr-new-resume__progress-fill {
  transition: width 0.3s ease;
}

/* Anima de 0% → 33% → 66% → 100% */
```

### **4. Truncamento com Fallback**
```css
.sr-new-resume__template-desc {
  /* Modern browsers */
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  
  /* Fallback (mostra texto completo) */
  /* Navegadores antigos ignoram -webkit-* */
}
```

### **5. Sticky com Z-Index**
```css
.sr-modal__header {
  position: sticky;
  top: 0;
  z-index: 1; /* Acima do conteúdo */
  background: var(--sr-surface); /* Cobre conteúdo ao scrollar */
}
```

---

## 📐 Hierarquia de Sizes (Mobile)

```css
/* Font Sizes - Mobile */
11px → Descrições, labels secundárias
12px → Inputs, textos auxiliares
13px → Títulos de seção, labels principais
14px → Título da modal
15px → (não usado no mobile para economia)

/* Spacing - Mobile */
4px  → Gaps internos (progress bar)
6px  → Gaps mínimos (progress text/bar)
8px  → Gaps padrão conteúdo
10px → Paddings pequenos
12px → Paddings padrão

/* Heights - Mobile */
32px → Botões de fechar
44px → Botões de ação (área toque)
48px → Header total
54px → Footer total
80px → Preview cards
```

---

## 🎯 Fórmula do Sucesso

### **Layout Flex 3 Áreas**
```
┌─────────────────┐
│ Header          │ ← flex-shrink: 0 (fixo)
├─────────────────┤
│ Content         │ ← flex: 1 (cresce)
│ (scroll aqui)   │   overflow-y: auto
│                 │   min-height: 0
├─────────────────┤
│ Footer          │ ← flex-shrink: 0 (fixo)
└─────────────────┘
```

### **CSS Completo**
```css
.container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.header {
  flex-shrink: 0;
}

.content {
  flex: 1;
  overflow-y: auto;
  min-height: 0; /* ⚠️ Crítico! */
}

.footer {
  flex-shrink: 0;
}
```

---

## 🐛 Problemas Comuns e Fixes

### **Problema 1: Scroll não funciona**
```css
/* ❌ Errado */
.content {
  flex: 1;
  overflow-y: auto;
}

/* ✅ Correto */
.content {
  flex: 1;
  overflow-y: auto;
  min-height: 0; /* Adicione isso! */
}
```

### **Problema 2: Footer rola junto**
```css
/* ❌ Errado */
.footer {
  /* Sem flex-shrink */
}

/* ✅ Correto */
.footer {
  flex-shrink: 0; /* Garante que nunca encolhe */
}
```

### **Problema 3: Scroll horizontal aparece**
```css
/* ✅ Adicione em todos os níveis */
.content {
  overflow-x: hidden;
}

.content > * {
  max-width: 100%;
  box-sizing: border-box;
}
```

### **Problema 4: Botões quebram linha**
```css
/* ❌ Errado */
.footer > button {
  width: 50%; /* Não respeita gaps */
}

/* ✅ Correto */
.footer > button {
  flex: 1; /* Divide espaço automaticamente */
  min-width: 0;
}
```

---

## 📚 Recursos Úteis

### **Flexbox Guide**
- `flex: 1` = `flex-grow: 1; flex-shrink: 1; flex-basis: 0`
- `flex-shrink: 0` = "não encolha, mantenha tamanho"
- `min-height: 0` = fix para overflow em flex items

### **Line Clamp Browser Support**
- Chrome/Edge: 100%
- Safari: 100%
- Firefox: 68+ (2019)
- Fallback: Mostra texto completo (graceful degradation)

### **CSS Variables**
```css
var(--sr-accent)       → Cor primária
var(--sr-accent-rgb)   → RGB para rgba()
var(--sr-border)       → Cor de bordas
var(--sr-surface)      → Fundo componentes
var(--sr-ink)          → Texto principal
var(--sr-ink-subtle)   → Texto secundário
```

---

**Última atualização**: 2026-01-19  
**Compatibilidade**: Chrome 90+, Safari 14+, Firefox 68+, Edge 90+  
**Mobile tested**: iOS 14+, Android 9+
