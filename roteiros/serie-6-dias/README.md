# Série "Os 6 dias da Zoe": status e como continuar

Três Reels narrados pela Isabela sobre os dias de busca. O roteiro, os fatos e a mídia de cada episódio ficam em [roteiro.md](roteiro.md).

## Status (30/09)

| Ep. | Dias | Situação |
|---|---|---|
| 1 | sex 18 e sáb 19/09 | **Pronto e versionado** (commit 294a1b9): `saida/video/video3/03-os-6-dias-parte-1.mp4` (+ `-sem-musica.mp4`), 67,2 s |
| 2 | dom 20, seg 21 e ter 22/09 | **Pronto (30/09)**: `saida/video/video4/04-os-6-dias-parte-2.mp4` (+ `-sem-musica.mp4`), 64,2 s, com a capa (`capa-04.png`) e o texto do post (`legenda-04.txt`). Ainda não versionado |
| 3 | qua 23/09 | Aguardando os fatos. O fecho leva ao Reel 01 (o reencontro, 24/09) |

A divisão mudou em 29/09: o Ep. 2 ficou com três dias (a terça das câmeras fecha o episódio), e o Ep. 3 com um só.

## O fluxo que funcionou no Ep. 1

1. **Fatos:** o Guilherme conta o que aconteceu nos dois dias. Eles entram no `roteiro.md` com a ideia do episódio, a narração (≈ 140 palavras) e o mapa de tempo. Nada é inventado; o que falta vira pergunta.
2. **Mídia:** sincronizar o Drive (`rclone copy gdrive: drive/`) e checar a data real de cada arquivo:
   - vídeos do iPhone: `com.apple.quicktime.creationdate`, no ffprobe;
   - WhatsApp e prints: a data vem no nome do arquivo;
   - HEIC: pela ordem da numeração.

   Com isso sai o painel `epN-candidatos.jpg`, que o Guilherme aprova antes da montagem. É a checagem de spoiler: nenhum episódio pode mostrar material de dias posteriores.
3. **Gravação:** a Isabela grava **um áudio por parágrafo** (áudio do WhatsApp, `.ogg`).
4. **Montagem:** delegada a um agente com um briefing completo (fontes, mídia aprovada, blurs, mapa de tempo, regras).
5. **Revisão do supervisor:**
   - folha de contato com 1 quadro a cada 1,5 s;
   - quadros em resolução cheia (telefones borrados, zona segura, textos);
   - níveis de áudio (`volumedetect`), para confirmar que a trilha zera no bloco do silêncio.
6. **Correções:** o Guilherme assiste e pede os ajustes; o agente corrige, e o supervisor revisa de novo.

## Peças reutilizáveis

- `editor/build_03.py`: base para `build_04.py` e `build_05.py`. Copiar e trocar PARTS/GAPS, SHOTS, cartelas e textos.
- `editor/trilha_03.py`: trilha original sintetizada (75 BPM, piano abafado + pad), que zera no bloco do silêncio.
- `editor/mapa.py`: ruas reais de Passo Fundo (OpenStreetMap, cache em `videos/osm-passo-fundo.json`), em camadas para animar. A rota da fuga está nas constantes `ESQ_BRITO`, `ESQ_LAVAPES` e `FIM`.
- Um venv Python 3.9 com numpy, scipy, Pillow e faster-whisper. Ele fica numa pasta temporária; para recriar: `py -3.9 -m venv <pasta>` e `pip install numpy scipy Pillow faster-whisper`.

## Padrão fixo da série (manter nos Ep. 2 e 3)

- **Gancho:** "OS 6 DIAS DA ZOE" grande (Fontsize 170, cream) e "PARTE N" em lilac, sobre um degradê ink no topo, sem cobrir rostos.
- **Contador** de 6 segmentos no topo, enchendo a cada cartela.
- **Cartelas:** "DIA N" / "DOM 20/09", em Poppins ExtraBold sobre ink, em ~1 s de respiro, sem legenda por cima.
- **Legendas** no padrão do Reel 01: até 3 palavras, caixa alta, palavra ativa em amarelo, y=1180.
- **Fecho sóbrio:** a Zoe hoje, em casa, com "PARTE N+1 · DIAS X E Y →" e o **@souazoe.pf** discreto.
- **Trilha** original e contida, que corta nos momentos de silêncio. Sempre sai também uma versão sem música.
- **Blur:** telefones e marcações de contas de terceiros sempre borrados.
- **Zona segura do Reels:** conteúdo entre y 230 e 1500, e nada nos 130 px da direita.

## O que o Guilherme pediu nas correções do Ep. 1 (vale para os próximos)

- **Prints e fotos de divulgação:** um por vez, inteiros e devagar, com um zoom lento só. Sem punch-ins, sem repetir, sem excesso de transição. O mais marcante vai por último.
- **Pausas curtas:** não esticar o silêncio antes de uma frase de impacto.
- **Título do gancho grande e legível.**
- **Nada que confunda com a Zoe:** recortar outros cachorros para fora do quadro.
- **Trajetos no mapa fiéis ao que se sabe.** Ele desenha por cima de um quadro, se precisar.
- **(Ep. 2) Cartões de vídeo centralizados e grandes:**
  - margens iguais dos dois lados, com ~980–1000 px de largura; os 130 px da direita só importam na metade de baixo, onde ficam os botões do Reels;
  - o zoom acompanha o assunto, mas **nunca passa da borda da imagem**: nada de faixa escura ou de borda de monitor dentro do cartão.

## Ep. 2: o que falta

As pendências estão no fim da seção do Ep. 2 no [roteiro.md](roteiro.md). A mídia veio do Drive em `set26/dia 3e4e5/`, e alguns arquivos não têm extensão (são MP4 e JPEG).

Cuidados na montagem:
- **`filmagemzoe1`:** cortar antes dos 12 s, porque depois aparece uma pessoa correndo.
- **`filmagemzoe2`:** é o celular filmando o monitor, de lado. Girar 90° e recortar as notificações ("Empréstimo da Vivo", "Atividade humana detectada").
- **Carimbos na tela:** cada parecida leva um carimbo "NÃO ERA ELA", e as fotos de IA dos golpes levam a etiqueta "GERADA POR IA", para ninguém confundir com a Zoe.
- **As duas gravações vão em vídeo**, com a passagem dela em câmera lenta. Não usar quadro parado.
- **Mapa:** `mapa.FIM_EP2` (Lava Pés × Capitão Eleutério). As camadas saem com `python editor/mapa.py ep2-camadas`.

**Reservado para o Ep. 3 ou depois:**
- as outras gravações de câmera do percurso dela;
- o mapa do raio de 3 km (salvo em 24/09, às 7h12);
- os vídeos de câmera de 24/09;
- a pasta "dia do encontro" (Reel 01);
- os vídeos na clínica (tema "estado clínico").

## Cuidados técnicos

- **Áudios:** `audios/1.ogg` a `8.ogg` são a narração do Ep. 1, e o `build_03.py` lê daí. **Os áudios do Ep. 2 estão em `audios/dias3e4e5/`**, e o `build_04.py` lê daí. Os do Ep. 3 devem ir numa pasta própria, para não sobrescrever os anteriores. O `build_01.py` também espera um `audios/1.ogg` (do Reel 01): não rodar sem ajustar.
- **PATH no Git Bash:** o ffmpeg e o rclone ficam fora do PATH. `export PATH="$PATH:$HOME/AppData/Local/Microsoft/WinGet/Links"`.
- **Python:** o padrão da máquina é o 3.7, e o `python3` é um atalho quebrado. Use `python` ou `py -3.9`.
