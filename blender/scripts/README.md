# Scripts de geração sintética no Blender

Esta pasta reúne os scripts usados para gerar as imagens sintéticas do projeto **ChildSafe Vision** no Blender 2.83.

O projeto trabalha com quatro classes de detecção no formato YOLO:

| ID | Classe |
|---:|---|
| 0 | tesoura |
| 1 | faca |
| 2 | pilha |
| 3 | tomada |

Os scripts automatizam a preparação da cena, a variação dos objetos e da câmera, a renderização das imagens e a criação dos arquivos de anotação.

## Estrutura

```text
blender/scripts/
├── tesoura/
├── faca/
├── pilha/
├── tomada/
└── README.md
```

- `tesoura/`: scripts correspondentes aos lotes da classe tesoura.
- `faca/`: versões e tentativas usadas durante a geração da classe faca.
- `pilha/`: scripts dos lotes de pilhas, incluindo uma tentativa intermediária.
- `tomada/`: scripts das tomadas próximas, distantes e em distância intermediária.

As cenas mistas não fazem parte do dataset final e, por isso, não estão incluídas nesta estrutura.

## Origem dos scripts

Os scripts da classe faca já existiam como arquivos `.py` durante o desenvolvimento.

Os códigos de tesoura, pilha e tomada foram inicialmente escritos no editor de texto interno do Blender e ficaram incorporados aos arquivos `.blend`. Posteriormente, eles foram exportados para esta pasta sem alterar a lógica original.

Os arquivos `.blend` continuam sendo importantes, pois preservam as cenas, os materiais, os objetos, as câmeras e as fontes de luz usados em cada lote.

## Funcionamento geral

Embora cada classe tenha características próprias, o fluxo básico dos scripts é semelhante:

1. Carregar ou construir os objetos da cena.
2. Configurar materiais, fundo, mesa ou parede.
3. Posicionar câmera e fontes de luz.
4. Definir uma semente para manter a geração reproduzível.
5. Variar posição, rotação, escala, iluminação e enquadramento.
6. Verificar se o objeto aparece adequadamente na imagem.
7. Renderizar uma imagem PNG em 640 × 640 pixels.
8. Projetar a caixa tridimensional do objeto no plano da câmera.
9. Converter a caixa para o formato normalizado do YOLO.
10. Salvar a imagem e o arquivo `.txt` correspondente.

O formato de cada linha de anotação é:

```text
classe x_centro y_centro largura altura
```

Os valores de posição e dimensão ficam normalizados entre 0 e 1.

## Scripts por classe

### Tesoura

A classe tesoura utiliza um modelo 3D externo e foi produzida em lotes com mudanças de iluminação, fundo e aparência do cabo.

A pasta contém scripts equivalentes às seguintes faixas:

```text
0001–0400
0401–0800
0801–1000
```

O último lote adotou uma configuração de cabo preto e vermelho e ajustes visuais para aumentar a diversidade do conjunto.

### Faca

A faca foi a classe que exigiu mais testes. Foram utilizados três tipos principais de modelo:

- `boning knife`;
- `butter knife`;
- `KitchenKnife`.

Os scripts podem ser identificados por padrões semelhantes a:

```text
gerar_faca_boning*.py
gerar_faca_butter_knife*.py
gerar_faca_kitchenknife*.py
```

Existem versões com alterações de:

- modelo 3D;
- tamanho do objeto;
- fundo;
- intensidade da iluminação;
- faixa de imagens;
- quantidade de tentativas para obter uma amostra válida;
- enquadramento e visibilidade do cabo e da lâmina.

O dataset final da classe foi formado por:

```text
400 imagens de boning knife
200 imagens de butter knife
400 imagens de KitchenKnife
```

As versões intermediárias foram preservadas porque documentam os ajustes realizados até obter imagens adequadas.

### Pilha

As pilhas foram construídas proceduralmente por código, sem depender de um arquivo FBX específico.

Cada unidade é formada por componentes cilíndricos e materiais que representam:

- corpo preto;
- parte superior cobre;
- terminais metálicos;
- formato aproximado de uma pilha AA.

As cenas podem conter de uma a seis pilhas. Cada instância recebe sua própria caixa delimitadora.

A pasta contém scripts equivalentes aos lotes:

```text
0001–0500
0301–0600 — tentativa intermediária
0601–1000
```

A faixa sobreposta de 301 a 600 representa uma tentativa de correção e não deve ser executada junto com os lotes finais sem revisar os diretórios de saída.

Essa classe exige mais tempo de renderização porque cada imagem pode conter vários objetos, várias transformações e várias anotações.

### Tomada

A tomada americana também foi criada proceduralmente com primitivas do Blender, incluindo cubos, cilindros e esferas.

As cenas combinam:

- placa da tomada;
- dois conjuntos de encaixes;
- parede procedural;
- materiais claros;
- iluminação e distância variadas.

Os scripts estão separados em configurações de:

```text
tomadas próximas
tomadas distantes
tomadas em distância intermediária
```

O dataset final possui 1.100 imagens da classe tomada.

## Requisitos

- Blender 2.83.
- Python incluído no Blender.
- Engine de renderização Eevee.
- Ativos 3D presentes na estrutura esperada do projeto.
- Permissão de escrita nos diretórios de imagens e labels.

O módulo `bpy` pertence ao Blender e não é executado pelo Python comum do sistema.

## Como executar pela interface do Blender

1. Abra o arquivo `.blend` correspondente ao lote.
2. Acesse a área **Scripting**.
3. Abra o script `.py` relacionado à cena.
4. Revise os caminhos de entrada e saída.
5. Execute o script com **Run Script**.

É recomendável fazer um teste com poucas imagens antes de iniciar um lote completo.

## Como executar em modo background

Exemplo no Windows:

```powershell
"C:\Program Files\Blender Foundation\Blender 2.83\blender.exe" `
  -b "CAMINHO_DA_CENA.blend" `
  -P "CAMINHO_DO_SCRIPT.py"
```

Exemplo:

```powershell
"C:\Program Files\Blender Foundation\Blender 2.83\blender.exe" `
  -b "C:\caminho\blender\cenas\pilha_dataset_0601_1000.blend" `
  -P "C:\caminho\blender\scripts\pilha\gerar_pilha_0601_1000.py"
```

O caminho real deve ser adaptado ao computador em que o projeto será executado.

## Atenção aos caminhos absolutos

Alguns scripts mantêm caminhos absolutos usados durante o desenvolvimento original. Antes de executar uma nova geração, revise principalmente:

- caminho do modelo 3D;
- pasta de saída das imagens;
- pasta de saída dos labels;
- intervalo inicial e final;
- quantidade esperada;
- semente;
- nome dos arquivos.

Não execute todos os scripts em sequência sem verificar as faixas, pois existem versões intermediárias e intervalos sobrepostos.

## Saídas esperadas

Cada lote produz duas pastas correspondentes:

```text
images/
labels/
```

Para cada imagem:

```text
images/nome_da_imagem.png
labels/nome_da_imagem.txt
```

O nome-base da imagem e do label deve ser exatamente o mesmo.

## Validação recomendada

Depois de gerar um lote, verifique:

- mesma quantidade de imagens e labels;
- ausência de arquivos vazios;
- classes dentro do intervalo de 0 a 3;
- cinco campos em cada linha;
- coordenadas entre 0 e 1;
- largura e altura maiores que zero;
- objetos visíveis e caixas corretamente posicionadas;
- ausência de nomes duplicados;
- distribuição adequada de posições, escalas e orientações.

A validação completa do dataset final também está registrada no notebook principal do projeto.

## Observações

- Os scripts foram desenvolvidos para reproduzir os lotes do projeto, não como uma biblioteca genérica.
- Algumas versões representam testes ou correções e foram mantidas para registrar o processo.
- Os arquivos `.blend1` são backups automáticos do Blender e não são necessários para executar os scripts.
- A geração completa pode demorar, principalmente na classe pilha.
- Alterações na versão do Blender podem mudar materiais, iluminação, importação de modelos e resultados de renderização.
