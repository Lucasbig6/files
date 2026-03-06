# Automação eGestor APS com Playwright e Python

Este projeto automatiza a navegação no sistema eGestor APS, uma plataforma do governo brasileiro. O script utiliza Playwright para simular a interação humana, realizando login, navegando até a seção de indicadores de qualidade e iterando por uma lista de municípios.

## Funcionalidades

- **Login Automatizado**: Acessa o sistema eGestor APS de forma automática utilizando credenciais do gov.br.
- **Navegação Inteligente**: Navega através do sistema até a seção de componentes de qualidade.
- **Processamento em Lote**: Itera sobre uma lista de municípios a partir de um arquivo `municipios.csv`.
- **Resumo de Progresso**: Salva o último município processado e retoma a partir dele em caso de interrupção.
- **Interação Humanizada**: Simula o comportamento humano para evitar bloqueios e detecções, com pausas e digitação realistas.
- **Tratamento de Erros e Reinício Automático**: O script é projetado para ser resiliente, com múltiplas tentativas de cliques e um mecanismo de reinício automático em caso de falhas.

## Pré-requisitos

- [Python 3.8+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/) (geralmente incluído na instalação do Python)

## Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/seu-repositorio.git
    cd seu-repositorio
    ```

2.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Instale os navegadores do Playwright:**
    ```bash
    playwright install
    ```

## Configuração

1.  **Crie o arquivo de ambiente:**
    Copie o arquivo de exemplo `.env.example` para um novo arquivo chamado `.env`.
    ```bash
    cp .env.example .env
    ```

2.  **Configure suas credenciais:**
    Abra o arquivo `.env` e substitua os valores de `EGESTOR_CPF` e `EGESTOR_SENHA` pelas suas credenciais de acesso ao sistema gov.br.

    ```ini
    EGESTOR_CPF=seu_cpf_aqui
    EGESTOR_SENHA=sua_senha_aqui
    ```

## Uso

Para iniciar a automação, execute o script principal:

```bash
python egestor.py
```

O script irá abrir um navegador, realizar o login (pode exigir a resolução de um CAPTCHA manualmente na primeira vez) e iniciar o processo de navegação pelos municípios.

## Estrutura do Projeto

| Função (`egestor.py`)      | Descrição                                                                      |
| -------------------------- | ------------------------------------------------------------------------------ |
| `login()`                  | Realiza o processo de autenticação no sistema via gov.br.                      |
| `navegar_sistema()`        | Navega pela interface do eGestor até a seção de indicadores.                   |
| `selecionar_municipio()`   | Busca e seleciona um município na lista de opções.                             |
| `navegar_indicadores()`    | Percorre e clica nos links dos diferentes indicadores de saúde.                |
| `salvar_progresso()`       | Salva o nome do último município processado com sucesso.                       |
| `carregar_progresso()`     | Lê o último município salvo para retomar o processo.                           |
| `executar_fluxo()`         | Orquestra o fluxo principal da automação, processando cada município.          |
| `main()`                   | Controla a execução do script, incluindo o mecanismo de reinício automático.   |

## Aviso

Este script foi desenvolvido para fins de automação de tarefas repetitivas. O uso de scripts de automação em sistemas governamentais deve ser feito com responsabilidade. Esteja ciente dos termos de serviço da plataforma e evite sobrecarregar o sistema com um número excessivo de requisições. O desenvolvedor não se responsabiliza por qualquer uso indevido.
