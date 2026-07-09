# Instalação nos PCs das funcionárias

Guia para o Rui instalar a app num PC novo, sem erros. A ideia: três coisas
manuais (uma vez por PC), depois **um script** faz o resto e **um verificador**
confirma que ficou tudo bem.

Tempo por PC: ~10 minutos (a maior parte é o download das dependências).

---

## Antes de começar (pré-requisitos, uma vez por PC)

O instalador trata das dependências Python, mas há três coisas que têm de
existir primeiro no PC:

1. **Python 3.10 ou superior**
   - Descarregar de https://www.python.org/downloads/
   - **IMPORTANTE:** no instalador do Python, marcar a caixa **"Add Python to PATH"**.

2. **LibreOffice** (para ler as escrituras `.doc` antigas)
   - Descarregar (grátis) de https://pt.libreoffice.org/descarregar/
   - Instalar com as opções por defeito.

3. **O código do projeto** na pasta `C:\cartorio-automacao`
   - Se tens Git: `git clone https://github.com/<TEU_USER>/cartorio-automacao.git C:\cartorio-automacao`
   - Se não tens Git: copia a pasta toda do projeto para `C:\cartorio-automacao`.

Tem à mão a **chave da API do Claude** (começa por `sk-ant-...`). O instalador
vai pedi-la.

---

## Instalar (um comando)

1. Abre a pasta `C:\cartorio-automacao`.
2. Botão direito no ficheiro **`instalar.ps1`** → **"Executar com o PowerShell"**.
   - Se preferires pela consola: abre o PowerShell na pasta e corre
     `powershell -ExecutionPolicy Bypass -File instalar.ps1`
3. Segue o que aparece no ecrã. A dada altura pede a **chave da API**: cola-a e Enter.
4. No fim, o instalador corre os **testes automáticos** e mostra o resultado.

Tudo o que aparece no ecrã fica também gravado num ficheiro de log em
`logs\instalacao_<data>.log` (é o que me envias se algo correr mal).

---

## Confirmar que ficou bem (o verificador)

No fim o instalador corre `verificar_instalacao.py`, que testa o PC linha a linha:

```
[ OK  ]  Versao do Python
[ OK  ]  Pacote anthropic (Claude)
[ OK  ]  Leitor de .doc antigo  ->  LibreOffice em ...
[ OK  ]  Chave da API (ANTHROPIC_API_KEY)  ->  definida
[ OK  ]  Teste a' API (internet)  ->  chave valida, modelo responde
...
 RESULTADO: TUDO OK.
```

- **`[ OK  ]`** = passou.
- **`[FALHA]`** = tem de ser resolvido (o resumo no fim lista o que falhou).
- **`[AVISO]`** = não é crítico (ex: um provedor que não usas).

Só está pronto quando disser **`RESULTADO: TUDO OK`**.

Podes voltar a correr os testes a qualquer momento (sem reinstalar):

```
.venv\Scripts\python.exe verificar_instalacao.py
```

(ou `... verificar_instalacao.py --offline` para saltar o teste que precisa de internet.)

---

## Usar a app

Duplo-clique no atalho **"Cartorio Escrituras"** que apareceu no ambiente de
trabalho. Abre o browser em `http://localhost:8501`.

Para parar: fechar a janela do browser e a app (ou a consola, se abriste pelo
`iniciar_app.bat`).

---

## Se falhar algo (resolução rápida)

| O verificador diz... | O que fazer |
|---|---|
| `Versao do Python [FALHA]` ou "Python nao encontrado" | Reinstalar o Python marcando **"Add Python to PATH"**. |
| `Pacote pyautogui/pywinauto/opencv [FALHA]` | O `pip` falhou (net?). Correr `instalar.ps1` outra vez. |
| `Leitor de .doc antigo [FALHA]` | Instalar o LibreOffice e correr o verificador de novo. |
| `Chave da API [FALHA]` | Pôr a chave: `instalar.ps1` outra vez, ou setá-la à mão (ver abaixo). |
| `Teste a' API [FALHA]` | Chave errada ou sem internet. Confirmar a chave `sk-ant-...`. |

Setar a chave à mão (se preciso), no PowerShell, e **reabrir a janela** a seguir:

```powershell
[System.Environment]::SetEnvironmentVariable("LLM_PROVIDER", "claude", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...A_TUA_CHAVE...", "User")
```

---

## Atualizações futuras (quando eu mudar o código)

```powershell
cd C:\cartorio-automacao
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe verificar_instalacao.py
```

Se o verificador der `TUDO OK`, a atualização ficou bem.
