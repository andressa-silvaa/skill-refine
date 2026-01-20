# 🧪 Guia Rápido de Teste - Modal Wizard Mobile

## 🚀 Como Testar (5 minutos)

### 1️⃣ Abrir no Navegador

```bash
# Se o servidor ainda não está rodando
cd client
npm run dev
```

Abra: `http://localhost:3000/curriculos`

---

### 2️⃣ Abrir DevTools Mobile

**Chrome DevTools:**
1. F12 ou Ctrl+Shift+I
2. Toggle device toolbar (Ctrl+Shift+M)
3. Selecionar dispositivo

**Dispositivos recomendados:**
- iPhone SE (375px) - menor iOS
- iPhone 12/13 Pro (390px)
- Samsung Galaxy S20 (360px)
- Pixel 5 (393px)
- iPad Mini (768px)

---

### 3️⃣ Abrir Modal Wizard

1. Clique no botão "Novo Currículo"
2. Modal de 9 etapas abre

---

## ✅ O Que Verificar

### 📊 Bloco de Progresso (Topo)

```
✅ Linha 1: [1 de 9] .......................... [● Alterações não salvas]
✅ Linha 2: [████░░░░░░░░░░░░░░] (barra visual)
```

**Esperado:**
- "1 de 9" alinhado à esquerda
- Status alinhado à direita
- Barra embaixo, full width
- Se status muito longo, trunca com "..."

---

### 🔢 Stepper (Logo Abaixo)

**Desktop (> 768px):**
```
[1 Modelo] [2 Básico] [3 Contato] [4 Experiência] ...
```

**Mobile (≤ 768px):**
```
[1] [2] [3] [4] [5] [6] [7] [8] [9] → (scroll horizontal)
```

**Mobile ≤ 480px:**
```
[1] [②] [3] [4] [5] [6] [7] [8] [9] → (② = ativo, destaque forte)
```

**Checklist:**
- [ ] Apenas números visíveis (labels ocultos)
- [ ] Scroll horizontal funciona
- [ ] Scrollbar não aparece
- [ ] Item ativo (2) tem borda mais grossa + cor accent
- [ ] Todos os 9 números visíveis ao scrollar
- [ ] Touch nos números funciona (mudar etapa se permitido)

---

### 📝 Conteúdo (Meio)

**Checklist:**
- [ ] Formulário da etapa atual aparece
- [ ] Conteúdo rola verticalmente
- [ ] Header/Stepper não rolam (ficam fixos)
- [ ] Footer não rola (fica fixo)
- [ ] Sem overflow horizontal (não tem scroll lateral no content)

---

### 🎯 Footer (Rodapé)

**Desktop:**
```
[Voltar] ................................. [Visualizar] [Salvar] [Próximo →]
```

**Mobile (≤ 480px):**
```
Linha 1: [   Voltar   ] [   Próximo →   ]  (50% / 50%)
Linha 2: [ Visualizar ] [ Salvar rascunho ] (50% / 50%)
```

**Checklist:**
- [ ] Linha 1: Voltar + Próximo, mesmo tamanho
- [ ] Linha 2: Visualizar + Salvar (se visíveis)
- [ ] "Próximo" é primary (cor accent)
- [ ] "Voltar" é secondary (outline)
- [ ] "Visualizar" e "Salvar" são ghost (discretos)
- [ ] Botões têm pelo menos 44px de altura (linha 1)
- [ ] Fácil de tocar sem erro
- [ ] Separação clara entre navegação e ações

**Observações:**
- Etapa 1 (template): Só aparece "Cancelar" e "Próximo"
- Etapa 9 (review): "Próximo" vira "Concluir"
- "Visualizar" só aparece da etapa 2 em diante
- "Salvar" só aparece se houver mudanças não salvas

---

## 🎨 Comparação Visual

### ANTES (Mobile):
```
┌─────────────────────────────┐
│ [Progress] 2 de 9           │ ← linha
│ [● Alterações não salvas]   │ ← outra linha
│ ─────────────────────────── │
│                             │
│ [1 Modelo] [2 Básico]       │ ← quebra de linha
│ [3 Contato] [4 Exp...]      │ ← mais linhas
│ [5 Formação] ...            │ ← denso!
│ ─────────────────────────── │
│                             │
│ [  Formulário aqui  ]       │ ← espaço pequeno
│                             │
│ ─────────────────────────── │
│ [Voltar]                    │ ← linha
│ [Visualizar] [Salvar] [→]   │ ← 3 botões apertados
└─────────────────────────────┘
```

### DEPOIS (Mobile):
```
┌─────────────────────────────┐
│ [2 de 9] ........ [● Alt...] │ ← 1 linha compacta
│ [████░░░░░░░] (barra)        │
│ ─────────────────────────── │
│                             │
│ [1][②][3][4][5][6][7][8][9] │ ← 1 linha, scroll →
│ ─────────────────────────── │
│                             │
│                             │
│ [  Formulário aqui  ]       │ ← 30% mais espaço!
│       (área maior)          │
│                             │
│ ─────────────────────────── │
│ [  Voltar  ] [  Próximo →  ] │ ← navegação clara
│ [Visualizar] [Salvar rasc.] │ ← ações secundárias
└─────────────────────────────┘
```

---

## 🐛 Bugs Comuns e Como Identificar

### 1. Stepper quebra linha
**Sintoma:** Números aparecem em 2+ linhas
**Causa:** `flex-wrap: wrap` ou falta `nowrap`
**Verificar:** `.sr-stepper` tem `flex-wrap: nowrap` no CSS

### 2. Footer 3 botões na mesma linha
**Sintoma:** [Vis][Salv][Próx] espremidos
**Causa:** Media query não aplicada
**Verificar:** Testar em <= 480px real, não 481px

### 3. Conteúdo não rola
**Sintoma:** Formulário cortado, sem scroll
**Causa:** `overflow-y: auto` faltando
**Verificar:** `.sr-resume-builder-wizard__content`

### 4. Header rola junto
**Sintoma:** Progresso/Stepper somem ao rolar
**Causa:** Grid template rows incorreto
**Verificar:** `grid-template-rows: auto auto 1fr auto`

---

## 📐 Breakpoints Críticos

Testar **especificamente** nestes tamanhos:

```
1. 480px  → Entra modo mobile compacto (footer 2 linhas)
2. 481px  → Ainda tablet (footer 1 linha)
3. 768px  → Limite tablet/desktop
4. 375px  → iPhone SE (mais comum)
5. 360px  → Android pequeno
6. 1024px → Desktop padrão
```

**Como testar:**
1. DevTools → Responsive
2. Digitar largura manualmente
3. Recarregar página se necessário

---

## 🎯 Teste em 30 Segundos

**Checklist Express:**

```bash
1. Abrir modal (Novo Currículo)
2. Redimensionar para 375px
3. Verificar:
   ✓ Stepper = só números, scroll horizontal
   ✓ Footer = 2 linhas separadas
   ✓ Conteúdo rola, header/footer fixos
4. Ir para próxima etapa
5. Verificar:
   ✓ Número ativo muda (1 → 2)
   ✓ Barra de progresso atualiza
   ✓ Botões continuam organizados
```

**Se tudo acima ✓ = Funcionando!**

---

## 📱 Teste em Dispositivo Real (Opcional)

### iOS (Safari)
1. Conectar iPhone via USB
2. Safari → Develop → [Seu iPhone]
3. Navegar até localhost (ou usar ngrok/tunnel)

### Android (Chrome)
1. Conectar via USB
2. Chrome → `chrome://inspect`
3. Inspecionar dispositivo

**Vantagens:**
- Touch real (não simulado)
- Performance real
- Scrolling nativo
- Possíveis bugs específicos de device

---

## ✅ Critérios de Sucesso

### Funcional
- [ ] Todas as 9 etapas navegáveis
- [ ] Botões funcionam (Voltar, Próximo, Visualizar, Salvar)
- [ ] Stepper clicável (etapas já visitadas)
- [ ] Scroll horizontal suave
- [ ] Scroll vertical apenas no content

### Visual
- [ ] Hierarquia clara (navegação vs ações)
- [ ] Touch targets >= 44px
- [ ] Sem elementos cortados ou sobrepostos
- [ ] Cores e espaçamento consistentes
- [ ] Transições suaves

### UX
- [ ] Intuitivo localizar "Próximo" e "Voltar"
- [ ] Claro qual etapa está ativa
- [ ] Área de formulário confortável (não espremida)
- [ ] Fácil tocar botões sem erro

---

**Tempo estimado:** 5-10 min (teste completo)
**Dispositivos mínimos:** 2 (mobile + desktop)
**Data:** Janeiro 2026
