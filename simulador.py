"""
Simulador de Gerenciamento de Memória - TP2 de Sistemas Operacionais.

Uso (por argumentos):
    python3 simulador.py --modo 1 --memoria 32 --politica worst --arquivo testes/teste_particoes.txt
    python3 simulador.py --modo 2 --memoria 64 --arquivo testes/teste_buddy.txt --passo
    python3 simulador.py --modo 3 --memoria 64 --pagina 8 --arquivo testes/teste_paginacao.txt
Uso interativo (pergunta cada parâmetro):
    python3 simulador.py

==============================================================================
CLASSE Simulador - FLUXO (pseudocódigo) e classes que ela usa
==============================================================================
  main():
      parametros <- ler da linha de comando (ou perguntar ao usuário)
      valida parâmetros (memória e página potências de 2, etc.)
      memoria <- criar_memoria(parametros):
          modo 1 -> ParticoesVariaveis(memoria, politica)   [particoes.py]
          modo 2 -> Buddy(memoria)                          [buddy.py]
          modo 3 -> Paginacao(memoria, pagina)              [paginacao.py]
      Simulador(memoria).executar(arquivo, passo_a_passo)

  Simulador.executar(arquivo):
      para cada linha do arquivo:
          ignora linha vazia ou comentário (#)
          comando <- interpretar_linha(linha)          # IN / OUT / ACC ou erro
          se erro de sintaxe: mensagem de erro
          senão:  IN  -> memoria.entrar(id, tam)
                  OUT -> memoria.sair(id)
                  ACC -> memoria.acessar(id, endereco)
          imprime resultado + memoria.estado()
          atualiza estatísticas (admitidos, rejeitados, ocupação máx., fragmentação)
          se passo a passo: espera ENTER
      imprime resumo final

  Interface comum que as 3 classes de memória oferecem (duck typing):
      entrar(pid, tam) -> (sucesso, mensagem)
      sair(pid)        -> (sucesso, mensagem)
      acessar(pid, end)-> (sucesso, mensagem)
      estado()         -> lista de linhas de texto
      ocupado()        -> memória em uso
      fragmentacao()   -> modo 1: externa (livre - maior bloco); modos 2 e 3: interna total
==============================================================================
"""

import argparse  # leitura de argumentos da linha de comando
import re  # expressões regulares para interpretar os comandos
import sys  # acesso a sys.argv e sys.exit

from buddy import Buddy  # modo 2
from paginacao import Paginacao  # modo 3
from particoes import CIRCULAR_FIT, WORST_FIT, ParticoesVariaveis  # modo 1

ESPACO_INSUFICIENTE = "ESPAÇO INSUFICIENTE DE MEMÓRIA"  # mensagem usada para contar rejeições

# Comando: NOME ( ID [, NUMERO] ) com espaços opcionais; NOME em qualquer caixa.
PADRAO_COMANDO = re.compile(r"^\s*([A-Za-z]+)\s*\(\s*([^,()\s]+)\s*(?:,\s*([^,()\s]+)\s*)?\)\s*$")  # regex do comando


def eh_potencia_de_2(n):
    """
    Pseudocódigo:
        retorna n > 0 e n tem um único bit 1  (n AND (n-1) = 0)
    """
    return n > 0 and (n & (n - 1)) == 0  # potência de 2 tem apenas um bit ligado


def interpretar_linha(linha):
    """
    Pseudocódigo:
        casa a linha com o padrão NOME(ID[,NUM])
        se não casou: erro de sintaxe
        NOME em maiúsculas
        IN  : exige NUM inteiro > 0           -> ("IN", id, tam)
        OUT : não pode ter NUM                -> ("OUT", id, None)
        ACC : exige NUM inteiro               -> ("ACC", id, endereco)
        outro nome: erro "comando desconhecido"
        retorna (comando, id, numero, erro)
    """
    casou = PADRAO_COMANDO.match(linha)  # tenta reconhecer o formato do comando
    if not casou:  # formato não reconhecido?
        return None, None, None, "ERRO DE COMANDO: sintaxe inválida"  # linha malformada
    nome = casou.group(1).upper()  # nome do comando em maiúsculas
    pid = casou.group(2)  # ID do processo (aceita letras ou números)
    argumento = casou.group(3)  # segundo argumento (tamanho/endereço) ou None
    if nome == "OUT":  # comando OUT
        if argumento is not None:  # OUT não aceita segundo argumento
            return None, None, None, "ERRO DE COMANDO: OUT recebe apenas o ID"  # erro de sintaxe
        return nome, pid, None, None  # OUT válido
    if nome not in ("IN", "ACC"):  # nome desconhecido?
        return None, None, None, "ERRO DE COMANDO: comando desconhecido '%s'" % nome  # erro
    if argumento is None:  # IN e ACC precisam do segundo argumento
        return None, None, None, "ERRO DE COMANDO: %s precisa de dois argumentos" % nome  # erro
    try:  # tenta converter o argumento para inteiro
        numero = int(argumento)  # tamanho (IN) ou endereço (ACC)
    except ValueError:  # não era um número inteiro
        return None, None, None, "ERRO DE COMANDO: '%s' não é um número inteiro" % argumento  # erro
    if nome == "IN" and numero <= 0:  # tamanho de processo precisa ser positivo
        return None, None, None, "ERRO DE COMANDO: tamanho deve ser maior que zero"  # erro
    return nome, pid, numero, None  # IN ou ACC válidos (ACC negativo é tratado na memória)


class Simulador:
    """Lê o arquivo de requisições e conduz a simulação (ver fluxo no topo)."""

    def __init__(self, memoria):
        """
        Pseudocódigo:
            guarda o objeto de memória e zera as estatísticas
        """
        self.memoria = memoria  # ParticoesVariaveis, Buddy ou Paginacao
        self.admitidos = 0  # quantidade de IN bem-sucedidos
        self.rejeitados = 0  # quantidade de IN rejeitados por falta de espaço
        self.ocupacao_maxima = 0  # maior memória ocupada observada
        self.soma_fragmentacao = 0  # soma da fragmentação após cada linha
        self.linhas_processadas = 0  # quantidade de linhas de comando processadas

    def executar_comando(self, linha):
        """
        Pseudocódigo:
            (cmd, id, num, erro) <- interpretar_linha(linha)
            se erro: retorna mensagem de erro
            IN  -> memoria.entrar; conta admitido ou rejeitado por espaço
            OUT -> memoria.sair
            ACC -> memoria.acessar
            retorna mensagem
        """
        comando, pid, numero, erro = interpretar_linha(linha)  # interpreta o texto da linha
        if erro:  # houve erro de sintaxe?
            return erro  # devolve a mensagem de erro de comando
        if comando == "IN":  # criação de processo
            sucesso, mensagem = self.memoria.entrar(pid, numero)  # tenta alocar
            if sucesso:  # alocou?
                self.admitidos += 1  # conta processo admitido
            elif mensagem == ESPACO_INSUFICIENTE:  # rejeitado por falta de espaço?
                self.rejeitados += 1  # conta processo rejeitado
        elif comando == "OUT":  # término de processo
            sucesso, mensagem = self.memoria.sair(pid)  # tenta liberar
        else:  # comando ACC
            sucesso, mensagem = self.memoria.acessar(pid, numero)  # tenta traduzir o endereço
        if sucesso:  # para operações bem-sucedidas
            mensagem = "OK: %s %s" % (pid, mensagem)  # prefixa com OK e o ID
        return mensagem  # mensagem a ser exibida

    def atualizar_estatisticas(self):
        """
        Pseudocódigo:
            ocupacao_maxima <- max(ocupacao_maxima, memoria.ocupado())
            soma_fragmentacao += memoria.fragmentacao(); linhas += 1
        """
        self.ocupacao_maxima = max(self.ocupacao_maxima, self.memoria.ocupado())  # pico de ocupação
        self.soma_fragmentacao += self.memoria.fragmentacao()  # acumula para a média
        self.linhas_processadas += 1  # mais uma linha considerada na média

    def executar(self, caminho, passo_a_passo):
        """
        Pseudocódigo:
            para cada (numero, linha) do arquivo:
                se vazia ou começa com '#': pula
                mensagem <- executar_comando(linha)
                imprime linha, mensagem e estado da memória
                atualizar_estatisticas()
                se passo a passo: espera ENTER
            imprimir_resumo()
        """
        with open(caminho, encoding="utf-8", errors="replace") as arquivo:  # abre o arquivo; caracteres inválidos não derrubam o programa
            linhas = arquivo.readlines()  # lê todas as linhas
        for numero, linha in enumerate(linhas, start=1):  # percorre numerando a partir de 1
            texto = linha.strip()  # remove espaços e quebra de linha
            if not texto or texto.startswith("#"):  # linha vazia ou comentário?
                continue  # ignora
            mensagem = self.executar_comando(texto)  # executa o comando
            print("Linha %d: %s" % (numero, texto))  # mostra a linha lida
            print("  -> %s" % mensagem)  # mostra o resultado
            for info in self.memoria.estado():  # cada linha de estado da memória
                print("     %s" % info)  # mostra indentado
            print()  # linha em branco separando os passos
            self.atualizar_estatisticas()  # atualiza os números do resumo
            if passo_a_passo:  # modo passo a passo?
                try:  # input pode falhar se a entrada padrão acabar
                    input("[ENTER para continuar]")  # espera o usuário
                except EOFError:  # sem entrada disponível
                    passo_a_passo = False  # segue em modo contínuo
        self.imprimir_resumo()  # mostra o resumo final

    def imprimir_resumo(self):
        """
        Pseudocódigo:
            media <- soma_fragmentacao / linhas (0 se não houve linhas)
            imprime admitidos, rejeitados, ocupação máxima (valor e %), fragmentação média
        """
        total = self.memoria.tamanho_memoria  # tamanho da memória para o percentual
        media = self.soma_fragmentacao / self.linhas_processadas if self.linhas_processadas else 0  # evita divisão por zero
        tipo = "externa" if isinstance(self.memoria, ParticoesVariaveis) else "interna"  # tipo de fragmentação medida
        print("=" * 60)  # separador visual
        print("RESUMO FINAL")  # título
        print("Processos admitidos: %d" % self.admitidos)  # IN bem-sucedidos
        print("Processos rejeitados por falta de espaço: %d" % self.rejeitados)  # IN rejeitados
        print("Ocupação máxima da memória: %d de %d (%.1f%%)" % (self.ocupacao_maxima, total, 100.0 * self.ocupacao_maxima / total))  # pico
        print("Fragmentação %s média: %.2f" % (tipo, media))  # média por linha
        print("=" * 60)  # separador visual


def perguntar_parametros():
    """
    Pseudocódigo:
        pergunta modo, memória, política (modo 1), página (modo 3), arquivo e passo a passo
        retorna um objeto com esses campos
    """
    p = argparse.Namespace(politica=None, pagina=None)  # objeto com os mesmos campos do argparse
    p.modo = int(input("Modo (1=partições variáveis, 2=buddy, 3=paginação): "))  # modo de operação
    p.memoria = int(input("Tamanho da memória (potência de 2): "))  # tamanho da memória
    if p.modo == 1:  # política só existe no modo 1
        p.politica = input("Política (worst/circular): ").strip().lower()  # Worst-Fit ou Circular-Fit
    if p.modo == 3:  # tamanho de página só existe no modo 3
        p.pagina = int(input("Tamanho da página (potência de 2): "))  # tamanho da página
    p.arquivo = input("Arquivo de requisições: ").strip()  # caminho do arquivo
    p.passo = input("Passo a passo? (s/n): ").strip().lower().startswith("s")  # modo de execução
    return p  # devolve os parâmetros


def ler_parametros():
    """
    Pseudocódigo:
        se não há argumentos: retorna perguntar_parametros()
        senão: usa argparse para ler --modo, --memoria, --politica, --pagina, --arquivo, --passo
    """
    if len(sys.argv) == 1:  # nenhum argumento informado?
        return perguntar_parametros()  # modo interativo
    leitor = argparse.ArgumentParser(description="Simulador de gerenciamento de memória")  # cria o leitor
    leitor.add_argument("--modo", type=int, required=True, choices=[1, 2, 3], help="1=partições, 2=buddy, 3=paginação")  # modo
    leitor.add_argument("--memoria", type=int, required=True, help="tamanho da memória (potência de 2)")  # memória
    leitor.add_argument("--politica", help="modo 1: worst (wf) ou circular (cf)")  # política
    leitor.add_argument("--pagina", type=int, help="modo 3: tamanho da página (potência de 2)")  # página
    leitor.add_argument("--arquivo", required=True, help="arquivo de requisições")  # arquivo
    leitor.add_argument("--passo", action="store_true", help="execução passo a passo (ENTER a cada linha)")  # passo a passo
    return leitor.parse_args()  # lê e devolve os argumentos


def criar_memoria(p):
    """
    Pseudocódigo:
        valida memória (potência de 2)
        modo 1: valida política -> ParticoesVariaveis
        modo 2: Buddy
        modo 3: valida página (potência de 2 e <= memória) -> Paginacao
        se inválido: encerra com mensagem de erro
    """
    if not eh_potencia_de_2(p.memoria):  # memória precisa ser potência de 2 em qualquer modo
        sys.exit("ERRO: o tamanho da memória deve ser uma potência de 2")  # encerra
    if p.modo == 1:  # partições variáveis
        politica = (p.politica or "").lower()  # normaliza o texto da política
        if politica in ("worst", "wf", "worst-fit"):  # nomes aceitos para Worst-Fit
            return ParticoesVariaveis(p.memoria, WORST_FIT)  # cria memória Worst-Fit
        if politica in ("circular", "cf", "circular-fit"):  # nomes aceitos para Circular-Fit
            return ParticoesVariaveis(p.memoria, CIRCULAR_FIT)  # cria memória Circular-Fit
        sys.exit("ERRO: política inválida (use worst ou circular)")  # política desconhecida
    if p.modo == 2:  # buddy
        return Buddy(p.memoria)  # cria memória buddy
    if p.modo == 3:  # paginação
        if p.pagina is None or not eh_potencia_de_2(p.pagina) or p.pagina > p.memoria:  # página inválida?
            sys.exit("ERRO: o tamanho da página deve ser potência de 2 e <= memória")  # encerra
        return Paginacao(p.memoria, p.pagina)  # cria memória paginada
    sys.exit("ERRO: modo inválido (use 1, 2 ou 3)")  # modo fora de 1..3


def main():
    """
    Pseudocódigo:
        p <- ler_parametros()
        memoria <- criar_memoria(p)
        Simulador(memoria).executar(p.arquivo, p.passo)
    """
    try:  # captura entradas não numéricas no modo interativo
        p = ler_parametros()  # obtém os parâmetros
    except ValueError:  # int() recebeu texto inválido
        sys.exit("ERRO: valor numérico inválido")  # encerra
    except EOFError:  # a entrada acabou antes de responder todas as perguntas
        sys.exit("ERRO: entrada de parâmetros incompleta")  # encerra sem traceback
    memoria = criar_memoria(p)  # cria a memória do modo escolhido
    try:  # o arquivo pode não existir
        Simulador(memoria).executar(p.arquivo, p.passo)  # roda a simulação
    except OSError as erro:  # problema ao abrir/ler o arquivo
        sys.exit("ERRO: não foi possível ler o arquivo: %s" % erro)  # encerra


if __name__ == "__main__":  # só executa quando chamado diretamente (não ao importar)
    main()  # ponto de entrada do programa
