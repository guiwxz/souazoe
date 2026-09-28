# Zoe | Causas Animais

Produção de conteúdo (Reels, carrosséis, Stories) para o lançamento do perfil **Zoe | Causas Animais** no Instagram e no TikTok (Passo Fundo/RS).

A Zoe é uma cachorra que ficou **6 dias desaparecida** e foi encontrada em **24/09/2026, às 16h, perto do Instituto Menino Deus**, depois de uma grande mobilização da cidade. Os tutores são **Isabela** e **Guilherme**. A estratégia digital é de **Gabriela Fabian**.

A tese da marca: *"A Zoe não será a cachorra que viralizou porque sumiu. Ela será a cachorra que voltou porque uma comunidade se mobilizou, e que agora mobiliza essa comunidade por outros animais."*

## Documentos de referência (ler antes de criar conteúdo)

- `Estrategia_Lancamento_Zoe_Causas_Animais.pdf`: a estratégia completa (posicionamento, bio, os 3 conteúdos de lançamento, a linha editorial da semana 1, os pilares, os Stories de transferência, o que NÃO fazer e as métricas).
- `Carrossel_Apresentacao_Zoe.pdf`: o roteiro card a card do carrossel de apresentação (primeiro post), com a direção de copy e design.

Para ler: `pdftotext -layout <arquivo>.pdf -`

## Resumo da estratégia

**Posicionamento.** A Zoe é a personagem que cria vínculo, a experiência vivida gera utilidade e as causas animais dão o propósito. O perfil não é um perfil genérico de pet nem uma página pesada de sofrimento animal. Três eixos: HISTÓRIA (6 dias, mobilização, reencontro), PERSONALIDADE (rotina, humor, família, recuperação) e PROPÓSITO (desaparecidos, adoção, identificação, prevenção).

**Identidade.** O nome de exibição é "Zoe | Causas Animais", com o mesmo @ nas duas redes. Evitar "SOS", "procura-se" e "desaparecida".
Bio: `Fiquei 6 dias perdida. Uma cidade inteira ajudou a me trazer pra casa. ❤️ / Agora minha história vai ajudar outros animais. 🐾 / 📍 Passo Fundo/RS`

**Lançamento.** Não anunciar um perfil vazio: publicar 3 conteúdos antes do chamado público.
1. **Como encontramos a Zoe**: Collab com a Isabela, é o principal conteúdo de transferência de audiência. A veterinária a reconhece saindo do mato perto do Instituto Menino Deus, avisa a família, a equipe procura, uma câmera mostra uma fração de segundo, a Isabela chama e a Zoe aparece.
2. **O que aconteceu nesses 6 dias?**: "a gente não sabe". NUNCA inventar o período desconhecido. Mostrar só o que se sabe (chuva, distância, estado físico, minutos reconstruídos pelas câmeras).
3. **O golpe durante a busca**: utilidade pública (pedido de dinheiro para gasolina, depois para um suposto problema no carro). CTA: "Salva esse vídeo."

**Semana 1:** (1) Como encontramos a Zoe · (2) Onde ela esteve nos 6 dias · (3) O golpe · (4) Como as câmeras reconstruíram os primeiros minutos · (5) 5 coisas que faríamos diferente · (6) Como está a Zoe agora · (7) Manifesto da causa.

**Pilares depois do lançamento:** 40% ZOE (rotina, humor), 25% CAUSA (adoção, ONGs, campanhas verificadas), 25% UTILIDADE (busca, cartazes, câmeras, golpes, prevenção), 10% ARQUIVO (bastidores dos 6 dias).

**Collab:** usar SÓ no lançamento e em grandes campanhas. Rotina e humor saem apenas no perfil da Zoe.

**Papéis das redes:** o Instagram é para comunidade local, Collabs e Stories. O TikTok é para uma narrativa mais crua, com a Isabela falando para a câmera, e títulos pesquisáveis ("cachorro desaparecido: o que fazer").

**O que NÃO fazer:** publicidade ou monetização cedo, pedidos de ajuda sem checagem, inventar fatos, deixar o perfil preso ao desaparecimento, impulsionar antes de entender o que converte.

**Métricas:** views/alcance, visitas ao perfil, seguidores por conteúdo, compartilhamentos, salvamentos, retenção e DMs.

## Direção de copy e visual

- **Voz** (no carrossel): a própria Zoe narra. O humor vem da lógica dela, sem diminuir a gravidade. A família aparece pelos olhos dela.
- **Fotos reais primeiro.** Na fase da busca, usar material documental verdadeiro. No fechamento, uma Zoe segura e em casa (nada de estética de "cachorra perdida").
- Pouco texto na arte, hierarquia forte, frases curtas e respiro.
- Cada assunto (Instituto Menino Deus, golpe, câmeras, estado clínico, quilometragem) tem seu próprio conteúdo. Não antecipar tudo num único post.
- Idioma: português do Brasil.

## Estrutura do projeto

```
drive/        # espelho do Google Drive (NÃO versionado): fonte da verdade da mídia bruta
  dia do encontro/        # vídeos/fotos do reencontro (24/09) + Reel 01 já exportado
  Set／26/                # fotos/vídeos de setembro (HEIC/MOV do iPhone)
    cartazes/             # vídeos/fotos dos cartazes da busca
  instagram/apresentação / # material para o carrossel de apresentação (a pasta tem um espaço no final do nome)
  posts/                  # o que já foi publicado (Reel 01 v2, capa, carrossel1 com 9 cards)
  Meme/                   # imagens avulsas
videos/, audios/  # cópias locais de trabalho usadas na geração (NÃO versionadas)
editor/       # pipeline dos Reels em ffmpeg
  build_01.py   # monta o Reel 01 "Como encontramos a Zoe" (1080x1920, 30fps) → saida/video/video1/
  words-01.json # timestamps por palavra (faster-whisper) da narração audios/1.ogg
  build_02.py   # monta o Reel 02 "Tchau, cartaz" (retirada dos cartazes, 19,5 s, sem narração) → saida/video/video2/
  trilha_02.py  # trilha original do Reel 02 (120 BPM, sintetizada com numpy+scipy) → audios/trilha-02.wav
  capa_02.py    # capa do Reel 02 (Pillow, padrão da capa do Reel 01, telefones do cartaz borrados) → saida/video/video2/capa-02.png
  fonts/        # Poppins + Caveat
carrossel/    # template padronizado dos carrosséis (versionado)
  index.html    # 8 cards de 1080x1350, com a identidade visual
  render.sh     # Chrome headless → saida/carrossel/<nome>/zoe-XX.png + _preview.jpg (ex.: ./render.sh carrossel2; padrão carrossel1)
  img/          # fotos já recortadas para cada card (1.jpg..8.jpg)
  fonts/        # Poppins + Caveat (manuscrita)
perdidos/     # artes recebidas de animais desaparecidos (ex.: garibaldi.jpeg)
templates/    # templates reutilizáveis na identidade da Zoe, sem o nome escrito (versionado)
  fonts/        # Poppins + Caveat compartilhadas pelos templates
  desaparecidos/  # alerta de desaparecido: feed 1080x1350 + Stories 1080x1920 do mesmo index.html
    index.html    # fundo lilás, degradê ink, tag em caixa ink, nomes em Caveat, telefone em caixa rosa
    render.sh     # Chrome headless → saida/<nome>-feed.png e saida/<nome>-story.png (ex.: ./render.sh garibaldi-masha)
    recorte.py    # recorta os cães da arte recebida (rembg + opencv num venv temporário) → img/
saida/        # renders finais (versionado), um agrupamento por peça
  carrossel/carrossel1/   # zoe-01..08.png + _preview.jpg (carrossel de apresentação)
  video/video1/           # 01-como-encontramos-a-zoe.mp4 + legendas-01.ass
  video/video2/           # 02-tchau-cartaz.mp4 (+ -sem-musica.mp4, para usar áudio em alta no app) + capa-02.png + legendas-02.ass
```

Novas peças entram em `saida/carrossel/carrosselN/` e `saida/video/videoN/`, numeradas em sequência.

### Identidade visual (carrossel/index.html)

- Cores: `--ink #17131F`, `--cream #F6F1E9`, `--lilac #B9A7F3`, `--pink #EC4899`, `--muted #6E667A`.
- Tipografia: Poppins (400–800) nos títulos e no texto, Caveat para os comentários "manuscritos" da Zoe.
- Layouts: `.full` (foto inteira com degradê e texto embaixo), `.split` (foto em cima e painel de texto, altura via `--ph`), `.dark` e `.doc` (P&B com "REC", para material documental). Barra de progresso no topo.
- Reaproveitar esse template (copiar e adaptar) em novos carrosséis para manter o padrão.

### Reels (editor/build_01.py)

- Os cortes ficam sincronizados com as palavras da narração (lista `SHOTS`), com um pan lento em todos os takes.
- Legendas ASS: blocos de até 3 palavras, em caixa alta, Poppins ExtraBold, com a palavra ativa em amarelo e um gancho no topo nos primeiros segundos.
- Áudio: highpass + afftdn + loudnorm (-14 LUFS). Saída em H.264 CRF 18 com AAC 192k.
- Transcrição: faster-whisper num venv temporário (não está instalado globalmente), gerando uma lista `[{"w","s","e"}]`.
- Uso: `python3 editor/build_01.py editor/words-01.json editor/fonts`
- Tamanho de fonte no ASS: o `Fontsize` do libass é a altura da linha, não o "em". Na Poppins, a maiúscula tem ~0,41 × Fontsize (use 150–270 para títulos em 1080x1920).
- Reel 02 (sem narração): cortes no tempo da trilha própria (1 tempo = 0,5 s) e cada cartaz rasga num tempo forte. Primeiro `python editor/trilha_02.py audios/trilha-02.wav` (numpy+scipy num venv temporário), depois `python3 editor/build_02.py`. Lê direto de `drive/set26/`; as fotos (HEIC e o quadro único do IMG_8445) são convertidas para `videos/` na primeira execução.

## Sincronização do Google Drive (rclone)

A mídia vem do Google Drive e é sincronizada **manualmente, de tempos em tempos**, com o rclone. A pasta `drive/` não entra no git.

- Requisito: ter o `rclone` instalado (aqui em `~/.local/bin/rclone`) e um remote chamado **`gdrive`** configurado (somente leitura):
  ```sh
  rclone config create gdrive drive scope=drive.readonly   # abre o navegador para o login no Google
  ```
- Sincronizar (a raiz do remote corresponde a `drive/`):
  ```sh
  rclone copy gdrive: drive/ --transfers 8 -q
  ```
  Usar `copy`, não `sync`, para não apagar arquivos locais.
- Antes de procurar mídia nova, sugerir uma sincronização se o conteúdo parecer desatualizado.
- Atenção: o remote usa o client_id compartilhado do rclone, que será desativado em 2026. Se a sincronização parar, será preciso criar um client_id próprio no Google Cloud (https://rclone.org/drive/#making-your-own-client-id).
- Nunca copiar o token de `~/.config/rclone/rclone.conf` para dentro do projeto.

## Ferramentas

ffmpeg/ffprobe, python3 + Pillow, google-chrome (headless para os carrosséis), node/npx (MCP do Remotion em `.mcp.json` e skills do Remotion em `.claude/skills/`, caso algum vídeo seja feito em Remotion). Os arquivos HEIC/MOV do iPhone precisam ser convertidos antes do uso (o ffmpeg 7.1+ lê HEIC direto; os vídeos atuais são H.264 SDR, sem HDR).

No Windows (Git Bash), o ffmpeg e o rclone vêm do winget (`Gyan.FFmpeg`, `Rclone.Rclone`), e o Chrome fica em `C:\Program Files\Google\Chrome\Application\chrome.exe`. `build_01.py` e `render.sh` funcionam nos dois sistemas.

## Regras de trabalho

- Nunca inventar fatos da história da Zoe. Se faltar informação, perguntar.
- Os nomes das pastas do Drive têm caracteres especiais (`Set／26` usa uma barra fullwidth, e `apresentação ` tem um espaço no final): sempre usar aspas nos caminhos. No Windows, o rclone grava esse espaço final como `␠` (U+2420), então a pasta local é `drive/instagram/apresentação␠`.
- Mídia bruta (drive/, videos/, audios/) não vai para o git. Renders finais em saida/ vão, assim como scripts, templates, fontes, imagens recortadas e documentos.
