# Arranque no cartório — deixar a app pronta em todos os PCs

Guia curto e prático. Duas partes: (1) atualizar cada PC, (2) ligar o email dos reportes.

---

## Parte 1 — Atualizar cada PC (uma vez por PC)

A app passou a **atualizar-se sozinha** ao abrir. Mas a versão antiga ainda não sabe
disso, por isso é preciso um empurrão inicial em cada PC:

1. Duplo-clique em **`atualizar.bat`**. Esperar até dizer **"ATUALIZAÇÃO CONCLUÍDA"**.
2. Abrir a app pelo atalho normal. Deve aparecer **"A verificar atualizações..."** e abrir.

A partir daqui, **abrir a app já traz sempre a última versão** (não é preciso mais o
`atualizar.bat` à mão). Se não houver internet ou o token expirar, a app abre na
mesma com a versão que está no PC e mostra um popup a avisar.

---

## Parte 2 — Ligar o email dos reportes (uma vez)

Quando algo corre mal, a funcionária carrega num botão e **recebes o caso por email**.
Para isso é preciso uma conta Gmail que ENVIE (pode ser uma dedicada do cartório).

### 2a. Preparar a conta Gmail (fazes tu, 1 vez)
1. Entra na conta Gmail que vai enviar. Em **myaccount.google.com → Segurança**:
   ativa a **Verificação em 2 passos** (obrigatório para o passo seguinte).
2. Em **Segurança → Palavras-passe de aplicação** (ou myaccount.google.com/apppasswords):
   cria uma nova, dá-lhe um nome (ex: "app cartorio"), e **copia as 16 letras**.

### 2b. Em CADA PC, definir 2 variáveis de ambiente (como já fazes com as chaves da API)
No PowerShell (do utilizador da funcionária):
```powershell
[System.Environment]::SetEnvironmentVariable('REPORT_EMAIL_USER','a-conta-que-envia@gmail.com','User')
[System.Environment]::SetEnvironmentVariable('REPORT_EMAIL_PASS','as16letrassemespacos','User')
```
- O destino por defeito é **rui.edh.ferreira@gmail.com**. Para mudar, define também
  `REPORT_EMAIL_TO` da mesma maneira.
- **Fecha e reabre a app** depois de definir (para apanhar as variáveis).

### 2c. Testar (1 min)
Na app: barra lateral → **🐞 Reportar problema** → escreve "teste" → **Enviar reporte ao Rui**.
Deves receber um email com um ZIP anexado.

> Se o email não estiver configurado ou falhar, **o reporte não se perde**: fica um
> ZIP na pasta `reportes/` do PC. Nesse caso recolhes o ficheiro à mão.

---

## O que recebes num reporte

Um email com um ZIP que contém:
- `DESCRICAO_DA_FUNCIONARIA.txt` — o que ela escreveu.
- `DIAGNOSTICO.txt` — versão da app (commit), tipo de ato, PC/Windows, provider do LLM,
  e o **erro técnico (traceback)** se rebentou.
- `campos.json` — o que foi extraído.
- `texto_extraido.txt` — o texto que foi para o LLM.
- `escritura/<ficheiro>` — a própria escritura que estava a ser processada.

Ou seja: chega-me tudo o que preciso para reproduzir e corrigir.

---

## Se um PC pedir utilizador/password ao atualizar

Significa que o **token do git expirou** nesse PC. A app abre na mesma (versão local).
Avisa-me para renovar o token. (Alternativa definitiva: tornar o repo público, aí o
`git pull` dispensa token.)
