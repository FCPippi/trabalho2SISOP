"""
Modo 1 - Partições variáveis (Worst-Fit e Circular-Fit).

==============================================================================
CLASSE ParticoesVariaveis - FLUXO (pseudocódigo)
==============================================================================
  Estrutura: lista "blocos" ordenada por endereço que cobre TODA a memória.
             Cada bloco = [inicio, tamanho, dono]; dono = None => bloco livre.

  criar(tamanho_memoria, politica):
      blocos <- [ [0, tamanho_memoria, livre] ]      # memória toda livre
      ponteiro <- 0                                   # usado só no Circular-Fit

  entrar(pid, tam):                                   # comando IN
      se pid já está em algum bloco -> "ERRO: PROCESSO JÁ EXISTE"
      se politica = WORST  -> bloco <- maior bloco livre que caiba (empate: menor endereço)
      se politica = CIRCULAR -> bloco <- 1º livre que caiba começando no ponteiro (com volta)
      se não achou -> "ESPAÇO INSUFICIENTE DE MEMÓRIA"
      parte o bloco: [inicio, tam, pid] + [inicio+tam, sobra, livre] (se sobra > 0)
      se CIRCULAR: ponteiro <- inicio + tam (volta a 0 se = tamanho da memória)

  sair(pid):                                          # comando OUT
      se pid não existe -> "ERRO: PROCESSO NÃO ENCONTRADO"
      marca o bloco como livre e funde com vizinhos livres (esquerda e direita)

  acessar(pid, endereco):                             # comando ACC
      ignorado neste modo (apenas aviso)

  estado(): imprime blocos livres + total, mapa, maior bloco livre, total livre

  Classes usadas: nenhuma outra classe do projeto; é usada por simulador.py
  (Simulador), que chama entrar/sair/acessar/estado/ocupado/fragmentacao.
==============================================================================
"""

WORST_FIT = "worst"  # constante que identifica a política Worst-Fit
CIRCULAR_FIT = "circular"  # constante que identifica a política Circular-Fit

INICIO = 0  # índice do campo "início" dentro de um bloco
TAMANHO = 1  # índice do campo "tamanho" dentro de um bloco
DONO = 2  # índice do campo "dono" (ID do processo ou None) dentro de um bloco


class ParticoesVariaveis:
    """Simula memória com partições variáveis (ver fluxo no topo do arquivo)."""

    def __init__(self, tamanho_memoria, politica):
        """
        Pseudocódigo:
            guarda tamanho e política
            blocos <- [ [0, tamanho_memoria, livre] ]
            ponteiro <- 0
        """
        self.tamanho_memoria = tamanho_memoria  # tamanho total da memória simulada
        self.politica = politica  # WORST_FIT ou CIRCULAR_FIT
        self.blocos = [[0, tamanho_memoria, None]]  # começa com um único bloco livre
        self.ponteiro = 0  # posição do ponteiro do Circular-Fit (começa em 0)

    # ------------------------------------------------------------------ busca
    def _indice_do_processo(self, pid):
        """
        Pseudocódigo:
            para cada bloco i em blocos:
                se dono de i = pid: retorna i
            retorna -1
        """
        for i, bloco in enumerate(self.blocos):  # percorre os blocos com seu índice
            if bloco[DONO] == pid:  # achou o bloco desse processo?
                return i  # devolve a posição do bloco na lista
        return -1  # processo não está na memória

    def _escolher_worst_fit(self, tam):
        """
        Pseudocódigo:
            melhor <- nenhum
            para cada bloco livre com tamanho >= tam (em ordem de endereço):
                se melhor = nenhum ou tamanho > tamanho de melhor: melhor <- bloco
            retorna índice de melhor (ou -1)
            (usar ">" e não ">=" garante que no empate fica o de menor endereço)
        """
        escolhido = -1  # índice do bloco escolhido (-1 = nenhum ainda)
        for i, bloco in enumerate(self.blocos):  # percorre em ordem crescente de endereço
            if bloco[DONO] is not None or bloco[TAMANHO] < tam:  # ocupado ou pequeno demais?
                continue  # pula para o próximo bloco
            if escolhido == -1 or bloco[TAMANHO] > self.blocos[escolhido][TAMANHO]:  # maior estritamente
                escolhido = i  # passa a ser o melhor candidato
        return escolhido  # índice do maior bloco que serve, ou -1

    def _escolher_circular_fit(self, tam):
        """
        Pseudocódigo:
            livres <- índices dos blocos livres (ordem crescente de endereço)
            ordem <- [livres com inicio >= ponteiro] + [livres com inicio < ponteiro]
            para cada i em ordem:
                se tamanho de i >= tam: retorna i
            retorna -1
        """
        livres = [i for i, b in enumerate(self.blocos) if b[DONO] is None]  # índices dos blocos livres
        depois = [i for i in livres if self.blocos[i][INICIO] >= self.ponteiro]  # a partir do ponteiro
        antes = [i for i in livres if self.blocos[i][INICIO] < self.ponteiro]  # os que ficam para a volta
        for i in depois + antes:  # busca circular: primeiro depois, depois dá a volta
            if self.blocos[i][TAMANHO] >= tam:  # o bloco comporta o processo?
                return i  # primeiro que serve é o escolhido
        return -1  # nenhum bloco livre comporta o processo

    # --------------------------------------------------------------- comandos
    def entrar(self, pid, tam):
        """
        Pseudocódigo:
            se pid existe: retorna erro "já existe"
            i <- escolher bloco conforme a política
            se i = -1: retorna (falha, "ESPAÇO INSUFICIENTE DE MEMÓRIA")
            inicio, tamanho_livre <- bloco i
            bloco i <- [inicio, tam, pid]
            se sobra = tamanho_livre - tam > 0: insere [inicio+tam, sobra, livre] após i
            se CIRCULAR: ponteiro <- (inicio + tam), e 0 se chegou ao fim da memória
            retorna (sucesso, mensagem com a faixa alocada)
        """
        if self._indice_do_processo(pid) != -1:  # processo com esse ID já está na memória?
            return False, "ERRO: PROCESSO JÁ EXISTE"  # não admite duplicado
        if self.politica == WORST_FIT:  # política Worst-Fit?
            i = self._escolher_worst_fit(tam)  # escolhe o maior bloco livre que serve
        else:  # senão é Circular-Fit
            i = self._escolher_circular_fit(tam)  # escolhe a partir do ponteiro
        if i == -1:  # nenhum bloco serviu?
            return False, "ESPAÇO INSUFICIENTE DE MEMÓRIA"  # processo rejeitado
        inicio, tamanho_livre, _ = self.blocos[i]  # lê início e tamanho do bloco livre escolhido
        sobra = tamanho_livre - tam  # quanto do bloco continua livre
        self.blocos[i] = [inicio, tam, pid]  # bloco passa a ser a partição do processo
        if sobra > 0:  # sobrou espaço?
            self.blocos.insert(i + 1, [inicio + tam, sobra, None])  # a sobra vira um bloco livre logo depois
        if self.politica == CIRCULAR_FIT:  # só o Circular-Fit usa ponteiro
            self.ponteiro = inicio + tam  # ponteiro vai para o fim da partição alocada
            if self.ponteiro == self.tamanho_memoria:  # chegou exatamente ao fim da memória?
                self.ponteiro = 0  # volta para o início
        return True, "alocado em [%d..%d]" % (inicio, inicio + tam - 1)  # sucesso com a faixa ocupada

    def sair(self, pid):
        """
        Pseudocódigo:
            i <- índice do bloco de pid; se não existe: erro "não encontrado"
            marca bloco i como livre
            se bloco à direita (i+1) é livre: soma tamanho e remove o da direita
            se bloco à esquerda (i-1) é livre: soma tamanho de i nele e remove i
            (a memória NÃO é circular: o último bloco nunca funde com o primeiro)
        """
        i = self._indice_do_processo(pid)  # procura a partição do processo
        if i == -1:  # não achou?
            return False, "ERRO: PROCESSO NÃO ENCONTRADO"  # erro de OUT
        inicio, tam, _ = self.blocos[i]  # guarda a faixa para a mensagem
        self.blocos[i][DONO] = None  # libera a partição
        if i + 1 < len(self.blocos) and self.blocos[i + 1][DONO] is None:  # vizinho da direita existe e está livre?
            self.blocos[i][TAMANHO] += self.blocos[i + 1][TAMANHO]  # absorve o tamanho do vizinho direito
            del self.blocos[i + 1]  # remove o vizinho que foi absorvido
        if i - 1 >= 0 and self.blocos[i - 1][DONO] is None:  # vizinho da esquerda existe e está livre?
            self.blocos[i - 1][TAMANHO] += self.blocos[i][TAMANHO]  # o da esquerda absorve o bloco atual
            del self.blocos[i]  # remove o bloco atual que foi absorvido
        return True, "liberado [%d..%d]" % (inicio, inicio + tam - 1)  # sucesso com a faixa liberada

    def acessar(self, pid, endereco):
        """
        Pseudocódigo:
            retorna aviso: ACC não se aplica ao modo 1
        """
        return False, "AVISO: ACC ignorado no modo 1 (partições variáveis)"  # comando ignorado

    # ------------------------------------------------------------ informações
    def livres(self):
        """
        Pseudocódigo:
            retorna lista de blocos cujo dono é livre
        """
        return [b for b in self.blocos if b[DONO] is None]  # filtra só os blocos livres

    def total_livre(self):
        """
        Pseudocódigo:
            retorna soma dos tamanhos dos blocos livres
        """
        return sum(b[TAMANHO] for b in self.livres())  # soma tamanhos livres

    def maior_livre(self):
        """
        Pseudocódigo:
            retorna maior tamanho entre os blocos livres (0 se não houver)
        """
        return max([b[TAMANHO] for b in self.livres()], default=0)  # maior bloco livre ou 0

    def ocupado(self):
        """
        Pseudocódigo:
            retorna tamanho da memória - total livre
        """
        return self.tamanho_memoria - self.total_livre()  # memória em uso pelos processos

    def fragmentacao(self):
        """
        Pseudocódigo:
            fragmentação externa <- total livre - maior bloco livre
            (memória livre que não pode ser usada por um único pedido contíguo)
        """
        return self.total_livre() - self.maior_livre()  # fragmentação externa

    def estado(self):
        """
        Pseudocódigo:
            linha 1: blocos livres "inicio..fim(tam)" separados por " | " e o total
            linha 2: mapa com todos os blocos (processo ou "livre")
            linha 3: maior bloco livre e total livre
            retorna as linhas
        """
        livres = ["[%d..%d](%d)" % (b[INICIO], b[INICIO] + b[TAMANHO] - 1, b[TAMANHO]) for b in self.livres()]  # texto de cada bloco livre
        mapa = ["[%d..%d %s]" % (b[INICIO], b[INICIO] + b[TAMANHO] - 1, b[DONO] or "livre") for b in self.blocos]  # texto de cada bloco do mapa
        linhas = []  # linhas de saída
        linhas.append("Blocos livres: %s  (total de blocos: %d)" % (" | ".join(livres) or "nenhum", len(livres)))  # lista de livres
        linhas.append("Mapa: %s" % " ".join(mapa))  # mapa da memória
        linhas.append("Maior bloco livre: %d | Total livre: %d" % (self.maior_livre(), self.total_livre()))  # resumo
        if self.politica == CIRCULAR_FIT:  # no Circular-Fit vale mostrar o ponteiro
            linhas.append("Ponteiro (Circular-Fit): %d" % self.ponteiro)  # posição atual do ponteiro
        return linhas  # devolve as linhas para o simulador imprimir
