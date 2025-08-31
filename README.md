# Assistente de Lives Ceyra

![Logo do Assistente de Lives Ceyra](dist/favicon.ico)

Um bot de chat personalizável para Twitch que rastreia o uso de comandos e persiste dados em formato JSON. Perfeito para streamers que querem engajar com sua audiência!

## Guia de Configuração 🛠️

### 1. Pré-requisitos
- 1.1 Python 3.8 ou superior
- 1.2 Conta na Twitch (para o bot)
- 1.3 [Token de Acesso do Bot](https://twitchtokengenerator.com)

### 2. Configuração
Crie ou modifique o arquivo `.config` na pasta fora do diretório do projeto:

```ini
[CHAT]
CHAT_TOKEN = oauth:SEU_TOKEN_DO_BOT_AQUI
CHANNELS = [SEU_CANAL_EM_MINUSCULO_AQUI]
PREFIX = !
BOT_USERNAME = SEU_NOME_DO_BOT_AQUI
CLIENT_ID = OPCIONAL_SEU_CLIENT_ID_AQUI  # Apenas para funcionalidades avançadas
```

**Como obter esses valores:**
- `CHAT_TOKEN`: Gere em [Twitch Token Generator](https://twitchtokengenerator.com) (selecione "Bot Chat Token")
- `CHANNELS`: Seu nome de canal da Twitch em minúsculo (ex: `["lucasdatacoding"]`)
- `BOT_USERNAME`: Nome de usuário da conta do bot

### 3. Instalação ✨

## Instalação
- 1.1 Baixe este projeto [Clicando Aqui](https://github.com/LucasDataCoding/assistente-lives-ceyra/archive/refs/heads/main.zip)
- 1.2 Extraia os arquivos zipados do passo 1.1
- 1.3 Baixe o Python [Clicando Aqui](https://www.python.org/downloads/)

# Instale as dependências
pip install -r requirements.txt

## Executando o Bot 🚀
Dentro do projeto, abra o terminal e execute:
```
python bot.py
ou
py bot.py
ou 
python3 bot.py
```

## Personalização 🎨
### Adicionar novos comandos:
Edite `bot.py` e adicione novos manipuladores de comandos:
```python
@commands.command()
async def seucomando(self, ctx: commands.Context):
    await ctx.send("Sua resposta personalizada!")
```

## Solução de Problemas 🔧
| Problema | Solução |
|----------|---------|
| Bot conecta mas não responde | Verifique se o token tem permissões `chat:read` e `chat:write` |
| "Falha na autenticação de login" | Gere um novo token OAuth |
| Comandos funcionam mas nenhuma mensagem é enviada | Adicione o bot como moderador: `/mod NOME_DO_SEU_BOT` |

## Licença 📄
Licença MIT - Sinta-se livre para modificar e distribuir!

---

**Boas Lives!** 🎮📺  
*Se você gostou deste bot, considere dar uma estrela no repositório!*
