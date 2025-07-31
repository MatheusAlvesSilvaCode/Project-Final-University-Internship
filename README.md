# Sistema de Visualização de Eventos Sísmicos

Este repositório contém o código-fonte de uma aplicação web desenvolvida com [Dash](https://dash.plotly.com/) para visualização interativa de eventos sísmicos captados por estações de monitoramento. A aplicação permite o carregamento de dados armazenados no [MinIO](https://min.io/), aplicação de filtros temporais e categóricos, geração de gráficos analíticos e exportação de relatórios em PDF e TXT.

---

## Funcionalidades Principais

- **Filtragem de eventos por data e tipo** (Ruído, Local, Global)
- **Visualização gráfica** de:
  - Séries temporais por estação e direção (T, R, V)
  - Espectros de frequência (FFT)
- **Tabelas dinâmicas** com estatísticas por estação
- **Classificação automática de eventos**
- **Mapa interativo da barragem**
- **Exportação de relatórios** em PDF
- **Exportação de dados brutos** em ficheiros `.txt`

---

## Tecnologias Utilizadas

| Tecnologia        | Descrição                                       |
|-------------------|------------------------------------------------|
| Python 3.x        | Linguagem principal                            |
| Dash + Plotly     | Interface web e gráficos interativos           |
| Dash Bootstrap    | Componentes de layout responsivos              |
| Pandas            | Manipulação e análise de dados                 |
| MinIO             | Object Storage para dados sísmicos             |
| PDFKit + wkhtmltopdf | Geração de relatórios em PDF              |

---

## Estrutura do Projeto
├── home.py # Página inicial com filtros e pré-visualização
├── main.py # Página de relatórios e exportação
├── minio_loader.py # Funções de conexão e extração do MinIO
├── assets/ # Imagens
├── templates/ # HTMLs para geração de PDF
├── requirements.txt # Dependências do projeto
└── README.md # Este ficheiro

---

## 🚀 Como Executar Localmente

1. **Clone o repositório**
   ```bash
   git clone https://gitlab.com/seu-usuario/nome-do-repositorio.git
   cd nome-do-repositorio

2. **Crie e ative o ambiente virtual**
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

3. **Instale as dependências** 
pip install -r requirements.txt

4. **Configure suas credenciais do MinIO (opcional: .env ou direto no código)**

5. **Execute a aplicação**
python main.py




Relatório Técnico
O relatório técnico completo encontra-se no ficheiro Relatorio Dash Projeto.pdf, contendo:

Explicação por módulos (home.py, main.py, minio_loader.py)

Fluxo de dados e arquitetura do sistema

Justificativa e objetivos do projeto

Capturas de tela e estrutura de visualização

Conclusão e referências

 Manual do Utilizador
1. Página Inicial
Selecione o tipo de evento e o intervalo de datas

Clique em “Buscar Eventos”

Os eventos aparecerão em cartões coloridos

Clique em um cartão para ver o relatório

2. Página de Relatório
A aba “Resumo” mostra dados gerais do evento

Cada aba de estação traz:

Séries temporais (T, R, V)

Espectros de frequência

Tabelas com os maiores picos

Exporte os dados em PDF ou TXT

3. Mapa da Barragem
Visualize as localizações das estações

Interaja com o SVG da barragem para facilitar análises espaciais

 Requisitos
Python ≥ 3.8

Acesso à instância MinIO com dados sísmicos

Ferramenta wkhtmltopdf instalada (necessária para gerar PDF)

Contato
Autor: Matheus Silva
Email: [masilva@lnec.pt]
GitLab: https://gitlab.com/matheus.silva33

