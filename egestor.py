from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
import pandas as pd
import argparse
import fcntl
import os
import time
import random
import re
import subprocess
import sys

load_dotenv()

gov_user = os.getenv("EGESTOR_CPF")
gov_password = os.getenv("EGESTOR_SENHA")
state_file = os.getenv("EGESTOR_STATE_FILE", "state_user.json")
force_login = os.getenv("EGESTOR_FORCE_LOGIN", "0") == "1"

INDICADORES = [
    "Mais Acesso",
    "Desenvolvimento Infantil",
    "Gestação e Puerpério",
    "Diabetes",
    "Hipertensão",
    "Pessoa Idosa",
    "Prevenção do Câncer"
]

CAMPOS_SAIDA = [
    "EQUIPE",
    "NM",
    "DN",
    "PONTUAÇÃO",
    "INDICADOR",
    "COMPETENCIA SELECIONADA",
    "TIPO EQUIPE",
    "MUNICIPIO",
]


# ----------------------------
# Funções humanizadas
# ----------------------------

def delay_humano(min=0.8, max=2.5):
    time.sleep(random.uniform(min, max))


def digitar_humano(page, texto):
    for letra in texto:
        page.keyboard.type(letra)
        time.sleep(random.uniform(0.05, 0.18))


def retry_click(locator, tentativas=3):

    for tentativa in range(tentativas):

        try:
            delay_humano()
            locator.click()
            return

        except PlaywrightTimeoutError:

            print(f"Tentativa {tentativa+1} falhou")

            delay_humano(2,4)

    raise Exception("Falha ao clicar")


# ----------------------------
# Progresso
# ----------------------------

def carregar_processados(caminho_processados):
    if not os.path.exists(caminho_processados):
        return set()

    with open(caminho_processados, "r", encoding="utf-8") as f:
        return {linha.strip() for linha in f if linha.strip()}


def salvar_processado(municipio, caminho_processados):
    with open(caminho_processados, "a", encoding="utf-8") as f:
        f.write(f"{municipio}\n")


def chave_municipio_indicador(municipio, indicador):
    return (limpar_texto(municipio).casefold(), limpar_texto(indicador).casefold())


def carregar_pares_processados_csv(caminho_csv):
    if not os.path.exists(caminho_csv):
        return set()

    try:
        df = pd.read_csv(caminho_csv, usecols=["MUNICIPIO", "INDICADOR"], dtype=str)
    except Exception as e:
        print(f"Aviso: não foi possível ler pares processados do CSV ({e})")
        return set()

    pares = set()
    for _, row in df.dropna(subset=["MUNICIPIO", "INDICADOR"]).iterrows():
        pares.add(chave_municipio_indicador(row["MUNICIPIO"], row["INDICADOR"]))
    return pares


# ----------------------------
# Login
# ----------------------------

def login(page):

    page.goto("https://acesso-egestoraps.saude.gov.br/login")

    delay_humano()

    retry_click(page.get_by_role("link", name="Entrar com gov.br"))

    delay_humano()

    page.get_by_role("textbox", name="Digite seu CPF").click()

    digitar_humano(page, gov_user)

    retry_click(page.get_by_role("button", name="Continuar"))

    print("Resolva o captcha e pressione ENTER")
    input()

    page.get_by_role("textbox", name="Senha").click()

    digitar_humano(page, gov_password)

    retry_click(page.get_by_role("button", name="Entrar"))

    page.wait_for_load_state("networkidle")

    delay_humano(2,4)


def sessao_ativa(page):

    page.goto("https://acesso-egestoraps.saude.gov.br/")

    try:
        page.get_by_role("link", name="Sistema SIAPS").first.wait_for(timeout=10000)
        return True
    except Exception:
        return False


def autenticar_se_necessario(page, context, state_path):

    if force_login:
        print("EGESTOR_FORCE_LOGIN=1. Realizando login limpo.")
        login(page)
        context.storage_state(path=state_path)
        print(f"Estado da sessão salvo em: {state_path}")
        return

    if sessao_ativa(page):
        print("Sessão ativa encontrada. Pulando login.")
        return

    print("Sessão ausente/expirada. Realizando login.")
    login(page)
    context.storage_state(path=state_path)
    print(f"Estado da sessão salvo em: {state_path}")


# ----------------------------
# Navegação sistema
# ----------------------------

def navegar_sistema(page):

    retry_click(page.get_by_role("link", name="Sistema SIAPS"))

    retry_click(page.get_by_role("link", name="Estado TERESINA - PI"))

    retry_click(page.get_by_role("button", name="Acessar Sistema"))

    retry_click(page.get_by_role("button", name="Fechar"))

    retry_click(page.get_by_role("button", name="Acessar Componentes"))

    retry_click(page.get_by_role("button", name="Componente Qualidade ➔"))

    delay_humano(3,5)


# ----------------------------
# Seleção município
# ----------------------------

def selecionar_municipio(page, municipio):

    combo = page.locator('[role="combobox"]').first

    retry_click(combo)

    delay_humano()

    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")

    digitar_humano(page, municipio)

    delay_humano()

    opcao = page.get_by_role("option", name=re.compile(municipio, re.IGNORECASE))

    opcao.wait_for(timeout=10000)

    retry_click(opcao)

    page.wait_for_load_state("networkidle")

    delay_humano(2,4)


# ----------------------------
# Indicadores
# ----------------------------

def navegar_indicadores(page, municipio, caminho_csv, pares_processados):

    for indicador in INDICADORES:
        chave = chave_municipio_indicador(municipio, indicador)
        if chave in pares_processados:
            print(f"   Indicador já processado no CSV, pulando: {indicador}")
            continue

        tentativas_indicador = 3
        sucesso = False

        for tentativa in range(1, tentativas_indicador + 1):
            print(f"   Acessando indicador: {indicador} (tentativa {tentativa}/{tentativas_indicador})")

            try:
                link = page.get_by_role("link", name=indicador)
                retry_click(link)
                delay_humano(3,5)
                selecionar_competencias(page, municipio, indicador, caminho_csv)
                sucesso = True
                pares_processados.add(chave)
                break
            except Exception as e:
                print(f"Erro no indicador {indicador}: {e}")
                delay_humano(1, 2)

        if not sucesso:
            raise Exception(f"Falha definitiva no indicador {indicador}")


def selecionar_competencias(page, municipio, indicador, caminho_csv):

    botao_competencia = page.get_by_role("button", name=re.compile("Competência", re.IGNORECASE))

    retry_click(botao_competencia)
    delay_humano(0.5, 1.2)

    painel_competencia = obter_painel_competencia(page)
    checkboxes = painel_competencia.locator(".p-checkbox-box:visible")
    total_competencias = checkboxes.count()

    if total_competencias == 0:
        print("   Nenhuma competência encontrada")
        return

    print(f"   Competências encontradas: {total_competencias}")

    for indice in range(total_competencias):
        if indice > 0:
            retry_click(botao_competencia)
            delay_humano(0.5, 1.2)
            painel_competencia = obter_painel_competencia(page)
            checkboxes = painel_competencia.locator(".p-checkbox-box:visible")

        checkbox = checkboxes.nth(indice)
        competencia = extrair_nome_competencia(checkbox, indice)

        retry_click(checkbox)
        delay_humano(0.4, 1)

        retry_click(page.get_by_role("button", name="OK"))
        delay_humano(0.4, 1)

        retry_click(page.get_by_role("button", name="Aplicar filtro"))
        delay_humano(1.2, 2.5)

        competencia = obter_competencia_selecionada(page, competencia)
        tipo_equipe = obter_tipo_equipe(page)
        linhas = extrair_linhas_tabela(page, municipio, indicador, competencia, tipo_equipe)
        salvar_dados_webscraping(linhas, caminho_csv)
        print(f"   Linhas coletadas ({competencia}): {len(linhas)}")


def obter_painel_competencia(page):
    painel = page.locator(".p-overlaypanel:visible, .p-dialog:visible").last
    painel.wait_for(timeout=10000)
    return painel


def extrair_nome_competencia(checkbox, indice):
    try:
        container = checkbox.locator("xpath=ancestor::div[contains(@class,'p-element')][1]")
        texto = container.inner_text().strip()
        texto = re.sub(r"\s+", " ", texto)
        if texto:
            return texto
    except Exception:
        pass
    return f"competencia-{indice+1}"


def obter_competencia_selecionada(page, fallback):
    padrao_competencia = r"(?i)\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/\d{2}\b"
    try:
        bloco = page.get_by_label("Visão por Competência").locator("resultado-component").first
        texto = limpar_texto(bloco.inner_text())
        match = re.search(padrao_competencia, texto)
        if match:
            return match.group(0).upper()
    except Exception:
        pass

    try:
        texto = page.locator("body").inner_text()
        match = re.search(r"Compet[eê]ncia selecionada:\s*([A-Za-zÀ-ÿ]{3}/\d{2})", texto)
        if match:
            return match.group(1).upper()
    except Exception:
        pass

    return fallback


def obter_tipo_equipe(page):
    try:
        texto = page.locator("body").inner_text()
        match = re.search(r"Tipo de Equipe:\s*(.+)", texto)
        if match:
            return match.group(1).splitlines()[0].strip()
    except Exception:
        pass
    return ""


def limpar_texto(valor):
    if valor is None:
        return ""
    return re.sub(r"\s+", " ", str(valor)).strip()


def extrair_linhas_pagina(rows, municipio, indicador, competencia, tipo_equipe):
    linhas = []
    total = rows.count()

    for i in range(total):
        row = rows.nth(i)
        colunas = row.locator("td")
        if colunas.count() < 4:
            continue

        equipe_texto = limpar_texto(colunas.nth(0).inner_text())
        nm = limpar_texto(colunas.nth(1).inner_text())
        dn = limpar_texto(colunas.nth(2).inner_text())
        pontuacao = limpar_texto(colunas.nth(3).inner_text())

        equipe = equipe_texto
        if "Equipe:" in equipe_texto:
            equipe = limpar_texto(equipe_texto.split("Equipe:", 1)[1])

        linhas.append({
            "EQUIPE": equipe,
            "NM": nm,
            "DN": dn,
            "PONTUAÇÃO": pontuacao,
            "INDICADOR": indicador,
            "COMPETENCIA SELECIONADA": competencia,
            "TIPO EQUIPE": tipo_equipe,
            "MUNICIPIO": municipio,
        })

    return linhas


def extrair_linhas_tabela(page, municipio, indicador, competencia, tipo_equipe):
    try:
        tabela = (
            page.locator("table[role='table']:visible")
            .filter(has=page.locator("thead th:has-text('EQUIPE')"))
            .filter(has=page.locator("thead th:has-text('NM')"))
            .filter(has=page.locator("thead th:has-text('DN')"))
            .filter(has=page.locator("thead th:has-text('PONTUAÇÃO')"))
            .first
        )
        tabela.wait_for(timeout=15000)

        rows = tabela.locator("tbody tr:visible")
        datatable = tabela.locator("xpath=ancestor::*[contains(@class,'p-datatable')][1]").first
    except Exception:
        print(f"   Tabela visível não encontrada para {indicador} / {competencia}")
        return []

    linhas = []
    pagina = 1
    max_paginas = 200

    while pagina <= max_paginas:
        rows = tabela.locator("tbody tr:visible")
        if rows.count() > 0:
            linhas.extend(extrair_linhas_pagina(rows, municipio, indicador, competencia, tipo_equipe))

        paginator = datatable.locator(".p-paginator:visible").first
        if paginator.count() == 0:
            break

        botao_next = paginator.locator("button.p-paginator-next").first
        if botao_next.count() == 0 or botao_next.is_disabled():
            break

        pagina_atual = ""
        marcador_atual = paginator.locator(".p-paginator-page.p-highlight").first
        if marcador_atual.count() > 0:
            pagina_atual = limpar_texto(marcador_atual.inner_text())

        retry_click(botao_next)
        delay_humano(0.4, 0.9)

        mudou_pagina = False
        for _ in range(20):
            marcador_novo = paginator.locator(".p-paginator-page.p-highlight").first
            if marcador_novo.count() == 0:
                mudou_pagina = True
                break
            pagina_nova = limpar_texto(marcador_novo.inner_text())
            if pagina_nova and pagina_nova != pagina_atual:
                mudou_pagina = True
                break
            time.sleep(0.15)

        if not mudou_pagina and pagina_atual:
            print("   Aviso: paginação não avançou, encerrando coleta dessa competência.")
            break

        pagina += 1

    if pagina > max_paginas:
        print(f"   Aviso: limite de {max_paginas} páginas atingido em {indicador} / {competencia}")

    return linhas


def salvar_dados_webscraping(dados, caminho):
    if not dados:
        return

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    df_saida = pd.DataFrame(dados)

    for campo in CAMPOS_SAIDA:
        if campo not in df_saida.columns:
            df_saida[campo] = ""
    df_saida = df_saida[CAMPOS_SAIDA]
    lock_path = f"{caminho}.lock"
    with open(lock_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            arquivo_existe = os.path.exists(caminho)
            df_saida.to_csv(
                caminho,
                mode="a",
                header=not arquivo_existe,
                index=False,
                encoding="utf-8-sig" if not arquivo_existe else "utf-8",
            )
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    print(f"Dados exportados em CSV: {caminho} (+{len(df_saida)} linhas)")


# ----------------------------
# Fluxo principal
# ----------------------------

def arquivo_worker(path_base, worker_id, worker_total):
    if worker_total <= 1:
        return path_base
    raiz, ext = os.path.splitext(path_base)
    return f"{raiz}.w{worker_id + 1}of{worker_total}{ext}"


def executar_fluxo(worker_id=0, worker_total=1):

    df = pd.read_csv("municipios.csv")

    municipios = df["nome_municipio"].tolist()
    municipios = [m for idx, m in enumerate(municipios) if idx % worker_total == worker_id]

    caminho_csv = os.path.join("downloads", "dados_webscraping.csv")
    caminho_processados = arquivo_worker("processados.txt", worker_id, worker_total)
    state_path = arquivo_worker(state_file, worker_id, worker_total)
    pares_processados = carregar_pares_processados_csv(caminho_csv)

    processados = carregar_processados(caminho_processados)
    municipios = [m for m in municipios if m not in processados]
    print(f"Worker {worker_id + 1}/{worker_total} | Municípios já processados: {len(processados)}")
    print(f"Worker {worker_id + 1}/{worker_total} | Municípios pendentes: {len(municipios)}")
    print(f"Worker {worker_id + 1}/{worker_total} | Pares MUNICIPIO+INDICADOR já no CSV: {len(pares_processados)}")


    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            slow_mo=80,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context_kwargs = {}
        if os.path.exists(state_path) and not force_login:
            context_kwargs["storage_state"] = state_path

        context = browser.new_context(**context_kwargs)

        page = context.new_page()

        page.set_default_timeout(60000)

        autenticar_se_necessario(page, context, state_path)

        navegar_sistema(page)

        for municipio in municipios:

            print(f"\nProcessando município: {municipio}")

            try:

                selecionar_municipio(page, municipio)

                navegar_indicadores(page, municipio, caminho_csv, pares_processados)

                salvar_processado(municipio, caminho_processados)

            except Exception as e:

                print(f"Erro no município {municipio}")

                raise

        browser.close()


# ----------------------------
# Auto restart
# ----------------------------

def executar_com_retry(worker_id=0, worker_total=1):
    tentativas = 5

    for tentativa in range(1, tentativas + 1):

        try:

            print(f"\nIniciando automação tentativa {tentativa} | Worker {worker_id + 1}/{worker_total}")

            executar_fluxo(worker_id=worker_id, worker_total=worker_total)

            print("Automação finalizada")

            return 0

        except Exception as e:

            print("Erro detectado")

            print("Reiniciando em 5 segundos")

            time.sleep(5)

    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-id", type=int, default=0)
    parser.add_argument("--worker-total", type=int, default=1)
    parser.add_argument("--parallel-workers", type=int, default=0)
    args = parser.parse_args()

    if args.parallel_workers > 1 and args.worker_total == 1:
        processos = []
        for wid in range(args.parallel_workers):
            cmd = [
                sys.executable,
                os.path.abspath(__file__),
                "--worker-id",
                str(wid),
                "--worker-total",
                str(args.parallel_workers),
            ]
            processos.append(subprocess.Popen(cmd))

        codigos = [p.wait() for p in processos]
        if any(codigo != 0 for codigo in codigos):
            raise SystemExit(1)
        raise SystemExit(0)

    if args.worker_total < 1 or args.worker_id < 0 or args.worker_id >= args.worker_total:
        raise SystemExit("Parâmetros de worker inválidos.")

    raise SystemExit(executar_com_retry(worker_id=args.worker_id, worker_total=args.worker_total))

if __name__ == "__main__":
    main()
