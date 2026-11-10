"""
Modo 2 - Sistema Buddy.

==============================================================================
CLASSE Buddy - FLUXO (pseudocódigo)
==============================================================================
  Estruturas:
      livres    : lista de blocos livres (endereco, tamanho)
      alocados  : dicionário pid -> (endereco, tamanho_bloco, tamanho_pedido)

  criar(tamanho_memoria):                     # tamanho é potência de 2
      livres <- [ (0, tamanho_memoria) ]

  entrar(pid, tam):                           # comando IN
      se pid já alocado -> "ERRO: PROCESSO JÁ EXISTE"
      k <- menor potência de 2 >= tam
      bloco <- menor bloco livre com tamanho >= k (empate: menor endereço)
      se não há -> "ESPAÇO INSUFICIENTE DE MEMÓRIA"
      enquanto tamanho do bloco > k:
          divide ao meio; metade DIREITA vira livre; continua com a ESQUERDA
      aloca o bloco para pid; frag. interna do processo = k - tam

  sair(pid):                                  # comando OUT
      se pid não existe -> "ERRO: PROCESSO NÃO ENCONTRADO"
      bloco <- bloco de pid
      repete: buddy <- endereco XOR tamanho
              se buddy livre e de mesmo tamanho: junta (endereço = menor, tamanho x2)
              senão: para
      insere bloco resultante em livres

  acessar(): ignorado neste modo (apenas aviso)
  estado(): blocos livres + total, mapa e fragmentação interna total

  Classes usadas: nenhuma outra do projeto; é usada por simulador.py (Simulador).
==============================================================================
"""


def proxima_potencia_de_2(n):
    """
    Pseudocódigo:
        p <- 1
        enquanto p < n: p <- p * 2
        retorna p
    """
    p = 1  # começa na menor potência de 2
    while p < n:  # enquanto ainda não comporta n
        p *= 2  # dobra
    return p  # menor potência de 2 >= n


class Buddy:
    """Simula memória com o sistema buddy (ver fluxo no topo do arquivo)."""

    def __init__(self, tamanho_memoria):
        """
        Pseudocódigo:
            livres <- [(0, tamanho_memoria)]; alocados <- vazio
        """
        self.tamanho_memoria = tamanho_memoria  # tamanho total (potência de 2)
        self.livres = [(0, tamanho_memoria)]  # no início há um único bloco livre
        self.alocados = {}  # pid -> (endereco, tamanho_do_bloco, tamanho_pedido)

    def entrar(self, pid, tam):
        """
        Pseudocódigo:
            se pid em alocados: erro "já existe"
            k <- próxima potência de 2 de tam
            candidatos <- livres com tamanho >= k
            se vazio: "ESPAÇO INSUFICIENTE DE MEMÓRIA"
            (end, t) <- candidato de menor tamanho; empate: menor endereço
            remove (end, t) de livres
            enquanto t > k:
                t <- t / 2
                adiciona (end + t, t) em livres   # metade direita fica livre
            alocados[pid] <- (end, k, tam)
        """
        if pid in self.alocados:  # já existe processo com esse ID?
            return False, "ERRO: PROCESSO JÁ EXISTE"  # rejeita duplicado
        k = proxima_potencia_de_2(tam)  # tamanho do bloco necessário
        candidatos = [b for b in self.livres if b[1] >= k]  # blocos livres que comportam k
        if not candidatos:  # nenhum bloco serve?
            return False, "ESPAÇO INSUFICIENTE DE MEMÓRIA"  # processo rejeitado
        endereco, t = min(candidatos, key=lambda b: (b[1], b[0]))  # menor tamanho; empate pelo menor endereço
        self.livres.remove((endereco, t))  # o bloco escolhido deixa de estar livre
        while t > k:  # bloco ainda é maior que o necessário?
            t //= 2  # divide ao meio
            self.livres.append((endereco + t, t))  # a metade direita (buddy) fica livre
        self.alocados[pid] = (endereco, k, tam)  # a metade esquerda é do processo
        return True, "bloco de %d em [%d..%d], frag. interna %d" % (k, endereco, endereco + k - 1, k - tam)  # sucesso

    def sair(self, pid):
        """
        Pseudocódigo:
            se pid não está em alocados: erro "não encontrado"
            (end, t) <- bloco de pid; remove pid
            repete:
                buddy <- end XOR t
                se t < tamanho_memoria e (buddy, t) está livre:
                    remove buddy de livres; end <- min(end, buddy); t <- 2t
                senão: sai do laço
            adiciona (end, t) em livres
        """
        if pid not in self.alocados:  # processo não está na memória?
            return False, "ERRO: PROCESSO NÃO ENCONTRADO"  # erro de OUT
        endereco, t, _ = self.alocados.pop(pid)  # retira o processo e pega seu bloco
        while t < self.tamanho_memoria:  # o bloco inteiro da memória não tem buddy
            buddy = endereco ^ t  # endereço do buddy: inverte o bit correspondente ao tamanho
            if (buddy, t) not in self.livres:  # buddy não está livre (ou foi dividido)?
                break  # não dá para juntar; para a coalescência
            self.livres.remove((buddy, t))  # o buddy deixa de ser um bloco separado
            endereco = min(endereco, buddy)  # o bloco unido começa no menor dos dois endereços
            t *= 2  # o bloco unido tem o dobro do tamanho
        self.livres.append((endereco, t))  # insere o bloco final (já coalescido) como livre
        return True, "liberado; bloco livre resultante [%d..%d](%d)" % (endereco, endereco + t - 1, t)  # sucesso

    def acessar(self, pid, endereco):
        """
        Pseudocódigo:
            retorna aviso: ACC não se aplica ao modo 2
        """
        return False, "AVISO: ACC ignorado no modo 2 (buddy)"  # comando ignorado

    def ocupado(self):
        """
        Pseudocódigo:
            retorna soma dos tamanhos dos blocos alocados (inclui frag. interna)
        """
        return sum(t for _, t, _ in self.alocados.values())  # memória em blocos alocados

    def fragmentacao(self):
        """
        Pseudocódigo:
            retorna soma de (tamanho do bloco - tamanho pedido) dos processos
        """
        return sum(t - pedido for _, t, pedido in self.alocados.values())  # fragmentação interna total

    def estado(self):
        """
        Pseudocódigo:
            ordena livres por endereço e monta texto "[ini..fim](tam)"
            mapa <- livres + alocados, ordenados por endereço
            retorna linhas: livres + total, mapa, fragmentação interna total
        """
        livres = sorted(self.livres)  # blocos livres em ordem de endereço
        texto_livres = ["[%d..%d](%d)" % (e, e + t - 1, t) for e, t in livres]  # texto de cada livre
        blocos = [(e, t, "livre") for e, t in livres]  # blocos livres do mapa
        for pid, (e, t, pedido) in self.alocados.items():  # cada processo alocado
            blocos.append((e, t, "%s:%d/%d" % (pid, pedido, t)))  # rótulo "ID:pedido/bloco"
        blocos.sort()  # ordena o mapa por endereço
        mapa = ["[%d..%d %s]" % (e, e + t - 1, rotulo) for e, t, rotulo in blocos]  # texto de cada bloco do mapa
        linhas = []  # linhas de saída
        linhas.append("Blocos livres: %s  (total de blocos: %d, total livre: %d)" % (" | ".join(texto_livres) or "nenhum", len(livres), sum(t for _, t in livres)))  # livres
        linhas.append("Mapa: %s" % " ".join(mapa))  # mapa da memória
        linhas.append("Fragmentação interna total: %d" % self.fragmentacao())  # fragmentação interna
        return linhas  # devolve para o simulador imprimir
