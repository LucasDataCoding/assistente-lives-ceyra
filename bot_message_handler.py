import asyncio
from twitchio.ext import commands
import os
import configparser
import json
import websockets
from flask import Flask, send_from_directory, request, jsonify
import threading
import mimetypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask_cors import CORS

# Load configuration from .config file
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', '.config'))
app = Flask(__name__)

# Configure CORS para permitir requisições do frontend
CORS(app, origins=["http://localhost:5000", "http://localhost:5173", "http://127.0.0.1:5000", "http://127.0.0.1:5173"])

# Configura MIME types manualmente
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('image/svg+xml', '.svg')

# Configurações globais
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'configs.json')

# Variável global para o bot (vamos acessá-la no event handler)
global_bot = None

class ConfigFileHandler(FileSystemEventHandler):
    """Monitora mudanças no arquivo de configuração"""
    
    def on_modified(self, event):
        if event.src_path == CONFIG_FILE:
            print("📁 Arquivo de configuração modificado")
            # Usamos call_soon_threadsafe para executar no event loop correto
            if global_bot:
                asyncio.run_coroutine_threadsafe(global_bot.broadcast_config_update(), global_bot.loop)

@app.route('/')
def serve_vue_app():
    return send_from_directory('dist', 'index.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve arquivos da pasta assets com MIME types corretos"""
    response = send_from_directory('dist/assets', path)
    
    # Define MIME types corretos
    if path.endswith('.js'):
        response.headers.set('Content-Type', 'application/javascript')
    elif path.endswith('.css'):
        response.headers.set('Content-Type', 'text/css')
    elif path.endswith('.json'):
        response.headers.set('Content-Type', 'application/json')
    
    return response

@app.route('/<path:path>')
def serve_static(path):
    """Serve outros arquivos estáticos"""
    static_extensions = ['.js', '.css', '.json', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.woff', '.woff2', '.ttf', '.eot']
    
    # Verifica se é um arquivo estático
    if any(path.endswith(ext) for ext in static_extensions):
        if os.path.exists(f'dist/{path}'):
            response = send_from_directory('dist', path)
            
            # Define MIME types
            if path.endswith('.js'):
                response.headers.set('Content-Type', 'application/javascript')
            elif path.endswith('.css'):
                response.headers.set('Content-Type', 'text/css')
            elif path.endswith('.json'):
                response.headers.set('Content-Type', 'application/json')
            elif path.endswith('.ico'):
                response.headers.set('Content-Type', 'image/x-icon')
            
            return response 
    
    # Para todas as outras rotas, serve index.html (Vue Router)
    return send_from_directory('dist', 'index.html')

# Rota para OBTER configurações
@app.route('/api/configs', methods=['GET'])
def get_configs():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return jsonify(config_data)
    except FileNotFoundError:
        # Retorna configurações padrão se o arquivo não existir
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
        
        # Salva no arquivo
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_configs, f, indent=2, ensure_ascii=False)
        
        print("✅ Configurações salvas com sucesso")
        return jsonify({"message": "Configurações salvas com sucesso", "configs": new_configs})
    
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar configurações: {str(e)}"}), 500

def run_flask():
    """Executa o servidor Flask em uma thread separada"""
    print("🚀 Iniciando servidor Flask na porta 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

class ChatBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config.get('CHAT', 'CHAT_TOKEN', fallback='oauth:YOUR_BOT_TOKEN_HERE'),
            nick=config.get('CHAT', 'BOT_USERNAME', fallback='YOUR_BOT_NAME_HERE'),
            prefix=config.get('CHAT', 'PREFIX', fallback='!'),
            initial_channels=[config.get('CHAT', 'CHANNEL', fallback='YOUR_CHANNEL_NAME_LOWERCASE_HERE')]
        )
        self.websocket_clients = set()
        self.websocket_server = None
        self.file_observer = None
        self.loop = asyncio.get_event_loop()

    async def start_websocket_server(self):
        """Inicia o servidor WebSocket para comunicação com Vue.js"""
        async def websocket_handler(websocket):
            self.websocket_clients.add(websocket)
            print(f"👤 Cliente Vue.js conectado. Total: {len(self.websocket_clients)}")
            
            try:
                # Envia as configurações atuais para o novo cliente
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        current_config = json.load(f)
                    await websocket.send(json.dumps({
                        'type': 'config_update',
                        'configs': current_config
                    }))
                    print("📤 Configurações iniciais enviadas para novo cliente")
                except Exception as e:
                    print(f"❌ Erro ao enviar configurações iniciais: {e}")
                
                async for message in websocket:
                    # Processar mensagens do Vue aqui se necessário
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'config_save':
                            # Salva as configurações via HTTP
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
            
            print(f"📤 Enviando atualização de configurações: {json.dumps(message)}")
            
            await self.broadcast_to_vue(message)
            print("📤 Configurações enviadas para clientes WebSocket")
        except Exception as e:
            print(f"❌ Erro ao enviar configurações: {e}")

    async def broadcast_to_vue(self, data):
        """Envia dados para todos os clientes Vue.js conectados"""
        if not self.websocket_clients:
            print("❌ Nenhum cliente WebSocket conectado")
            return

        message = json.dumps(data)
        print(f"👥 Clientes conectados: {len(self.websocket_clients)}")
        
        for client in self.websocket_clients.copy():
            try:
                await client.send(message)
                print(f"✅ Mensagem enviada para cliente")
            except Exception as e:
                print(f"❌ Erro ao enviar para cliente: {e}")
                self.websocket_clients.discard(client)
                
    def start_file_watcher(self):
        """Inicia o observador de arquivos"""
        event_handler = ConfigFileHandler()
        self.file_observer = Observer()
        self.file_observer.schedule(event_handler, path=os.path.dirname(CONFIG_FILE), recursive=False)
        self.file_observer.start()
        print("👀 Observador de arquivos iniciado")

    async def event_ready(self):
        print(f'🎉 Bot connected as {self.nick}')
        self.start_file_watcher()
        await self.start_websocket_server()

    async def event_message(self, message):
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
        
        await self.broadcast_to_vue(data)
        await self.handle_commands(message)

    @commands.command()
    async def bot(self, ctx: commands.Context):
        await ctx.send("🤖 Comandos disponíveis: !bot, !github, !botcode and !chatcode, !chatvuecode")
    
    @commands.command()
    async def github(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding")
        
    @commands.command()
    async def botcode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")
    
    @commands.command()
    async def youtube(self, ctx: commands.Context):
        await ctx.send("https://www.youtube.com/@lucas-data-coding")

    @commands.command()
    async def chatcode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")
    
    @commands.command()
    async def chatvuecode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-chat-bash-theme")

async def main():
    # Iniciar Flask em uma thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Iniciar o bot Twitch
    bot = ChatBot()
    
    # Definir o bot global para o file watcher
    global global_bot
    global_bot = bot
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Desligando bot...")
        if bot.file_observer:
            bot.file_observer.stop()
            bot.file_observer.join()
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(main())