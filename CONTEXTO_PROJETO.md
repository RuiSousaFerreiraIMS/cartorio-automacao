# Contexto do Projeto: Automação do Cartório (Peça A + Peça B)

> Documento de arranque. Cola isto nas instruções do Project (ou carrega como ficheiro)
> para que qualquer conversa continue exatamente de onde paramos, sem regressões.

## 1. O que é o projeto

Automatizar o registo de escrituras no **SIMN** (Sistema de Informação e do Movimento
Notarial) no Cartório do Notário Rui Ferreira, em Alcobaça.

Hoje: depois de a escritura estar redigida (Word), uma funcionária lê o documento e
insere manualmente os dados nos campos do SIMN. ~150 atos/mês. Cada registo demora
5 min (best case), tempo médio real provavelmente 8-12 min com casos complicados.

Objetivo: ler a escritura .docx, extrair os campos, validar com humano, e ter um robô
a preencher o SIMN. O notário quer algo **prático, não perfeito**. Validação humana
é obrigatória em todas as fases.

## 2. Arquitetura (decidida)

Duas peças desacopladas, ligadas por um ficheiro JSON. NUNCA entrelaçar.

```
[Escritura .docx]
      v
[PEÇA A - Interface mediadora (Streamlit, local)]
  - extrai campos (template parsing + Claude API onde varia)
  - valida com Pydantic, mostra warnings
  - funcionária revê/corrige no ecrã  <- VALIDAÇÃO 1 (sobre os dados)
  - carrega RUN
      v
   campos.json   <- o "contrato" entre as duas peças
      v
[PEÇA B - Robô RPA (PyWinAuto, local)]
  - lê o JSON, preenche os campos do SIMN
      v
[SIMN preenchido]
  - funcionária confere no SIMN  <- VALIDAÇÃO 2 (sobre o resultado)
  - regista
```

Princípio-chave: a validação acontece ANTES de o robô correr (no ecrã da Peça A),
não depois. O robô só executa o que já foi aprovado.

## 3. Stack (decidida)

- **Linguagem:** Python para tudo.
- **Peça A (extração + interface):**
  - `python-docx` -> ler o Word
  - template parsing + **Claude API** (`anthropic` SDK) só onde a redação varia
  - **Pydantic** -> validar o JSON de saída (garante campos e tipos certos)
  - **Streamlit** -> interface local (localhost), ecrã de colar/rever/RUN
- **Peça B (robô):** **PyWinAuto** (confirmado: SIMN é app desktop nativa Windows .exe,
  não web. Logo NÃO é Playwright).
- **Hospedagem:** TUDO LOCAL, na máquina do cartório onde corre o SIMN. Não cloud.
  Razões: (1) o RPA tem de estar onde está o SIMN, controla teclado/rato daquele ecrã;
  (2) sigilo notarial, dados ficam dentro de casa. Única coisa que sai: texto da
  escritura para a Claude API (a minimizar; quanto mais template parsing, menos sai).

## 4. O SIMN (o que sabemos pela foto)

- Aplicação desktop nativa Windows (.exe). Visual antigo, menus no topo
  (Gestão de escrituras, Clientes, Outorgantes, Comunicações, Livros, etc.).
- Corre num servidor mas todos os PCs da empresa o têm e correm; inserção feita
  nos PCs locais. Tudo partilhado (documentos também). SO Windows. Sem restrições de TI
  aparentes (pode instalar software). App local = sem atualizações = ecrã estável
  (bom para RPA).
- Estrutura de uma Compra-venda no SIMN:
  - Cabeçalho: Livro, Folhas, Data, Nº Conta, Mnemónica (CV)
  - Vendedor(es) -> identificados por NIF
  - Comprador(es) -> por NIF
  - Bens -> por código (ex: 100108 - U - 1948)
  - Objeto (texto grande)
  - Verbete estatístico (Nº)
  - Importâncias: Hipoteca, Preço da venda
  - DUCs: número + montante (vem das Finanças)
  - Relações: tabela que liga Vendedor -> Bem -> Comprador

## 5. Descobertas importantes / hipóteses a confirmar no vídeo

1. **Outorgantes parecem ser inseridos por NIF, não por nome.** Forte indício de que o
   SIMN tem base de dados de Clientes/Outorgantes. Se o cliente já existe, a funcionária
   só associa o NIF e o SIMN puxa o resto.
   - CONFIRMAR NO VÍDEO: ela escreve só o NIF e aparece o nome, ou escreve nome+morada+
     estado civil+regime de bens de raiz?
   - Cenário Fácil (cliente já na base): robô só mete NIFs + preço + código bem + relações.
     Extrator só precisa de tirar NIFs e valores (menos dados sensíveis, melhor).
   - Cenário Difícil (cliente novo): robô tem de criar o outorgante de raiz primeiro.
2. **Código do bem (100108 - U - 1948):** identificador interno, NÃO aparece tal-e-qual
   na escritura. CONFIRMAR: vem da base? pesquisa predial? escrito à mão? Pode ser passo
   manual fora do âmbito do robô.
3. **DUC (montante, ex: 14.906,04):** vem do Portal das Finanças (IMT + Imposto do Selo),
   NÃO da escritura. Quase de certeza passo manual obrigatório nas Finanças antes do SIMN.
   PROVAVELMENTE FORA DO ÂMBITO do robô (envolve login Finanças + responsabilidade fiscal).
   Dizer isto ao notário já: o robô trata da escritura, o DUC continua manual.

## 6. Faseamento

- **Fase 1 (Peça A):** extração + interface de validação. Desenvolve-se e testa-se
  AQUI/no Project, sem o SIMN, com escrituras anonimizadas. Passa para produção fácil.
- **Fase 2 (Peça B):** robô PyWinAuto. SÓ se pode desenvolver/testar contra o SIMN real,
  na máquina do cartório, por tentativa-erro contra os ecrãs reais. Alimentado pelos
  JSON que a Peça A já produz bem.
- Ordem de construção: schema (modelos.py) -> extração (extrator.py) -> interface (app.py)
  -> robô (peca_b). Os 3 primeiros podem ser feitos já, sem SIMN.

## 7. Prioridade dos tipos de ato

Cobrir primeiro os 3-4 tipos que representam ~80% do volume (Pareto). Começar por
Compra-venda. Aguardar lista de tipos + frequências do notário.

## 8. ROI (expectativa realista)

~150 atos/mês x ~8-12 min ≈ 20-30 h/mês de inserção. Corte de ~80% -> poupança real,
mas o ganho maior é qualitativo: menos erros, libertar a pessoa, tirar tarefa chata.
NÃO prometer revolução de horas. Justifica-se por qualidade + libertar pessoas.

## 9. Privacidade / RGPD / sigilo notarial

- Escrituras com dados reais NÃO entram no Project/dev. Só dados anonimizados (estrutura
  e linguagem intactas, nomes/NIFs/moradas fictícios).
- Em produção, dados reais ficam na máquina do cartório.
- Minimizar o que vai para a Claude API. Onde a estrutura for fixa, extrair 100% local.

## 10. Estado atual / próximos passos

- [x] Arquitetura, stack, faseamento decididos.
- [x] Esqueleto da Peça A criado (modelos.py, extrator.py, app.py, requirements.txt).
- [x] Recebida 1 escritura real de compra-venda de fração (representa ~80% dos casos).
- [x] Descoberto que os ficheiros são .doc (Word 97-2003), NÃO .docx. Extrator adaptado
      para ler ambos (via LibreOffice/antiword para o .doc antigo).
- [x] Schema (modelos.py) refinado com os campos reais da escritura. Extração validada:
      separa casais em 2 outorgantes, apanha NIFs, preço por extenso, VPT, DUCs, hipoteca
      a cancelar. Ver partilha/campos_exemplo.json.
- [ ] Receber mais escrituras (outros tipos de ato) + frequências.
- [ ] Gravar vídeo do SIMN e responder às 3 perguntas-chave (secção 5).
- [ ] Definir o campo Objeto (texto grande): ver como a funcionária o escreve no SIMN.
- [ ] Construir Peça B contra o SIMN real, no cartório.

### Notas técnicas da escritura real (importante)
- Ficheiros .doc antigo: precisa de LibreOffice ou antiword na máquina para ler.
- Outorgantes vêm em blocos "Primeiro:/Segundo:". Um bloco pode ser um CASAL (2 NIFs
  juntos, "respectivamente"). O extrator separa em 2 outorgantes ligados por conjuge_de_nif.
- Preço aparece POR EXTENSO ("DUZENTOS E OITENTA MIL EUROS"). O LLM converte para número.
- DUCs (IMT + TGIS/imposto do selo) aparecem no "Arquivo" como nº de documento. O MONTANTE
  não está na escritura (vem das Finanças). Confirmar no vídeo se o robô trata ou fica manual.
- Aparece código de Certidão Predial Permanente (PP-...), descrição predial, artigo
  matricial e VPT. O codigo_simn interno (100108-U-1948) continua a NÃO vir da escritura.
- O título interno do .doc dizia "PARTILHA" mas é uma compra-venda (template reaproveitado).
  Não fiar pelo título interno do ficheiro.

## 11. Preferências de trabalho

- Sem em-dashes no texto escrito (usar vírgulas, parênteses ou pontos).
- Tom direto, aplicado, iterativo. Problemas concretos com dados reais.
- Nunca vender IA onde automação simples chega.
