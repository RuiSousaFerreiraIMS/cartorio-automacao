# Deploy no PC do cartório

Guia único para instalar o sistema num PC novo do cartório. ~15 minutos.

## 0. Pré-requisitos

Verifica que já tens instalado:

```powershell
python --version   # deve devolver 3.12+ (ou o que tinhas antes)
git --version      # 2.x
```

Se algum não existir:
- Python: https://www.python.org/downloads/ (marca "Add Python to PATH")
- Git for Windows: https://git-scm.com/download/win

## 1. Clonar o projecto (1 min)

Escolhe uma pasta onde vais guardar tudo. Recomendo `C:\cartorio-automacao`
para ficar sempre no mesmo sítio:

```powershell
cd C:\
git clone https://github.com/<TEU_USER>/cartorio-automacao.git
cd cartorio-automacao
```

## 2. Criar ambiente Python isolado (2 min)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyautogui pywinauto
```

Se der erro "execution policy" no Activate:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 3. Configurar a chave da API do LLM (2 min)

**Nunca metas a chave no repositório.** Guarda-a como variável de sistema:

```powershell
[System.Environment]::SetEnvironmentVariable("LLM_PROVIDER", "groq", "User")
[System.Environment]::SetEnvironmentVariable("GROQ_API_KEY", "gsk_XXXXXX_A_TUA_CHAVE_XXXXXX", "User")
[System.Environment]::SetEnvironmentVariable("GROQ_MODEL", "llama-3.3-70b-versatile", "User")
```

Fecha o PowerShell e abre um novo (as variáveis só ficam disponíveis nas
janelas novas).

Confirmar que ficou:
```powershell
echo $env:GROQ_API_KEY
```

## 4. Confirmar Java Access Bridge (2 min)

O robô precisa de o JAB estar activo para ler campos do SIMN. Como
Administrador:

```powershell
jabswitch -enable
```

Se disser "não reconhecido", encontrar e usar o caminho completo:
```powershell
"C:\Program Files\Java\jre1.8.0_471\bin\jabswitch.exe" -enable
```

Configurar variável de ambiente para a DLL (uma vez):
```powershell
[System.Environment]::SetEnvironmentVariable("RC_JAVA_ACCESS_BRIDGE_DLL", "C:\Program Files\Java\jre1.8.0_471\bin\WindowsAccessBridge-64.dll", "User")
```

## 5. Testar a Peça A (Streamlit) (3 min)

```powershell
cd peca_a_extracao
python -m streamlit run app.py
```

Abre o browser em http://localhost:8501. Faz upload de uma escritura de
`exemplos/` e valida que:
- ✅ Extrai os campos correctamente
- ✅ Mostra avisos
- ✅ Consegues clicar em "Exportar" e gera `partilha/campos.json`

Para parar: `Ctrl+C` no PowerShell.

## 6. Testar a Peça B (Robô) (5 min)

Abre o SIMN, cria Nova Escritura → Compra-venda, adiciona Vendedor(es) →
Novo Outorgante Singular, cursor no primeiro campo (Nº Contribuinte).

Alt+Tab para o PowerShell:

```powershell
cd ..\peca_b_robo
python robo.py
```

Contagem decrescente de 5s: Alt+Tab de volta ao SIMN. O robô preenche.

Emergência: mover rato para canto superior esquerdo.

## 7. Criar atalhos no desktop para as funcionárias

Cria um ficheiro `iniciar_app.bat` na raiz do repositório com o conteúdo:

```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
cd peca_a_extracao
python -m streamlit run app.py
pause
```

Cria atalho no desktop apontando para este `.bat`. Duplo-clique arranca
a app inteira. Fecha a janela = pára tudo.

## Actualizações futuras

Sempre que houver alterações no repositório:

```powershell
cd C:\cartorio-automacao
git pull
```

Se `requirements.txt` mudou:
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Estrutura de pastas depois de tudo montado

```
C:\cartorio-automacao\
├── .venv\                # ambiente Python (local, não sincronizado)
├── exemplos\             # escrituras de teste
├── partilha\
│   └── campos.json       # gerado pela funcionária, lido pelo robô
├── peca_a_extracao\      # Streamlit app (extração)
├── peca_b_robo\          # Robô que preenche o SIMN
│   ├── imagens\          # recortes dos botões do SIMN
│   ├── robo.py           # entry point
│   ├── robo_actions.py   # helpers pyautogui
│   ├── robo_forms.py     # preenchimento de forms
│   └── robo_fluxos.py    # orquestração por tipo de acto
├── iniciar_app.bat       # atalho para as funcionárias
└── README.md
```

## Se algo correr mal

- **`python` não encontrado**: reinstalar Python marcando "Add to PATH"
- **`git pull` diz "detached HEAD"**: `git checkout main` primeiro
- **Streamlit não abre no browser**: abrir manualmente http://localhost:8501
- **Robô diz "botão X não encontrado"**: as imagens em `peca_b_robo/imagens/`
  não batem com o SIMN actual. Enviar screenshot ao Rui para novos recortes.
- **`WindowsAccessBridge dll not found`**: refazer o passo 4 (variável +
  reiniciar SIMN)
