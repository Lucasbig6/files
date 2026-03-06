# Automação eGestor APS — Playwright + Python

## Instalação

```bash
# 1. Instale as dependências Python
pip install -r requirements.txt

# 2. Instale o navegador Chromium do Playwright
playwright install chromium

# 3. Configure suas credenciais
cp .env.example .env
# Edite o .env com seu CPF e senha
```

## Uso

```bash
python egestor.py
```

## Estrutura do script

| Função                    | O que faz                                           |
|---------------------------|-----------------------------------------------------|
| `fazer_login()`           | Acessa o sistema e autentica via gov.br             |
| `navegar_relatorios()`    | Clica no menu de Relatórios                         |
| `extrair_dados_relatorio()` | Lê dados de tabelas na página de relatório        |

## Como adaptar

### Ajustar seletores
Abra o navegador com `headless=False` (já está assim por padrão), 
inspecione os elementos com F12 e atualize os seletores nos comentários `# Ajuste`.

### Adicionar filtros/período
No `main()`, descomente e implemente as funções de exemplo:
```python
await selecionar_periodo(page, "2024-01", "2024-12")
await aplicar_filtros(page, unidade="UBS Centro")
await exportar_csv(page)
```

### Screenshots de debug
Cada etapa gera um `screenshot_NNN_*.png` na pasta atual — 
use para entender onde o script trava.

## Autenticação gov.br
O eGestor usa SSO do gov.br. Se aparecer **validação em 2 fatores** 
(SMS ou app), será necessário tratar a etapa extra no fluxo de login.
