from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv
import pandas as pd
import os
import time
import random
import re

load_dotenv()

gov_user = os.getenv("EGESTOR_CPF")
gov_password = os.getenv("EGESTOR_SENHA")

INDICADORES = [
    "Mais Acesso",
    "Desenvolvimento Infantil",
    "Gestação e Puerpério",
    "Diabetes",
    "Hipertensão",
    "Pessoa Idosa",
    "Prevenção do Câncer"
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

def salvar_progresso(municipio):

    with open("progresso.txt", "w", encoding="utf-8") as f:
        f.write(municipio)


def carregar_progresso():

    if os.path.exists("progresso.txt"):

        with open("progresso.txt", "r", encoding="utf-8") as f:
            return f.read().strip()

    return None


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

def navegar_indicadores(page):

    for indicador in INDICADORES:

        print(f"   Acessando indicador: {indicador}")

        try:

            link = page.get_by_role("link", name=indicador)

            retry_click(link)

            delay_humano(3,5)

        except Exception as e:

            print(f"Erro no indicador {indicador}: {e}")


# ----------------------------
# Fluxo principal
# ----------------------------

def executar_fluxo():

    df = pd.read_csv("municipios.csv")

    municipios = df["nome_municipio"].tolist()

    ultimo = carregar_progresso()

    if ultimo:

        print(f"Retomando de {ultimo}")

        idx = municipios.index(ultimo)

        municipios = municipios[idx:]


    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            slow_mo=80,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context()

        page = context.new_page()

        page.set_default_timeout(60000)

        login(page)

        navegar_sistema(page)

        for municipio in municipios:

            print(f"\nProcessando município: {municipio}")

            try:

                selecionar_municipio(page, municipio)

                navegar_indicadores(page)

                salvar_progresso(municipio)

            except Exception as e:

                print(f"Erro no município {municipio}")

                raise

        browser.close()


# ----------------------------
# Auto restart
# ----------------------------

def main():

    tentativas = 5

    for tentativa in range(1, tentativas + 1):

        try:

            print(f"\nIniciando automação tentativa {tentativa}")

            executar_fluxo()

            print("Automação finalizada")

            break

        except Exception as e:

            print("Erro detectado")

            print("Reiniciando em 5 segundos")

            time.sleep(5)


if __name__ == "__main__":
    main()