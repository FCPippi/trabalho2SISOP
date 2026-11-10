"""
Modo 3 - Paginação simples.

==============================================================================
CLASSE Paginacao - FLUXO (pseudocódigo)
==============================================================================
  Estruturas:
      frames    : lista com num_frames posições; cada uma = None (livre)
                  ou (pid, página)
      processos : dicionário pid -> {"tam": tamanho, "tabela": [frame da pág 0, 1, ...]}

  criar(tamanho_memoria, tamanho_pagina):
      num_frames <- tamanho_memoria / tamanho_pagina
      frames <- todos livres

  entrar(pid, tam):                         # comando IN
      se pid existe -> "ERRO: PROCESSO JÁ EXISTE"
      n <- teto(tam / tamanho_pagina)
      livres <- índices dos frames livres (ordem crescente)
      se |livres| < n -> "ESPAÇO INSUFICIENTE DE MEMÓRIA"
      página i vai para livres[i]  (frames NÃO precisam ser contíguos)
      frag. interna do processo = n * tamanho_pagina - tam

  sair(pid):                                # comando OUT
      se pid não existe -> "ERRO: PROCESSO NÃO ENCONTRADO"
      libera todos os frames da tabela de pid

  acessar(pid, endereco):                   # comando ACC
      se pid não existe -> "ERRO: PROCESSO NÃO ENCONTRADO"
      se endereco < 0 ou endereco >= tam -> "ERRO: ENDEREÇO INVÁLIDO"
      página <- endereco div tamanho_pagina; desloc <- endereco mod tamanho_pagina
      físico <- tabela[página] * tamanho_pagina + desloc

  estado(): frames livres + total, mapa, tabela de páginas do processo
            envolvido no comando e fragmentação interna total

  Classes usadas: nenhuma outra do projeto; é usada por simulador.py (Simulador).
==============================================================================
"""


class Paginacao:
    """Simula memória com paginação simples (ver fluxo no topo do arquivo)."""

    def __init__(self, tamanho_memoria, tamanho_pagina):
        """
        Pseudocódigo:
            num_frames <- tamanho_memoria / tamanho_pagina
            frames <- [livre] * num_frames; processos <- vazio
        """
        self.tamanho_memoria = tamanho_memoria  # tamanho total da memória
        self.tamanho_pagina = tamanho_pagina  # tamanho de página = tamanho de frame
        self.num_frames = tamanho_memoria // tamanho_pagina  # quantidade de frames físicos
        self.frames = [None] * self.num_frames  # None = frame livre; senão (pid, página)
        self.processos = {}  # pid -> {"tam": tamanho, "tabela": lista de frames}
        self.ultimo_pid = None  # processo envolvido no último comando (para mostrar a tabela)

    def entrar(self, pid, tam):
        """
        Pseudocódigo:
            ultimo_pid <- pid
            se pid existe: erro "já existe"
            n <- teto(tam / tamanho_pagina)
            livres <- frames livres em ordem crescente
            se |livres| < n: "ESPAÇO INSUFICIENTE DE MEMÓRIA"
            tabela <- primeiros n frames livres
            para cada página i: frames[tabela[i]] <- (pid, i)
            processos[pid] <- {tam, tabela}
        """
        self.ultimo_pid = pid  # este é o processo envolvido no comando
        if pid in self.processos:  # ID já está na memória?
            return False, "ERRO: PROCESSO JÁ EXISTE"  # rejeita duplicado
        n = (tam + self.tamanho_pagina - 1) // self.tamanho_pagina  # teto(tam / página) só com inteiros
        livres = [f for f in range(self.num_frames) if self.frames[f] is None]  # frames livres, menor índice primeiro
        if len(livres) < n:  # não há frames livres suficientes?
            return False, "ESPAÇO INSUFICIENTE DE MEMÓRIA"  # processo rejeitado
        tabela = livres[:n]  # usa os n frames livres de menor índice
        for pagina, frame in enumerate(tabela):  # para cada página do processo
            self.frames[frame] = (pid, pagina)  # o frame passa a guardar essa página
        self.processos[pid] = {"tam": tam, "tabela": tabela}  # registra o processo e sua tabela de páginas
        frag = n * self.tamanho_pagina - tam  # sobra na última página
        return True, "%d página(s) nos frames %s, frag. interna %d" % (n, tabela, frag)  # sucesso

    def sair(self, pid):
        """
        Pseudocódigo:
            ultimo_pid <- pid
            se pid não existe: erro "não encontrado"
            para cada frame da tabela de pid: frames[frame] <- livre
            remove pid de processos
        """
        self.ultimo_pid = pid  # processo envolvido no comando
        if pid not in self.processos:  # processo não existe?
            return False, "ERRO: PROCESSO NÃO ENCONTRADO"  # erro de OUT
        tabela = self.processos.pop(pid)["tabela"]  # remove o processo e pega seus frames
        for frame in tabela:  # percorre os frames que ele usava
            self.frames[frame] = None  # libera o frame
        return True, "frames liberados %s" % tabela  # sucesso

    def acessar(self, pid, endereco):
        """
        Pseudocódigo:
            ultimo_pid <- pid
            se pid não existe: erro "não encontrado"        (checado primeiro)
            se endereco < 0 ou endereco >= tam: erro "endereço inválido"
            pagina <- endereco div tamanho_pagina
            desloc <- endereco mod tamanho_pagina
            frame <- tabela[pagina]
            fisico <- frame * tamanho_pagina + desloc
        """
        self.ultimo_pid = pid  # processo envolvido no comando
        if pid not in self.processos:  # processo não existe?
            return False, "ERRO: PROCESSO NÃO ENCONTRADO"  # erro de ACC (vem antes do endereço)
        processo = self.processos[pid]  # dados do processo
        if endereco < 0 or endereco >= processo["tam"]:  # endereço fora do espaço lógico?
            return False, "ERRO: ENDEREÇO INVÁLIDO"  # erro de ACC
        pagina = endereco // self.tamanho_pagina  # número da página lógica
        desloc = endereco % self.tamanho_pagina  # deslocamento dentro da página
        frame = processo["tabela"][pagina]  # frame físico onde está a página
        fisico = frame * self.tamanho_pagina + desloc  # endereço físico final
        return True, "página %d, deslocamento %d, frame %d -> endereço físico %d" % (pagina, desloc, frame, fisico)  # sucesso

    def ocupado(self):
        """
        Pseudocódigo:
            retorna (número de frames ocupados) * tamanho_pagina
        """
        usados = sum(1 for f in self.frames if f is not None)  # conta frames ocupados
        return usados * self.tamanho_pagina  # converte para unidades de memória

    def fragmentacao(self):
        """
        Pseudocódigo:
            para cada processo: soma (páginas * tamanho_pagina - tam)
        """
        return sum(len(p["tabela"]) * self.tamanho_pagina - p["tam"] for p in self.processos.values())  # frag. interna total

    def estado(self):
        """
        Pseudocódigo:
            linha 1: frames livres e total
            linha 2: mapa "frame:pid/página" ou "frame:livre"
            linha 3: tabela de páginas do processo envolvido (se ele existir)
            linha 4: fragmentação interna total
        """
        livres = [f for f in range(self.num_frames) if self.frames[f] is None]  # índices dos frames livres
        mapa = []  # textos do mapa
        for f, conteudo in enumerate(self.frames):  # percorre todos os frames
            if conteudo is None:  # frame livre?
                mapa.append("[%d: livre]" % f)  # mostra como livre
            else:  # frame ocupado
                mapa.append("[%d: %s/p%d]" % (f, conteudo[0], conteudo[1]))  # mostra processo e página
        linhas = []  # linhas de saída
        linhas.append("Frames livres: %s  (total: %d)" % (", ".join(str(f) for f in livres) or "nenhum", len(livres)))  # livres
        linhas.append("Mapa: %s" % " ".join(mapa))  # mapa dos frames
        if self.ultimo_pid in self.processos:  # o processo envolvido ainda está na memória?
            tabela = self.processos[self.ultimo_pid]["tabela"]  # sua tabela de páginas
            pares = ["p%d->f%d" % (p, f) for p, f in enumerate(tabela)]  # pares página -> frame
            linhas.append("Tabela de páginas de %s: %s" % (self.ultimo_pid, " ".join(pares)))  # mostra a tabela
        else:  # processo não está (foi removido, rejeitado ou nunca existiu)
            linhas.append("Tabela de páginas de %s: (processo não está na memória)" % self.ultimo_pid)  # avisa
        linhas.append("Fragmentação interna total: %d" % self.fragmentacao())  # fragmentação interna
        return linhas  # devolve para o simulador imprimir
