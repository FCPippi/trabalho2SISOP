"""
Testes automáticos com os exemplos do enunciado.

Executar:  python3 -m unittest test_simulador.py -v

==============================================================================
CLASSE TestesEnunciado - FLUXO (pseudocódigo)
==============================================================================
  para cada exemplo do PDF:
      cria a memória do modo correspondente (ParticoesVariaveis, Buddy, Paginacao)
      executa os comandos na ordem do enunciado
      compara blocos livres / fragmentação / frames com os valores do PDF
==============================================================================
"""

import unittest  # framework de testes da biblioteca padrão

from buddy import Buddy  # modo 2
from paginacao import Paginacao  # modo 3
from particoes import CIRCULAR_FIT, WORST_FIT, ParticoesVariaveis  # modo 1
from simulador import eh_potencia_de_2, interpretar_linha  # funções auxiliares


def tamanhos_livres(memoria):
    """
    Pseudocódigo:
        retorna lista com o tamanho de cada bloco livre, em ordem de endereço
    """
    return [bloco[1] for bloco in memoria.livres()]  # pega só o campo tamanho


def rodar_exemplo_modo1(politica):
    """
    Pseudocódigo:
        cria memória de 32 com a política; executa a sequência do PDF (seção 5)
        retorna (memória, lista de resultados dos IN de E, F, G)
    """
    m = ParticoesVariaveis(32, politica)  # memória do exemplo
    for pid, tam in [("A", 8), ("B", 4), ("C", 6), ("D", 5)]:  # alocações iniciais
        m.entrar(pid, tam)  # aloca cada processo
    m.sair("A")  # libera A
    m.sair("C")  # libera C
    resultados = [m.entrar(pid, tam)[0] for pid, tam in [("E", 3), ("F", 6), ("G", 7)]]  # sucesso de cada IN
    m.sair("B")  # libera B (gera a fusão final)
    return m, resultados  # devolve para os testes conferirem


class TestesEnunciado(unittest.TestCase):
    """Confere os exemplos do PDF e algumas regras gerais."""

    def test_worst_fit(self):
        """Pseudocódigo: roda o exemplo WF; espera G rejeitado e livres 12|6."""
        m, resultados = rodar_exemplo_modo1(WORST_FIT)  # executa o exemplo
        self.assertEqual(resultados, [True, True, False])  # G é rejeitado
        self.assertEqual(tamanhos_livres(m), [12, 6])  # estado final do PDF

    def test_circular_fit(self):
        """Pseudocódigo: roda o exemplo CF; espera todos admitidos e livre 11."""
        m, resultados = rodar_exemplo_modo1(CIRCULAR_FIT)  # executa o exemplo
        self.assertEqual(resultados, [True, True, True])  # todos entram
        self.assertEqual(tamanhos_livres(m), [11])  # estado final do PDF
        self.assertEqual(m.ponteiro, 7)  # ponteiro após alocar G em 0..6

    def test_buddy(self):
        """Pseudocódigo: roda o exemplo buddy; confere frag. interna após cada linha."""
        m = Buddy(64)  # memória do exemplo
        esperado = [3, 10, 22, 24, 24]  # fragmentação após A, B, C, D, E
        for (pid, tam), frag in zip([("A", 5), ("B", 9), ("C", 20), ("D", 6), ("E", 3)], esperado):  # cada IN
            m.entrar(pid, tam)  # executa o IN
            self.assertEqual(m.fragmentacao(), frag)  # confere com a tabela do PDF
        self.assertNotIn("E", m.alocados)  # E foi rejeitado
        for pid, frag in [("A", 21), ("D", 19), ("B", 12), ("C", 0)]:  # cada OUT
            m.sair(pid)  # executa o OUT
            self.assertEqual(m.fragmentacao(), frag)  # confere fragmentação
        self.assertEqual(m.livres, [(0, 64)])  # tudo coalescido em um bloco

    def test_paginacao(self):
        """Pseudocódigo: roda o exemplo de paginação; confere frames, ACC e frag."""
        m = Paginacao(64, 8)  # memória do exemplo
        self.assertTrue(m.entrar("A", 20)[0])  # A admitido
        self.assertTrue(m.entrar("B", 9)[0])  # B admitido
        self.assertEqual(m.entrar("C", 30)[1], "ESPAÇO INSUFICIENTE DE MEMÓRIA")  # C rejeitado
        self.assertTrue(m.entrar("D", 16)[0])  # D admitido
        self.assertIn("endereço físico 32", m.acessar("B", 8)[1])  # tradução do PDF
        self.assertEqual(m.acessar("A", 22)[1], "ERRO: ENDEREÇO INVÁLIDO")  # fora do processo
        m.sair("A")  # libera A
        self.assertEqual(m.fragmentacao(), 7)  # frag. após OUT(A)
        self.assertTrue(m.entrar("C", 30)[0])  # agora C cabe
        self.assertEqual(m.processos["C"]["tabela"], [0, 1, 2, 7])  # frames não contíguos
        self.assertEqual(m.fragmentacao(), 9)  # frag. final do PDF

    def test_erros_gerais(self):
        """Pseudocódigo: confere ordem de checagem dos erros e o parser."""
        m = Paginacao(64, 8)  # memória qualquer
        self.assertEqual(m.acessar("X", -1)[1], "ERRO: PROCESSO NÃO ENCONTRADO")  # processo antes do endereço
        self.assertEqual(m.sair("X")[1], "ERRO: PROCESSO NÃO ENCONTRADO")  # OUT de inexistente
        m.entrar("A", 8)  # cria A
        self.assertEqual(m.entrar("A", 8)[1], "ERRO: PROCESSO JÁ EXISTE")  # duplicado
        self.assertEqual(interpretar_linha("in( a ,  8 )")[:3], ("IN", "a", 8))  # espaços e minúsculas
        self.assertIsNotNone(interpretar_linha("IN(A)")[3])  # falta argumento
        self.assertIsNotNone(interpretar_linha("IN(A, 0)")[3])  # tamanho zero
        self.assertTrue(eh_potencia_de_2(64))  # 64 é potência de 2
        self.assertFalse(eh_potencia_de_2(48))  # 48 não é


if __name__ == "__main__":  # permite rodar com "python3 test_simulador.py"
    unittest.main()  # executa todos os testes
