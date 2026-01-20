# ⚡ Teste Rápido - Modal Mobile (5 minutos)

## 🎯 Objetivo
Validar rapidamente se as otimizações mobile estão funcionando corretamente sem bugs visuais ou de interação.

---

## 🛠️ Setup (30 segundos)

### **Chrome DevTools**
1. Abra a aplicação
2. Pressione **F12**
3. Clique no ícone de **celular** (Toggle Device Toolbar) ou **Ctrl+Shift+M**
4. Selecione **"iPhone SE"** ou configure **375x667** manualmente
5. Refresh (F5)

---

## ✅ Checklist Express

### **1. Abrir Modal** (10 segundos)
- [ ] Clique em "Novo Currículo" ou botão que abre a modal
- [ ] Modal abre em tela cheia (sem bordas arredondadas)
- [ ] Header visível com título "Novo Currículo"

### **2. Verificar Header** (10 segundos)
- [ ] Título legível (não muito pequeno)
- [ ] Subtítulo presente e legível
- [ ] Botão [×] no canto superior direito funcional
- [ ] Header ocupa ~48px (não muito alto)

### **3. Verificar Indicador de Progresso** (15 segundos)
- [ ] Logo abaixo do header: "ETAPA 1 DE 3"
- [ ] Barra de progresso azul abaixo do texto
- [ ] Barra preenchida em ~33%
- [ ] **NÃO** aparece os círculos [1] [2] [3]

### **4. Verificar Cards (Passo 1)** (30 segundos)
- [ ] Título "Selecione seu modelo" visível
- [ ] 3 cards empilhados verticalmente (1 por linha)
- [ ] Cada card tem:
  - [ ] Preview colorido (~80px altura)
  - [ ] Título do modelo (Tech/Business/Minimal)
  - [ ] Botão "Selecionar" **ao lado do título** (não abaixo)
  - [ ] Descrição em 1 linha (truncada com "...")
- [ ] Cards **NÃO** estão lado a lado (seria erro)
- [ ] Possível ver todos os 3 cards sem scroll (ou com scroll mínimo)

### **5. Verificar Footer** (20 segundos)
- [ ] Footer fixo no fundo da tela
- [ ] 2 botões: "Cancelar" e "Próximo"
- [ ] Botões lado a lado ocupando largura similar
- [ ] Footer **NÃO** desaparece ao scrollar
- [ ] Borda sutil separando footer do conteúdo

### **6. Testar Scroll** (30 segundos)
- [ ] Scroll na área de cards funciona
- [ ] **Header permanece fixo** ao scrollar
- [ ] **Footer permanece fixo** ao scrollar
- [ ] Apenas conteúdo central rola
- [ ] Scroll suave (sem trepidação)

### **7. Navegação entre Passos** (60 segundos)

**Passo 1 → 2:**
- [ ] Clique "Selecionar" em qualquer card
- [ ] Clique "Próximo"
- [ ] Indicador muda para "ETAPA 2 DE 3"
- [ ] Barra de progresso anima para ~66%
- [ ] Input de nome aparece
- [ ] Footer muda para "Voltar" + "Próximo"

**Passo 2 → 3:**
- [ ] Digite qualquer texto (mínimo 3 caracteres)
- [ ] Clique "Próximo"
- [ ] Indicador muda para "ETAPA 3 DE 3"
- [ ] Barra de progresso completa (100%)
- [ ] Cards de "Próximas etapas" aparecem
- [ ] Footer muda para "Voltar" + "Criar currículo"

**Passo 3 → 2 (Voltar):**
- [ ] Clique "Voltar"
- [ ] Volta para passo 2
- [ ] Indicador volta para "ETAPA 2 DE 3"
- [ ] Barra volta para ~66%

### **8. Testar Fechamento** (15 segundos)
- [ ] Clique "Cancelar" → modal fecha
- [ ] Reabra modal → volta para passo 1
- [ ] Clique no [×] → modal fecha
- [ ] Clique no fundo escuro (backdrop) → modal fecha
- [ ] Pressione ESC → modal fecha

### **9. Responsividade** (30 segundos)

**Teste em 3 larguras:**

**480px:**
- [ ] Arraste para 480px de largura
- [ ] Layout mobile ainda ativo
- [ ] Indicador "ETAPA X DE 3" visível

**481px:**
- [ ] Arraste para 481px
- [ ] Layout muda para desktop
- [ ] Círculos [1] [2] [3] aparecem
- [ ] Modal não ocupa tela cheia

**375px (iPhone SE):**
- [ ] Configure 375px width
- [ ] Layout mobile funciona
- [ ] Nenhum overflow horizontal
- [ ] Botões do footer não quebram linha

### **10. Dark Mode** (20 segundos se disponível)
- [ ] Ative dark mode na aplicação
- [ ] Modal permanece legível
- [ ] Footer tem background escuro
- [ ] Bordas sutis mas visíveis
- [ ] Cores de texto adequadas

---

## 🚨 Checklist de Problemas Comuns

Se encontrar algum desses, há um bug:

- ❌ Cards aparecem lado a lado no mobile (deve ser 1 por linha)
- ❌ Círculos [1] [2] [3] visíveis no mobile (deve ser "ETAPA X DE 3")
- ❌ Footer desaparece ao scrollar (deve ser fixo)
- ❌ Header some ao scrollar (deve ser fixo)
- ❌ Scroll horizontal aparece (tela deve caber 100%)
- ❌ Botões do footer quebram em 2 linhas (devem ficar lado a lado)
- ❌ Modal não ocupa tela cheia no mobile (deve ocupar 100%)
- ❌ Barra de progresso não anima entre passos
- ❌ Preview dos cards muito grande (deve ser ~80px)
- ❌ Descrição dos cards em 2 linhas (deve truncar em 1)

---

## 📸 Referências Visuais

### ✅ **CORRETO** (Mobile ≤ 480px)

```
┌─────────────────────┐
│ [×] Novo Currículo  │ ← Header compacto, fixo
│ Preencha as...      │
├─────────────────────┤
│ ETAPA 1 DE 3        │ ← Indicador + barra
│ ████░░░░░░░░        │
├─────────────────────┤
│ Selecione seu...   │ ← Área scrollável
│                     │
│ ┌─────────────────┐ │
│ │ [Preview 80px]  │ │ ← 1 card por linha
│ │ Tech [Selecionar]│ │
│ │ Ideal para...   │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ [Preview 80px]  │ │
│ │ Business [Sel]  │ │
│ │ Foco em...      │ │
│ └─────────────────┘ │
│                     │
├─────────────────────┤
│ [Cancelar] [Próximo]│ ← Footer fixo
└─────────────────────┘
```

### ❌ **INCORRETO** (se ver isso, há problema)

```
┌─────────────────────┐
│ [×] Novo Currículo  │
│ Preencha as...      │
├─────────────────────┤
│ [1] [2] [3]         │ ← Círculos (erro!)
├─────────────────────┤
│ Selecione seu...   │
│                     │
│ ┌──────┐ ┌──────┐  │ ← 2 cards lado a lado
│ │[120px]│ │[120px]│ │   (erro!)
│ │      │ │      │  │
│ │ Tech │ │ Biz  │  │
│ │ Desc │ │ Desc │  │
│ │[Sel] │ │[Sel] │  │
│ └──────┘ └──────┘  │
│                     │
│ [Cancelar] [Próximo]│ ← Botões rolam (erro!)
│                     │
│ (scroll continua)   │
```

---

## 🎮 Teste Interativo Completo (2 minutos)

1. **Abra modal** → ESC → Fecha ✅
2. **Reabra** → Selecione "Tech" → Próximo ✅
3. **Digite** "Meu Currículo 2026" → Próximo ✅
4. **Observe** barra de progresso 100% ✅
5. **Volte** 2 vezes → Volta ao passo 1 ✅
6. **Scroll** para baixo e cima → Header/Footer fixos ✅
7. **Clique** backdrop → Fecha ✅

**Todos os passos funcionaram? Parabéns, otimização mobile 100%! 🎉**

---

## 🐛 Reportar Problema

Se encontrou um bug, anote:

1. **Largura da tela testada**: _____ px
2. **Passo da modal**: 1 / 2 / 3
3. **Comportamento esperado**: _____
4. **Comportamento observado**: _____
5. **Screenshot**: (se possível)

---

## 📱 Dispositivos Reais (Opcional)

Se tiver acesso, teste em:

- **iPhone SE / 12 Mini** (375px)
- **iPhone 12/13/14** (390px)
- **Galaxy S21/S22** (360px)
- **Pixel 5/6** (393px)

Procedimento:
1. Acesse aplicação pelo IP local (ex: `192.168.1.x:3000`)
2. Abra modal "Novo Currículo"
3. Execute checklist acima

---

## ✅ Validação Final

**Tudo funcionando se:**
- ✅ Indicador "ETAPA X DE 3" visível (não círculos)
- ✅ Cards em 1 coluna vertical
- ✅ Preview ~80px (não 120px)
- ✅ Botão ao lado do título (não abaixo)
- ✅ Footer sempre visível
- ✅ Scroll apenas no conteúdo
- ✅ Transições suaves
- ✅ Sem overflow horizontal

**Tempo total de teste: ~5 minutos**

---

**Última atualização**: 2026-01-19  
**Breakpoint testado**: ≤ 480px  
**Navegadores**: Chrome/Edge/Safari mobile
