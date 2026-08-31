# Arranque no cartório — deixar a app pronta nos 4 PCs

Guião de setup. Fazes o **Passo 0 uma vez** (no GitHub) e depois repetes os
**Passos 1–3 em cada PC**.

Repo: `https://github.com/RuiSousaFerreiraIMS/cartorio-automacao`

---

## Passo 0 — Tornar o repositório público (UMA vez, no GitHub)

Isto resolve de vez o problema do token: um repo **público** atualiza-se sem token
nenhum, nunca expira. (Não há segredos nem dados de clientes no repo.)

1. Vai a `https://github.com/RuiSousaFerreiraIMS/cartorio-automacao/settings`
2. Desce até **Danger Zone** → **Change repository visibility** → **Make public** → confirma.

Feito isto, as atualizações passam a funcionar em todos os PCs **sem depender do teu
token** (o git de um repo público lê sem autenticação; o token guardado, mesmo
expirado, deixa simplesmente de ser usado).

---

## Passo 1 — Pôr o PC na última versão (UMA vez por PC)

Só 1 PC tem a versão nova; os outros 3 estão numa versão antiga do git. Este passo
põe qualquer PC igual ao GitHub.

1. Abre a pasta do projeto (a que tem o `iniciar_app.bat`) no Explorador.
2. Clica na **barra de endereço**, escreve **`powershell`** e Enter (abre o PowerShell
   já nessa pasta).
3. Cola e corre:
```powershell
git fetch origin
git reset --hard origin/main
```
   Deve dizer `HEAD is now at ...`. Fecha o PowerShell.

A partir daqui, **abrir a app já a atualiza sozinha** sempre que abre. Não é preciso
mais fazer isto à mão.

> Se o `git fetch` pedir utilizador/password: o repo ainda não ficou público (revê o
> Passo 0) ou o GitHub ainda não propagou. Espera 1 min e tenta outra vez.

---

## Passo 2 — Ligar o email dos reportes

Quando algo corre mal, a funcionária carrega num botão e **recebes o caso por email**.

### 2a. Preparar a conta Gmail (fazes tu, 1 vez)
1. Numa conta Gmail que vá ENVIAR (pode ser dedicada do cartório), em
   **myaccount.google.com → Segurança**: ativa a **Verificação em 2 passos**.
2. Em **myaccount.google.com/apppasswords**: cria uma **palavra-passe de app**
   (nome ex: "app cartorio") e **copia as 16 letras**.

### 2b. Em CADA PC (no PowerShell do utilizador da funcionária)
```powershell
[System.Environment]::SetEnvironmentVariable('REPORT_EMAIL_USER','a-conta-que-envia@gmail.com','User')
[System.Environment]::SetEnvironmentVariable('REPORT_EMAIL_PASS','as16letrassemespacos','User')
```
- Destino por defeito: **rui.edh.ferreira@gmail.com**. Para mudar, define também
  `REPORT_EMAIL_TO`.
- Fecha e reabre a app para apanhar as variáveis.

> Sem isto o reporte **não se perde**: fica um ZIP na pasta `reportes/` do PC.

---

## Passo 3 — Testar o PC (1 min)

1. Abre a app pelo atalho normal → deve aparecer **"A verificar atualizações..."** e abrir.
2. Barra lateral → **🐞 Reportar problema** → escreve "teste" → **Enviar reporte ao Rui**.
   Deves receber o email com um ZIP.

Se os dois funcionam, o PC está pronto. Repete Passos 1–3 no PC seguinte.

---

## O que recebes num reporte (ZIP)
- `DESCRICAO_DA_FUNCIONARIA.txt` — o que ela escreveu.
- `DIAGNOSTICO.txt` — versão da app (commit), tipo de ato, PC/Windows, provider LLM,
  e o **erro técnico (traceback)** se rebentou.
- `campos.json`, `texto_extraido.txt`, e a **escritura** original.

---

## Resumo de estado por PC (marca à medida que fazes)

| PC | Passo 1 (atualizado) | Passo 2 (email) | Passo 3 (testado) |
|----|:---:|:---:|:---:|
| PC 1 |  |  |  |
| PC 2 |  |  |  |
| PC 3 |  |  |  |
| PC 4 |  |  |  |
