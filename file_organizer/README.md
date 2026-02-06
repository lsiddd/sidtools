# File Organizer

Uma ferramenta CLI abrangente em Python para organizar arquivos e diretórios. Oferece múltiplos modos para gerenciar sistemas de arquivos, incluindo localização e movimentação de repositórios Git, remoção de arquivos temporários ou de build indesejados, organização de arquivos por tipo em pastas categorizadas, detecção e remoção de duplicatas, e monitoramento de diretórios em tempo real.

Recursos incluem resolução de conflitos, limitação de profundidade, manipulação de itens ocultos, modo dry-run para pré-visualização segura das ações, e sistema de undo para reverter operações.

## Instalação

### Com uv (Recomendado)

```bash
# Instalar dependências
uv sync

# Instalar em modo desenvolvimento
uv pip install -e .

# Ou instalar com dependências de desenvolvimento para testes
uv pip install -e ".[dev]"
```

## Uso

A ferramenta fornece sete subcomandos principais: `git`, `cleanup`, `organize`, `dedup`, `watch`, `undo` e `history`.

### Executando com uv

Todas as operações podem ser executadas com `uv run`:

```bash
# Executar diretamente
uv run file-organizer <comando> [opções]

# Ou como módulo Python
uv run python -m file_organizer <comando> [opções]
```

---

## Modo Git

Localiza e move repositórios Git para uma localização centralizada.

```bash
uv run file-organizer git --source <dir_origem> --destination <dir_destino> [opções]
```

### Opções:
- `--source, -s`: O diretório para escanear em busca de repositórios git. **Obrigatório.** Pode ser especificado múltiplas vezes.
- `--destination, -d`: O diretório de destino (repos vão para `DEST/git/`). **Obrigatório.**
- `--dry-run, -n`: Simular sem fazer alterações.
- `--yes, -y`: Pular prompts de confirmação (para automação).
- `--include-hidden, -a`: Incluir diretórios ocultos na busca.
- `--conflict-resolution, -c`: Estilo de resolução de conflitos (`number`, `timestamp`, `uuid`). Padrão: `number`.
- `--cleanup-empty-dirs`: Remover diretórios vazios após o processamento.
- `--verbose, -v`: Habilitar saída detalhada.

### Exemplos:

```bash
# Dry run: Ver quais repositórios git seriam movidos
uv run file-organizer git -s ~/projetos -d ~/organizados --dry-run

# Mover repositórios git de múltiplas origens
uv run file-organizer git -s ~/projetos -s ~/documentos -d ~/organizados

# Mover com limpeza de diretórios vazios
uv run file-organizer git -s ~/projetos -d ~/organizados --cleanup-empty-dirs
```

---

## Modo Cleanup

Remove arquivos e diretórios indesejados (cache, artefatos de build, etc.).

```bash
uv run file-organizer cleanup --source <dir_origem> [opções]
```

### Opções:
- `--source, -s`: O diretório para escanear em busca de itens indesejados. **Obrigatório.** Pode ser especificado múltiplas vezes.
- `--dry-run, -n`: Simular sem fazer alterações.
- `--yes, -y`: Pular prompts de confirmação (para automação).
- `--include-hidden, -a`: Incluir arquivos e diretórios ocultos.
- `--verbose, -v`: Habilitar saída detalhada.

### Padrões removidos por padrão:
- **Python:** `__pycache__`, `.venv`, `venv`, `.pyc`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`
- **Node.js:** `node_modules`
- **Build:** `target`, `build`, `dist`, `.cache`
- **Editor:** `.swp`, `.swo`, `~` (arquivos de backup)
- **OS:** `Thumbs.db`, `.DS_Store`, `.Trash`

### Exemplos:

```bash
# Dry run: Ver o que seria removido
uv run file-organizer cleanup -s ~/projetos --dry-run

# Limpar múltiplos diretórios
uv run file-organizer cleanup -s ~/projetos -s ~/downloads

# Limpar com confirmação automática
uv run file-organizer cleanup -s ~/projetos -y
```

---

## Modo Organize

Organiza arquivos por tipo em subdiretórios categorizados.

```bash
uv run file-organizer organize --source <dir_origem> --destination <dir_destino> [opções]
```

### Opções:
- `--source, -s`: O diretório a organizar. **Obrigatório.** Pode ser especificado múltiplas vezes.
- `--destination, -d`: O diretório de destino para arquivos organizados. **Obrigatório.**
- `--max-depth, -m`: Profundidade máxima de recursão. Diretórios na profundidade máxima são movidos inteiros.
- `--dry-run, -n`: Simular sem fazer alterações.
- `--yes, -y`: Pular prompts de confirmação (para automação).
- `--include-hidden, -a`: Incluir arquivos e diretórios ocultos.
- `--conflict-resolution, -c`: Estilo de resolução de conflitos (`number`, `timestamp`, `uuid`). Padrão: `number`.
- `--cleanup-empty-dirs`: Remover diretórios vazios após o processamento.
- `--verbose, -v`: Habilitar saída detalhada.

### Categorias de arquivos:
- `videos/`: mp4, mkv, avi, mov, webm, etc.
- `audio/`: mp3, wav, flac, aac, ogg, etc.
- `images/`: jpg, png, gif, bmp, webp, svg, etc.
- `documents/pdf/`, `documents/word/`, `documents/excel/`, `documents/text/`
- `archives/`: zip, tar, gz, rar, 7z, etc.
- `code/python/`, `code/javascript/`, `code/go/`, etc.
- `databases/`: sqlite, sql, db
- `fonts/`: ttf, otf, woff, woff2
- `disk_images/`: iso, img, vhd, vmdk
- `stuff/`: Arquivos com extensões desconhecidas
- `directories/`: Diretórios na profundidade máxima

### Exemplos:

```bash
# Dry run: Pré-visualizar organização
uv run file-organizer organize -s ~/downloads -d ~/organizados --dry-run

# Organizar com limite de profundidade (subdiretórios na profundidade 2+ movidos inteiros)
uv run file-organizer organize -s ~/downloads -d ~/organizados --max-depth 2

# Organizar com resolução de conflitos por timestamp
uv run file-organizer organize -s ~/downloads -d ~/organizados -c timestamp --cleanup-empty-dirs

# Organizar múltiplas origens
uv run file-organizer organize -s ~/downloads -s ~/temp -d ~/organizados
```

---

## Modo Dedup

Localiza e remove arquivos duplicados usando hash de conteúdo.

```bash
uv run file-organizer dedup --source <dir_origem> [opções]
```

### Opções:
- `--source, -s`: O diretório para escanear. **Obrigatório.** Pode ser especificado múltiplas vezes.
- `--destination, -d`: Mover duplicatas para cá ao invés de deletar (opcional).
- `--keep, -k`: Estratégia para qual arquivo manter: `oldest`, `newest`, `shortest_path`, `longest_path`, `first`. Padrão: `oldest`.
- `--min-size`: Tamanho mínimo do arquivo em bytes a considerar (padrão: 1).
- `--dry-run, -n`: Simular sem fazer alterações.
- `--yes, -y`: Pular prompts de confirmação (para automação).
- `--include-hidden, -a`: Incluir arquivos ocultos.
- `--verbose, -v`: Habilitar saída detalhada.

### Exemplos:

```bash
# Dry run: Ver quais arquivos são duplicados
uv run file-organizer dedup -s ~/downloads --dry-run

# Remover duplicatas mantendo o arquivo mais recente
uv run file-organizer dedup -s ~/downloads --keep newest

# Mover duplicatas para um diretório ao invés de deletar
uv run file-organizer dedup -s ~/downloads -d ~/duplicatas

# Deduplicar apenas arquivos maiores que 1MB
uv run file-organizer dedup -s ~/downloads --min-size 1048576
```

---

## Modo Watch

Monitora um diretório e organiza novos arquivos em tempo real.

```bash
uv run file-organizer watch --source <dir_origem> --destination <dir_destino> [opções]
```

### Opções:
- `--source, -s`: Diretório para monitorar novos arquivos. **Obrigatório.**
- `--destination, -d`: Diretório de destino para arquivos organizados. **Obrigatório.**
- `--include-hidden, -a`: Incluir arquivos ocultos.
- `--conflict-resolution, -c`: Estilo de resolução de conflitos (`number`, `timestamp`, `uuid`). Padrão: `number`.
- `--delay`: Segundos para aguardar após criação do arquivo antes de mover (padrão: 1.0).
- `--verbose, -v`: Habilitar saída detalhada.

### Exemplos:

```bash
# Monitorar diretório de downloads e organizar automaticamente
uv run file-organizer watch -s ~/downloads -d ~/organizados

# Monitorar com delay maior (útil para downloads grandes)
uv run file-organizer watch -s ~/downloads -d ~/organizados --delay 5.0
```

---

## Modo Undo

Desfaz uma sessão de operação anterior (restaura arquivos movidos).

```bash
uv run file-organizer undo [session_id] [opções]
```

### Opções:
- `session_id`: ID da sessão para desfazer (padrão: mais recente).
- `--dry-run, -n`: Simular sem fazer alterações.
- `--yes, -y`: Pular prompts de confirmação (para automação).
- `--verbose, -v`: Habilitar saída detalhada.

### Exemplos:

```bash
# Desfazer a operação mais recente
uv run file-organizer undo

# Desfazer uma sessão específica
uv run file-organizer undo abc123def456

# Dry run para ver o que seria desfeito
uv run file-organizer undo --dry-run
```

---

## Modo History

Mostra histórico de sessões de operação.

```bash
uv run file-organizer history [opções]
```

### Opções:
- `--limit, -l`: Número máximo de sessões para mostrar (padrão: 20).
- `--verbose, -v`: Mostrar contagens detalhadas de operações.

### Exemplos:

```bash
# Ver histórico de operações
uv run file-organizer history

# Ver apenas as 5 mais recentes
uv run file-organizer history --limit 5

# Ver com detalhes
uv run file-organizer history --verbose
```

---

## Configuração

A ferramenta usa `config.yaml` para personalizar mapeamentos de extensões e padrões indesejados. O arquivo de configuração é procurado em:
1. Diretório do pacote
2. Diretório de trabalho atual

Veja `config.yaml` para a lista completa de opções configuráveis.

---

## Desenvolvimento

### Executando Testes

```bash
# Executar todos os testes
uv run pytest tests/ -v

# Executar arquivo de teste específico
uv run pytest tests/test_utils.py -v

# Executar com cobertura
uv run pytest tests/ --cov=file_organizer
```

### Verificação de Tipos

```bash
uv run mypy file_organizer/
```

### Linting

```bash
uv run ruff check file_organizer/
```

---

## Estrutura do Projeto

```
file_organizer/
├── file_organizer/
│   ├── __init__.py
│   ├── __main__.py          # Ponto de entrada para python -m
│   ├── cli.py               # Comandos CLI Typer
│   ├── config.py            # Gerenciamento de configuração
│   ├── logger.py            # Utilitários de logging
│   ├── utils.py             # Utilitários compartilhados
│   ├── detection.py         # Detecção inteligente de tipo de arquivo
│   ├── metadata.py          # Extração de metadados
│   ├── operations.py        # Sistema de undo/redo
│   ├── parallel.py          # Processamento paralelo
│   ├── rules.py             # Sistema de regras customizáveis
│   └── modes/
│       ├── __init__.py
│       ├── git.py           # Implementação do modo Git
│       ├── cleanup.py       # Implementação do modo Cleanup
│       ├── organize.py      # Implementação do modo Organize
│       ├── dedup.py         # Implementação do modo Dedup
│       ├── watch.py         # Implementação do modo Watch
│       └── date_organize.py # Organização por data
├── tests/
│   ├── __init__.py
│   ├── test_utils.py
│   ├── test_git.py
│   ├── test_cleanup.py
│   └── test_organize.py
├── config.yaml              # Configuração externa
├── pyproject.toml           # Metadados e dependências do projeto
└── README.md
```

---

## Recursos Avançados

### Detecção Inteligente de Arquivos

A ferramenta usa múltiplas técnicas para identificar tipos de arquivo:
- Análise de extensão
- Detecção de tipo MIME usando `python-magic`
- Análise de metadados com `mutagen` (áudio) e `Pillow` (imagens)
- Hash de conteúdo usando `xxhash` para detecção de duplicatas

### Sistema de Undo

Todas as operações (exceto modo watch) são registradas e podem ser desfeitas:
- Cada sessão de operação recebe um ID único
- Metadados de operações são armazenados em `~/.file-organizer/sessions/`
- Use `history` para ver operações anteriores
- Use `undo` para reverter alterações

### Resolução de Conflitos

Quando um arquivo de destino já existe, três estratégias estão disponíveis:
- `number`: Adiciona um número ao nome do arquivo (ex: `arquivo (1).txt`)
- `timestamp`: Adiciona um timestamp (ex: `arquivo_20260206_143022.txt`)
- `uuid`: Adiciona um UUID curto (ex: `arquivo_a1b2c3d4.txt`)

---

## Aviso

Use a opção `--dry-run` extensivamente antes de executar qualquer modo sem ela, pois esta ferramenta realiza operações de movimentação e exclusão potencialmente irreversíveis. Certifique-se de ter backups. Links simbólicos na origem são ignorados.

---

## Licença

MIT
