# Azure Function: Extrator de Metadados de Fotos

Este projeto implementa uma **Azure Function** em Python que recebe o link de uma imagem armazenada (por exemplo, no OneDrive), baixa a foto, extrai os metadados EXIF (data/hora, latitude e longitude) e retorna essas informações num formato JSON. O projeto utiliza o modelo novo de função do Azure, baseado no arquivo `function_app.py` e decoradores, facilitando a definição e a configuração de triggers.

## Visão Geral

Quando você recebe um e-mail com uma foto como anexo e salva esse anexo no OneDrive, um fluxo no Power Automate pode capturar o link da imagem e chamar esta função HTTP. A função baixa a imagem no link fornecido, extrai os metadados EXIF disponíveis (como data e hora da foto e coordenadas de latitude/longitude) e devolve esses dados para o fluxo, permitindo que você os utilize em etapas posteriores do seu processo de automação.

## Estrutura do Projeto

A estrutura básica do repositório é:

```
/ (raiz)
├── host.json             # Configurações da runtime do Functions
├── local.settings.json   # Configurações locais (não deve ser incluído no controle de versão)
├── requirements.txt      # Lista de dependências Python
├── README.md             # Este arquivo de documentação
└── function_app.py       # Implementação da Azure Function usando o novo modelo
```

No modelo clássico haveria uma pasta por função contendo `__init__.py` e `function.json`, mas no modelo novo o ponto de entrada único e os decorators definem comportamentos diferentes e não são necessárias pastas adicionais para a função.

## Pré-requisitos

Para trabalhar com este projeto, você precisará de:

- Python 3.9 ou superior instalado no seu sistema
- [VS Code](https://code.visualstudio.com/) ou outro editor de sua preferência
- Extensões do Azure Functions instaladas no VS Code
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) instalado para autenticação (embora a publicação possa ser feita sem CLI diretamente pelo VS Code)
- [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local) para execução local
- Uma conta do Azure com uma assinatura ativa (por exemplo, uma assinatura do tipo Visual Studio) e, se necessário, com autenticação multifator configurada
- [Pip](https://pip.pypa.io/en/stable/) disponível para instalar dependências

## Configuração Inicial

1. Clone o repositório ou baixe o código para o seu computador.
2. Entre na pasta do projeto:
   ```bash
   cd <diretório_do_projeto>
   ```
3. Crie e ative um ambiente virtual Python:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # no Linux/macOS
   .\.venv\Scripts\activate  # no Windows (PowerShell)
   ```
4. Instale as dependências usando o pip com o arquivo `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

## Execução e Teste Local

Com o ambiente virtual ativo e as dependências instaladas, você pode rodar a função localmente:

```bash
func start
```

Este comando inicia o runtime do Azure Functions em sua máquina local. Por padrão, a função ficará disponível em http://localhost:7071. Use uma chamada `curl` ou acesse via navegador para testar, passando o parâmetro `fileUrl` com o link da imagem:

```bash
curl "http://localhost:7071/api/GetPhotoMetadata?fileUrl=<URL_DA_IMAGEM>"
```

Ou use o Postman ou outro cliente HTTP para enviar uma requisição GET ou POST. Para o POST você pode enviar o JSON no body:

```json
{
    "fileUrl": "<URL_DA_IMAGEM>"
}
```

Verifique a resposta em JSON com os campos `date_time`, `latitude` e `longitude`.

## Publicação no Azure usando o VS Code

1. No VS Code, instale a extensão **Azure Functions** caso ainda não tenha feito.
2. Faça login no Azure pela extensão (ícone do Azure na barra lateral e clique em "Sign in to Azure"). Se sua conta usar MFA, siga as instruções no navegador ou use `az login --use-device-code` na CLI antes.
3. No painel do Azure Functions no VS Code, clique na opção de criar um novo Function App: "Create Function App in Azure". Escolha um nome globalmente único, runtime Python (3.9+), sistema operacional (Linux é recomendado) e plano de consumo.
4. Depois de criado, use o comando do VS Code: **Azure Functions: Deploy to Function App**. Selecione sua aplicação recém-criada. O VS Code compactará o projeto e fará o upload.
5. Ao final da publicação, será exibida a URL básica da função, como:
   ```text
   https://<nome_da_app>.azurewebsites.net/api/GetPhotoMetadata
   ```
   Se o nível de autorização for `function`, adicione o código de acesso (key) como parâmetro: `?code=<sua_function_key>` (que pode ser obtida no portal do Azure, menu "Manage").

## Configuração de CI/CD com GitHub Actions

Você pode automatizar o deploy da função toda vez que fizer push no GitHub:

1. Inicialize o repositório Git local (se ainda não iniciou):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <URL_DO_REPOSITORIO_GITHUB>
   git push -u origin main
   ```
2. No portal do Azure, abra sua Function App, acesse a seção **Deployment Center** e configure como fonte o seu repositório GitHub e o branch desejado. Isso criará um workflow de GitHub Actions automaticamente e implantará o código a cada push naquele branch.
3. Opcionalmente, você pode criar manualmente um arquivo de workflow no repositório `.github/workflows/azure-functions-deploy.yml` com o seguinte conteúdo de exemplo:
   ```yaml
   name: Build and deploy Python Azure Function

   on:
     push:
       branches:
         - main

   jobs:
     build-and-deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: '3.9'
         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip
             pip install -r requirements.txt
         - name: 'Deploy to Azure Functions'
           uses: Azure/functions-action@v1
           with:
             app-name: '<NOME_DA_SUA_FUNCTION_APP>'
             package: '.'
   ```
   Substitua `<NOME_DA_SUA_FUNCTION_APP>` pelo nome real da sua Function App no Azure.

## Integração com Power Automate

Após publicar a função no Azure, você poderá integrá-la em um fluxo do Power Automate:

1. No Power Automate, crie um fluxo que seja disparado quando você recebe um e-mail com um anexo. Utilize o conector do Office 365 Outlook, por exemplo, para capturar o anexo.
2. Utilize a ação para salvar o anexo no OneDrive ou SharePoint e recupere o link de acesso ao arquivo gerado por essa ação.
3. Insira uma ação **HTTP** no fluxo e configure:
   - **Método**: GET (ou POST caso prefira enviar no body)
   - **URI**: `https://<nome_da_app>.azurewebsites.net/api/GetPhotoMetadata?fileUrl=<link_do_OneDrive>`
   - Caso sua Azure Function exija chave (se authorization level for `function`) acrescente `&code=<sua_function_key>`.
4. Analise a resposta JSON da ação HTTP usando expressões do Power Automate, por exemplo `body('HTTP')['latitude']` para pegar a latitude, e use esses valores em etapas subsequentes no seu fluxo (como gravar numa planilha, enviar um e-mail, etc.).

---

Esse README fornece todas as instruções necessárias para você configurar, testar, publicar e integrar sua Azure Function de extração de metadados de fotos. Se precisar de mais detalhes, consulte a [documentação oficial do Azure Functions](https://docs.microsoft.com/azure/azure-functions/).