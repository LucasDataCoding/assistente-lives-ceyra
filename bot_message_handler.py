import asyncio
from twitchio.ext import commands
import os
import json
import websockets
from flask import Flask, send_from_directory, request, jsonify
import threading
import mimetypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask_cors import CORS
import time

app = Flask(__name__)

# Configure CORS
CORS(app, origins=["http://localhost:5000", "http://localhost:5173", "http://127.0.0.1:5000", "http://127.0.0.1:5173"])

# Configura MIME types manualmente
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('image/svg+xml', '.svg')

# Configurações globais
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'configs.json')

# Variável global para o bot
global_bot = None
bot_connected = False  # Nova variável para controlar estado do bot

class ConfigFileHandler(FileSystemEventHandler):
    """Monitora mudanças no arquivo de configuração"""
    
    def on_modified(self, event):
        if event.src_path == CONFIG_FILE:
            print("📁 Arquivo de configuração modificado")
            if global_bot:
                asyncio.run_coroutine_threadsafe(global_bot.broadcast_config_update(), global_bot.loop)

def load_bot_config():
    """Carrega as configurações do bot do arquivo configs.json"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Arquivo configs.json não encontrado. Criando padrão...")
        # Configuração padrão
        default_config = {
            "CHAT": {
                "CHAT_TOKEN": "oauth:YOUR_BOT_TOKEN_HERE",
                "BOT_USERNAME": "YOUR_BOT_NAME_HERE", 
                "PREFIX": "!",
                "CHANNEL": "YOUR_CHANNEL_NAME_LOWERCASE_HERE"
            }
        }
        # Salva o arquivo padrão
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config
    except Exception as e:
        print(f"❌ Erro ao carregar configs.json: {e}")
        return {}

@app.route('/')
def serve_vue_app():
    return send_from_directory('dist', 'index.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    response = send_from_directory('dist/assets', path)
    if path.endswith('.js'):
        response.headers.set('Content-Type', 'application/javascript')
    elif path.endswith('.css'):
        response.headers.set('Content-Type', 'text/css')
    elif path.endswith('.json'):
        response.headers.set('Content-Type', 'application/json')
    return response

@app.route('/<path:path>')
def serve_static(path):
    static_extensions = ['.js', '.css', '.json', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.woff', '.woff2', '.ttf', '.eot']
    
    if any(path.endswith(ext) for ext in static_extensions):
        if os.path.exists(f'dist/{path}'):
            response = send_from_directory('dist', path)
            if path.endswith('.js'):
                response.headers.set('Content-Type', 'application/javascript')
            elif path.endswith('.css'):
                response.headers.set('Content-Type', 'text/css')
            elif path.endswith('.json'):
                response.headers.set('Content-Type', 'application/json')
            elif path.endswith('.ico'):
                response.headers.set('Content-Type', 'image/x-icon')
            return response 
    
    return send_from_directory('dist', 'index.html')

# Rota para verificar status do bot
@app.route('/api/bot-status', methods=['GET'])
def get_bot_status():
    return jsonify({
        'connected': bot_connected,
        'message': 'Bot conectado ao Twitch' if bot_connected else 'Bot não conectado - Configure as credenciais'
    })

# Rota para OBTER configurações
@app.route('/api/configs', methods=['GET'])
def get_configs():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return jsonify(config_data)
    except FileNotFoundError:
        default_config = {
            "theme": "default",
            "settings": {},
            "chat": {
                "show_timestamps": True,
                "show_badges": True
            }
        }
        return jsonify(default_config)
    except Exception as e:
        return jsonify({"error": f"Erro ao ler configurações: {str(e)}"}), 500

# Rota para SALVAR configurações
@app.route('/api/configs', methods=['POST'])
def save_configs():
    try:
        new_configs = request.get_json()
        
        if not new_configs:
            return jsonify({"error": "Dados de configuração não fornecidos"}), 400
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_configs, f, indent=2, ensure_ascii=False)
        
        print("✅ Configurações salvas com sucesso")
        
        # Se o bot está rodando, reconecta com as novas credenciais
        if global_bot:
            asyncio.run_coroutine_threadsafe(global_bot.reconnect_with_new_config(), global_bot.loop)
            
        return jsonify({"message": "Configurações salvas com sucesso", "configs": new_configs})
    
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar configurações: {str(e)}"}), 500

def run_flask():
    print("🚀 Iniciando servidor Flask na porta 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

class ChatBot(commands.Bot):
    def __init__(self):
        # Carrega configurações do arquivo JSON
        bot_config = load_bot_config()
        chat_config = bot_config.get('CHAT', {})
        
        self.token = chat_config.get('CHAT_TOKEN', 'oauth:YOUR_BOT_TOKEN_HERE')
        self.nickname = chat_config.get('BOT_USERNAME', 'YOUR_BOT_NAME_HERE')
        self.channel_name = chat_config.get('CHANNEL', 'YOUR_CHANNEL_NAME_LOWERCASE_HERE')
        
        super().__init__(
            token=self.token,
            nick=self.nickname,
            prefix=chat_config.get('PREFIX', '!'),
            initial_channels=[self.channel_name]
        )
        self.websocket_clients = set()
        self.websocket_server = None
        self.file_observer = None
        self.loop = asyncio.get_event_loop()
        self.should_reconnect = True

    async def safe_connect(self):
        """Tenta conectar de forma segura, mesmo com credenciais inválidas"""
        global bot_connected
        
        try:
            # Verifica se as credenciais são padrão
            if (self.token == 'oauth:YOUR_BOT_TOKEN_HERE' or 
                self.nickname == 'YOUR_BOT_NAME_HERE' or 
                self.channel_name == 'YOUR_CHANNEL_NAME_LOWERCASE_HERE'):
                print("⚠️  Credenciais não configuradas. Servidor rodando em modo de configuração.")
                bot_connected = False
                return False
                
            print(f"🔗 Tentando conectar ao Twitch como {self.nickname}...")
            await self.start()
            bot_connected = True
            print(f'🎉 Bot conectado como {self.nickname}')
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar ao Twitch: {e}")
            print("⚠️  Servidor continuará rodando para configuração via interface web")
            bot_connected = False
            return False

    async def reconnect_with_new_config(self):
        """Reconecta com novas configurações"""
        global bot_connected
        
        print("🔄 Reconectando com novas configurações...")
        self.should_reconnect = False
        await self.close()
        
        # Recarrega configurações
        bot_config = load_bot_config()
        chat_config = bot_config.get('CHAT', {})
        
        self.token = chat_config.get('CHAT_TOKEN', 'oauth:YOUR_BOT_TOKEN_HERE')
        self.nickname = chat_config.get('BOT_USERNAME', 'YOUR_BOT_NAME_HERE')
        self.channel_name = chat_config.get('CHANNEL', 'YOUR_CHANNEL_NAME_LOWERCASE_HERE')
        
        self.should_reconnect = True
        await self.safe_connect()

    async def start_websocket_server(self):
        """Inicia o servidor WebSocket para comunicação com Vue.js"""
        async def websocket_handler(websocket):
            self.websocket_clients.add(websocket)
            print(f"👤 Cliente Vue.js conectado. Total: {len(self.websocket_clients)}")
            
            try:
                # Envia status do bot
                await websocket.send(json.dumps({
                    'type': 'bot_status',
                    'connected': bot_connected,
                    'message': 'Conectado ao Twitch' if bot_connected else 'Aguardando configuração'
                }))
                
                # Envia configurações atuais
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        current_config = json.load(f)
                    await websocket.send(json.dumps({
                        'type': 'config_update',
                        'configs': current_config
                    }))
                except Exception as e:
                    print(f"❌ Erro ao enviar configurações: {e}")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'config_save':
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.post(
                                    'http://localhost:5000/api/configs',
                                    json=data.get('configs'),
                                    headers={'Content-Type': 'application/json'}
                                ) as response:
                                    if response.status != 200:
                                        print("❌ Erro ao salvar configurações via WebSocket")
                    except json.JSONDecodeError:
                        print("❌ Mensagem WebSocket inválida")
            
            except websockets.exceptions.ConnectionClosed:
                print("👤 Cliente Vue.js desconectado")
            finally:
                self.websocket_clients.remove(websocket)

        self.websocket_server = await websockets.serve(
            websocket_handler, 
            "localhost", 
            8765
        )
        print("🚀 Servidor WebSocket iniciado em ws://localhost:8765")

    async def broadcast_config_update(self):
        """Envia atualização de configurações para todos os clientes"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
            
            message = {
                'type': 'config_update',
                'configs': current_config
            }
            
            await self.broadcast_to_vue(message)
        except Exception as e:
            print(f"❌ Erro ao enviar configurações: {e}")

    async def broadcast_to_vue(self, data):
        """Envia dados para todos os clientes Vue.js conectados"""
        if not self.websocket_clients:
            return

        message = json.dumps(data)
        for client in self.websocket_clients.copy():
            try:
                await client.send(message)
            except Exception as e:
                self.websocket_clients.discard(client)
                
    def start_file_watcher(self):
        """Inicia o observador de arquivos"""
        event_handler = ConfigFileHandler()
        self.file_observer = Observer()
        self.file_observer.schedule(event_handler, path=os.path.dirname(CONFIG_FILE), recursive=False)
        self.file_observer.start()
        print("👀 Observador de arquivos iniciado")

    async def event_ready(self):
        """Evento quando o bot se conecta com sucesso"""
        global bot_connected
        bot_connected = True
        print(f'🎉 Bot conectado como {self.nick}')
        self.start_file_watcher()
        await self.start_websocket_server() 
        
        # Anuncia status para todos os clientes
        await self.broadcast_to_vue({
            'type': 'bot_status',
            'connected': True,
            'message': f'Conectado como {self.nick}'
        })

    async def event_error(self, error):
        """Evento quando ocorre um erro no bot"""
        global bot_connected
        bot_connected = False
        print(f"❌ Erro no bot: {error}")
        
        # Anuncia status de erro para clientes
        await self.broadcast_to_vue({
            'type': 'bot_status',
            'connected': False,
            'message': f'Erro de conexão: {str(error)}'
        })

    async def event_message(self, message):
        """Processa mensagens do chat"""
        if message.echo:
            return
        
        data = {
            'channel': message.channel.name,
            'username': message.author.name,
            'message_color': message.author.color,
            'message': message.content,
            'timestamp': str(getattr(message, 'timestamp', '')),
            'type': 'chat_message'
        }
        
        print(f"📨 Mensagem recebida: {message.author.name}: {message.content}")
        print(f"👥 Clientes WebSocket conectados: {len(self.websocket_clients)}")
        
        await self.broadcast_to_vue(data)
        await self.handle_commands(message)

    def reload_config(self):
        """Recarrega as configurações do arquivo"""
        self.config_data = load_bot_config()
        return self.config_data
    @commands.command(name='youtube')
    async def youtube_command(self, ctx):
        """Comando !youtube - Mostra o link do YouTube"""
        config = self.reload_config()
        youtube_link = config.get('linkYoutube', '')
        
        if youtube_link:
            await ctx.send(f"📺 Inscreva-se no nosso YouTube: {youtube_link}")
        else:
            await ctx.send("🔗 Link do YouTube não configurado. Use !comandos para ver todos os links.")


    @commands.command(name='youtube')
    async def youtube_command(self, ctx):
        await ctx.send("🔗 Baixe o projeto para utilizar o tema em: https://github.com/LucasDataCoding/assistente-lives-ceyra. Use !comandos para ver todos os links.")

    @commands.command(name='discord')
    async def discord_command(self, ctx):
        """Comando !discord - Mostra o link do Discord"""
        config = self.reload_config()
        discord_link = config.get('linkDiscord', '')
        
        if discord_link:
            await ctx.send(f"🎮 Entre no nosso Discord: {discord_link}")
        else:
            await ctx.send("🔗 Link do Discord não configurado. Use !comandos para ver todos os links.")

    @commands.command(name='twitch')
    async def twitch_command(self, ctx):
        """Comando !twitch - Mostra o link da Twitch"""
        config = self.reload_config()
        twitch_link = config.get('linkTwitch', '')
        
        if twitch_link:
            await ctx.send(f"🎥 Siga nossa Twitch: {twitch_link}")
        else:
            await ctx.send("🔗 Link da Twitch não configurado. Use !comandos para ver todos os links.")

    @commands.command(name='comandos', aliases=['commands', 'ajuda', 'help'])
    async def commands_command(self, ctx):
        """Comando !comandos - Mostra todos os comandos disponíveis"""
        config = self.reload_config()
        
        response = "📋 Comandos disponíveis: "
        commands_list = []
        
        # Verifica cada comando e adiciona se estiver configurado
        youtube_link = config.get('linkYoutube', '')
        discord_link = config.get('linkDiscord', '')
        twitch_link = config.get('linkTwitch', '')
        
        if youtube_link:
            commands_list.append("!youtube")
        if discord_link:
            commands_list.append("!discord")
        if twitch_link:
            commands_list.append("!twitch")
        
        # Adiciona comandos fixos
        commands_list.extend(["!comandos", "!ajuda"])
        
        response += " | ".join(commands_list)
        
        # Adiciona informações adicionais se configurado
        highlight_text = config.get('highlightText', '')
        if highlight_text:
            response += f" | {highlight_text}"
        
        await ctx.send(response)

    @commands.command(name='configtest')
    async def config_test_command(self, ctx):
        """Comando de teste para verificar as configurações carregadas"""
        config = self.reload_config()
        
        # Mostra apenas informações não sensíveis
        response = "⚙️ Configurações carregadas: "
        response += f"YouTube: {'✅' if config.get('linkYoutube') else '❌'} | "
        response += f"Discord: {'✅' if config.get('linkDiscord') else '❌'} | "
        response += f"Twitch: {'✅' if config.get('linkTwitch') else '❌'}"
        
        await ctx.send(response)
    # ... (comandos existentes)

async def main():
    # Inicia Flask em thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Aguarda o Flask iniciar
    time.sleep(2)
    
    # Cria e inicia o bot
    bot = ChatBot()
    global global_bot
    global_bot = bot
    
    print("🌐 Servidor Flask rodando em http://localhost:5000")
    print("📋 Acesse http://localhost:5000 para configurar o bot")
    print("⚡ Iniciando bot Twitch...")
    
    # SEMPRE inicia o WebSocket, independente da conexão do bot
    print("🔌 Iniciando WebSocket...")
    await bot.start_websocket_server()
    bot.start_file_watcher()
    
    # Tenta conectar o bot (mesmo que falhe, o servidor continua)
    connection_success = await bot.safe_connect()
    
    if connection_success:
        print("✅ Bot conectado ao Twitch com sucesso")
    else:
        print("⚠️  Bot não conectado ao Twitch - Modo configuração")
    
    try:
        # Mantém o loop rodando
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Desligando servidor...")
        if bot.file_observer:
            bot.file_observer.stop()
            bot.file_observer.join()
            
if __name__ == "__main__":
    asyncio.run(main())